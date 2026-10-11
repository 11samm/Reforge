"""Actual archived recordings, offline dashboard; no model/reference/harness sessions."""
import json, shutil, tempfile, threading, unittest
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parent
class PortableUI(unittest.TestCase):
 def test_relocated_bundles_offline_and_run_isolation(self):
  with tempfile.TemporaryDirectory(prefix='reforge-portable-') as other:
   other=Path(other)
   for name in ['brightness','contrast']:shutil.copyfile(ROOT/f'dashboard/public/runs/{name}-success.reforge.json',other/f'{name}.json')
   class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
   server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT/'dashboard/dist')))
   worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
   try:
    with sync_playwright() as p:
     browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];api=[]
     page.on('pageerror',lambda e:errors.append(str(e)))
     def block(route):api.append(route.request.url);route.abort()
     page.route('**/api/**',block)
     page.goto(f'http://127.0.0.1:{server.server_port}')
     for name,ident in [('brightness','82b68e6daf5e41ddb7c03c13a91ba1f9'),('contrast','9df7c33da7a5425db3934e2cd928c5ee')]:
      page.locator('input[type=file]').set_input_files(str(other/f'{name}.json'))
      expect(page.get_by_text('RECORDED PLAYBACK',exact=True)).to_be_visible()
      expect(page.locator('.identity strong')).to_have_text(ident)
      expect(page.get_by_text('In progress at this point',exact=True)).to_be_visible()
      page.get_by_role('button',name='Event log',exact=True).click()
      expect(page.locator('.events')).not_to_contain_text('Accepted')
      expect(page.locator('.events')).not_to_contain_text('Rejected')
      expect(page.locator('.events')).not_to_contain_text('cases passed')
      expect(page.locator('.events')).to_contain_text('not available yet')
      page.get_by_role('button',name='Candidates',exact=True).click()
      expect(page.get_by_text('Not available at this recorded time.',exact=True)).to_be_visible()
      expect(page.locator('img')).to_have_count(0)
      page.get_by_title('Jump to end',exact=True).click()
      expect(page.locator('.candidates .inspector img').first).to_be_visible()
      page.wait_for_function("Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0)")
      assert page.locator('.pixel-broken').count()==0
      assert page.locator('img').evaluate_all("imgs=>imgs.every(i=>i.src.startsWith('blob:'))")
      assert page.locator('.live-browsers').count()==0
      page.get_by_role('tab',name='RGB ×16',exact=True).first.click()
      page.wait_for_function("Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0)")
      page.get_by_title('Restart replay',exact=True).click()
      expect(page.get_by_text('Not available at this recorded time.',exact=True)).to_be_visible()
      expect(page.locator('img')).to_have_count(0)
      page.get_by_role('button',name='Overview',exact=True).click()
     # Built-in/imported switching must keep the retained imported URLs valid.
     page.locator('.run-picker select').select_option('brightness-success')
     expect(page.locator('.identity strong')).to_have_text('82b68e6daf5e41ddb7c03c13a91ba1f9')
     page.locator('.run-picker select').select_option('imported')
     expect(page.locator('.identity strong')).to_have_text('9df7c33da7a5425db3934e2cd928c5ee')
     page.get_by_role('button',name='Candidates',exact=True).click()
     page.get_by_title('Jump to end',exact=True).click()
     page.wait_for_function("Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0)")
     assert page.locator('.pixel-broken').count()==0
     page.get_by_role('button',name='Overview',exact=True).click()
     bad=json.loads((other/'brightness.json').read_text(encoding='utf8'));bad['assets'].pop();(other/'missing.json').write_text(json.dumps(bad),encoding='utf8')
     page.locator('input[type=file]').set_input_files(str(other/'missing.json'))
     expect(page.locator('.load-error')).to_contain_text('Missing asset')
     expect(page.locator('img')).to_have_count(0)
     self.assertEqual(api,[]);self.assertEqual(errors,[]);browser.close()
   finally:server.shutdown();server.server_close();worker.join()
if __name__=='__main__':unittest.main()
