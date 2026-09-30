"""Explicit administrator CLI; no default passwords or public registration."""
import argparse
import getpass
import json
import sqlite3
import uuid
from pathlib import Path
import auth
import settings
import store

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest='command',required=True)
    u=sub.add_parser('user');u.add_argument('email')
    d=sub.add_parser('disable-user');d.add_argument('email')
    b=sub.add_parser('backup');b.add_argument('path')
    sub.add_parser('cleanup');sub.add_parser('audit')
    args=p.parse_args();store.migrate()
    if args.command=='user':
        if '@' not in args.email or len(args.email)>254:raise SystemExit('Enter a valid email address.')
        password=getpass.getpass('Password (at least 12 characters): ')
        if len(password)<12 or len(password)>256:raise SystemExit('Password must be 12–256 characters.')
        if password!=getpass.getpass('Confirm password: '):raise SystemExit('Passwords do not match.')
        with store.connection(True) as db:
            email=args.email.lower().strip()
            db.execute('INSERT INTO users VALUES (?,?,?,0) ON CONFLICT(email) DO UPDATE SET password=excluded.password,disabled=0',(uuid.uuid4().hex,email,auth.password_hash(password)))
            uid=db.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()[0]
            db.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
            store.audit(db,uid,'admin.password-reset')
        print('Account ready; existing sessions revoked.')
    elif args.command=='disable-user':
        with store.connection(True) as db:
            db.execute('UPDATE users SET disabled=1 WHERE email=?',(args.email.lower().strip(),))
    elif args.command=='backup':
        dest=Path(args.path)
        if dest.exists():raise SystemExit('Backup destination already exists.')
        dest.parent.mkdir(parents=True,exist_ok=True)
        with store.connection() as src:
            with sqlite3.connect(dest) as target:src.backup(target)
        print('Backup complete.')
    elif args.command=='cleanup':store.cleanup();print('Retention cleanup complete.')
    else:
        with store.connection() as db:
            for r in db.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 100'):print(json.dumps(dict(r)))
if __name__=='__main__':main()
