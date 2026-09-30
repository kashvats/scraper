"""Single-host SQLite WAL store. Explicit transactions and fencing for workers."""
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
import settings

@contextmanager
def connection(write=False):
    settings.DATA.mkdir(parents=True, exist_ok=True)
    db=sqlite3.connect(settings.DB, timeout=30)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=30000')
    try:
        if write:db.execute('BEGIN IMMEDIATE')
        yield db
        if write:db.commit()
    except Exception:
        if write:db.rollback()
        raise
    finally:db.close()

def migrate():
    with connection() as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL,disabled INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,csrf TEXT NOT NULL,expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS rates(key TEXT PRIMARY KEY,count INTEGER NOT NULL,expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,owner TEXT NOT NULL REFERENCES users(id),config TEXT NOT NULL,status TEXT NOT NULL,created REAL NOT NULL,updated REAL NOT NULL,lease TEXT,heartbeat REAL,pages INTEGER NOT NULL DEFAULT 0,row_count INTEGER NOT NULL DEFAULT 0,errors TEXT NOT NULL DEFAULT '[]',checkpoint TEXT,cancel INTEGER NOT NULL DEFAULT 0,current_url TEXT NOT NULL DEFAULT '',failure TEXT NOT NULL DEFAULT '');
        CREATE INDEX IF NOT EXISTS jobs_owner_created ON jobs(owner,created DESC);
        CREATE INDEX IF NOT EXISTS jobs_status ON jobs(status,created);
        CREATE TABLE IF NOT EXISTS results(job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,seq INTEGER NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(job_id,seq));
        CREATE TABLE IF NOT EXISTS templates(id TEXT PRIMARY KEY,owner TEXT NOT NULL REFERENCES users(id),name TEXT NOT NULL,config TEXT NOT NULL,updated REAL NOT NULL,UNIQUE(owner,name));
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,at REAL NOT NULL,owner TEXT,action TEXT NOT NULL,resource TEXT);
        CREATE TABLE IF NOT EXISTS worker_health(id TEXT PRIMARY KEY,seen REAL NOT NULL);
        PRAGMA user_version=1;
        ''')
        db.execute("INSERT OR IGNORE INTO users(id,email,password,disabled) VALUES ('local','local','',0)")

def audit(db,owner,action,resource=''):
    db.execute('INSERT INTO audit(at,owner,action,resource) VALUES (?,?,?,?)',(time.time(),owner,action,resource))

def rate(key,limit,window):
    now=time.time()
    with connection(True) as db:
        db.execute('DELETE FROM rates WHERE expires<?',(now,))
        row=db.execute('SELECT count FROM rates WHERE key=?',(key,)).fetchone()
        if row and row['count']>=limit:return False
        db.execute('INSERT INTO rates VALUES (?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1',(key,now+window))
    return True

def create_job(owner,config):
    now=time.time();jid=uuid.uuid4().hex
    with connection(True) as db:
        count=db.execute("SELECT count(*) FROM jobs WHERE owner=? AND status IN ('queued','running')",(owner,)).fetchone()[0]
        total=db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]
        if count>=5 or total>=100:raise ValueError('Queue limit reached. Wait for an active job to finish.')
        db.execute('INSERT INTO jobs(id,owner,config,status,created,updated) VALUES (?,?,?,?,?,?)',(jid,owner,json.dumps(config),'queued',now,now))
        audit(db,owner,'job.create',jid)
    return jid

def get_job(jid,owner=None):
    with connection() as db:
        row=db.execute('SELECT * FROM jobs WHERE id=?'+(' AND owner=?' if owner else ''),(jid,owner) if owner else (jid,)).fetchone()
    return decode(row) if row else None

def decode(row):
    d=dict(row)
    for k in ('config','errors','checkpoint'):
        if k in d:d[k]=json.loads(d[k]) if d[k] else None
    return d

def claim(worker_id):
    now=time.time()
    with connection(True) as db:
        db.execute('INSERT INTO worker_health VALUES (?,?) ON CONFLICT(id) DO UPDATE SET seen=excluded.seen',(worker_id,now))
        # An old worker cannot commit after recovery: every write checks its lease token.
        db.execute("UPDATE jobs SET status=CASE WHEN cancel=1 THEN 'cancelled' ELSE 'queued' END,lease=NULL,updated=? WHERE status='running' AND heartbeat<?",(now,now-90))
        row=db.execute("SELECT id FROM jobs WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
        if not row:return None
        token=uuid.uuid4().hex
        db.execute("UPDATE jobs SET status='running',lease=?,heartbeat=?,updated=? WHERE id=?",(token,now,now,row['id']))
    return get_job(row['id'])

def heartbeat(jid,token,worker_id):
    now=time.time()
    with connection(True) as db:
        db.execute('INSERT INTO worker_health VALUES (?,?) ON CONFLICT(id) DO UPDATE SET seen=excluded.seen',(worker_id,now))
        cur=db.execute("UPDATE jobs SET heartbeat=? WHERE id=? AND lease=? AND status='running'",(now,jid,token))
        return cur.rowcount==1

def checkpoint(jid,token,state,new_rows,errors,pages,url):
    with connection(True) as db:
        row=db.execute("SELECT row_count FROM jobs WHERE id=? AND lease=? AND status='running'",(jid,token)).fetchone()
        if not row:raise RuntimeError('Job lease lost')
        offset=row['row_count']
        db.executemany('INSERT INTO results VALUES (?,?,?)',[(jid,offset+i,json.dumps(r)) for i,r in enumerate(new_rows)])
        db.execute('UPDATE jobs SET checkpoint=?,row_count=?,errors=?,pages=?,current_url=?,updated=? WHERE id=? AND lease=?',
            (json.dumps(state),offset+len(new_rows),json.dumps(errors),pages,url,time.time(),jid,token))

def finish(jid,token,status,failure=''):
    with connection(True) as db:
        db.execute("UPDATE jobs SET status=CASE WHEN cancel=1 THEN 'cancelled' ELSE ? END,failure=?,updated=?,lease=NULL WHERE id=? AND lease=?",(status,failure,time.time(),jid,token))

def cancelled(jid,token):
    j=get_job(jid)
    return not j or j['cancel'] or j['lease']!=token

def cleanup():
    now=time.time()
    with connection(True) as db:
        db.execute('DELETE FROM sessions WHERE expires<?',(now,))
        db.execute('DELETE FROM rates WHERE expires<?',(now,))
        db.execute("DELETE FROM jobs WHERE updated<? AND status NOT IN ('queued','running')",(now-settings.RETENTION_DAYS*86400,))
        db.execute('DELETE FROM audit WHERE at<?',(now-90*86400,))
