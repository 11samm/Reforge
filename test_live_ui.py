"""Explicitly synthetic UI fixtures; never evidence of harness browser execution."""
import base64
import io
import json
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer
from PIL import Image
from playwright.sync_api import sync_playwright, expect
from adapter.png import ROOT
from verify_shell import QuietHandler

class SyntheticLiveUI(unittest.TestCase):
    def test_job_switch_building_disconnect_cancel_and_narrow_layout(self):
        image=io.BytesIO(); Image.new('RGB',(2,2),'blue').save(image,format='JPEG')
        frame=base64.b64encode(image.getvalue()).decode()
        a='a'*32; b='b'*32
        def job(ident,status):
            return {'id':ident,'request':'Synthetic UI lifecycle fixture','presentation_label':'Synthetic UI fixture: these frames and events are not harness evidence','status':status,'stage':'Reconstruct','elapsed_seconds':7.5,'events':[]}
        jobs=[job(a,'running'),job(b,'cancelled')]
        state='building'; disconnected=False; mismatch=False
        def feed():
            session=lambda status:{'state':status,'frame':frame if status=='ready' else None,'action':'Synthetic action','purpose':'Synthetic purpose','parameters':{'input':'fixture.png','value':17},'action_elapsed_seconds':2.5}
            return {'job_id':b if mismatch else a,'mode':'live','stage':'Reconstruct','elapsed_seconds':7.5,'activity':'Synthetic backend event','experiment':{'question':'Synthetic experiment purpose','input':{'kind':'fixture'},'value':17},'sessions':{'reference':session('ready'),'candidate':session(state)}}
        static=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT/'dashboard/dist')))
        threading.Thread(target=static.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True); page=browser.new_page(viewport={'width':1440,'height':1000})
                def route(r):
                    if r.request.url.endswith('/live'):
                        if disconnected: return r.abort()
                        data=feed()
                    elif r.request.url.endswith('/cancel'):
                        jobs[0]['status']='cancelling'; data=jobs[0]
                    else: data={'pilot_enabled':False,'jobs':jobs}
                    r.fulfill(content_type='application/json',body=json.dumps(data))
                page.route('**/api/jobs**',route)
                page.goto(f'http://127.0.0.1:{static.server_port}'); page.get_by_role('button',name='Implement a feature',exact=True).click()
                pane=page.locator('.live-execution')
                expect(pane.get_by_text('building',exact=True)).to_be_visible()
                expect(pane.locator('img')).to_have_count(1)
                expect(pane.get_by_text('Synthetic experiment purpose',exact=True)).to_be_visible()
                expect(pane.get_by_text('0:07.5',exact=True)).to_be_visible()
                state='ready'; expect(pane.locator('img')).to_have_count(2)
                page.get_by_role('combobox',name='Job history').select_option(b)
                expect(pane.locator('img')).to_have_count(0)
                page.get_by_role('combobox',name='Job history').select_option(a)
                expect(pane.locator('img')).to_have_count(2)
                mismatch=True; expect(pane.locator('img')).to_have_count(0)
                mismatch=False; expect(pane.locator('img')).to_have_count(2)
                disconnected=True; expect(pane.locator('img')).to_have_count(0)
                disconnected=False; expect(pane.locator('img')).to_have_count(2)
                for width in (980,390):
                    page.set_viewport_size({'width':width,'height':1000})
                    self.assertFalse(page.locator('.content').evaluate('e=>e.scrollWidth>e.clientWidth'))
                    if width==390:
                        columns=page.locator('.live-browser-pair').evaluate('e=>getComputedStyle(e).gridTemplateColumns')
                        self.assertEqual(len(columns.split()),1)
                page.get_by_role('button',name='Cancel run',exact=True).click()
                expect(pane.locator('img')).to_have_count(0)
                browser.close()
        finally: static.shutdown(); static.server_close()
