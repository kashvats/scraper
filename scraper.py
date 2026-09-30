"""Shared traversal; interchangeable real browser engines."""
import os
import time
from collections import deque
from urllib.parse import urljoin, urlsplit, urlunsplit
from pydantic import BaseModel, Field, model_validator
from typing import Literal

class Column(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    selector: str = Field(min_length=1, max_length=500)
    attribute: str = Field(default='', max_length=80)
    multiple: bool = False

class Config(BaseModel):
    url: str
    engine: Literal['playwright', 'selenium'] = 'playwright'
    link_levels: list[str] = Field(default_factory=list, max_length=5)
    next_selector: str = ''
    row_selector: str = ''
    wait_selector: str = ''
    fields: list[Column] = Field(min_length=1, max_length=30)
    max_pages: int = Field(default=50, ge=1, le=500)
    max_rows: int = Field(default=1000, ge=1, le=10000)
    delay_ms: int = Field(default=500, ge=0, le=10000)
    settle_ms: int = Field(default=300, ge=0, le=10000)
    timeout_ms: int = Field(default=20000, ge=1000, le=60000)
    same_origin: bool = True

    @model_validator(mode='after')
    def validate_config(self):
        self.url = canonical(self.url)
        names = [f.name.strip() for f in self.fields]
        if len(set(names)) != len(names) or any(not n or n in ('source_url', 'parent_url') for n in names):
            raise ValueError('Use unique, nonempty column names; source_url and parent_url are reserved.')
        for f, n in zip(self.fields, names):
            f.name = n
        if any(not s.strip() for s in self.link_levels):
            raise ValueError('Each link level needs a CSS selector.')
        return self

def canonical(url):
    p = urlsplit(url)
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
        raise ValueError('Enter an HTTP or HTTPS URL without embedded credentials.')
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or '/', p.query, ''))

# Runs identically in both engines. CSS selection only; no user-supplied JavaScript.
EXTRACT = r'''(cfg) => {
 const links = s => s ? Array.from(document.querySelectorAll(s)).map(e => e.href || e.getAttribute('href')).filter(Boolean) : [];
 let rows = [];
 if (cfg.extract) {
   const roots = cfg.row_selector ? Array.from(document.querySelectorAll(cfg.row_selector)) : [document];
   rows = roots.slice(0, cfg.remaining).map(root => Object.fromEntries(cfg.fields.map(f => {
     const nodes = Array.from(root.querySelectorAll(f.selector));
     const chosen = f.multiple ? nodes : nodes.slice(0,1);
     const values = chosen.map(el => {
       if (!f.attribute) return (el.innerText || el.textContent || '').trim();
       const value = el.getAttribute(f.attribute) || '';
       if (value && ['href','src'].includes(f.attribute)) {try {return new URL(value, document.baseURI).href} catch {}}
       return value.trim();
     });
     return [f.name, values.join(' | ').slice(0, 32000)];
   })));
 }
 return {rows, links: links(cfg.link_selector).slice(0, 500), next: links(cfg.next_selector).slice(0,1)};
}'''

class Browser:
    def __init__(self, config):
        self.c = config
        self.driver = self.pw = self.browser = None
    def __enter__(self):
        try:
            if self.c.engine == 'playwright':
                from playwright.sync_api import sync_playwright
                self.pw = sync_playwright().start()
                options = {'headless': True}
                if os.getenv('CHROME_BINARY'):
                    options['executable_path'] = os.environ['CHROME_BINARY']
                self.browser = self.pw.chromium.launch(**options)
                self.page = self.browser.new_page()
                self.page.set_default_timeout(self.c.timeout_ms)
            else:
                from selenium import webdriver
                from selenium.webdriver.chrome.service import Service
                options = webdriver.ChromeOptions()
                options.add_argument('--headless=new')
                options.add_argument('--disable-dev-shm-usage')
                if os.getenv('CHROME_NO_SANDBOX') == '1':
                    options.add_argument('--no-sandbox')
                if os.getenv('CHROME_BINARY'):
                    options.binary_location = os.environ['CHROME_BINARY']
                service = Service(executable_path=os.environ['CHROMEDRIVER']) if os.getenv('CHROMEDRIVER') else Service()
                self.driver = webdriver.Chrome(options=options, service=service)
                self.driver.set_page_load_timeout(self.c.timeout_ms / 1000)
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise
    def visit(self, url, leaf):
        if self.c.engine == 'playwright':
            response = self.page.goto(url, wait_until='domcontentloaded', timeout=self.c.timeout_ms)
            if response and response.status >= 400:
                raise RuntimeError(f'HTTP {response.status}: {url}')
            if leaf and self.c.wait_selector:
                self.page.locator(self.c.wait_selector).first.wait_for(state='attached')
            time.sleep(self.c.settle_ms / 1000)
            return self.page.url
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        self.driver.get(url)
        if leaf and self.c.wait_selector:
            WebDriverWait(self.driver, self.c.timeout_ms / 1000).until(EC.presence_of_element_located((By.CSS_SELECTOR, self.c.wait_selector)))
        time.sleep(self.c.settle_ms / 1000)
        return self.driver.current_url
    def extract(self, cfg):
        if self.c.engine == 'playwright':
            return self.page.evaluate(EXTRACT, cfg)
        return self.driver.execute_script('return (' + EXTRACT + ')(arguments[0]);', cfg)
    def __exit__(self, *_):
        for item, method in ((self.driver, 'quit'), (self.browser, 'close'), (self.pw, 'stop')):
            if item:
                try: getattr(item, method)()
                except Exception: pass

def crawl(config, emit, cancelled, browser_factory=Browser):
    """Breadth-first crawl; next links retain depth, nested links advance depth."""
    queue = deque([(config.url, 0, '')])
    scheduled = {(config.url, 0)}
    visited_final = set()
    origin = urlsplit(config.url).netloc
    rows, errors, visited = [], [], 0
    with browser_factory(config) as browser:
        while queue and visited < config.max_pages and len(rows) < config.max_rows and not cancelled():
            url, depth, parent = queue.popleft()
            leaf = depth == len(config.link_levels)
            visited += 1
            emit(rows, errors, visited, url)
            try:
                final = canonical(browser.visit(url, leaf))
                if config.same_origin and urlsplit(final).netloc != origin:
                    raise ValueError('Redirect left the starting host; extraction skipped.')
                if (final, depth) in visited_final:
                    continue
                visited_final.add((final, depth))
                data = browser.extract({
                    'extract': leaf, 'fields': [f.model_dump() for f in config.fields],
                    'row_selector': config.row_selector, 'remaining': config.max_rows-len(rows),
                    'link_selector': '' if leaf else config.link_levels[depth],
                    'next_selector': config.next_selector,
                })
                for row in data['rows']:
                    rows.append({**row, 'source_url': final, 'parent_url': parent})
                for target, next_depth, next_parent in (
                    [(x, depth+1, final) for x in data['links']] +
                    [(x, depth, parent) for x in data['next']]
                ):
                    try: target = canonical(urljoin(final, target))
                    except ValueError: continue
                    if config.same_origin and urlsplit(target).netloc != origin: continue
                    key = (target, next_depth)
                    if key not in scheduled and len(scheduled) < 5000:
                        scheduled.add(key)
                        queue.append((target, next_depth, next_parent))
            except Exception as exc:
                errors.append({'url': url, 'message': str(exc)[:800]})
            emit(rows, errors, visited, url)
            if queue and not cancelled(): time.sleep(config.delay_ms / 1000)
    limited = bool(queue) and (visited >= config.max_pages or len(rows) >= config.max_rows)
    return rows, errors, visited, limited
