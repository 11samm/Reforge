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
                page.route('**/api/jobs**',lambda r:r.fulfill(status=400 if r.request.method=='POST' else 200,content_type='application/json',body=json.dumps({'error':'Synthetic preparation failure'} if r.request.method=='POST' else fixture if r.request.url.endswith('/api/jobs') else {'job_id':'a'*32,'experiments':[],'candidates':[]})))
                errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{s.server_port}')
                page.get_by_role('button',name='Implement a feature',exact=True).click()
                expect(page.get_by_text('Service connected',exact=True)).to_be_visible()
                expect(page.get_by_role('button',name='Learn Brightness',exact=True)).to_be_disabled()
                expect(page.get_by_text('Offline fixture: missing visible control domain',exact=False)).to_be_visible()
                expect(page.get_by_role('button',name='Replay run',exact=True)).to_have_count(0)
                page.screenshot(path=str(ROOT/'.scratch/feature-dashboard.png'))
                fixture['pilot_enabled']=True
                expect(page.get_by_role('button',name='Learn Brightness',exact=True)).to_be_disabled()
                page.get_by_role('button',name='Prepare fresh Brightness demo',exact=True).click()
                expect(page.get_by_role('alert')).to_have_text('Synthetic preparation failure')
                page.wait_for_timeout(1200)
                expect(page.get_by_role('alert')).to_have_text('Synthetic preparation failure')
                # The integrated entry point chooses a real portable recording.
                with page.expect_file_chooser() as chooser:
                    page.get_by_role('button',name='Replay saved run',exact=True).click()
                chooser.value.set_files(str(ROOT/'dashboard/public/runs/brightness-success.reforge.json'))
                expect(page.get_by_text('RECORDED PLAYBACK',exact=True)).to_be_visible()
                expect(page.locator('.identity strong')).to_have_text('82b68e6daf5e41ddb7c03c13a91ba1f9')
                expect(page.get_by_text('In progress at this point',exact=True)).to_be_visible()
                expect(page.locator('.live-browsers')).to_have_count(0)
                expect(page.get_by_role('button',name='Play',exact=True)).to_be_visible()
                page.get_by_title('Jump to end',exact=True).click()
                expect(page.get_by_role('button',name='Replay run',exact=True)).to_be_visible()
                self.assertEqual(errors,[])
                b.close()
        finally: s.shutdown(); s.server_close(); t.join()

if __name__=='__main__': unittest.main()


class IntegrationUI(unittest.TestCase):
    def test_feature_states_actions_and_mobile_navigation(self):
        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self,*args): pass
        s=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT/'dashboard/dist')))
        t=threading.Thread(target=s.serve_forever,daemon=True); t.start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True); page=browser.new_page(viewport={'width':1440,'height':1000})
                ident='b'*32; previous='a'*32
                def job(i,status):
                    return {'id':i,'request':'Implement Contrast','status':status,'stage':'Verify' if status=='accepted' else 'Investigate','activity':'All gates passed' if status=='accepted' else 'Collecting diagnostic evidence','elapsed_seconds':346 if status=='accepted' else 60,'usage':None,'events':[{'sequence':1,'event':'start','elapsed_seconds':0},{'sequence':2,'event':'evidence','elapsed_seconds':30,'artifact':f'/api/jobs/{i}/evidence/spec.json'}],'budget':{'seconds':1200}}
                state={'pilot_enabled':True,'jobs':[]}; offline=False; posts=[]
                demo={'id':ident,'request':'Implement Brightness','preview_status':'unavailable','preparation':{'target_absent':True,'model_invoked':False,'memory':{'fixture':'Synthetic starting-state policy'}}}
                def route(r):
                    nonlocal state
                    path=r.request.url.split('/api/jobs')[1]
                    if offline: return r.fulfill(status=503,content_type='application/json',body=json.dumps({'error':'Service unavailable'}))
                    if r.request.method=='POST':
                        posts.append((path,r.request.post_data_json))
                        self.assertEqual(r.request.headers.get('x-reforge-request'),'1')
                        if path=='/prepare':
                            state['prepared_demos']=[demo]
                            return r.fulfill(status=201,content_type='application/json',body=json.dumps(demo))
                        updated=job(ident,'cancelling' if path.endswith('/cancel') else 'queued')
                        state['jobs']=[updated]
                        return r.fulfill(status=200,content_type='application/json',body=json.dumps(updated))
                    r.fulfill(status=200,content_type='application/json',body=json.dumps(state if path=='' else {'job_id':path.split('/')[1],'experiments':[],'candidates':[]}))
                page.route('**/api/jobs**',route)
                page.goto(f'http://127.0.0.1:{s.server_port}')
                page.get_by_role('button',name='Implement a feature',exact=True).click()
                expect(page.get_by_text('No feature jobs yet',exact=True)).to_be_visible()
                page.get_by_role('button',name='Prepare fresh Brightness demo',exact=True).click()
                expect(page.get_by_role('button',name='Learn Brightness',exact=True)).to_be_enabled()
                page.get_by_role('button',name='Learn Brightness',exact=True).click()
                expect(page.get_by_text('queued',exact=True)).to_be_visible()
                # Preparation scrolls presenters to the editor; starting a run
                # must bring the actual browser panes back into the viewport.
                live=page.locator('.live-execution').bounding_box()
                content=page.locator('.content').bounding_box()
                self.assertGreaterEqual(live['y'],content['y']-2)
                self.assertLess(live['y'],content['y']+content['height']/2)
                expect(page.get_by_role('button',name='Learn Brightness',exact=True)).to_be_disabled()
                page.get_by_role('button',name='Cancel run',exact=True).click()
                expect(page.get_by_role('button',name='Cancelling…',exact=True)).to_be_disabled()
                self.assertEqual(posts,[('/prepare',{'request':'Implement Brightness'}),('',{'request':'Implement Brightness','prepared_demo_id':ident}),(f'/{ident}/cancel',{})])
                state['jobs']=[job(ident,'running'),job(previous,'accepted')]
                expect(page.get_by_text('running',exact=True)).to_be_visible()
                shots=ROOT/'dashboard/docs/screenshots/integration'; shots.mkdir(parents=True,exist_ok=True)
                page.screenshot(path=str(shots/'feature-running-desktop.png'))
                page.get_by_role('combobox',name='Job history').select_option(previous)
                expect(page.get_by_text('accepted',exact=True)).to_be_visible()
                page.wait_for_timeout(1200)
                expect(page.get_by_text('accepted',exact=True)).to_be_visible()
                expect(page.get_by_role('button',name='Learn Brightness',exact=True)).to_be_disabled()
                expect(page.get_by_role('link',name='spec.json')).to_have_attribute('href',f'/api/jobs/{previous}/evidence/spec.json')
                page.screenshot(path=str(shots/'feature-accepted-desktop.png'))
                for status in ('unresolved','failed','cancelled'):
                    state['jobs']=[job(previous,status)]
                    expect(page.get_by_text(status,exact=True)).to_be_visible()
                    expect(page.get_by_role('button',name='Cancel run',exact=True)).to_have_count(0)
                    expect(page.get_by_text('This job did not establish a verified feature.',exact=False)).to_be_visible()
                state['jobs']=[job(previous,'accepted')]
                expect(page.get_by_text('accepted',exact=True)).to_be_visible()
                for width in (980,390):
                    page.set_viewport_size({'width':width,'height':1000})
                    expect(page.get_by_role('navigation',name='Dashboard sections')).to_be_visible()
                    self.assertEqual(page.locator('.mobile-nav').evaluate('e=>getComputedStyle(e).flexDirection'),'row')
                    self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'))
                    self.assertEqual(page.locator('.content').evaluate('e=>e.scrollWidth > e.clientWidth'),False)
                    page.screenshot(path=str(shots/f'feature-accepted-{width}.png'))
                page.get_by_role('button',name='Candidates',exact=True).click()
                expect(page.get_by_role('button',name='Replay run',exact=True)).to_be_visible()
                page.set_viewport_size({'width':1440,'height':1000})
                page.get_by_role('row').filter(has=page.get_by_text('candidate-2',exact=True)).first.click()
                expect(page.get_by_role('tab',name='Side by side',exact=True)).to_be_visible()
                expect(page.locator('.side-by-side img')).to_have_count(2)
                page.screenshot(path=str(shots/'inspector-desktop.png'))
                page.get_by_role('tab',name='RGB ×16',exact=True).click()
                page.get_by_role('tab',name='Side by side',exact=True).click()
                page.set_viewport_size({'width':390,'height':1000})
                page.get_by_role('button',name='Implement a feature',exact=True).click()
                expect(page.get_by_text('accepted',exact=True)).to_be_visible()
                offline=True
                expect(page.get_by_text('Service offline',exact=True)).to_be_visible()
                expect(page.get_by_role('alert')).to_have_text('Service unavailable')
                expect(page.get_by_role('button',name='Learn Brightness',exact=True)).to_be_disabled()
                page.screenshot(path=str(shots/'feature-offline-mobile.png'))
                browser.close()
        finally: s.shutdown(); s.server_close(); t.join()
