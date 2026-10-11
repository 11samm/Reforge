"""Trusted locator/action interpreter; model text never becomes executable code."""
import json
import re
import time
from pathlib import Path
from playwright.sync_api import expect
from adapter.minipaint import MiniPaintAdapter
from adapter.png import compare_pngs, png_info, ROOT
from learning.core import digest, save
from .spec import locator, parameter, validate, value_in_domain

def resolve(root, strategy):
    locator(strategy)
    if strategy['by'] == 'row':
        found = root.get_by_role('row', name=re.compile('^'+re.escape(strategy['name'].rstrip().removesuffix(':').rstrip())+r':')).get_by_role(strategy['role'])
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
                want = value if c['label'] == spec['parameter'] else c['default']
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
 .map(e=>({tag:e.tagName,type:e.getAttribute('type'),role:e.getAttribute('role'),
 label:e.getAttribute('aria-label'),dialog:(e.closest('[role="dialog"]')?.querySelector('h1,h2,h3')?.innerText||'').slice(0,160),row:(e.closest('tr')?.innerText||'').slice(0,160),text:(e.innerText||'').slice(0,160),
 min:e.getAttribute('min'),max:e.getAttribute('max'),step:e.getAttribute('step'),
 value:('value' in e?String(e.value).slice(0,160):null)}))'''

class DiscoveryBroker:
    def __init__(self, page, directory, limits, clock=time.monotonic, notify=lambda **data:None):
        self.page=page; self.directory=Path(directory); self.limits=limits; self.clock=clock; self.start=clock()
        self.actions=0; self.observations={}; self.audit=[]; self.bytes=0
        self.notify=notify
        self.recoverable_errors=0; self.recovery_enabled=False; self.memory=None
        self.site_map=None; self.navigation=[]; self.snapshot=None; self.snapshot_counter=0; self.calls=0; self.storage_bytes=0
    def check(self):
        if self.clock()-self.start >= self.limits['seconds']: raise TimeoutError('Discovery time budget exhausted')
    def call(self, tool, args):
        try:
            return self._call(tool, args)
        except Exception as error:
            # Retain bounded structured action diagnostics, never arbitrary tool payloads.
            entry = {'tool': str(tool)[:80], 'status': 'failed',
                     'error': {'type': type(error).__name__, 'message': str(error)[:1000]}}
            if tool in ('visible_click', 'visible_set') and isinstance(args, dict):
                entry['arguments'] = {key: args[key] for key in ('locator', 'dialog', 'value') if key in args}
                if len(json.dumps(entry, default=str)) > 4000:
                    entry.pop('arguments', None)
            self.audit.append(entry)
            save(self.directory/'failed-actions.json', [row for row in self.audit if row.get('status') == 'failed'])
            from .recovery import category, LESSONS
            kind = category(error) if isinstance(error, ValueError) else None
            if self.recovery_enabled and kind and self.recoverable_errors < 2:
                self.recoverable_errors += 1
                if self.memory: self.memory.record(kind)
                self.notify(activity='Recoverable discovery action failed; inspect and correct within existing budget')
                return [{'type': 'inputText', 'text': json.dumps({'action_status': 'failed',
                        'error': entry['error'], 'guidance': LESSONS[kind],
                        'remaining_corrections': 2-self.recoverable_errors,
                        'instruction': 'This is not a successful observation. Inspect current visible state before correction.'})}]
            raise

    def _response(self, payload):
        content=[{'type':'inputText','text':json.dumps(payload)}]
        size=len(json.dumps(content).encode())
        if size>self.limits['output_bytes']: raise ValueError('Visible output too large; unresolved')
        self.bytes+=size
        if self.bytes>self.limits['total_bytes']: raise ValueError('Cumulative observation output budget exhausted')
        return content

    def _call(self, tool, args):
        self.check(); self.calls+=1
        if self.calls>self.limits['tool_calls']: raise ValueError('Discovery tool budget exhausted')
        from learning.core import exact
        if tool in ('map_query','map_route'):
            if self.site_map is None: raise ValueError('No interaction map configured')
            if tool=='map_query':
                exact(args,['query','parent','page']); payload=self.site_map.query(**args)
            else:
                exact(args,['feature']); payload={'route':self.site_map.route(args['feature'])}
            self.audit.append({'tool':tool,'arguments':args})
            return self._response(payload)
        if tool not in ('visible_inspect','visible_screenshot','visible_click','visible_set'): raise ValueError('Discovery tool denied')
        if tool in ('visible_click','visible_set'):
            exact(args,['locator','dialog']+(['value'] if tool=='visible_set' else []))
            if not isinstance(args['dialog'],str) or len(args['dialog'])>160: raise ValueError('Invalid visible dialog name')
            if self.actions>=self.limits['actions']: raise ValueError('Action budget exhausted')
            self.actions+=1; root=self.page
            if args['dialog']:
                root=self.page.get_by_role('dialog'); expect(root).to_have_count(1)
                expect(root.get_by_role('heading',name=args['dialog'],exact=True)).to_be_visible()
            field=resolve(root,args['locator']); accepted=None
            if tool=='visible_click':
                if args['locator']['role'] not in ('menuitem','button'): raise ValueError('Click only visible menu items/buttons')
                field.click()
                if not args['dialog']:
                    self.navigation=(self.navigation+[args['locator']])[-6:]
            else:
                if args['locator']['role'] not in ('slider','spinbutton'): raise ValueError('Numeric controls only')
                control={'min':float(field.get_attribute('min')),'max':float(field.get_attribute('max')),'step':float(field.get_attribute('step')),
                         'locator':args['locator'],'type':args['locator']['role'],'label':args['locator']['name']}
                if (control['max']-control['min'])/control['step']>2000: raise ValueError('Numeric action size limit')
                accepted=set_numeric(root,control,args['value'])
            self.snapshot=None
            self.audit.append({'tool':tool,'arguments':args,'action_status':'succeeded','accepted':accepted})
            self.notify(activity=f'{tool} succeeded; inspect current visible state separately')
            return self._response({'action_status':'succeeded','accepted':accepted,'inspection_required':True})
        if len(self.observations)>=self.limits['observations']: raise ValueError('Observation budget exhausted')
        ident='observation-'+str(len(self.observations)+1)
        if tool=='visible_screenshot':
            if args!={}: raise ValueError('Screenshot takes no paths/code')
            path=self.directory/(ident+'.png'); self.page.screenshot(path=str(path),full_page=False,timeout=5000)
            data=path.read_bytes()
            if len(data)>self.limits['screenshot_bytes']: raise ValueError('Screenshot output too large')
            import base64
            content=[{'type':'inputText','text':'Untrusted screenshot evidence '+ident},{'type':'inputImage','imageUrl':'data:image/png;base64,'+base64.b64encode(data).decode()}]
            size=len(json.dumps(content).encode()); self.bytes+=size
            if self.bytes>self.limits['total_bytes']: raise ValueError('Cumulative observation output budget exhausted')
            observation={'screenshot':path.name,'sha256':digest(path)}
        else:
            if args=={}: args={'scope':'auto','dialog':'','page':0}
            exact(args,['scope','dialog','page'])
            if args['scope'] not in ('auto','page','dialog') or not isinstance(args['dialog'],str) or len(args['dialog'])>160 or type(args['page']) is not int or not 0<=args['page']<100: raise ValueError('Invalid visible inspection request')
            selection=(args['scope'],args['dialog'])
            if args['page']==0:
                root=self.page.locator('body'); scope='page'
                dialogs=self.page.get_by_role('dialog'); visible=[dialogs.nth(i) for i in range(dialogs.count()) if dialogs.nth(i).is_visible()]
                if args['scope']=='dialog' or (args['scope']=='auto' and visible):
                    if len(visible)!=1: raise ValueError('Ambiguous or missing visible dialog')
                    root=visible[0]; scope='dialog'
                    if args['dialog']: expect(root.get_by_role('heading',name=args['dialog'],exact=True)).to_be_visible()
                raw={'accessibility':root.aria_snapshot(timeout=5000),'controls':root.evaluate(VISIBLE_DOM,timeout=5000)}
                if len(raw['controls'])>2000 or len(json.dumps(raw).encode())>self.limits['total_bytes']: raise ValueError('Visible snapshot storage limit')
                self.storage_bytes+=len(json.dumps(raw).encode())
                if self.storage_bytes>self.limits['total_bytes']: raise ValueError('Cumulative visible snapshot storage limit')
                from .inspection import pages
                chunks=pages(raw,self.limits['output_bytes']); self.snapshot_counter+=1
                self.snapshot={'id':'snapshot-'+str(self.snapshot_counter),'selection':selection,'pages':chunks,'scope':scope}
                save(self.directory/(self.snapshot['id']+'.json'),raw)
            if not self.snapshot or self.snapshot['selection']!=selection: raise ValueError('Snapshot changed; request page zero again')
            if args['page']>=len(self.snapshot['pages']): raise ValueError('Unknown observation page')
            observation={**self.snapshot['pages'][args['page']], 'snapshot_id':self.snapshot['id'],'page':args['page'],
                         'pages':len(self.snapshot['pages']),'scope':self.snapshot['scope']}
            content=self._response({'id':ident,'untrusted_visible_data':observation})
            if self.site_map:
                source=self.directory.relative_to(ROOT).as_posix() if self.directory.is_relative_to(ROOT) else self.directory.name
                self.site_map.observe(self.navigation,ident,observation['controls'],source+'/'+ident)
        self.observations[ident]=observation; save(self.directory/(ident+'.json'),observation)
        self.audit.append({'tool':tool,'arguments':args,'observation_id':ident})
        self.notify(activity=f'{tool}: {self.actions}/{self.limits["actions"]} actions; {len(self.observations)}/{self.limits["observations"]} observations')
        self.check(); return content


def ground(spec, observations):
    """Reject invented domains/defaults even when the model cites a valid ID."""
    validate(spec,observations,ready=True)
    snapshots={o.get('snapshot_id') for o in observations.values() if any(r.get('dialog')==spec['dialog'] for r in o.get('controls',[]))}
    for snapshot in snapshots-{None}:
        rows=[o for o in observations.values() if o.get('snapshot_id')==snapshot]
        if {o['page'] for o in rows} != set(range(rows[0]['pages'])): raise ValueError('Inspect every page of the dialog before declaring discovery complete')
    dialog_controls=[r for o in observations.values() for r in o.get('controls',[]) if r.get('dialog')==spec['dialog'] and r.get('type') in ('range','number')]
    labels={c['label'] for c in spec['controls']}
    for r in dialog_controls:
        if not any(r.get('label')==label or (r.get('row') or '').startswith(label.rstrip().removesuffix(':').rstrip()+':') for label in labels): raise ValueError('Unspecified numeric dialog control; unresolved')
    for c in spec['controls']:
        wanted={'min':c['min'],'max':c['max'],'step':c['step'],'value':c['default']}
        rows=[r for ident in c['observation_ids'] for r in observations[ident].get('controls',[]) if r.get('type') == ('range' if c['type']=='slider' else 'number') and (r.get('label')==c['label'] or (r.get('row') or '').startswith(c['label'].rstrip().removesuffix(':').rstrip()+':'))]
        if not any(all(r.get(k) is not None and float(r[k])==v for k,v in wanted.items()) for r in rows): raise ValueError('Control facts absent from cited visible observations')
    return spec
