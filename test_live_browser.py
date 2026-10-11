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
    def test_persistent_owners_close_before_final_evaluation(self):
        from features import live
        from features.sessions import Pool, job_environment
        import uuid
        ident=uuid.uuid4().hex
        with BrowserLock('feature-service'), BrowserLock(), job_environment(ident):
            with Pool(ROOT/'generated-app') as owners:
                deadline=time.monotonic()+40
                job={'id':ident,'status':'running','stage':'Verify','elapsed_seconds':0}
                while time.monotonic()<deadline:
                    if all(s['state']=='ready' and s['frame'] for s in live.snapshot(job)['sessions'].values()): break
                    time.sleep(.05)
                self.assertTrue(all(s['state']=='ready' and s['frame'] for s in live.snapshot(job)['sessions'].values()))
                processes=[row[0] for row in owners.workers.values()]
                live.hide()
                self.assertTrue(all(proc.poll() is not None for proc in processes))
                self.assertFalse(live.enabled())
                self.assertTrue(all(s['state']=='hidden' and s['frame'] is None for s in live.snapshot(job)['sessions'].values()))

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
                    seen=set(); actions=set(); stages=set(); overlap=False; overlap_check=False; deadline=time.monotonic()+150
                    shots=ROOT/'.scratch/live-validation'; shots.mkdir(parents=True,exist_ok=True)
                    while worker.is_alive() and time.monotonic()<deadline:
                        # UI's natural polling drives observation; execution has no artificial delay.
                        page.locator('.live-execution').is_visible()
                        stages.add(page.locator('.live-activity').inner_text())
                        visible_roles=set()
                        for role,title in [('reference','miniPaint reference'),('candidate','Candidate editor')]:
                            pane=page.locator('.live-browser').filter(has=page.get_by_text(title,exact=True))
                            image=pane.locator('img')
                            if image.count() and image.evaluate('e=>e.complete && e.naturalWidth>0'):
                                visible_roles.add(role)
                                actions.add(pane.locator('.live-browser-action').inner_text())
                                if role not in seen:
                                    seen.add(role); page.screenshot(path=str(shots/(role+'-real.png')))
                        if visible_roles=={'reference','candidate'}:
                            if not overlap: page.screenshot(path=str(shots/'both-real.png'))
                            overlap=True
                            if any('Export PNG and compare' in a or 'Set adjustment parameter' in a or 'Apply adjustment' in a for a in actions): overlap_check=True
                        page.wait_for_timeout(100) # Observer sampling only, never worker pacing.
                    worker.join(timeout=5)
                    self.assertFalse(worker.is_alive(),'Verification worker deadline')
                    self.assertEqual(seen,{'reference','candidate'})
                    self.assertTrue(overlap,'Both actual sessions must be visible simultaneously')
                    self.assertTrue(overlap_check,'Reference must remain visible through actual candidate actions')
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
                (shots/'result.json').write_text(json.dumps({'job_id':ident,'real_frames_seen':sorted(seen),'simultaneously_visible':overlap,'distinct_actions_seen':len(actions),'headed_headless_exact_parity':True,'model_calls':0},indent=2))
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
                if all(s['state']=='ready' and s['frame'] for s in snapshot(store.get(ident))['sessions'].values()):
                    seen=True; break
                time.sleep(.05) # Observe readiness; the worker is never paced.
            self.assertTrue(seen,'Both actual worker-owned browsers did not become ready')
            pids=[json.loads((ROOT/'.scratch/live'/ident/(role+'.json')).read_text())['pid'] for role in ('reference','candidate')]
            store.cancel(ident)
            self.assertIsNone(snapshot(store.get(ident))['sessions']['reference']['frame'])
            worker.join(timeout=15)
            self.assertFalse(worker.is_alive(),'Owned worker process tree did not stop')
            from features.live import alive
            self.assertTrue(all(not alive(pid) for pid in pids),'Both owner processes must terminate')
            self.assertEqual(store.get(ident)['status'],'cancelled')
            self.assertIsNone(snapshot(store.get(ident))['sessions']['reference']['frame'])

if __name__=='__main__': unittest.main()
