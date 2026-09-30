"""Run separately from the API: python worker.py. One supervised browser job at a time."""
import logging
import multiprocessing
import os
import signal
import threading
import time
import uuid
import settings
import store
from scraper import Config, crawl

log=logging.getLogger('harvest.worker')

def execute(jid,token):
    if hasattr(os,'setsid'):os.setsid()
    job=store.get_job(jid)
    if not job or job['lease']!=token:return
    sent=0
    def save(state,rows,errors,pages,url):
        nonlocal sent
        store.checkpoint(jid,token,state,rows[sent:],errors,pages,url)
        sent=len(rows)
    try:
        _, errors, _, limited=crawl(Config(**job['config']),lambda *a:None,lambda:store.cancelled(jid,token),
                                    checkpoint=job['checkpoint'],on_checkpoint=save)
        store.finish(jid,token,'limited' if limited else ('completed_with_errors' if errors else 'completed'))
    except Exception:
        log.exception('job.failed id=%s',jid)
        store.finish(jid,token,'failed','Browser execution failed. Check worker logs for this job ID; saved results are retained.')

def terminate(child):
    if not child.is_alive():return
    try:
        if hasattr(os,'killpg'):os.killpg(child.pid,signal.SIGTERM)
        else:child.terminate()
    except ProcessLookupError:
        if child.is_alive():child.terminate()
    child.join(5)
    if child.is_alive():
        try:
            if hasattr(os,'killpg'):os.killpg(child.pid,signal.SIGKILL)
            else:child.kill()
        except ProcessLookupError:pass
        child.join(2)

def main():
    settings.validate();store.migrate()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(name)s %(message)s')
    stop=threading.Event()
    for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,lambda *_:stop.set())
    wid=uuid.uuid4().hex;ctx=multiprocessing.get_context('spawn');last_cleanup=0
    while not stop.is_set():
        if time.time()-last_cleanup>3600:store.cleanup();last_cleanup=time.time()
        job=store.claim(wid)
        if not job:stop.wait(1);continue
        log.info('job.start id=%s',job['id'])
        child=ctx.Process(target=execute,args=(job['id'],job['lease']));child.start()
        start=time.monotonic();lastbeat=0
        while child.is_alive() and not stop.is_set():
            if time.monotonic()-lastbeat>5:
                if not store.heartbeat(job['id'],job['lease'],wid):break
                lastbeat=time.monotonic()
            if store.cancelled(job['id'],job['lease']):break
            if time.monotonic()-start>settings.MAX_JOB_SECONDS:break
            child.join(.5)
        if child.is_alive():
            terminate(child)
            if stop.is_set():store.finish(job['id'],job['lease'],'queued')
            elif store.cancelled(job['id'],job['lease']):store.finish(job['id'],job['lease'],'cancelled')
            else:store.finish(job['id'],job['lease'],'failed','Job exceeded its execution budget or lost its lease. Resume to continue from the last saved page.')
        else:
            child.join()
            if child.exitcode:store.finish(job['id'],job['lease'],'failed','Worker process exited unexpectedly. Resume from the last saved page.')
        log.info('job.end id=%s',job['id'])
if __name__=='__main__':main()
