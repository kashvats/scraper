"""Live acceptance against the Docker stack. Run only against a disposable test instance.
HARVEST_TEST_EMAIL / HARVEST_TEST_PASSWORD must name a pre-created account.
"""
import csv
import io
import os
import time
from pathlib import Path
import httpx
from openpyxl import load_workbook
from playwright.sync_api import sync_playwright

BASE=os.getenv('HARVEST_TEST_URL','http://localhost:8000')
EMAIL=os.environ['HARVEST_TEST_EMAIL'];PASSWORD=os.environ['HARVEST_TEST_PASSWORD']

def run():
    with httpx.Client(base_url=BASE,trust_env=False,timeout=60) as client:
        for _ in range(60):
            try:
                if client.get('/health/ready').status_code==200:break
            except httpx.HTTPError:pass
            time.sleep(1)
        else:raise AssertionError('Stack not ready')
        r=client.post('/api/auth/login',json={'email':EMAIL,'password':PASSWORD});r.raise_for_status()
        client.headers['X-CSRF-Token']=r.json()['csrf']
        demo=client.get('/api/settings').json()['demo_url']
        for engine in ('playwright','selenium'):
            c={'url':demo,'engine':engine,'link_levels':['.product a'],'next_selector':'a.next',
               'fields':[{'name':'Product Name','selector':'h1'},{'name':'Price','selector':'.price'}],'delay_ms':100}
            r=client.post('/api/jobs',json=c);r.raise_for_status();jid=r.json()['id']
            for _ in range(120):
                j=client.get('/api/jobs/'+jid).json()
                if j['status'] not in ('queued','running'):break
                time.sleep(.5)
            assert j['status']=='completed',j
            assert j['pages']==6 and j['row_count']==4,j
            data=client.get(f'/api/jobs/{jid}/export/csv');assert len(list(csv.reader(io.StringIO(data.content.decode('utf-8-sig')))))==5
            wb=load_workbook(io.BytesIO(client.get(f'/api/jobs/{jid}/export/xlsx').content));assert wb.active.max_row==5
            # Restarting the API must not erase the job: covered separately in deployment acceptance.
            print(engine,'PASS: six pages, four products, CSV and XLSX')
        # A known private/metadata URL must fail through the egress policy.
        for url in ('http://169.254.169.254/latest/meta-data/','http://api:8000/health/live'):
            r=client.post('/api/jobs',json={'url':url,'fields':[{'name':'body','selector':'body'}],'max_pages':1,'timeout_ms':5000,'retries':0})
            r.raise_for_status();jid=r.json()['id']
            for _ in range(40):
                j=client.get('/api/jobs/'+jid).json()
                if j['status'] not in ('queued','running'):break
                time.sleep(.5)
            assert j['row_count']==0 and j['status'] in ('failed','completed_with_errors'),j
    Path('test-artifacts').mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,chromium_sandbox=True)
        page=browser.new_page(viewport={'width':1440,'height':1100});errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(BASE);page.locator('#login-email').fill(EMAIL);page.locator('#login-password').fill(PASSWORD)
        page.locator('#login-submit').click();page.locator('#app-shell').wait_for(state='visible')
        page.locator('#sample').click();page.wait_for_function("document.querySelector('#site-image').naturalWidth>0",timeout=60000)
        # DOM fixture heading is at x40,y~60 in a 1000x650 remote viewport.
        img=page.locator('#site-image');box=img.bounding_box()
        page.mouse.click(box['x']+150*box['width']/1000,box['y']+95*box['height']/650)
        page.locator('#selection-details').wait_for(state='visible')
        assert page.locator('#picked-value').inner_text()=='Sample catalog'
        page.locator('#picked-name').fill('Catalog Heading');page.locator('#save-selection').click()
        assert page.locator('[data-key="name"]').input_value()=='Catalog Heading'
        page.screenshot(path='test-artifacts/desktop.png',full_page=True)
        page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path='test-artifacts/mobile.png',full_page=True)
        page.locator('#close-browser').click();assert not errors,errors
        browser.close()
        print('Visual picker PASS: browser screenshot, coordinate selection, custom column and responsive layout')
if __name__=='__main__':run()
