"""One isolated browser per picker; Playwright stays on its owning thread."""
import base64
import queue
import threading
import uuid
from concurrent.futures import Future, TimeoutError
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from scraper import Browser, Config, canonical

DOM = Path(__file__).with_name('picker_dom.js').read_text()
router = APIRouter(prefix='/api/picker')
sessions = {}
mutex = threading.Lock()

class Open(BaseModel):
    url: str

class Action(BaseModel):
    kind: Literal['refresh','navigate','back','scroll','select','parent','click','type','press','preview']
    url: str = ''
    x: float = Field(default=0, ge=0, le=1000)
    y: float = Field(default=0, ge=0, le=650)
    dy: int = Field(default=0, ge=-2000, le=2000)
    selector: str = Field(default='', max_length=2000)
    attribute: str = Field(default='', max_length=100)
    text: str = Field(default='', max_length=2000)
    key: Literal['Enter','Tab','Escape','Backspace','ArrowDown','ArrowUp'] = 'Enter'

class Session:
    def __init__(self, url):
        self.id = uuid.uuid4().hex
        self.url = url
        self.commands = queue.Queue(maxsize=3)
        self.ready = Future()
        self.closed = threading.Event()
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def snapshot(self, selection=None, preview=None):
        raw = self.page.screenshot(type='jpeg', quality=80, timeout=10000)
        return {'id':self.id, 'url':self.page.url, 'width':1000, 'height':650,
                'image':'data:image/jpeg;base64,'+base64.b64encode(raw).decode(),
                'selection':selection, 'preview':preview}

    def loop(self):
        try:
            c = Config(url=self.url, fields=[{'name':'unused','selector':'body'}], timeout_ms=20000)
            with Browser(c) as browser:
                self.page = browser.page
                self.page.set_viewport_size({'width':1000,'height':650})
                self.page.on('dialog', lambda dialog: dialog.dismiss())
                # Keep all normal link browsing in this one visible page.
                self.page.context.on('page', lambda popup: popup.close())
                browser.visit(self.url, False)
                self.ready.set_result(self.snapshot())
                while not self.closed.is_set():
                    try: command, future = self.commands.get(timeout=600)
                    except queue.Empty: break
                    if command is None: break
                    if future.cancelled(): continue
                    try: result = self.act(command)
                    except Exception as exc:
                        future.set_exception(exc)
                    else: future.set_result(result)
        except Exception as exc:
            if not self.ready.done(): self.ready.set_exception(exc)
        finally:
            self.closed.set()
            while True:
                try: _, pending = self.commands.get_nowait()
                except queue.Empty: break
                if pending and not pending.done(): pending.set_exception(RuntimeError('Browser session closed. Open the site again.'))
            with mutex: sessions.pop(self.id, None)

    def act(self, a):
        selection = preview = None
        if a.kind == 'navigate':
            self.page.goto(canonical(a.url), wait_until='domcontentloaded', timeout=20000)
        elif a.kind == 'back':
            self.page.go_back(wait_until='domcontentloaded', timeout=20000)
        elif a.kind == 'scroll':
            self.page.mouse.move(500,325)
            self.page.mouse.wheel(0,a.dy)
        elif a.kind in ('select','parent'):
            selection = self.page.evaluate(DOM, {'x':a.x,'y':a.y,'selector':a.selector,'parent':a.kind=='parent'})
        elif a.kind == 'click':
            # Anchors navigate their actual destination without opening hidden tabs.
            picked = self.page.evaluate(DOM, {'x':a.x,'y':a.y})
            if picked['link']:
                self.page.goto(canonical(picked['link']['url']),wait_until='domcontentloaded',timeout=20000)
            else: self.page.mouse.click(a.x,a.y)
        elif a.kind == 'type': self.page.keyboard.insert_text(a.text)
        elif a.kind == 'press': self.page.keyboard.press(a.key)
        elif a.kind == 'preview':
            preview = self.page.evaluate('''(a) => {
                const els=Array.from(document.querySelectorAll(a.selector));
                return {count:els.length,values:els.slice(0,10).map(e=>{
                  if(!a.attribute)return (e.innerText || e.textContent || '').trim().slice(0,2000);
                  const v=e.getAttribute(a.attribute)||'';
                  return v && ['src','href'].includes(a.attribute)?new URL(v,document.baseURI).href:v;
                })};
            }''',a.model_dump())
        if a.kind not in ('select','parent','preview'): self.page.wait_for_timeout(350)
        return self.snapshot(selection,preview)

    def submit(self, command):
        if self.closed.is_set(): raise HTTPException(410,'Browser session closed. Open the site again.')
        future=Future()
        try: self.commands.put_nowait((command,future))
        except queue.Full: raise HTTPException(429,'Browser is busy. Wait for the current action.')
        try:return future.result(timeout=45)
        except TimeoutError: raise HTTPException(504,'Browser action timed out. Refresh or reopen the site.')
        except Exception as exc: raise HTTPException(400,str(exc)[-1000:])

    def close(self):
        self.closed.set()
        try:self.commands.put_nowait((None,None))
        except queue.Full:pass

@router.post('')
def open_browser(body: Open):
    try:url=canonical(body.url)
    except ValueError as exc:raise HTTPException(422,str(exc))
    with mutex:
        if len(sessions)>=2:raise HTTPException(429,'Close an existing site view first (maximum two).')
        s=Session(url)
        sessions[s.id]=s
    try:return s.ready.result(timeout=45)
    except Exception as exc:
        s.close()
        raise HTTPException(400,'Could not open the browser. Check the browser installation. '+str(exc)[-1000:])

@router.post('/{session_id}/action')
def action(session_id: str, body: Action):
    with mutex:s=sessions.get(session_id)
    if not s:raise HTTPException(410,'Browser session expired. Open the site again.')
    return s.submit(body)

@router.delete('/{session_id}')
def close_browser(session_id: str):
    with mutex:s=sessions.get(session_id)
    if s:s.close()
    return {'closed':True}

def shutdown():
    with mutex: current=list(sessions.values())
    for s in current:s.close()
