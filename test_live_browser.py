"""Real no-model reference/candidate sessions displayed through the production UI.
Synthetic job metadata is labeled; browser frames come from the real workers.
"""
import json
import os
import threading
import time
import unittest
from functools import partial
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from playwright.sync_api import sync_playwright, expect
from adapter.png import ROOT
from features.jobs import JobStore, BrowserLock
from features.service import server
from features.live_demo import prepare, run
from verify_shell import QuietHandler

class RealBrowsers(unittest.TestCase):
    def test_saved_brightness_workers_in_dashboard_and_headless_parity(self):
        with BrowserLock('feature-service'), BrowserLock():
            store=JobStore(ROOT/'evidence/feature-jobs')
            ident=prepare(store); api=server(store,0,False)
            api_thread=threading.Thread(target=api.serve_forever,daemon=True); api_thread.start()
            static=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT/'dashboard/dist')))
            static_thread=threading.Thread(target=static.serve_forever,daemon=True); static_thread.start()
            worker=None
            try:
                with sync_playwright() as p:
                    browser=p.chromium.launch(headless=True)
                    page=browser.new_page(viewport={'width':1440,'height':1000})
                    errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
                    def route(r):
                        path=r.request.url.split('/api/jobs',1)[1]
                        with urlopen(f'http://127.0.0.1:{api.server_port}/api/jobs'+path) as response:
                            r.fulfill(status=response.status,content_type='application/json',body=response.read())
                    page.route('**/api/jobs**',route)
                    page.goto(f'http://127.0.0.1:{static.server_port}')
                    page.get_by_role('button',name='Implement a feature',exact=True).click()
                    expect(page.get_by_text('Deterministic browser verification:',exact=False).first).to_be_visible()
                    worker=threading.Thread(target=run,args=(store,ident)); worker.start()
                    seen=set(); actions=set(); stages=set(); deadline=time.monotonic()+150
                    shots=ROOT/'.scratch/live-validation'; shots.mkdir(parents=True,exist_ok=True)
                    while worker.is_alive() and time.monotonic()<deadline:
                        # UI's natural polling drives observation; execution has no artificial delay.
                        page.locator('.live-execution').is_visible()
                        stages.add(page.locator('.live-activity').inner_text())
                        for role,title in [('reference','miniPaint reference'),('candidate','Candidate editor')]:
                            pane=page.locator('.live-browser').filter(has=page.get_by_text(title,exact=True))
                            image=pane.locator('img')
                            if image.count() and image.evaluate('e=>e.complete && e.naturalWidth>0'):
                                actions.add(pane.locator('.live-browser-action').inner_text())
                                if role not in seen:
                                    seen.add(role); page.screenshot(path=str(shots/(role+'-real.png')))
                        page.wait_for_timeout(100) # Observer sampling only, never worker pacing.
                    worker.join(timeout=5)
                    self.assertFalse(worker.is_alive(),'Verification worker deadline')
                    self.assertEqual(seen,{'reference','candidate'})
                    self.assertGreaterEqual(len(actions),3)
                    self.assertTrue(any('Validate procedure' in s for s in stages))
                    self.assertTrue(any('Verify' in s for s in stages))
                    self.assertEqual(store.get(ident)['activity'],'deterministic_browser_checks_passed')
                    expect(page.locator('.live-browser img')).to_have_count(0)
                    for width in (980,390):
                        page.set_viewport_size({'width':width,'height':1000})
                        self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
                        self.assertFalse(page.locator('.content').evaluate('e=>e.scrollWidth>e.clientWidth'))
                        page.screenshot(path=str(shots/(str(width)+'-completed.png')))
                    self.assertEqual(errors,[]); browser.close()
                # Same saved candidate worker without presentation must retain exact outcomes.
                from learning.worker import candidate
                d=ROOT/'evidence/learning'/('offline-feature-live-'+ident)
                request=json.loads((d/'candidate/request.json').read_text())
                headed=json.loads((d/'candidate/result.json').read_text())
                output=d/'headless-parity'; output.mkdir()
                from unittest.mock import patch
                with patch.dict(os.environ,{'REFORGE_LIVE_ENABLED':'0'}): result=candidate(request,output)
                self.assertTrue(result['ui_valid']); self.assertTrue(result['independent'])
                self.assertEqual([c['status'] for c in result['cases']],[c['status'] for c in headed['cases']])
                self.assertTrue(all(c['status']=='passed' for c in result['cases']))
                (shots/'result.json').write_text(json.dumps({'job_id':ident,'real_frames_seen':sorted(seen),'distinct_actions_seen':len(actions),'headed_headless_exact_parity':True,'model_calls':0},indent=2))
            finally:
                api.shutdown(); api.server_close(); static.shutdown(); static.server_close()
                if worker: worker.join(timeout=130)

    def test_real_worker_cancellation_clears_presentation(self):
        from features.live import snapshot
        with BrowserLock('feature-service'), BrowserLock():
            store=JobStore(ROOT/'evidence/feature-jobs'); ident=prepare(store)
            worker=threading.Thread(target=run,args=(store,ident)); worker.start()
            deadline=time.monotonic()+40; seen=False
            while worker.is_alive() and time.monotonic()<deadline:
                if snapshot(store.get(ident))['sessions']['reference']['state']=='ready':
                    seen=True; break
                time.sleep(.05) # Observe readiness; the worker is never paced.
            self.assertTrue(seen,'Actual worker-owned reference browser did not become ready')
            store.cancel(ident)
            self.assertIsNone(snapshot(store.get(ident))['sessions']['reference']['frame'])
            worker.join(timeout=15)
            self.assertFalse(worker.is_alive(),'Owned worker process tree did not stop')
            self.assertEqual(store.get(ident)['status'],'cancelled')
            self.assertIsNone(snapshot(store.get(ident))['sessions']['reference']['frame'])

if __name__=='__main__': unittest.main()
