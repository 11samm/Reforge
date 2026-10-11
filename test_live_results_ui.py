"""No-model preparation + saved REAL accepted evidence; no new acceptance claims."""
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from unittest.mock import patch
from playwright.sync_api import sync_playwright, expect
from adapter.png import ROOT
from learning.core import save
from features.jobs import JobStore, BrowserLock
from features.service import server
from features.demos import Demos
from features.presentation import publish, publish_available
from verify_shell import QuietHandler

SOURCE=Path(os.environ.get('REFORGE_SAVED_BRIGHTNESS_ROOT', str(ROOT.parent/'contrast-brightness-worktree')))
IDENT='82b68e6daf5e41ddb7c03c13a91ba1f9'
ARCHIVE=SOURCE/'evidence/learning/20261011T183641Z-73504a72-dev-resume'

class RealSavedUI(unittest.TestCase):
    @unittest.skipUnless((ARCHIVE/'report.json').exists(), 'Saved accepted Brightness source not present; set REFORGE_SAVED_BRIGHTNESS_ROOT')
    def test_prepare_missing_brightness_and_review_saved_accepted_candidate(self):
        with BrowserLock('feature-service'), tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); store=JobStore(root/'jobs')
            original=json.loads((SOURCE/'evidence/feature-jobs'/IDENT/'job.json').read_text())
            self.assertEqual(original['status'],'accepted')
            self.assertEqual(json.loads((ARCHIVE/'report.json').read_text())['first_acceptance']['candidate_id'],'candidate-2')
            save(store.directory/IDENT/'job.json',original)
            job_root=root/'evidence/learning'/('feature-'+IDENT); job_root.mkdir(parents=True)
            events=[json.loads(line) for line in (ARCHIVE/'events.jsonl').read_text().splitlines()]
            publish_available(job_root,ARCHIVE,events)
            with patch('features.presentation.publish',side_effect=PermissionError('Permanent presentation test denial')):
                publish_available(job_root,ARCHIVE,events)
            save(job_root/'final-summary.json',json.loads((SOURCE/'evidence/learning'/('feature-'+IDENT)/'final-summary.json').read_text()))
            Demos.snapshot(store.directory/IDENT,SOURCE/'dev-workspaces'/('feature-'+IDENT),IDENT)
            with patch('features.service.ROOT',root):
                api=server(store,0,False); threading.Thread(target=api.serve_forever,daemon=True).start()
                static=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT/'dashboard/dist')))
                threading.Thread(target=static.serve_forever,daemon=True).start()
                try:
                    with sync_playwright() as p:
                        browser=p.chromium.launch(headless=True); page=browser.new_page(viewport={'width':1440,'height':1000})
                        errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
                        def proxy(r):
                            path=r.request.url.split('/api/jobs',1)[1]
                            headers={'Content-Type':'application/json','X-Reforge-Request':'1'} if r.request.method=='POST' else {}
                            if r.request.headers.get('origin')=='null': headers['Origin']='null'
                            request=Request(f'http://127.0.0.1:{api.server_port}/api/jobs'+path, data=r.request.post_data.encode() if r.request.post_data else None, headers=headers)
                            with urlopen(request) as response:
                                r.fulfill(status=response.status,headers=dict(response.headers),body=response.read())
                        page.route('**/api/jobs**',proxy)
                        page.goto(f'http://127.0.0.1:{static.server_port}')
                        page.get_by_role('button',name='Implement a feature',exact=True).click()
                        expect(page.get_by_text('Service connected',exact=True)).to_be_visible()
                        expect(page.get_by_text('Candidate candidate-1',exact=True)).to_be_visible()
                        expect(page.get_by_text('Candidate candidate-2',exact=True)).to_be_visible()
                        expect(page.get_by_text('Presentation degraded:',exact=False)).to_be_visible()
                        expect(page.get_by_text('Presentation degraded:',exact=False)).to_contain_text('Last complete snapshot:')
                        page.get_by_role('button',name='Prepare fresh Brightness demo',exact=True).click()
                        prepared=page.frame_locator('iframe[title="Prepared editor — target operation absent"]')
                        expect(prepared.get_by_text('No image loaded',exact=True)).to_be_visible(timeout=30000)
                        expect(page.get_by_role('button',name='Learn Brightness',exact=True)).to_be_disabled()
                        expect(prepared.get_by_role('menuitem',name='Image',exact=True)).to_be_disabled()
                        demo=Demos(store.directory/'prepared-demos').list()[0]
                        self.assertFalse(demo['model_invoked']); self.assertTrue(demo['preparation']['target_absent'])
                        self.assertFalse((Path(demo['preparation']['app'])/'src/brightness.ts').exists())
                        page.get_by_role('button',name='Review accepted candidate',exact=True).click()
                        review=page.frame_locator('iframe[title="Accepted isolated candidate — interactive exploration"]')
                        expect(review.get_by_text('No image loaded',exact=True)).to_be_visible()
                        self.assertTrue(review.locator('body').evaluate('()=>{try{void parent.document;return false}catch{return true}}'), 'Preview must not access dashboard DOM')
                        # A new exploration input, never added to acceptance records.
                        from PIL import Image
                        upload=root/'exploration.png'; Image.new('RGBA',(9,7),(10,20,30,255)).save(upload)
                        review.locator('input[type=file]').set_input_files(str(upload))
                        expect(review.get_by_role('img',name='Original image preview: exploration.png',exact=True)).to_be_visible()
                        review.get_by_role('menuitem',name='Image',exact=True).click()
                        review.get_by_role('menuitem',name='Color Corrections',exact=False).click()
                        review.get_by_role('slider',name='Brightness:',exact=True).fill('20')
                        shots=ROOT/'.scratch/live-results-validation'; shots.mkdir(parents=True,exist_ok=True)
                        page.screenshot(path=str(shots/'before-apply.png'))
                        review.get_by_role('button',name='Apply',exact=True).click(timeout=5000)
                        expect(review.locator('dialog[open]')).to_have_count(0)
                        self.assertEqual(store.get(IDENT),original)
                        for width in (980,390):
                            page.set_viewport_size({'width':width,'height':1000})
                            self.assertFalse(page.locator('.content').evaluate('e=>e.scrollWidth>e.clientWidth'))
                            review.get_by_role('menuitem',name='Image',exact=True).click()
                            review.get_by_role('menuitem',name='Color Corrections',exact=False).click()
                            review.get_by_role('slider',name='Brightness:',exact=True).fill('-10')
                            review.get_by_role('button',name='Apply',exact=True).click()
                            expect(review.locator('dialog[open]')).to_have_count(0)
                        shots=ROOT/'.scratch/live-results-validation'; shots.mkdir(parents=True,exist_ok=True)
                        page.screenshot(path=str(shots/'saved-real-evidence-and-prepared-demo.png'))
                        save(shots/'result.json',{'saved_job':IDENT,'prepared_demo':demo['id'],'model_calls':0,'saved_evidence_preserved':True,'sandboxed_upload_and_brightness':True})
                        self.assertEqual(errors,[]); browser.close()
                finally: api.shutdown(); api.server_close(); static.shutdown(); static.server_close()

if __name__=='__main__': unittest.main()
