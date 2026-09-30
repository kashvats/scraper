"""Owner-scoped browser sessions in supervised child processes."""
import base64
import logging
import multiprocessing
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from auth import current_user
from scraper import Browser, Config, canonical
from worker import terminate
import store

DOM=Path(__file__).with_name('picker_dom.js').read_text()
router=APIRouter(prefix='/api/picker')
sessions={};mutex=threading.Lock();stop_reaper=threading.Event()
log=logging.getLogger('harvest.picker')

class Open(BaseModel):
    url:str=Field(max_length=4096)
class Action(BaseModel):
    kind:Literal['refresh','navigate','back','scroll','select','parent','click','type','press','preview']
    revision:int=Field(default=0,ge=0)
    url:str=Field(default='',max_length=4096)
    x:float=Field(default=0,ge=0,le=1000)
    y:float=Field(default=0,ge=0,le=650)
    dy:int=Field(default=0,ge=-2000,le=2000)
    selector:str=Field(default='',max_length=2000)
    attribute:str=Field(default='',max_length=100)
    text:str=Field(default='',max_length=2000)
    key:Literal['Enter','Tab','Escape','Backspace','ArrowDown','ArrowUp']='Enter'

class PageSession:
    def __init__(self,page,sid):self.page=page;self.id=sid;self.revision=0
    def snapshot(self,selection=None,preview=None):
        raw=self.page.screenshot(type='jpeg',quality=80,timeout=10000)
        self.revision+=1
        return {'id':self.id,'url':self.page.url,'width':1000,'height':650,'revision':self.revision,
                'image':'data:image/jpeg;base64,'+base64.b64encode(raw).decode(),'selection':selection,'preview':preview}
    def act(self,a):
        if a.revision!=self.revision and a.kind!='refresh':raise ValueError('The site view changed. Refresh it before selecting again.')
        selection=preview=None
        if a.kind=='navigate':self.page.goto(canonical(a.url),wait_until='domcontentloaded',timeout=20000)
        elif a.kind=='back':self.page.go_back(wait_until='domcontentloaded',timeout=20000)
        elif a.kind=='scroll':self.page.mouse.move(500,325);self.page.mouse.wheel(0,a.dy)
        elif a.kind in ('select','parent'):
            selection=self.page.evaluate(DOM,{'x':a.x,'y':a.y,'selector':a.selector,'parent':a.kind=='parent'})
        elif a.kind=='click':
            picked=self.page.evaluate(DOM,{'x':a.x,'y':a.y})
            if picked['link']:self.page.goto(canonical(picked['link']['url']),wait_until='domcontentloaded',timeout=20000)
            else:self.page.mouse.click(a.x,a.y)
        elif a.kind=='type':self.page.keyboard.insert_text(a.text)
        elif a.kind=='press':self.page.keyboard.press(a.key)
        elif a.kind=='preview':
            preview=self.page.evaluate('''(a)=>{
              const els=Array.from(document.querySelectorAll(a.selector));
              return {count:els.length,values:els.slice(0,10).map(e=>{
                if(!a.attribute)return (e.innerText||e.textContent||'').trim().slice(0,2000);
                const v=e.getAttribute(a.attribute)||'';
                return v&&['src','href'].includes(a.attribute)?new URL(v,document.baseURI).href:v;
              })};
            }''',a.model_dump())
        if a.kind not in ('select','parent','preview'):self.page.wait_for_timeout(350)
        return self.snapshot(selection,preview)

def browser_process(pipe,url,sid):
    if hasattr(os,'setsid'):os.setsid()
    try:
        c=Config(url=url,fields=[{'name':'unused','selector':'body'}],timeout_ms=20000)
        with Browser(c) as browser:
            page=browser.page;page.set_viewport_size({'width':1000,'height':650})
            page.on('dialog',lambda d:d.dismiss())
            page.context.on('page',lambda p:p.close())
            browser.visit(url,False)
            session=PageSession(page,sid)
            pipe.send({'data':session.snapshot()})
            opened=time.monotonic()
            while time.monotonic()-opened<1800 and pipe.poll(600):
                command=pipe.recv()
                if command is None:break
                try:pipe.send({'data':session.act(Action(**command))})
                except Exception:
                    log.exception('picker.action-failed session=%s',sid)
                    pipe.send({'error':'Could not complete the action. Refresh the view, check the selection, or reopen the site.'})
    except Exception:
        log.exception('picker.browser-failed session=%s',sid)
        try:pipe.send({'error':'Browser could not start or open this site. Check browser installation, network policy and server logs.'})
        except (BrokenPipeError,EOFError,OSError):pass
    finally:pipe.close()

class Session:
    def __init__(self,url,owner):
        self.id=uuid.uuid4().hex;self.owner=owner;self.last_used=time.monotonic();self.created=self.last_used
        self.lock=threading.Lock();self.closed=False
        ctx=multiprocessing.get_context('spawn')
        self.pipe,child_pipe=ctx.Pipe()
        self.process=ctx.Process(target=browser_process,args=(child_pipe,url,self.id))
        self.process.start();child_pipe.close()
    def receive(self):
        if not self.pipe.poll(45):self.close();raise HTTPException(504,'Browser timed out and was closed. Open the site again.')
        try:r=self.pipe.recv()
        except (EOFError,OSError):self.close();raise HTTPException(410,'Browser closed. Open the site again.')
        if 'error' in r:raise HTTPException(400,r['error'])
        return r['data']
    def submit(self,a):
        if not self.lock.acquire(blocking=False):raise HTTPException(409,'The browser is busy.')
        try:
            if self.closed:raise HTTPException(410,'Browser closed. Open the site again.')
            self.last_used=time.monotonic()
            try:self.pipe.send(a.model_dump())
            except (EOFError,OSError):raise HTTPException(410,'Browser closed. Open the site again.')
            return self.receive()
        finally:self.lock.release()
    def close(self):
        if self.closed:return
        self.closed=True
        terminate(self.process);self.pipe.close()

def find(sid,owner):
    with mutex:s=sessions.get(sid)
    if not s or s.owner!=owner:raise HTTPException(404,'Browser session not found or expired.')
    return s

@router.post('')
def open_browser(body:Open,user=Depends(current_user)):
    try:url=canonical(body.url)
    except ValueError as exc:raise HTTPException(422,str(exc))
    if not store.rate('picker:'+user['id'],30,3600):raise HTTPException(429,'Browser session rate limit reached.')
    with mutex:
        if len(sessions)>=2 or any(s.owner==user['id'] for s in sessions.values()):raise HTTPException(429,'Close your current site view, or wait for a browser slot.')
        s=Session(url,user['id']);sessions[s.id]=s
    try:return s.receive()
    except Exception:
        s.close()
        with mutex:sessions.pop(s.id,None)
        raise

@router.post('/{sid}/action')
def action(sid:str,body:Action,user=Depends(current_user)):
    return find(sid,user['id']).submit(body)

@router.delete('/{sid}')
def close_browser(sid:str,user=Depends(current_user)):
    s=find(sid,user['id']);s.close()
    with mutex:sessions.pop(sid,None)
    return {'closed':True}

def reaper():
    while not stop_reaper.wait(15):
        with mutex:current=list(sessions.values())
        for s in current:
            if s.closed or not s.process.is_alive() or time.monotonic()-s.last_used>600 or time.monotonic()-s.created>1800:
                s.close()
                with mutex:sessions.pop(s.id,None)

def startup():
    stop_reaper.clear();threading.Thread(target=reaper,daemon=True).start()
def shutdown():
    stop_reaper.set()
    with mutex:current=list(sessions.values());sessions.clear()
    for s in current:s.close()
