import csv
import io
import json
import logging
import os
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from urllib.parse import urlsplit
from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.responses import FileResponse, Response, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
import settings
import store
from auth import router as auth_router, current_user
from scraper import Config
from picker import router as picker_router, shutdown as close_pickers, startup as start_pickers

logging.basicConfig(level=logging.INFO,format='%(message)s')
log=logging.getLogger('harvest.api')

@asynccontextmanager
async def lifespan(app):
    settings.validate();store.migrate()
    handle=None
    # Picker sessions are local to one API process. Refuse a second process on this data directory.
    if os.name=='posix':
        import fcntl
        handle=open(settings.DATA/'api.lock','w')
        try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close();raise RuntimeError('Use one API process per data directory. Scale scraping workers separately.')
    start_pickers()
    yield
    close_pickers()
    if handle:handle.close()

app=FastAPI(title='Harvest',version='0.3.0',lifespan=lifespan,docs_url=None if settings.PRODUCTION else '/docs',redoc_url=None)
app.include_router(auth_router)
app.include_router(picker_router)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=list({urlsplit(settings.PUBLIC_ORIGIN).hostname,'localhost','127.0.0.1','testserver'}))

@app.middleware('http')
async def boundaries(request: Request,call_next):
    started=time.monotonic();request_id=uuid.uuid4().hex
    if request.method in ('POST','PUT','PATCH','DELETE'):
        origin=request.headers.get('origin')
        if origin and origin!=settings.PUBLIC_ORIGIN:return JSONResponse({'detail':'Cross-origin request blocked.'},403)
        chunks=[];size=0
        async for chunk in request.stream():
            size+=len(chunk)
            if size>1024*1024:return JSONResponse({'detail':'Request too large.'},413)
            chunks.append(chunk)
        request._body=b''.join(chunks)
    try:response=await call_next(request)
    except Exception:
        log.exception('request.failed id=%s',request_id)
        response=JSONResponse({'detail':'Unexpected server error. Reference: '+request_id},500)
    response.headers.update({'X-Request-ID':request_id,'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer',
      'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"})
    if request.url.path.startswith('/api/'):response.headers['Cache-Control']='no-store'
    if settings.COOKIE_SECURE:response.headers['Strict-Transport-Security']='max-age=31536000'
    log.info(json.dumps({'request_id':request_id,'method':request.method,'path':request.url.path,'status':response.status_code,'ms':round((time.monotonic()-started)*1000)}))
    return response

@app.get('/health/live')
def live():return {'status':'ok'}

@app.get('/health/ready')
def ready():
    try:
        with store.connection() as db:
            seen=db.execute('SELECT max(seen) FROM worker_health').fetchone()[0]
    except Exception:return JSONResponse({'status':'not_ready'},503)
    healthy=bool(seen and seen>time.time()-30)
    return JSONResponse({'status':'ready' if healthy else 'worker_unavailable'},200 if healthy else 503)

@app.get('/api/settings')
def config_info(user=Depends(current_user)):
    return {'demo_url':settings.DEMO_URL,'max_pages':500,'max_rows':10000,'retention_days':settings.RETENTION_DAYS}

def owned(jid,user):
    job=store.get_job(jid,user['id'])
    if not job:raise HTTPException(404,'Job not found.')
    return job

def public_job(job):
    return {k:job[k] for k in ('id','status','created','updated','pages','row_count','errors','current_url','failure','config')}

@app.get('/api/jobs')
def list_jobs(user=Depends(current_user),offset:int=Query(default=0,ge=0)):
    with store.connection() as db:rows=db.execute('SELECT * FROM jobs WHERE owner=? ORDER BY created DESC LIMIT 30 OFFSET ?',(user['id'],offset)).fetchall()
    return [public_job(store.decode(r)) for r in rows]

@app.post('/api/jobs',status_code=202)
def create_job(config: Config,user=Depends(current_user)):
    if not store.rate('jobs:'+user['id'],30,3600):raise HTTPException(429,'Hourly job limit reached.')
    try:jid=store.create_job(user['id'],config.model_dump())
    except ValueError as exc:raise HTTPException(429,str(exc))
    return {'id':jid}

@app.get('/api/jobs/{jid}')
def job_details(jid:str,user=Depends(current_user),offset:int=Query(default=0,ge=0)):
    job=owned(jid,user)
    with store.connection() as db:rows=db.execute('SELECT payload FROM results WHERE job_id=? ORDER BY seq LIMIT 200 OFFSET ?',(jid,offset)).fetchall()
    return {**public_job(job),'rows':[json.loads(r[0]) for r in rows],'offset':offset}

@app.post('/api/jobs/{jid}/cancel')
def cancel_job(jid:str,user=Depends(current_user)):
    owned(jid,user)
    with store.connection(True) as db:
        db.execute("UPDATE jobs SET cancel=1,status=CASE WHEN status='queued' THEN 'cancelled' ELSE status END,updated=? WHERE id=? AND status IN ('running','queued')",(time.time(),jid))
        store.audit(db,user['id'],'job.cancel',jid)
    return {'message':'Cancellation requested. Saved results are retained.'}

@app.post('/api/jobs/{jid}/resume',status_code=202)
def resume(jid:str,user=Depends(current_user)):
    job=owned(jid,user)
    if job['status'] not in ('failed','cancelled'):raise HTTPException(409,'Only failed or cancelled jobs can resume. Use a new run to change limits.')
    with store.connection(True) as db:
        n=db.execute("SELECT count(*) FROM jobs WHERE owner=? AND status IN ('queued','running')",(user['id'],)).fetchone()[0]
        if n>=5:raise HTTPException(429,'Queue limit reached.')
        cur=db.execute("UPDATE jobs SET status='queued',cancel=0,lease=NULL,failure='',updated=? WHERE id=? AND status IN ('failed','cancelled')",(time.time(),jid))
        if not cur.rowcount:raise HTTPException(409,'Job state changed. Refresh and try again.')
        store.audit(db,user['id'],'job.resume',jid)
    return {'id':jid}

@app.delete('/api/jobs/{jid}')
def delete_job(jid:str,user=Depends(current_user)):
    owned(jid,user)
    with store.connection(True) as db:
        state=db.execute('SELECT status FROM jobs WHERE id=?',(jid,)).fetchone()
        if state and state['status'] in ('queued','running'):raise HTTPException(409,'Stop the job before deleting it.')
        db.execute('DELETE FROM jobs WHERE id=?',(jid,));store.audit(db,user['id'],'job.delete',jid)
    return {'ok':True}

def safe_cell(value):
    text='' if value is None else str(value)
    if text.lstrip().startswith(('=','+','-','@')) or text.startswith(('\t','\r','\n')):text="'"+text
    return ''.join(c for c in text if ord(c)>=32 or c in '\t\r\n')[:32767]

def result_rows(jid,count):
    with store.connection() as db:
        for row in db.execute('SELECT payload FROM results WHERE job_id=? AND seq<? ORDER BY seq',(jid,count)):yield json.loads(row[0])

@app.get('/api/jobs/{jid}/export/{fmt}')
def export(jid:str,fmt:str,user=Depends(current_user)):
    if fmt not in ('csv','xlsx'):raise HTTPException(400,'Choose csv or xlsx.')
    job=owned(jid,user)
    headers=[f['name'] for f in job['config']['fields']]+['source_url','parent_url']
    with store.connection(True) as db:store.audit(db,user['id'],'job.export.'+fmt,jid)
    disposition={'Content-Disposition':f'attachment; filename="harvest-{jid[:8]}.{fmt}"'}
    if fmt=='csv':
        def generate():
            yield '\ufeff'
            buffer=io.StringIO(newline='');writer=csv.writer(buffer)
            writer.writerow([safe_cell(h) for h in headers]);yield buffer.getvalue();buffer.seek(0);buffer.truncate(0)
            for row in result_rows(jid,job['row_count']):
                writer.writerow([safe_cell(row.get(h,'')) for h in headers]);yield buffer.getvalue();buffer.seek(0);buffer.truncate(0)
        return StreamingResponse(generate(),media_type='text/csv; charset=utf-8',headers=disposition)
    wb=Workbook(write_only=True);ws=wb.create_sheet('Results');ws.freeze_panes='A2'
    def append(values):
        cells=[]
        for value in values:
            c=WriteOnlyCell(ws,safe_cell(value));c.data_type='s';cells.append(c)
        ws.append(cells)
    append(headers)
    for row in result_rows(jid,job['row_count']):append([row.get(h,'') for h in headers])
    fd,path=tempfile.mkstemp(suffix='.xlsx');os.close(fd)
    try:wb.save(path)
    except Exception:os.unlink(path);raise
    return FileResponse(path,filename=f'harvest-{jid[:8]}.xlsx',media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',background=BackgroundTask(os.unlink,path))

class Template(BaseModel):
    name:str=Field(min_length=1,max_length=120)
    config:Config

@app.get('/api/templates')
def templates(user=Depends(current_user)):
    with store.connection() as db:rows=db.execute('SELECT id,name,config,updated FROM templates WHERE owner=? ORDER BY updated DESC',(user['id'],)).fetchall()
    return [{**dict(r),'config':json.loads(r['config'])} for r in rows]

@app.post('/api/templates')
def save_template(body:Template,user=Depends(current_user)):
    with store.connection(True) as db:
        count=db.execute('SELECT count(*) FROM templates WHERE owner=?',(user['id'],)).fetchone()[0]
        exists=db.execute('SELECT id FROM templates WHERE owner=? AND name=?',(user['id'],body.name)).fetchone()
        if count>=100 and not exists:raise HTTPException(429,'Maximum 100 saved scrapers.')
        tid=exists['id'] if exists else uuid.uuid4().hex
        db.execute('INSERT INTO templates VALUES (?,?,?,?,?) ON CONFLICT(owner,name) DO UPDATE SET config=excluded.config,updated=excluded.updated',(tid,user['id'],body.name,json.dumps(body.config.model_dump()),time.time()))
        store.audit(db,user['id'],'template.save',tid)
    return {'id':tid}

@app.delete('/api/templates/{tid}')
def delete_template(tid:str,user=Depends(current_user)):
    with store.connection(True) as db:
        db.execute('DELETE FROM templates WHERE id=? AND owner=?',(tid,user['id']));store.audit(db,user['id'],'template.delete',tid)
    return {'ok':True}

@app.get('/')
def home():return FileResponse(settings.ROOT/'static/index.html')
app.mount('/static',StaticFiles(directory=settings.ROOT/'static'),name='static')
