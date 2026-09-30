import io
import os
import tempfile
os.environ['HARVEST_DATA'] = tempfile.mkdtemp()
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from app import app, save
from scraper import Config, crawl
import pytest

def config(**kw):
    return Config(url='https://shop.example/',fields=[{'name':'title','selector':'h1'}],delay_ms=0,**kw)
class FakeBrowser:
    def __init__(self,c): self.url=''
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def visit(self,url,leaf):self.url=url;return url
    def extract(self,c):
        if self.url.endswith('/'):return {'rows':[], 'links':['/category','/category#duplicate'],'next':[]}
        if self.url.endswith('/category'):return {'rows':[], 'links':['/product/1'],'next':['/category?page=2']}
        if 'page=2' in self.url:return {'rows':[], 'links':['/product/1','/product/2'],'next':['/category']}
        return {'rows':[{'title':self.url.rsplit('/',1)[-1]}], 'links':[], 'next':[]}
def test_nested_pagination_dedupe():
    rows, errors, pages, limited=crawl(config(link_levels=['.category','.product']),lambda *a:None,lambda:False,FakeBrowser)
    assert [r['title'] for r in rows]==['1','2']
    assert pages==5 and not errors and not limited
    assert rows[0]['parent_url']=='https://shop.example/category'
def test_limits_and_cancel():
    rows,_,pages,limited=crawl(config(link_levels=['.category','.product'],max_pages=2),lambda *a:None,lambda:False,FakeBrowser)
    assert pages==2 and limited and not rows
    rows,_,pages,_=crawl(config(),lambda *a:None,lambda:True,FakeBrowser)
    assert pages==0
def test_validation():
    with pytest.raises(ValueError):Config(url='file:///etc/passwd',fields=[{'name':'x','selector':'h1'}])
    with pytest.raises(ValueError):Config(url='https://example.com',fields=[{'name':'source_url','selector':'h1'}])
def test_exports_and_origin():
    save({'id':'test','config':config().model_dump(),'rows':[{'title':'=1+2','source_url':'https://shop.example/','parent_url':''}],'status':'completed','errors':[],'pages':1})
    with TestClient(app) as c:
        csv=c.get('/api/jobs/test/export/csv')
        assert csv.status_code==200 and "'=1+2" in csv.content.decode('utf-8-sig')
        wb=load_workbook(io.BytesIO(c.get('/api/jobs/test/export/xlsx').content))
        assert wb.active['A2'].data_type=='s' and wb.active['A2'].value=="'=1+2"
        assert c.post('/api/jobs',json=config().model_dump(),headers={'origin':'https://evil.example'}).status_code==403
        assert c.get('/api/jobs/missing').status_code==404
        assert c.get('/').status_code==200

def test_picker_request_validation():
    with TestClient(app) as c:
        assert c.post('/api/picker',json={'url':'file:///etc/passwd'}).status_code==422
        assert c.post('/api/picker/expired/action',json={'kind':'select','x':10,'y':10}).status_code==410
        assert c.post('/api/picker/expired/action',json={'kind':'select','x':1001,'y':10}).status_code==422
        assert c.post('/api/picker',json={'url':'https://example.com'},headers={'origin':'https://evil.example'}).status_code==403
        assert c.delete('/api/picker/expired').status_code==200
