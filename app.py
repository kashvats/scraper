import csv
import io
import json
import os
import sqlite3
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from openpyxl import Workbook
from scraper import Config, crawl
from picker import router as picker_router, shutdown as close_pickers

ROOT = Path(__file__).parent
DATA = Path(os.getenv('HARVEST_DATA', ROOT / 'data'))
DATA.mkdir(parents=True, exist_ok=True)
DB = DATA / 'jobs.sqlite3'
executor = ThreadPoolExecutor(max_workers=1)
cancels = {}
lock = threading.Lock()

def db():
    connection = sqlite3.connect(DB, timeout=30)
    connection.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    return connection

def save(job):
    with db() as conn:
        conn.execute('INSERT OR REPLACE INTO jobs VALUES (?, ?)', (job['id'], json.dumps(job)))

def get(job_id):
    with db() as conn:
        item = conn.execute('SELECT payload FROM jobs WHERE id=?', (job_id,)).fetchone()
    if not item: raise HTTPException(404, 'Job not found')
    return json.loads(item[0])

@asynccontextmanager
async def lifespan(app):
    with db() as conn:
        records = conn.execute('SELECT payload FROM jobs').fetchall()
    for record in records:
        job = json.loads(record[0])
        if job['status'] in ('queued', 'running'):
            job['status'] = 'interrupted'
            save(job)
    yield
    close_pickers()
    for event in list(cancels.values()): event.set()

app = FastAPI(title='Harvest Scraper', lifespan=lifespan)
app.include_router(picker_router)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=os.getenv('HARVEST_HOSTS', 'localhost,127.0.0.1,testserver').split(','))

@app.middleware('http')
async def local_origin(request: Request, call_next):
    origin = request.headers.get('origin')
    if request.method in ('POST', 'PUT', 'DELETE') and origin and urlsplit(origin).netloc != request.headers.get('host'):
        return Response('Cross-origin writes are disabled', status_code=403)
    return await call_next(request)

def run(job, config, event):
    try:
        if event.is_set():
            job['status'] = 'cancelled'
            return
        job['status'] = 'running'
        save(job)
        def emit(rows, errors, visited, url):
            job.update(rows=list(rows), errors=list(errors), pages=visited, current_url=url)
            save(job)
        rows, errors, pages, limited = crawl(config, emit, event.is_set)
        job.update(rows=rows, errors=errors, pages=pages)
        job['status'] = 'cancelled' if event.is_set() else ('limited' if limited else ('completed_with_errors' if errors else 'completed'))
    except Exception as exc:
        job['status'] = 'failed'
        job['errors'].append({'url': config.url, 'message': str(exc)[:300] + '\n' + str(exc)[-1200:]})
    finally:
        save(job)
        with lock: cancels.pop(job['id'], None)

@app.get('/api/jobs')
def list_jobs():
    with db() as conn:
        records = conn.execute('SELECT payload FROM jobs ORDER BY rowid DESC LIMIT 30').fetchall()
    return [{k:v for k,v in json.loads(r[0]).items() if k not in ('rows','config')} | {'row_count':len(json.loads(r[0])['rows'])} for r in records]

@app.post('/api/jobs', status_code=202)
def create_job(config: Config):
    with lock:
        if len(cancels) >= 5: raise HTTPException(429, 'The queue is full. Wait for a job to finish.')
        job_id = uuid.uuid4().hex
        event = threading.Event()
        cancels[job_id] = event
    job = dict(id=job_id, config=config.model_dump(), status='queued', rows=[], errors=[], pages=0, current_url='')
    save(job)
    executor.submit(run, job, config, event)
    return {'id':job_id}

@app.get('/api/jobs/{job_id}')
def job_details(job_id: str):
    job = get(job_id)
    return {**job, 'row_count':len(job['rows']), 'rows':job['rows'][:200]}

@app.post('/api/jobs/{job_id}/cancel')
def cancel_job(job_id: str):
    get(job_id)
    with lock:
        if job_id in cancels: cancels[job_id].set()
    return {'message':'Stop requested; the current navigation may need to finish.'}

def safe_cell(value):
    text = str(value or '')
    # Prevent formulas in CSV viewers; XLSX cells are explicitly text as well.
    if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t','\r','\n')):
        text = "'" + text
    return ''.join(c for c in text if ord(c) >= 32 or c in '\t\r\n')[:32767]

@app.get('/api/jobs/{job_id}/export/{fmt}')
def export(job_id: str, fmt: str):
    if fmt not in ('csv', 'xlsx'): raise HTTPException(400, 'Choose csv or xlsx')
    job = get(job_id)
    headers = [f['name'] for f in job['config']['fields']] + ['source_url','parent_url']
    values = [[safe_cell(row.get(h,'')) for h in headers] for row in job['rows']]
    if fmt == 'csv':
        stream = io.StringIO(newline='')
        writer = csv.writer(stream)
        writer.writerow([safe_cell(h) for h in headers])
        writer.writerows(values)
        content = stream.getvalue().encode('utf-8-sig')
        mime = 'text/csv; charset=utf-8'
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = 'Results'
        for row in [[safe_cell(h) for h in headers]] + values:
            ws.append(row)
        for row in ws:
            for cell in row: cell.data_type = 's'
        ws.freeze_panes = 'A2'
        ws.auto_filter.ref = ws.dimensions
        from openpyxl.styles import Font, PatternFill
        for cell in ws[1]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='164E63')
        from openpyxl.utils import get_column_letter
        for idx, _ in enumerate(headers, 1): ws.column_dimensions[get_column_letter(idx)].width = 30
        out = io.BytesIO()
        wb.save(out)
        content, mime = out.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return Response(content, media_type=mime, headers={'Content-Disposition':f'attachment; filename="harvest-{job_id[:8]}.{fmt}"'})

@app.get('/')
def home(): return FileResponse(ROOT / 'static/index.html')

# A self-contained sample catalog for learning and offline integration tests.
@app.get('/demo/{page:path}')
def demo(page: str):
    if page.startswith('product/'):
        n = int(page.split('/')[-1]) if page.split('/')[-1].isdigit() else 1
        return Response(f'<html><h1>Sample product {n}</h1><p class="price">₹{n*150}</p><div class="description">Demonstration item {n}</div></html>', media_type='text/html')
    second = page == 'page2'
    products = [3,4] if second else [1,2]
    html = ''.join(f'<article class="product"><a href="/demo/product/{n}">View product {n}</a></article>' for n in products)
    if not second: html += '<a class="next" href="/demo/page2">Next</a>'
    return Response('<html><h1>Sample catalog</h1>'+html+'</html>',media_type='text/html')

app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
