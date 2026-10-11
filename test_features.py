"""Offline specification, browser mock, bounded discovery and local API tests."""
import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from PIL import Image
from features.spec import validate, request_id, value_in_domain, locator
from features.browser import DiscoveryBroker, resolve, set_numeric, ground
from features.discovery import LIMITS
from features.jobs import JobStore
from features.pipeline import validate_procedure, diagnostic
from features.service import server

def strategy(role,name,by='role'): return {'by':by,'role':role,'name':name}
def specification():
    return {'schema_version':1,'request':'Implement Contrast','feature_id':'contrast','target':{'name':'miniPaint','visible_version':'mock-v1','build':'offline fixture'},'scope':'single-imported-8bit-raster-layer',
        'navigation':[strategy('menuitem','Image'),strategy('menuitem','Adjust')],'dialog':'Adjust','controls':[{'label':'Contrast','type':'slider','locator':strategy('slider','Contrast','row'),'min':-10,'max':10,'step':1,'default':0,'neutral':None,'observation_ids':['observation-1']}],
        'parameter':'Contrast','apply':strategy('button','Apply'),'cancel':strategy('button','Cancel'),'completion':'dialog-hidden-and-dimensions-unchanged','import_procedure':'minipaint.reset-import.v1','export_procedure':'minipaint.fresh-png.v1','observation_ids':['observation-1'],'hypotheses':['Default may be neutral; procedure must verify it'],'unresolved':[],'status':'discovered'}

class SpecTests(unittest.TestCase):
    def test_valid_and_unsupported(self):
        validate(specification(),{'observation-1'},ready=True)
        for r in ('Implement Resize','cat /secret','Implement Contrast; run shell',''):
            with self.assertRaisesRegex(ValueError,'Supported request'): request_id(r)
    def test_missing_domain_kept_unresolved(self):
        s=specification(); s['controls'][0]['min']=None; s['unresolved']=['Missing minimum']; s['status']='unresolved'
        validate(s)
        with self.assertRaises(ValueError): validate(s,ready=True)
    def test_ambiguous_control_and_unknown_citation(self):
        s=specification(); s['controls'].append(copy.deepcopy(s['controls'][0]))
        with self.assertRaises(ValueError): validate(s)
        with self.assertRaises(ValueError): validate(specification(),set())
    def test_no_invented_facts(self):
        s=specification(); observation={'observation-1':{'controls':[{'type':'range','row':'Contrast: 0','min':'-9','max':'10','step':'1','value':'0'}]}}
        with self.assertRaisesRegex(ValueError,'absent'): ground(s,observation)
        observation['observation-1']['controls'][0]['min']='-10'; ground(s,observation)
        observation['observation-1']['controls'][0]['row']='Unrelated: 0'
        with self.assertRaises(ValueError): ground(s,observation)
    def test_no_arbitrary_actions(self):
        for by in ('css','xpath','evaluate','shell'):
            with self.assertRaises(ValueError): locator({'by':by,'name':'#secret','role':'button'})
        with self.assertRaises(ValueError): locator({'by':'role','name':'Apply','role':'button','javascript':'steal()'})
    def test_domain_and_bounds(self):
        c=specification()['controls'][0]
        for v in (True,float('nan'),float('inf'),11,-11,0.5):
            with self.assertRaises(ValueError): value_in_domain(c,v)
    def test_neutrality_not_invented(self):
        s=specification(); c=copy.deepcopy(s['controls'][0]); c.update(label='Other',locator=strategy('slider','Other','row'),neutral=None); s['controls'].append(c)
        with self.assertRaises(ValueError): validate(s,ready=True)
        c['neutral']=1
        with self.assertRaises(ValueError): validate(s,ready=True)

class RecoveryTests(unittest.TestCase):
    def test_invalid_specification_corrected_and_reused_next_run(self):
        from features.recovery import Memory, validated_decision
        with tempfile.TemporaryDirectory() as d:
            memory = Memory(Path(d)/'memory.json'); calls=[]
            def invoke(index, previous):
                calls.append(previous)
                value=specification()
                if index == 0: value['parameter']='Instructions instead of label'
                return value
            result, failures=validated_decision(invoke, validate, memory)
            self.assertEqual(result['parameter'], 'Contrast')
            self.assertEqual(len(failures), 1)
            self.assertIn('previous_specification', calls[1])
            fresh=Memory(memory.path).guidance()['specification']
            self.assertEqual(fresh['failures'], 1)
            self.assertEqual(fresh['successful_recoveries'], 1)
    def test_specification_corrections_stop_at_limit(self):
        from features.recovery import Memory, validated_decision
        with tempfile.TemporaryDirectory() as d:
            calls=[]
            def invoke(index, previous):
                calls.append(index); return {}
            with self.assertRaises(ValueError):
                validated_decision(invoke, validate, Memory(Path(d)/'memory.json'))
            self.assertEqual(calls, [0, 1])
    def test_memory_rejects_arbitrary_lessons(self):
        from features.recovery import Memory
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'memory.json'; p.write_text(json.dumps({'schema':1,'lessons':{'execute code':{}}}))
            with self.assertRaises(ValueError): Memory(p).guidance()

class ProcedureTests(unittest.TestCase):
    def test_exact_import_readback_and_replay_gates(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp); path=d/'inputs/a.png'; diagnostic(path); calls=[]
            def worker(kind,request,out,timeout):
                calls.append(request); out.mkdir(parents=True); target=out/'output.png'; target.write_bytes(path.read_bytes())
                return {'status':'observed','accepted':request['value'],'original_confirmation':{'rgba_equal':True},'output_path':str(target)}
            self.assertEqual(validate_procedure(specification(),path,d,worker)['status'],'validated')
            self.assertEqual(len(calls),3)
            def bad(*args): return {'status':'observed','accepted':999,'original_confirmation':{'rgba_equal':False},'output_path':str(path)}
            self.assertEqual(validate_procedure(specification(),path,d,bad)['status'],'procedure_failure')
    def test_repeat_mismatch_is_behavior_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp); path=d/'inputs/a.png'; diagnostic(path); count=[0]
            def worker(kind,request,out,timeout):
                count[0]+=1; out.mkdir(parents=True); target=out/'output.png'; target.write_bytes(path.read_bytes())
                if count[0]==3: Image.new('RGBA',(17,9),(1,2,3,255)).save(target)
                return {'status':'observed','accepted':request['value'],'original_confirmation':{'rgba_equal':True},'output_path':str(target)}
            self.assertEqual(validate_procedure(specification(),path,d,worker)['status'],'behavior_mismatch')

class LearningIntegrationTests(unittest.TestCase):
    def test_contrast_broker_preserves_existing_sources(self):
        from features.learning import AdjustmentBroker
        with tempfile.TemporaryDirectory() as d:
            b=AdjustmentBroker(root=Path(d))
            for name in ('src/brightness.ts','src/current-image.ts','package.json','../evaluator/compare.py','layout-packet/reference.png'):
                with self.assertRaises(ValueError): b.path(name,True)
            with self.assertRaises(ValueError): b.path('src/brightness.ts')
            self.assertEqual(b.path('src/contrast.ts',True),Path(d)/'src/contrast.ts')
    def test_validated_procedure_required_before_learning(self):
        from features.learning import AdjustmentHarness
        with self.assertRaisesRegex(ValueError,'validation required'):
            AdjustmentHarness({},Path('unused'),specification(),{'status':'validated','spec_sha256':'wrong'})
    def test_controlled_full_loop_accepts_or_restores_without_promotion(self):
        # Model and worker responses are controlled offline fixtures. Existing independent
        # worker/baseline implementations are tested separately; no real model/browser here.
        from features.learning import AdjustmentHarness, AdjustmentBroker
        from learning.core import Budget, DEFAULTS, Checkpoints
        for suspect in (False,True):
            with self.subTest(suspect=suspect), tempfile.TemporaryDirectory() as temp:
                d=Path(temp); app=d/'app'; (app/'src').mkdir(parents=True)
                (app/'src/main.tsx').write_text('offline shell fixture'); (app/'src/current-image.ts').write_text('offline type fixture')
                h=object.__new__(AdjustmentHarness); h.app=app; h.directory=d/'run'; h.directory.mkdir()
                h.spec=specification(); h.domain=h.spec['controls'][0]; h.notify=lambda *a,**k:None
                h.config={**DEFAULTS,'fresh_experiments':2,'candidates':1}; h.budget=Budget(h.config)
                h.evidence=[]; h.events=[]; h.attempts=[]; h.first_acceptance=None; h.claims=[]; h.stop='not_started'
                h.op={'id':'contrast'}; h.guard=lambda:None
                h.checkpoints=Checkpoints(app,h.directory/'checkpoints',{'src/main.tsx','src/contrast.ts'})
                h.best=h.checkpoints.snapshot('start'); h.emit=lambda kind,**data:h.events.append({'event':kind,**data})
                h.baseline=lambda *a,**k:True
                calls=[]
                def worker(kind,request,out,timeout,*args):
                    calls.append((kind,request)); out.mkdir(parents=True,exist_ok=True)
                    if kind=='feature-reference':
                        target=out/'output.png'; target.write_bytes(Path(request['input_path']).read_bytes())
                        return {'status':'observed','accepted':request['value'],'output_path':str(target)}
                    if kind=='candidate':
                        return {'build_valid':True,'independent':True,'ui_valid':True,'evaluator_suspect':suspect if request['operation']=='contrast' else False,'cases':[{'status':'passed'} for c in request['suite']['cases']]}
                    return {'status':'passed'}
                h.worker=worker
                def ask(prompt,label,schema=None,builder=False,**kw):
                    if label=='planner': return {'plans':[{'question':'Distinguish hypotheses','hypotheses':['A','B'],'predictions':['Low','High'],'usefulness':'Different values','input':{'kind':'patches','width':17,'height':9},'value':v} for v in (-3,4)]}
                    if label=='contract': return {'decision':'Observed mock exports','claims':[{'id':'c','statement':'Mock diagnostic observation','status':'OBSERVED','target_version':'mock','setup':'local fixture','parameter_domain':{'min':-3,'max':4},'scope':'mock cases','supporting_evidence':[e['id'] for e in h.evidence],'contradicting_evidence':[],'alternatives':['A','B'],'unresolved':[],'verification_cases':[]}]}
                    if builder:
                        AdjustmentBroker(root=app).call('shell_write_file',{'path':'src/contrast.ts','text':'// controlled offline candidate fixture'})
                        return 'Written fixture'
                    raise AssertionError(label)
                h.ask=ask; h.run()
                self.assertEqual(h.report['status'],'unresolved' if suspect else 'accepted')
                self.assertEqual((app/'src/contrast.ts').exists(),not suspect)
                self.assertEqual((app/'src/main.tsx').read_text(),'offline shell fixture')
                self.assertFalse(h.report['promoted'])
                ops=[r['operation'] for k,r in calls if k=='candidate']; self.assertEqual(ops,['contrast','brightness'])
                self.assertTrue(any(k=='restore' for k in [e['event'] for e in h.events]))

MOCK='''<button role="menuitem">Image</button><button role="menuitem">Adjust</button>
<div role="dialog"><h2>Adjust</h2><table><tr><td>Contrast:</td><td><input type="range" min="-10" max="10" step="1" value="0"></td></tr></table>
<button onclick="this.closest('[role=dialog]').style.display='none'">Apply</button><button>Cancel</button></div>'''

class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw=sync_playwright().start(); cls.browser=cls.pw.chromium.launch(headless=True)
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()
    def setUp(self): self.page=self.browser.new_page(); self.page.set_content(MOCK)
    def tearDown(self): self.page.close()
    def test_visible_unique_and_missing(self):
        resolve(self.page,strategy('menuitem','Image'))
        self.page.locator('body').evaluate("e=>e.insertAdjacentHTML('beforeend','<button role=menuitem>Image</button>')")
        with self.assertRaisesRegex(ValueError,'Ambiguous'): resolve(self.page,strategy('menuitem','Image'))
        with self.assertRaises(ValueError): resolve(self.page,strategy('button','Missing'))
    def test_row_label_with_colon_sets_numeric_control(self):
        with tempfile.TemporaryDirectory() as d:
            broker = DiscoveryBroker(self.page, Path(d), LIMITS)
            for label, value in [('Contrast:', 3), ('Contrast', -7)]:
                broker.call('visible_set', {'locator': strategy('slider', label, 'row'),
                                           'dialog': 'Adjust', 'value': value})
                self.assertEqual(self.page.locator('input').input_value(), str(value))
            self.page.locator('table').evaluate("e=>e.insertAdjacentHTML('beforeend','<tr><td>Contrast:</td><td><input type=range min=-10 max=10 step=1></td></tr>')")
            with self.assertRaisesRegex(ValueError, 'Ambiguous'):
                resolve(self.page, strategy('slider', 'Contrast:', 'row'))

    def test_value_readback_and_changed_domain(self):
        c=specification()['controls'][0]
        self.assertEqual(set_numeric(self.page,c,-7),-7)
        self.page.locator('input').evaluate("e=>e.max='9'")
        with self.assertRaisesRegex(ValueError,'domain changed'): set_numeric(self.page,c,3)
    def test_rejected_value(self):
        self.page.locator('input').evaluate("e=>e.addEventListener('input',()=>e.value='0')")
        with self.assertRaisesRegex(ValueError,'rejected'): set_numeric(self.page,specification()['controls'][0],3)
    def test_discovery_limits_and_no_evaluation_tool(self):
        with tempfile.TemporaryDirectory() as d:
            limits={**LIMITS,'actions':1,'observations':2}; b=DiscoveryBroker(self.page,Path(d),limits)
            b.call('visible_inspect',{}); b.call('visible_click',{'locator':strategy('menuitem','Image'),'dialog':''})
            with self.assertRaisesRegex(ValueError,'budget'): b.call('visible_inspect',{})
            with self.assertRaises(ValueError): b.call('evaluate',{'code':'secret'})
            b=DiscoveryBroker(self.page,Path(d),{**LIMITS,'output_bytes':10})
            with self.assertRaisesRegex(ValueError,'large'): b.call('visible_inspect',{})
            b=DiscoveryBroker(self.page,Path(d),LIMITS,clock=lambda:999); b.start=0
            with self.assertRaises(TimeoutError): b.call('visible_inspect',{})
    def test_failed_discovery_action_preserves_bounded_diagnostics(self):
        with tempfile.TemporaryDirectory() as d:
            broker = DiscoveryBroker(self.page, Path(d), LIMITS)
            args = {'locator': strategy('slider', 'Missing'), 'dialog': 'Adjust', 'value': 3}
            with self.assertRaisesRegex(ValueError, 'missing'):
                broker.call('visible_set', args)
            record = json.loads((Path(d)/'failed-actions.json').read_text())[0]
            self.assertEqual(record['arguments'], args)
            self.assertEqual(record['error']['type'], 'ValueError')
            with self.assertRaises(ValueError):
                broker.call('evaluate', {'code': 'private payload'})
            self.assertNotIn('arguments', broker.audit[-1])

    def test_autonomous_action_correction_and_fatal_limits(self):
        from features.recovery import Memory
        with tempfile.TemporaryDirectory() as d:
            broker=DiscoveryBroker(self.page, Path(d), LIMITS)
            broker.recovery_enabled=True; broker.memory=Memory(Path(d)/'memory.json')
            bad={'locator':strategy('slider','Missing','row'),'dialog':'Adjust','value':3}
            response=broker.call('visible_set',bad)
            self.assertEqual(json.loads(response[0]['text'])['action_status'], 'failed')
            broker.call('visible_set',{'locator':strategy('slider','Contrast:','row'),'dialog':'Adjust','value':3})
            self.assertEqual(self.page.locator('input').input_value(),'3')
            broker.call('visible_set',bad)
            with self.assertRaises(ValueError): broker.call('visible_set',bad)
            with self.assertRaises(ValueError): broker.call('evaluate',{'code':'secret'})
            self.assertEqual(broker.memory.load()['locator']['failures'],2)
            broker.start -= 100
            with self.assertRaises(TimeoutError): broker.call('visible_inspect',{})

    def test_existing_fresh_export_download(self):
        # Local mock of the existing export dialog; use the unchanged MiniPaint fresh-download code.
        import base64
        from features.browser import FeatureAdapter
        from adapter.png import ROOT
        from learning.core import digest
        import uuid
        d=ROOT/'evidence/learning'/('offline-export-'+uuid.uuid4().hex); d.mkdir(parents=True)
        path=d/'source.png'; diagnostic(path); data=base64.b64encode(path.read_bytes()).decode()
        html='''Size: 17 x 9 px Resolution: 72 <button role="menuitem">File</button>
<button role="menuitem" onclick="document.querySelector('[role=dialog]').style.display='block'">Export ... Shortcut Key: S</button>
<div role="dialog" style="display:none"><h2>Export</h2><table><tr><th>File name:</th><td><input aria-label="File name"></td></tr><tr><th>Resolution:</th><td>72</td></tr></table>
<label><input type="radio" name="format">PNG - Portable Network Graphics</label><label><input type="radio" name="layers">All</label>
<button onclick="const a=document.createElement('a');a.href='data:image/png;base64,DATA';a.download=document.querySelector('input[aria-label]').value+'.png';a.click();this.closest('[role=dialog]').style.display='none'">Ok</button></div>'''.replace('DATA',data)
        self.page.set_content(html)
        a=FeatureAdapter(d); a.page=self.page; a.phase='imported'; a.setup={'canvas_width':17,'canvas_height':9}
        output=d/'fresh.png'; a.export_png(output); self.assertEqual(digest(path),digest(output))
        with self.assertRaisesRegex(ValueError,'overwrite'): a.export_png(output)

class JobTests(unittest.TestCase):
    def test_enabled_api_run_conflict_cancel_reconnect(self):
        with tempfile.TemporaryDirectory() as d, patch('features.service.execute'):
            store=JobStore(d); s=server(store,0,enabled=True); t=threading.Thread(target=s.serve_forever,daemon=True); t.start()
            base=f'http://127.0.0.1:{s.server_port}/api/jobs'
            def post(path,body):
                req=Request(base+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','X-Reforge-Request':'1'})
                with urlopen(req) as response: return json.load(response)
            try:
                job=post('',{'request':'Implement Contrast'})
                with self.assertRaises(HTTPError) as e: post('',{'request':'Implement Contrast'})
                self.assertEqual(e.exception.code,409); e.exception.close()
                with urlopen(base+'/'+job['id']) as response: self.assertEqual(json.load(response)['events'],job['events'])
                self.assertEqual(post('/'+job['id']+'/cancel',{})['status'],'cancelling')
                store.finish(job['id'],{'status':'accepted'}); self.assertEqual(store.get(job['id'])['status'],'cancelled')
                with self.assertRaises(HTTPError) as e: post('',{'request':'Implement Contrast','command':'cmd.exe'})
                self.assertEqual(e.exception.code,400); e.exception.close()
            finally: s.shutdown(); s.server_close(); t.join()
    def test_cancel_before_process_launch(self):
        from features.jobs import execute
        with tempfile.TemporaryDirectory() as d:
            store=JobStore(d); job=store.create('Implement Contrast'); store.cancel(job['id'])
            with patch('features.jobs.BrowserLock'),patch('features.jobs.subprocess.Popen') as process:
                execute(store,job['id']); process.assert_not_called()
            self.assertEqual(store.get(job['id'])['status'],'cancelled')
    def test_owned_tree_stops_child_on_owner_close(self):
        import os, subprocess, sys
        from features.processes import OwnedTree
        if os.name!='nt': self.skipTest('Windows job object lifetime test')
        proc=subprocess.Popen([sys.executable,'-c','import sys,time; sys.stdin.readline(); print("ready",flush=True); time.sleep(60)'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        tree=None
        try:
            tree=OwnedTree(proc); proc.stdin.write('owned\n'); proc.stdin.flush(); proc.stdin.close()
            self.assertEqual(proc.stdout.readline().strip(),'ready')
            start=__import__('time').monotonic(); tree.close(); proc.wait(timeout=5)
            self.assertLess(__import__('time').monotonic()-start,5)
        finally:
            if tree: tree.close()
            if proc.poll() is None: proc.kill(); proc.wait()
            proc.stdout.close()
    def test_lifecycle_concurrency_cancel_reconnect(self):
        with tempfile.TemporaryDirectory() as d:
            store=JobStore(d); job=store.create('Implement Contrast'); ident=job['id']
            with self.assertRaises(RuntimeError): store.create('Implement Contrast')
            store.event(ident,'stage',stage='Investigate',activity='Comparing hypotheses')
            self.assertEqual(JobStore(d).get(ident)['stage'],'Investigate')
            store.cancel(ident); store.finish(ident,{'status':'accepted','classification':'all_gates_pass'})
            self.assertEqual(store.get(ident)['status'],'cancelled')
            store.create('Implement Contrast')
    def test_interruption_never_accepts(self):
        with tempfile.TemporaryDirectory() as d:
            store=JobStore(d); job=store.create('Implement Contrast'); recovered=JobStore(d,recover=True)
            self.assertEqual(recovered.get(job['id'])['status'],'failed')
            with self.assertRaises(ValueError): recovered.get('../../secret')
    def test_api_loopback_disabled_and_allowlist(self):
        with tempfile.TemporaryDirectory() as d:
            store=JobStore(d); s=server(store,0); thread=threading.Thread(target=s.serve_forever,daemon=True); thread.start()
            base=f'http://127.0.0.1:{s.server_port}/api/jobs'
            try:
                self.assertFalse(json.load(urlopen(base))['pilot_enabled'])
                req=Request(base,data=b'{"request":"Implement Contrast"}',headers={'Content-Type':'application/json','X-Reforge-Request':'1'})
                with self.assertRaises(HTTPError) as c: urlopen(req)
                self.assertEqual(c.exception.code,409)
                c.exception.close()
                req=Request(base,data=b'{}',headers={'Content-Type':'application/json','X-Reforge-Request':'1','Origin':'https://attacker.invalid'})
                with self.assertRaises(HTTPError) as c: urlopen(req)
                self.assertEqual(c.exception.code,403)
                c.exception.close()
                job=store.create('Implement Contrast')
                self.assertEqual(json.load(urlopen(base+'/'+job['id']))['id'],job['id'])
                with self.assertRaises(HTTPError) as c: urlopen(base+'/'+job['id']+'/evidence/spec.json')
                c.exception.close()
            finally: s.shutdown(); s.server_close(); thread.join()

if __name__=='__main__': unittest.main()
