"""Production dashboard smoke against permitted local job fixtures; no models/reference."""
import json
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright, expect
from adapter.png import ROOT

class UI(unittest.TestCase):
    def test_local_jobs_and_recorded_playback_stay_distinct(self):
        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self,*args): pass
        s=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT/'dashboard/dist')))
        t=threading.Thread(target=s.serve_forever,daemon=True); t.start()
        try:
            with sync_playwright() as p:
                b=p.chromium.launch(headless=True); page=b.new_page(viewport={'width':1440,'height':1000})
                fixture={'pilot_enabled':False,'jobs':[{'id':'a'*32,'request':'Implement Contrast','status':'unresolved','stage':'Discover','activity':'Offline fixture: missing visible control domain','elapsed_seconds':12,'usage':None,'events':[{'sequence':1,'event':'start','elapsed_seconds':0},{'sequence':2,'event':'stop','elapsed_seconds':12,'status':'unresolved'}],'budget':{'seconds':600}}]}
                page.route('**/api/jobs',lambda r:r.fulfill(status=400 if r.request.method=='POST' else 200,content_type='application/json',body=json.dumps({'error':'Supported request: Implement Contrast'} if r.request.method=='POST' else fixture)))
                errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{s.server_port}')
                page.get_by_role('button',name='Implement a feature',exact=True).click()
                expect(page.get_by_text('LOCAL JOB SERVICE CONNECTED',exact=True)).to_be_visible()
                expect(page.get_by_role('button',name='Run',exact=True)).to_be_disabled()
                expect(page.get_by_text('Offline fixture: missing visible control domain',exact=False)).to_be_visible()
                expect(page.get_by_role('button',name='Replay run',exact=True)).to_have_count(0)
                page.screenshot(path=str(ROOT/'.scratch/feature-dashboard.png'))
                fixture['pilot_enabled']=True
                expect(page.get_by_role('button',name='Run',exact=True)).to_be_enabled()
                page.get_by_role('textbox',name='Feature request').fill('Implement Resize')
                page.get_by_role('button',name='Run',exact=True).click()
                expect(page.get_by_role('alert')).to_have_text('Supported request: Implement Contrast')
                page.wait_for_timeout(1200)
                expect(page.get_by_role('alert')).to_have_text('Supported request: Implement Contrast')
                page.get_by_role('button',name='Overview',exact=True).click()
                expect(page.get_by_text('RECORDED PLAYBACK',exact=True)).to_be_visible()
                expect(page.get_by_role('button',name='Replay run',exact=True)).to_be_visible()
                self.assertEqual(errors,[])
                b.close()
        finally: s.shutdown(); s.server_close(); t.join()

if __name__=='__main__': unittest.main()
