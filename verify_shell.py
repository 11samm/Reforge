"""Bounded local shell checks; never exposes fixtures/evaluation to coding agent."""
import base64
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import subprocess
import time
import uuid
from PIL import Image
from playwright.sync_api import sync_playwright, expect
from adapter.png import ROOT, FIXTURES, png_info, compare_pngs


class PixelMismatchError(AssertionError):
    pass


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass


def main(evidence=None):
    evidence=Path(evidence) if evidence is not None else ROOT/'evidence/shell-verification'/(time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
    evidence.mkdir(parents=True)
    report={'status':'failed','viewport':{'width':1440,'height':1000},'cases':[],'checks':{},'evidence':str(evidence)}
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT/'generated-app/dist')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,timeout=30000)
            page=browser.new_page(viewport=report['viewport'],device_scale_factor=1,locale='en-US',timezone_id='America/Los_Angeles',accept_downloads=True)
            page.set_default_timeout(8000)
            errors=[]; external=[]
            page.on('pageerror',lambda e: errors.append(str(e)))
            page.on('request',lambda r: external.append(r.url) if r.url.startswith(('http://','https://')) and not r.url.startswith('http://127.0.0.1:') else None)
            page.goto(f'http://127.0.0.1:{server.server_port}',wait_until='networkidle',timeout=30000)
            expect(page.get_by_text('No image loaded',exact=True)).to_be_visible()
            if page.evaluate('typeof window.milestoneTestChangePixel') != 'undefined': raise AssertionError('Test mutation hook leaked into production')
            page.screenshot(path=str(evidence/'generated-initial.png'))
            report['initial_accessibility']=page.locator('body').aria_snapshot()
            report['layout_bounds']={name:page.locator(selector).bounding_box() for name,selector in [('menu','.menu-row'),('options','.options'),('tools','.tool-strip'),('canvas','.document'),('sidebar','.sidebar'),('preview','.preview'),('colors','.colors'),('information','.information'),('details','.details'),('layers','.layers')]}
            page.get_by_role('menuitem',name='File',exact=True).click()
            expect(page.get_by_role('menuitem',name='Export PNG',exact=True)).to_be_disabled()
            page.keyboard.press('Escape')
            report['checks']['empty_export_disabled']=True
            for name in ('Edit','View','Image','Layer','Tools','Help'):
                expect(page.get_by_role('menuitem',name=name,exact=True)).to_be_disabled()
            for b in page.locator('.tool-strip button, .sidebar button, .sidebar input, .options input, .options button').all():
                expect(b).to_be_disabled()
            report['checks']['unimplemented_controls_disabled']=True
            page.get_by_role('menuitem',name='Effects',exact=True).click()
            page.get_by_role('menuitem',name='Gaussian Blur…',exact=True).click()
            dialog=page.get_by_role('dialog')
            expect(dialog).to_be_visible()
            expect(dialog.get_by_text('Unavailable until the learning loop implements it.',exact=False)).to_be_visible()
            slider=dialog.get_by_role('slider',name='Percentage:',exact=False)
            expect(slider).to_be_disabled()
            for attr,value in [('min','0'),('max','50'),('step','1')]: expect(slider).to_have_attribute(attr,value)
            expect(dialog.get_by_role('button',name='Apply')).to_be_disabled()
            page.screenshot(path=str(evidence/'generated-blur-unavailable.png'))
            dialog.get_by_role('button',name='Close',exact=True).click()
            expect(dialog).not_to_be_visible()
            report['checks']['blur_unavailable']=True

            def export_to(path):
                page.get_by_role('menuitem',name='File',exact=True).click()
                with page.expect_download(timeout=15000) as download:
                    page.get_by_role('menuitem',name='Export PNG',exact=True).click()
                if download.value.failure(): raise AssertionError('Export download failed')
                if path.exists(): raise AssertionError('Output reused')
                download.value.save_as(path)
                return download.value.suggested_filename

            def upload(path):
                page.locator('input[type=file]').set_input_files(str(path))
                img=page.get_by_role('img',name='Original image preview: '+path.name,exact=True)
                expect(img).to_be_visible()
                expect(page.get_by_role('alert')).to_have_count(0)
                page.wait_for_function('img => img.complete && img.naturalWidth > 0',arg=img.element_handle())
                return img

            for case in ('gb017','gb010'):
                original=FIXTURES/'inputs'/(case+'.png')
                img=upload(original)
                info=png_info(original)
                expect(page.get_by_text(f"Size: {info['width']} x {info['height']} px",exact=True)).to_be_visible()
                expect(page.locator('.layer-name')).to_have_count(1)
                expect(page.locator('.layer-name')).to_have_text(original.name)
                original_blob=base64.b64decode(img.evaluate("async img => {const a=new Uint8Array(await (await fetch(img.src)).arrayBuffer()); let s=''; for(const b of a)s+=String.fromCharCode(b);return btoa(s)}"))
                if original_blob!=original.read_bytes(): raise AssertionError('Preview source bytes changed')
                dimensions=img.evaluate('img => [img.naturalWidth,img.naturalHeight]')
                if dimensions!=[info['width'],info['height']]: raise AssertionError('Preview source dimensions changed')
                checker=page.locator('.document').evaluate('e=>getComputedStyle(e).backgroundImage')
                if 'gradient' not in checker: raise AssertionError('Missing checkerboard')
                out=evidence/(case+'-export.png')
                suggested=export_to(out)
                comparison=compare_pngs(out,original)
                if not comparison['rgba_equal']: raise PixelMismatchError('Exact original RGBA export mismatch')
                page.screenshot(path=str(evidence/(case+'-uploaded.png')))
                report['cases'].append({'case_id':case,'input':str(original),'original':info,'preview_original_bytes_equal':True,'preview_dimensions':dimensions,'single_layer':True,'checkerboard':True,'output':png_info(out),'suggested_filename':suggested,'comparison':comparison})

            # Explicit replacement gate on the same document: opaque -> transparent.
            upload(FIXTURES/'inputs/gb017.png')
            replacement=FIXTURES/'inputs/gb010.png'
            upload(replacement)
            expect(page.locator('.layer-name')).to_have_count(1)
            expect(page.locator('.layer-name')).to_have_text(replacement.name)
            export_to(evidence/'replacement-export.png')
            report['checks']['replacement']={'previous':'gb017','current':'gb010','single_layer':True}

            # A separate synthetic PNG checks invisible RGB and partial alpha preservation.
            edge=evidence/'alpha-sentinel.png'
            image=Image.new('RGBA',(3,1)); image.putdata([(19,37,91,0),(123,45,67,1),(200,100,50,128)]); image.save(edge)
            upload(edge); out=evidence/'alpha-sentinel-export.png'; export_to(out)
            report['checks']['invisible_rgb_and_partial_alpha']=compare_pngs(out,edge)
            if not report['checks']['invisible_rgb_and_partial_alpha']['rgba_equal']: raise PixelMismatchError('Invisible RGB lost')

            # Test-only entry imports the same production App and current-image module.
            # The mutation capability exists only in this separately bundled evidence fixture.
            fixture=evidence/'current-state-fixture'; fixture.mkdir()
            entry=fixture/'entry.tsx'
            main_path=(ROOT/'generated-app/src/main.tsx').as_posix()
            state_path=(ROOT/'generated-app/src/current-image.ts').as_posix()
            entry.write_text('import '+json.dumps(main_path)+';\nimport { currentImage } from '+json.dumps(state_path)+';\n'
                + "(window as any).milestoneTestChangePixel = (x: number,y: number,rgb: number[]) => {const r=currentImage.raster;if(!r || x<0 || y<0 || x>=r.width || y>=r.height)throw new Error('Invalid fixture pixel');const i=4*(y*r.width+x);r.data.set(rgb,i);return Array.from(r.data.slice(i,i+4));};\n",encoding='utf-8')
            bundle=subprocess.run(['node',str(ROOT/'generated-app/node_modules/esbuild/bin/esbuild'),str(entry),'--bundle','--format=esm','--jsx=automatic','--target=es2022','--outfile='+str(fixture/'fixture.js')],cwd=ROOT,timeout=30,capture_output=True,text=True)
            (fixture/'build.log').write_text(bundle.stdout+bundle.stderr,encoding='utf-8')
            if bundle.returncode: raise AssertionError('Isolated fixture build failed')
            (fixture/'index.html').write_text('<html><head><link rel="stylesheet" href="fixture.css"></head><body><div id="root"></div><script type="module" src="fixture.js"></script></body></html>')
            fixture_server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(fixture)))
            threading.Thread(target=fixture_server.serve_forever,daemon=True).start()
            try:
                page.goto(f'http://127.0.0.1:{fixture_server.server_port}',wait_until='networkidle')
                changed_input=evidence/'current-state-input.png'
                original_pixels=[(10+i,40+i,90+i,[0,1,64,128,255][i%5]) for i in range(12)]
                image=Image.new('RGBA',(4,3));image.putdata(original_pixels);image.save(changed_input)
                upload(changed_input)
                x,y=2,1;index=y*4+x;old=original_pixels[index]
                rgb=[17,231,83]
                accepted=page.evaluate('p=>window.milestoneTestChangePixel(p.x,p.y,p.rgb)',{'x':x,'y':y,'rgb':rgb})
                if accepted!=[*rgb,old[3]]: raise AssertionError('Current state mutation failed')
                changed_output=evidence/'current-state-export.png';export_to(changed_output)
                expected_pixels=original_pixels.copy();expected_pixels[index]=(*rgb,old[3])
                expected=evidence/'current-state-expected.png';image.putdata(expected_pixels);image.save(expected)
                comparison=compare_pngs(changed_output,expected)
                with Image.open(changed_output) as im:
                    output_pixels=list(im.convert('RGBA').getdata()); dimensions=im.size
                changed=[i for i,(a,b) in enumerate(zip(output_pixels,original_pixels)) if a!=b]
                if dimensions!=(4,3) or changed!=[index] or not comparison['rgba_equal'] or any(a[3]!=b[3] for a,b in zip(output_pixels,original_pixels)):
                    raise PixelMismatchError('Current state export failed pixel/dimensions/unaffected/alpha checks')
                report['checks']['current_state_export']={'fixture_entry':str(entry),'input':str(changed_input),'output':str(changed_output),'expected':str(expected),'mutation':{'x':x,'y':y,'before':old,'after':accepted},'dimensions':[4,3],'changed_pixels':len(changed),'unaffected_pixels_equal':True,'all_alpha_equal':True,'comparison':comparison,'export_path':'Production File > Export PNG calling serializeCurrentImage; only mutation injection is fixture-specific','production_test_hook_absent':True}
            finally:
                fixture_server.shutdown();fixture_server.server_close()
            page.goto(f'http://127.0.0.1:{server.server_port}',wait_until='networkidle')

            # JPEG is an allowed-input derivative, never a reference output.
            jpeg=evidence/'opaque-jpeg.jpg'
            with Image.open(FIXTURES/'inputs/gb017.png') as im: im.convert('RGB').save(jpeg,quality=95)
            img=upload(jpeg)
            browser_rgba=base64.b64decode(img.evaluate("img=>{const c=document.createElement('canvas');c.width=img.naturalWidth;c.height=img.naturalHeight;const x=c.getContext('2d');x.drawImage(img,0,0);const a=x.getImageData(0,0,c.width,c.height).data;let s='';for(const b of a)s+=String.fromCharCode(b);return btoa(s)}"))
            jpegout=evidence/'jpeg-export.png'; export_to(jpegout)
            with Image.open(jpegout) as im: encoded_rgba=im.convert('RGBA').tobytes()
            if encoded_rgba!=browser_rgba: raise PixelMismatchError('JPEG PNG export differs from browser preview decode')
            report['checks']['jpeg']={'browser_decoded_rgba_equal':True,'dimensions':[129,97],'alpha_extrema':png_info(jpegout)['alpha_extrema'],'browser_rgba_sha256':hashlib.sha256(browser_rgba).hexdigest()}
            for invalid in [{'name':'bad.txt','mimeType':'text/plain','buffer':b'hello'}, {'name':'broken.png','mimeType':'image/png','buffer':b'not a PNG'}, {'name':'broken.jpg','mimeType':'image/jpeg','buffer':b'\xff\xd8broken\xff\xd9'}]:
                page.locator('input[type=file]').set_input_files(invalid)
                expect(page.get_by_role('alert')).to_be_visible()
                expect(page.get_by_role('img',name='Original image preview: '+jpeg.name,exact=True)).to_be_visible()
                expect(page.locator('.layer-name')).to_have_text(jpeg.name)
            page.screenshot(path=str(evidence/'invalid-upload-retains-image.png'))
            report['checks']['unsupported_and_corrupt_retain_document']=True
            page.reload(wait_until='networkidle')
            page.locator('input[type=file]').set_input_files({'name':'bad.png','mimeType':'image/png','buffer':b'bad'})
            expect(page.get_by_role('alert')).to_be_visible()
            expect(page.get_by_text('No image loaded',exact=True)).to_be_visible()
            page.get_by_role('menuitem',name='File',exact=True).click()
            expect(page.get_by_role('menuitem',name='Export PNG',exact=True)).to_be_disabled()
            report['checks']['empty_error_state']=True
            report['browser_errors']=errors; report['external_requests']=external
            if errors or external: raise AssertionError('Browser errors or external network requests')
            report['status']='passed'
            browser.close()
    except Exception as error:
        report['classification']='pixel_mismatch' if isinstance(error,PixelMismatchError) else 'infrastructure_error'
        report['error']={'type':type(error).__name__,'message':str(error)[:2000]}
    finally:
        server.shutdown(); server.server_close()
        (evidence/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        (ROOT/'evidence/latest-shell-verification.json').write_text(json.dumps({'status':report['status'],'results':str(evidence/'results.json')},indent=2)+'\n')
        print(json.dumps({'status':report['status'],'evidence':str(evidence),'error':report.get('error')}))
    return 0 if report['status']=='passed' else 1


if __name__=='__main__': raise SystemExit(main())
