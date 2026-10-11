"""Trusted locator/action interpreter; model text never becomes executable code."""
import json
import re
import time
from pathlib import Path
from playwright.sync_api import expect
from adapter.minipaint import MiniPaintAdapter
from adapter.png import compare_pngs, png_info
from learning.core import digest, save
from .spec import locator, parameter, validate, value_in_domain

def resolve(root, strategy):
    locator(strategy)
    if strategy['by'] == 'row':
        found = root.get_by_role('row', name=re.compile('^'+re.escape(strategy['name'])+r':')).get_by_role(strategy['role'])
    elif strategy['by'] == 'label':
        found = root.get_by_label(strategy['name'], exact=True)
    else:
        found = root.get_by_role(strategy['role'], name=strategy['name'], exact=True)
    # Filter visibility before uniqueness, so hidden menu duplicates cannot be selected.
    visible = [found.nth(i) for i in range(found.count()) if found.nth(i).is_visible()]
    if len(visible) != 1: raise ValueError('Ambiguous or missing visible control: '+strategy['name'])
    return visible[0]

def set_numeric(root, control, value):
    value_in_domain(control, value)
    field = resolve(root, control['locator'])
    expect(field).to_be_enabled()
    for key in ('min','max','step'):
        got = field.get_attribute(key)
        if got is None or float(got) != control[key]: raise ValueError('Observed domain changed: '+control['label'])
    if control['type'] == 'spinbutton': field.fill(str(value))
    else:
        field.press('Home')
        for _ in range(round((value-control['min'])/control['step'])): field.press('ArrowRight')
    accepted = float(field.input_value())
    if accepted != value: raise ValueError('Requested value rejected: '+control['label'])
    return accepted

class FeatureAdapter(MiniPaintAdapter):
    def apply_feature(self, spec, value):
        validate(spec, ready=True); value_in_domain(parameter(spec), value)
        if self.phase != 'imported': raise ValueError('Operation requires confirmed fresh import')
        with self.action('declarative-adjustment', requested=value) as record:
            for strategy in spec['navigation']: resolve(self.page, strategy).click()
            dialog = self.dialog(spec['dialog'])
            if self.page.get_by_role('dialog').count() != 1: raise ValueError('Ambiguous dialog')
            values = {}
            for c in spec['controls']:
                field = resolve(dialog, c['locator'])
                if float(field.input_value()) != c['default']: raise ValueError('Fresh dialog default changed')
                want = value if c['label'] == spec['parameter'] else c['neutral']
                values[c['label']] = {'requested':want, 'accepted':set_numeric(dialog,c,want)}
            record['values'] = values
            self.capture_screenshot(self.artifact_dir/'accepted-values.png')
            resolve(dialog,spec['apply']).click(); expect(dialog).not_to_be_visible()
            self.assert_dimensions(); expect(self.page.locator('[id="layer_name"]')).to_have_count(1)
            self.capture_screenshot(self.artifact_dir/'operation-complete.png')
            self.phase = 'operated'
            return values

def reference(request, directory):
    """The worker's outer deadline kills its process tree, including the browser."""
    from adapter.png import within
    spec = validate(request['spec'], ready=True)
    path = within(request['input_path'], directory.parent.parent/'inputs')
    if digest(path) != request['input_sha256']: raise ValueError('Input changed')
    info = png_info(path)
    setup = {'canvas_width':info['width'],'canvas_height':info['height'],'transparent':True,'resolution_ui':72,'imported_layer_offset':[0,0],'layer_opacity_percent':100,'layer_rotation_degrees':0,'fresh_original_input':True,'other_visible_layers':False}
    report = {'status':'procedure_failure','requested':request['value']}
    try:
        with FeatureAdapter(directory,headed=True,window_position=[1600,0],diagnostic_input_root=path.parent) as a:
            a.reset_reference(setup); report['target'] = a.identity
            if a.identity['name'] != spec['target']['name'] or a.identity['visible_about_version'] != spec['target']['visible_version']: raise ValueError('Target identity changed')
            a.import_image(path,route='file_chooser'); a.export_png(directory/'original-confirmation.png')
            report['original_confirmation'] = compare_pngs(path,directory/'original-confirmation.png')
            if not report['original_confirmation']['rgba_equal']: raise ValueError('Original import normalization; no behavioral evidence')
            report['values'] = a.apply_feature(spec,request['value'])
            report['accepted'] = report['values'][spec['parameter']]['accepted']
            report['output'] = a.export_png(directory/'output.png')
            report['output_path'] = str(directory/'output.png'); report['actions'] = a.actions
            report['status'] = 'observed'
    except Exception as error: report['error'] = {'type':type(error).__name__,'message':str(error)[:1000]}
    save(directory/'reference-record.json',report)
    return report

# Fixed code reads only rendered DOM and native numeric attributes. Never model-supplied JS.
VISIBLE_DOM = '''body => [...body.querySelectorAll('button,input,label,[role="menuitem"],h1,h2,h3')]
 .filter(e=>e.getClientRects().length && getComputedStyle(e).visibility!=='hidden')
 .slice(0,150).map(e=>({tag:e.tagName,type:e.getAttribute('type'),role:e.getAttribute('role'),
 label:e.getAttribute('aria-label'),dialog:(e.closest('[role="dialog"]')?.querySelector('h1,h2,h3')?.innerText||'').slice(0,160),row:(e.closest('tr')?.innerText||'').slice(0,160),text:(e.innerText||'').slice(0,160),
 min:e.getAttribute('min'),max:e.getAttribute('max'),step:e.getAttribute('step'),
 value:('value' in e?String(e.value).slice(0,160):null)}))'''

class DiscoveryBroker:
    def __init__(self, page, directory, limits, clock=time.monotonic, notify=lambda **data:None):
        self.page=page; self.directory=Path(directory); self.limits=limits; self.clock=clock; self.start=clock()
        self.actions=0; self.observations={}; self.audit=[]; self.bytes=0
        self.notify=notify
    def check(self):
        if self.clock()-self.start >= self.limits['seconds']: raise TimeoutError('Discovery time budget exhausted')
    def call(self, tool, args):
        self.check()
        if tool not in ('visible_inspect','visible_screenshot','visible_click','visible_set'): raise ValueError('Discovery tool denied')
        if len(self.observations) >= self.limits['observations']: raise ValueError('Observation budget exhausted')
        if tool in ('visible_inspect','visible_screenshot'):
            if args != {}: raise ValueError('Inspection takes no code/paths')
        else:
            from learning.core import exact
            exact(args,['locator','dialog']+(['value'] if tool=='visible_set' else []))
            if not isinstance(args['dialog'],str) or len(args['dialog'])>160: raise ValueError('Invalid visible dialog name')
            if self.actions >= self.limits['actions']: raise ValueError('Action budget exhausted')
            self.actions += 1
            root=self.page
            if args['dialog']:
                root=self.page.get_by_role('dialog'); expect(root).to_have_count(1)
                expect(root.get_by_role('heading',name=args['dialog'],exact=True)).to_be_visible()
            field=resolve(root,args['locator'])
            if tool=='visible_click':
                if args['locator']['role'] not in ('menuitem','button'): raise ValueError('Click only visible menu items/buttons')
                field.click()
            else:
                if args['locator']['role'] not in ('slider','spinbutton'): raise ValueError('Numeric controls only')
                control={'min':float(field.get_attribute('min')),'max':float(field.get_attribute('max')),'step':float(field.get_attribute('step')),'locator':args['locator'],'type':args['locator']['role'],'label':args['locator']['name']}
                if (control['max']-control['min'])/control['step']>2000: raise ValueError('Numeric action size limit')
                set_numeric(root,control,args['value'])
        ident='observation-'+str(len(self.observations)+1)
        if tool=='visible_screenshot':
            path=self.directory/(ident+'.png'); self.page.screenshot(path=str(path),full_page=False,timeout=5000)
            data=path.read_bytes()
            if len(data)>self.limits['screenshot_bytes']: raise ValueError('Screenshot output too large')
            import base64
            content=[{'type':'inputText','text':'Untrusted screenshot evidence '+ident},{'type':'inputImage','imageUrl':'data:image/png;base64,'+base64.b64encode(data).decode()}]
            observation={'screenshot':path.name,'sha256':digest(path)}; size=len(data)
        else:
            observation={'accessibility':self.page.locator('body').aria_snapshot(timeout=5000),'controls':self.page.locator('body').evaluate(VISIBLE_DOM,timeout=5000)}
            encoded=json.dumps(observation,allow_nan=False); size=len(encoded.encode())
            if size>self.limits['output_bytes']: raise ValueError('Visible output too large; unresolved')
            content=[{'type':'inputText','text':json.dumps({'id':ident,'untrusted_visible_data':observation})}]
        response_size=len(json.dumps(content).encode())
        if tool!='visible_screenshot' and response_size>self.limits['output_bytes']: raise ValueError('Visible output too large; unresolved')
        self.bytes+=response_size
        if self.bytes>self.limits['total_bytes']: raise ValueError('Cumulative observation output budget exhausted')
        self.observations[ident]=observation
        save(self.directory/(ident+'.json'),observation)
        self.audit.append({'tool':tool,'arguments':args,'observation_id':ident})
        self.notify(activity=f'{tool}: {self.actions}/{self.limits["actions"]} actions; {len(self.observations)}/{self.limits["observations"]} observations')
        self.check()
        return content

def ground(spec, observations):
    """Reject invented domains/defaults even when the model cites a valid ID."""
    validate(spec,observations,ready=True)
    dialog_controls=[r for o in observations.values() for r in o.get('controls',[]) if r.get('dialog')==spec['dialog'] and r.get('type') in ('range','number')]
    labels={c['label'] for c in spec['controls']}
    for r in dialog_controls:
        if not any(r.get('label')==label or (r.get('row') or '').startswith(label+':') for label in labels): raise ValueError('Unspecified numeric dialog control; unresolved')
    for c in spec['controls']:
        wanted={'min':c['min'],'max':c['max'],'step':c['step'],'value':c['default']}
        rows=[r for ident in c['observation_ids'] for r in observations[ident].get('controls',[]) if r.get('type') == ('range' if c['type']=='slider' else 'number') and (r.get('label')==c['label'] or (r.get('row') or '').startswith(c['label']+':'))]
        if not any(all(r.get(k) is not None and float(r[k])==v for k,v in wanted.items()) for r in rows): raise ValueError('Control facts absent from cited visible observations')
    return spec
