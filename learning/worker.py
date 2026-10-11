"""Trusted bounded workers. Reference controller closes before candidate execution."""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import threading
import time
from PIL import Image
from playwright.sync_api import sync_playwright, expect
from adapter.minipaint import MiniPaintAdapter
from adapter.png import ROOT, EVIDENCE, within, png_info, compare_pngs
from evaluator.compare import evaluate, load_policy
from verify_shell import QuietHandler
from .core import save, digest, integer, resolve_app, validate_config, validate_plan

def reference(request, directory):
    c=validate_config(request['config']); p=validate_plan(request['plan'],c)
    return reference_procedure(request,p['input'],p['percentage'],c,directory)

def developer_reference(request, directory):
    """Developer-selected follow-up: same procedure and checks, developer generator set, declared domain."""
    from .diagnostics import ALL_DEFINITIONS
    c=validate_config(request['config']); spec=request['spec']
    if set(spec)!={'kind','width','height'} or spec['kind'] not in ALL_DEFINITIONS: raise ValueError('Unknown developer input')
    for k in ['width','height']: integer(spec[k],3,257)
    integer(request['percentage'],c['percentage_min'],c['percentage_max'])
    return reference_procedure(request,spec,request['percentage'],c,directory)

def reference_procedure(request, spec, percentage, c, directory):
    input_path=within(request['input_path'],directory.parent.parent/'inputs')
    if digest(input_path)!=request['input_sha256']: raise ValueError('Diagnostic input changed')
    setup={'canvas_width':spec['width'],'canvas_height':spec['height'],'transparent':True,'resolution_ui':72,
           'imported_layer_offset':[0,0],'layer_opacity_percent':100,'layer_rotation_degrees':0,
           'fresh_original_input':True,'other_visible_layers':False}
    p={'percentage':percentage}
    started=time.monotonic()
    report={'status':'infrastructure_failure','evidence_id':request['id'],'requested_percentage':p['percentage']}
    try:
        with MiniPaintAdapter(directory,headed=True,window_position=c['window_position'],
                              diagnostic_input_root=input_path.parent) as a:
            a.reset_reference(setup); report['target']=a.identity
            if a.identity['version_discrepancy']: raise ValueError('Visible reference version changed')
            report['import']=a.import_image(input_path)
            original=directory/'original-confirmation.png'; a.export_png(original)
            report['original_confirmation']=compare_pngs(original,input_path)
            if not report['original_confirmation']['rgba_equal']: raise ValueError('Original import/setup did not reproduce input')
            a.apply_operation({'Percentage':p['percentage']})
            report['accepted_percentage']=a.accepted_percentage
            if a.accepted_percentage!=p['percentage']: raise ValueError('Requested and accepted parameters differ')
            output=directory/'output.png'; report['output']=a.export_png(output)
            report['output_path']=str(output); report['status']='observed'
            report['actions']=a.actions
    except Exception as error:
        report['error']={'type':type(error).__name__,'message':str(error)[:2000]}
    report['elapsed_seconds']=round(time.monotonic()-started,3)
    return report

def command(args, log, timeout=55):
    result=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=timeout,
                          creationflags=subprocess.CREATE_NO_WINDOW if __import__('os').name=='nt' else 0)
    log.write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode: raise ValueError('Trusted command failed; inspect '+str(log))

def build(directory, app=None):
    app=resolve_app(app or ROOT/'generated-app')
    command(['node',str(app/'node_modules/typescript/bin/tsc'),'--noEmit','--project',str(app/'tsconfig.json')],directory/'typecheck.log')
    # Fixed command and config: builder cannot edit scripts, dependencies, config or lockfile.
    command(['node',str(app/'node_modules/vite/bin/vite.js'),'build',str(app),'--config',str(app/'vite.config.ts')],directory/'build.log')

def candidate(request,directory):
    app=resolve_app(request.get('app') or ROOT/'generated-app'); suite=request['suite']
    op=None
    if request.get('operation'):
        from .operations import operation_spec
        op=operation_spec(request['operation'])
    source=op['source'] if op else 'src/gaussian-blur.ts'
    function=op['export'] if op else 'applyGaussianBlur'
    key=op['parameter']['key'] if op else 'percentage'
    result={'build_valid':False,'independent':False,'app':str(app),
            'cases':[],'suite_sha256':request['suite_sha256'],'evaluator_suspect':False,'ui_valid':False}
    try:
        build(directory,app); result['build_valid']=True
        # Batch invocation has only generated operation code and inputs, no reference exports/adapter/browser.
        entry=directory/'batch-entry.ts'
        entry.write_text('import {readFileSync,writeFileSync} from "node:fs";\n'
            +'import {decodePngRaster} from '+json.dumps((app/'src/current-image.ts').as_posix())+';\n'
            +'import {'+function+'} from '+json.dumps((app/source).as_posix())+';\n'
            +'import {encode} from '+json.dumps((app/'node_modules/fast-png/lib/index.js').as_posix())+';\n'
            +'const cases=JSON.parse(readFileSync(process.argv[2],"utf8"));\n'
            +'for(const c of cases){const r=decodePngRaster(new Uint8Array(readFileSync(c.input)));'
            +'const out='+function+'(r,c.'+key+');if(!out||out.width!==r.width||out.height!==r.height||out.depth!==8||out.data.length!==r.width*r.height*4)throw Error("Invalid raster");'
            +'writeFileSync(c.output,encode({...out,channels:4}));}\n',encoding='utf-8')
        command(['node',str(app/'node_modules/esbuild/bin/esbuild'),str(entry),'--bundle','--platform=node',
                 '--format=esm','--outfile='+str(directory/'batch.mjs')],directory/'batch-build.log')
        exports=[]
        for row in suite['cases']:
            exports.append({'input':row['input'],key:row[key],'output':str(directory/(row['id']+'.png'))})
        save(directory/'batch-inputs.json',exports)
        # Node v24 permissions constrain files/child processes/native addons, but not network.
        # Trusted preloader denies standard network APIs; neither guard is an OS sandbox.
        guard=directory/'deny-network.cjs'
        guard.write_text('const deny=()=>{throw Error("Network disabled for candidate evaluation")};\n'
            +'for(const name of ["http","https","net","tls","dgram","dns"]){const m=require("node:"+name);'
            +'for(const k of Object.keys(m))if(typeof m[k]==="function"&&!/^[A-Z]/.test(k))m[k]=deny;'
            +'if(m.Socket)m.Socket.prototype.connect=deny;}\n'
            +'globalThis.fetch=deny;globalThis.WebSocket=class{constructor(){deny()}};'
            +'require("node:module").syncBuiltinESMExports();\n',encoding='utf-8')
        input_roots=sorted({str(Path(row['input']).parent) for row in suite['cases']})
        for root in input_roots:
            if Path(root).name!='inputs': raise ValueError('Batch may read only input directories')
        permissions=['node','--permission','--require='+str(guard),'--allow-fs-read='+str(directory),
                     *['--allow-fs-read='+root for root in input_roots],'--allow-fs-write='+str(directory)]
        command(permissions+['--input-type=module','-e','import {connect} from "node:net";import {request} from "node:https";'
            +'let n=0;for(const f of [()=>connect(1,"127.0.0.1"),()=>request("https://example.invalid"),()=>fetch("https://example.invalid")])'
            +'{try{f()}catch(e){if(String(e).includes("Network disabled"))n++}}if(n!==3)throw Error("Network guard failed");console.log("3 network guard probes denied");'],directory/'network-guard.log')
        command(permissions+[str(directory/'batch.mjs'),str(directory/'batch-inputs.json')],directory/'batch-execution.log')
        result['independent']=True
        result['execution']={'reference_browser_closed':True,'input_only_batch':exports,
                             'node_permission_guard':True,'standard_network_api_guard':'three probes denied; not an OS sandbox'}
        for row in suite['cases']:
            if digest(row['expected'])!=row['expected_sha256'] or digest(row['input'])!=row['input_sha256']:
                result['evaluator_suspect']=True; raise ValueError('Frozen expected/input changed')
            result['cases'].append(evaluate(row['id'],row['expected'],directory/(row['id']+'.png'),
                                            directory/'evaluation'/row['id'],suite['policy'],row['regions']))
        result['evaluator_suspect']=any(r['classification'] in ['infrastructure_error','invalid_region'] or
                                      r.get('reference_path') is None for r in result['cases'])
        # Check the shell applies to current image state and matches the same batch operation.
        first=next((c for c in suite['cases'] if c[key]!=0),suite['cases'][0]) if op else suite['cases'][0]
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(app/'dist')))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True,timeout=30000)
                page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1,accept_downloads=True)
                page.set_default_timeout(8000); external=[]; errors=[]
                def route(r):
                    if r.request.url.startswith(f'http://127.0.0.1:{server.server_port}/'): r.continue_()
                    else: external.append(r.request.url); r.abort()
                page.route('**/*',route); page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{server.server_port}',wait_until='networkidle')
                if op:
                    page.get_by_role('menuitem',name=op['ui_menu'],exact=True).click()
                    page.get_by_role('menuitem',name=op['ui_item'],exact=True).click()
                    empty=page.get_by_role('dialog')
                    expect(empty.get_by_role('slider',name='Brightness',exact=False)).to_be_disabled()
                    expect(empty.get_by_role('button',name='Apply',exact=True)).to_be_disabled()
                    empty.get_by_role('button',name='Close',exact=True).click()
                page.locator('input[type=file]').set_input_files(first['input'])
                expect(page.get_by_role('img',name='Original image preview: '+Path(first['input']).name,exact=True)).to_be_visible()
                page.get_by_role('menuitem',name=op['ui_menu'] if op else 'Effects',exact=True).click()
                page.get_by_role('menuitem',name=op['ui_item'] if op else 'Gaussian Blur…',exact=True).click()
                import re
                dialog=page.get_by_role('dialog'); slider=dialog.get_by_role('slider',name=re.compile('^'+(op['ui_parameter'] if op else 'Percentage')+r'(?::.*)?$'))
                slider.press('Home')
                for _ in range(first[key]-(op['parameter']['min'] if op else 0)): slider.press('ArrowRight')
                expect(slider).to_have_value(str(first[key]))
                dialog.get_by_role('button',name='Apply',exact=True).click()
                expect(dialog).not_to_be_visible()
                page.get_by_role('menuitem',name='File',exact=True).click()
                with page.expect_download(timeout=15000) as download:
                    page.get_by_role('menuitem',name='Export PNG',exact=True).click()
                ui=directory/'ui-blur-export.png'; download.value.save_as(str(ui))
                comparison=compare_pngs(ui,directory/(first['id']+'.png'))
                if not comparison['rgba_equal'] or external or errors: raise ValueError('UI/batch mismatch or unexpected external request/browser error')
                result['ui_check']={'case_id':first['id'],'comparison':comparison,'external_requests':external,'browser_errors':errors}
                result['ui_valid']=True
                page.screenshot(path=str(directory/'ui-blur.png'))
                browser.close()
        finally: server.shutdown(); server.server_close()
    except Exception as error:
        result['error']={'type':type(error).__name__,'message':str(error)[:2000]}
        result['procedure_failure']=type(error).__name__=='TimeoutError'
    return result

def selfcheck(directory):
    a=directory/'sentinel-a.png'; b=directory/'sentinel-b.png'
    Image.new('RGBA',(1,1),(1,2,3,4)).save(a); Image.new('RGBA',(1,1),(9,2,3,4)).save(b)
    equal=evaluate('equal',a,a,directory/'equal',load_policy())
    unequal=evaluate('unequal',a,b,directory/'unequal',load_policy())
    if equal['status']!='passed' or unequal['metrics']['rgb_mae_per_channel']!=[8,0,0] or unequal['status']!='failed':
        raise ValueError('Evaluator sentinel failed; stop promotion')
    return {'status':'passed','equal':equal,'unequal':unequal}

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('kind',choices=['reference','brightness-reference','devreference','candidate','build','selfcheck'])
    parser.add_argument('request',type=Path); parser.add_argument('directory',type=Path); args=parser.parse_args()
    d=within(args.directory,EVIDENCE/'learning'); d.mkdir(parents=True,exist_ok=True)
    try:
        request=json.loads(args.request.read_text())
        result={'status':'passed'}
        if args.kind=='reference': result=reference(request,d)
        elif args.kind=='brightness-reference':
            from adapter.brightness import reference_brightness
            result=reference_brightness(request,d)
        elif args.kind=='devreference': result=developer_reference(request,d)
        elif args.kind=='candidate': result=candidate(request,d)
        elif args.kind=='selfcheck': result=selfcheck(d)
        else: build(d,request.get('app'))
    except Exception as error: result={'status':'infrastructure_failure','error':{'type':type(error).__name__,'message':str(error)[:2000]}}
    save(d/'result.json',result)
    return 0 if result.get('status') in ['passed','observed'] or result.get('build_valid') else 1

if __name__=='__main__': raise SystemExit(main())
