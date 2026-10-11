"""Offline controlled fixtures: no real-trajectory failure is manufactured."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from adapter.png import ROOT
from build_shell import FileBroker
from learning.core import (DEFAULTS, Budget, Checkpoints, decide, relocated, validate_claims, validate_config, validate_plan)
from learning.diagnostics import generate, describe
from learning.model import BlurBroker

def plan():
    return {'question':'How are boundaries handled?','hypotheses':['zero outside','replicate edge'],
            'input':{'kind':'impulse_boundary','width':33,'height':33},'percentage':3,
            'predictions':['edge energy lost','edge energy retained'],'usefulness':'Discriminate boundary behavior'}

def claim():
    return {'id':'boundary','statement':'Alpha changes at edge','status':'OBSERVED','target_version':'4.14.3',
            'setup':'fresh transparent one-layer','parameter_domain':{'min':3,'max':3},'scope':'33x33 impulse',
            'supporting_evidence':['fresh-01'],'contradicting_evidence':[],'alternatives':['unknown kernel'],
            'unresolved':['rounding'],'verification_cases':['fresh-01']}

SOURCE=ROOT/'evidence/learning/20261010T184129Z-78c8e934'

def saved_evidence(ident):
    """Read-only actual attempt-2 evidence record used as a fixture."""
    return relocated(json.loads((SOURCE/'experiments'/ident/'evidence.json').read_text()))

def candidate(**kwargs):
    value={'build_valid':True,'independent':True,'baseline_pass':True,'evaluator_suspect':False,
           'suite_sha256':'frozen-v1','cases':[{'status':'passed','metrics':{'rgb_mae':0.2,'alpha_mae':0.1},'regions':{}}]}
    value.update(kwargs); return value

class LearningTests(unittest.TestCase):
    def test_schema_and_generator_limits(self):
        c=validate_config(DEFAULTS); validate_plan(plan(),c)
        for k,v in [('fresh_experiments',21),('candidates',6),('run_seconds',601),('retries',2),('model_seconds',True)]:
            bad=copy.deepcopy(c);bad[k]=v
            with self.assertRaises(ValueError): validate_config(bad)
        for v in [True,-1,11,1.5,'3']:
            bad=plan();bad['percentage']=v
            with self.assertRaises(ValueError): validate_plan(bad,c)
        bad=plan();bad['input']['kind']='arbitrary_script'
        with self.assertRaises(ValueError):validate_plan(bad,c)
        bad=plan();bad['input']['width']=258
        with self.assertRaises(ValueError):validate_plan(bad,c)
        bad=plan();bad['extra']='path'
        with self.assertRaises(ValueError):validate_plan(bad,c)

    def test_deterministic_diagnostic_original_is_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'evidence') as t:
            a,b=Path(t)/'a.png',Path(t)/'b.png'
            generate(plan(),a,DEFAULTS);generate(plan(),b,DEFAULTS)
            self.assertEqual(a.read_bytes(),b.read_bytes())
            self.assertEqual(describe(a)['center_row'][0],[255,255,255,255])
            with self.assertRaises(ValueError):generate(plan(),a,DEFAULTS)

    def test_budget_reserve_counts_and_timeouts(self):
        now=[0];c=copy.deepcopy(DEFAULTS);c.update(fresh_experiments=1,candidates=1)
        budget=Budget(c,lambda:now[0]);budget.spend('experiment');budget.spend('candidate')
        with self.assertRaises(TimeoutError):budget.spend('experiment')
        with self.assertRaises(TimeoutError):budget.spend('candidate')
        now[0]=501
        with self.assertRaises(TimeoutError):budget.timeout(30)
        self.assertEqual(budget.timeout(120,True),99)
        now[0]=600
        with self.assertRaises(TimeoutError):budget.timeout(1,True)

    def test_claim_evidence_and_verification_status(self):
        validate_claims([claim()],['fresh-01'],['fresh-01'])
        c=claim();c['status']='VERIFIED_WITHIN_SCOPE'
        with self.assertRaises(ValueError):validate_claims([c],['fresh-01'],['fresh-01'])
        validate_claims([c],['fresh-01'],['fresh-01'],['fresh-01'])
        c=claim();c['supporting_evidence']=['invented']
        with self.assertRaises(ValueError):validate_claims([c],['fresh-01'],['fresh-01'])
        c=claim();c['status']='CONTRADICTED'
        with self.assertRaises(ValueError):validate_claims([c],['fresh-01'],['fresh-01'])

    def test_acceptance_and_tie_same_suite(self):
        good=candidate();self.assertEqual(decide(good),(True,'all_gates_pass'))
        self.assertEqual(decide(good,good),(False,'tie_or_no_improvement'))
        for field in ['build_valid','independent','baseline_pass']:
            self.assertFalse(decide(candidate(**{field:False}))[0])
        self.assertEqual(decide(candidate(evaluator_suspect=True)),(False,'evaluator_defect'))
        self.assertEqual(decide(candidate(procedure_failure=True)),(False,'procedure_infrastructure'))
        bad=candidate(cases=[{'status':'failed','metrics':{'rgb_mae':0,'alpha_mae':0},'regions':{}}])
        self.assertFalse(decide(bad)[0])
        with self.assertRaises(ValueError):decide(candidate(suite_sha256='expanded'),good)

    def test_controlled_rollback_fixture_preserves_trusted_artifacts(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'evidence') as t:
            root=Path(t);app=root/'generated';app.mkdir();(app/'src').mkdir()
            (app/'src/main.tsx').write_text('CONTROLLED BASELINE FIXTURE')
            records=root/'evidence';records.mkdir();failure=records/'failure.json';failure.write_text('controlled deliberate invalid candidate')
            cp=Checkpoints(app,records/'checkpoints',{'src/main.tsx','src/gaussian-blur.ts'})
            best=cp.snapshot('best');(app/'src/main.tsx').write_text('CONTROLLED INVALID CANDIDATE')
            (app/'src/gaussian-blur.ts').write_text('throw Error("controlled fixture")')
            rejected=cp.snapshot('rejected');self.assertFalse(decide(candidate(build_valid=False))[0]);cp.restore(best)
            self.assertEqual((app/'src/main.tsx').read_text(),'CONTROLLED BASELINE FIXTURE')
            self.assertFalse((app/'src/gaussian-blur.ts').exists())
            self.assertTrue(failure.exists());self.assertTrue((rejected/'src/gaussian-blur.ts').exists())
            # Corrupt checkpoint must fail validation before modifying the current workspace.
            (best/'src/main.tsx').write_text('corrupt')
            with self.assertRaises(ValueError):cp.restore(best)
            self.assertEqual((app/'src/main.tsx').read_text(),'CONTROLLED BASELINE FIXTURE')

    def test_builder_denies_expected_policy_execution_and_config(self):
        broker=BlurBroker()
        for p in ['evaluator/compare.py','fixtures/development/reference_outputs/gb010.png','../learning/run.py',
                  'package.json','vite.config.ts','src/style.css']:
            with self.assertRaises(ValueError):broker.path(p,True)
        with self.assertRaises(ValueError):broker.call('browser_evaluate',{'script':'1'})
        with self.assertRaises(ValueError):broker.call('exec_command',{'cmd':'dir'})
        self.assertEqual(broker.path('src/gaussian-blur.ts',True).parent,ROOT/'generated-app/src')

    def test_diagnostic_root_cannot_point_to_protected_or_app(self):
        from adapter.minipaint import MiniPaintAdapter
        with tempfile.TemporaryDirectory(dir=ROOT/'evidence') as t:
            for p in [ROOT/'generated-app',ROOT/'fixtures/development/inputs']:
                with self.assertRaises(ValueError):MiniPaintAdapter(t,diagnostic_input_root=p)

    def test_contract_schema_constrains_actual_evidence_ids(self):
        from learning.run import Harness
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory(dir=ROOT/'evidence') as t:
            h=object.__new__(Harness);h.directory=Path(t);h.evidence=[saved_evidence('fresh-01')];h.claims=[];h.incumbent=None
            h.ask=Mock(return_value={'claims':[claim()],'decision':'Observed exported edge alpha'})
            h.emit=Mock();h.update_contract('controlled-contract')
            schema=h.ask.call_args.args[2]
            for key in ['supporting_evidence','contradicting_evidence','verification_cases']:
                self.assertEqual(schema['properties']['claims']['items']['properties'][key]['items']['enum'],['fresh-01'])

    def test_planner_rejects_replayed_and_overbudget_requests(self):
        from learning.run import Harness
        h=object.__new__(Harness);h.config=copy.deepcopy(DEFAULTS);h.budget=Budget(h.config);h.evidence=[]
        self.assertEqual(len(h.validate_plans({'plans':[plan()]})),1)
        h.evidence=[{'plan':plan()}]
        with self.assertRaises(ValueError):h.validate_plans({'plans':[plan()]})
        h.evidence=[];h.budget.experiments=12
        with self.assertRaises(TimeoutError):h.validate_plans({'plans':[plan()]})

    def test_controlled_full_orchestration_acceptance_and_restore(self):
        from learning.run import Harness
        from unittest.mock import Mock
        for outcome in ['accept','reject','timeout']:
            accept=outcome=='accept'
            with self.subTest(outcome=outcome),tempfile.TemporaryDirectory(dir=ROOT/'evidence') as t:
                root=Path(t);app=root/'app';(app/'src').mkdir(parents=True)
                (app/'src/main.tsx').write_text('CONTROLLED START')
                h=object.__new__(Harness);h.directory=root/'run';h.directory.mkdir()
                h.app=app;h.dev_app=False;h.mode='clean_start';h.prefix='fresh-';h.provenance={'mode':'clean_start'}
                h.accepted=None;h.base_result=None;h.base_label=None;h.packet_sizes=[]
                h.config=copy.deepcopy(DEFAULTS);h.config['candidates']=1;h.budget=Budget(h.config)
                h.checkpoints=Checkpoints(app,h.directory/'checkpoints',{'src/main.tsx','src/gaussian-blur.ts'})
                h.best=h.checkpoints.snapshot('start');h.attempts=[];h.events=[];h.claims=[]
                h.evidence=[{'id':'fresh-01','percentage':3}];h.incumbent=None;h.first_acceptance=None;h.stop='not_started'
                h.suite={'id':'controlled-visible'};h.suite_hash='frozen-v1'
                h.emit=Mock();h.guard=Mock();h.worker=Mock(return_value={'status':'passed'})
                h.baseline=Mock(return_value=True);h.prepared=Mock();h.experiment=Mock();h.freeze=Mock();h.update_contract=Mock()
                h.ask=Mock(return_value={'plans':[plan()]})
                result=candidate();result['cases'][0]['case_id']='fresh-01'
                if not accept:result['cases'][0]['status']='failed'
                h.evaluate=Mock(side_effect=[candidate(independent=False,cases=[]),result])
                def controlled_builder(*args):
                    (app/'src/main.tsx').write_text('CONTROLLED CANDIDATE')
                    (app/'src/gaussian-blur.ts').write_text('// controlled fixture, never production')
                    if outcome=='timeout':raise TimeoutError('CONTROLLED model deadline fixture')
                h.builder=controlled_builder
                with patch('learning.run.APP',app),patch('learning.run.ROOT',root):h.run()
                self.assertEqual(h.report['status'],'accepted' if accept else 'unresolved')
                self.assertEqual((app/'src/main.tsx').read_text(),'CONTROLLED CANDIDATE' if accept else 'CONTROLLED START')
                self.assertEqual((app/'src/gaussian-blur.ts').exists(),accept)
                self.assertTrue((h.directory/'candidates/candidate-1.json').exists())
                checkpoint='candidate-1-partial' if outcome=='timeout' else 'candidate-1'
                self.assertTrue((h.directory/'checkpoints'/checkpoint/'src/gaussian-blur.ts').exists())
                self.assertEqual(h.budget.candidates,1)

    def test_lossless_compact_export_profiles(self):
        from learning.diagnostics import compact_samples
        row=[[0,0,0,255]]*12+[[19,37,91,128]]*2+[[0,0,0,255]]*3
        sample={k:row for k in ['center_row','center_column','top_row']}
        compact=compact_samples(sample)
        for key in sample:
            reconstructed=[]
            for start,length,*rgba in compact[key+'_runs']:
                self.assertEqual(start,len(reconstructed));reconstructed.extend([rgba]*length)
            self.assertEqual(reconstructed,row)
            self.assertEqual(len(compact[key+'_runs']),3)

    def test_builder_journals_partial_writes_outside_capability_boundary(self):
        from learning.model import WRITABLE
        with tempfile.TemporaryDirectory(dir=ROOT/'evidence') as t:
            parent=Path(t);app=parent/'app';packet=parent/'packet';app.mkdir();packet.mkdir()
            broker=object.__new__(BlurBroker);FileBroker.__init__(broker,app,packet)
            broker.files=set(WRITABLE);broker.journal=parent/'audit'
            broker.call('shell_write_file',{'path':'src/gaussian-blur.ts','text':'// CONTROLLED PARTIAL SOURCE'})
            artifact=Path(broker.audit[-1]['written_source_artifact'])
            self.assertEqual(artifact.read_text(),'// CONTROLLED PARTIAL SOURCE')
            with self.assertRaises(ValueError):broker.path('audit/'+artifact.name)

    def test_controlled_host_provenance_archive(self):
        from contextlib import redirect_stdout
        import io
        from learning.run import Harness
        with tempfile.TemporaryDirectory(dir=ROOT/'evidence') as t:
            root=Path(t);app=root/'generated-app';(app/'src').mkdir(parents=True)
            (app/'src/main.tsx').write_text('// CONTROLLED START')
            for name in ['smoke.py','build_shell.py','verify_shell.py','baseline_regressions.py','workspaces.json']:
                (root/name).write_text('CONTROLLED HOST FIXTURE')
            (root/'learning').mkdir();(root/'learning/run.py').write_text('CONTROLLED ORCHESTRATOR FIXTURE')
            with patch('learning.run.ROOT',root),patch('learning.run.APP',app),redirect_stdout(io.StringIO()):
                h=Harness(copy.deepcopy(DEFAULTS))
            self.assertEqual((h.directory/'executed-host-source/learning/run.py').read_text(),'CONTROLLED ORCHESTRATOR FIXTURE')
            self.assertEqual((h.directory/'executed-host-source/workspaces.json').read_text(),'CONTROLLED HOST FIXTURE')
            self.assertTrue((h.best/'manifest.json').exists())


class PacketTests(unittest.TestCase):
    def test_channel_profile_encoding_is_lossless(self):
        from learning.packets import checked_profile, decode_profile, encode_profile
        import random
        rng=random.Random(7)
        rows=[[[0,0,0,255]]*12+[[19,37,91,128]]*2,[[v,v,v,255] for v in [0,1,1,2,255,255]],
              [[rng.randint(-255,255) for _ in range(4)] for _ in range(97)],[[5,5,5,0]]]
        for row in rows:
            self.assertEqual(decode_profile(encode_profile(row)),row);checked_profile(row)
        self.assertEqual(encode_profile(rows[1]),{'n':6,'RGB':'0 1*2 2 255*2','A':'255*6'})

    def test_compact_summary_round_trips_saved_exports(self):
        from learning.packets import compact_summary, expand_summary
        for ident in ['fresh-01','fresh-03','fresh-04']:
            samples=saved_evidence(ident)['export_samples']
            expanded=expand_summary(compact_summary(samples))
            for key in ['center_row','center_column','top_row','samples','alpha_sum','red_sum']:
                self.assertEqual(expanded[key],samples[key])

    def test_generated_inputs_only_omitted_when_exactly_reconstructed(self):
        from learning.packets import evidence_table, generated_input_matches
        e=saved_evidence('fresh-02');self.assertTrue(generated_input_matches(e))
        self.assertEqual(evidence_table([e])['items'][0]['input'],{'generator':'impulse_boundary','width':65,'height':49})
        wrong=copy.deepcopy(e);wrong['plan']['input']['kind']='impulse_center'
        self.assertFalse(generated_input_matches(wrong))
        self.assertIn('row_y24',evidence_table([wrong])['items'][0]['input'])

    def test_limits_fail_before_any_model_request(self):
        from learning.run import Harness
        from learning.packets import PacketLimitError
        with tempfile.TemporaryDirectory(dir=ROOT/'evidence') as t:
            h=object.__new__(Harness);h.directory=Path(t);h.config=copy.deepcopy(DEFAULTS);h.packet_sizes=[];h.events=[]
            h.budget=Budget(h.config);h.config['packet_limits']['contract']={'bytes':1000,'tokens':1000}
            with patch('learning.run.model.invoke') as invoke,patch('builtins.print'):
                with self.assertRaises(PacketLimitError) as raised:h.ask('x'*2000,'oversized',None,role='contract')
                invoke.assert_not_called()
            self.assertIn('no model request was sent',str(raised.exception))
            report=json.loads((Path(t)/'packet-sizes.json').read_text())
            self.assertFalse(report['packets'][0]['within_limits']);self.assertIn('calibrated',report['method'])

    def test_configured_limits_reject_historical_and_prechange_packets(self):
        from learning.packets import PacketLimitError, enforce, measure
        limits=DEFAULTS['packet_limits']
        for role,name in [('contract','contract-1'),('route','route-2'),('repair','builder-3'),('builder','builder-1')]:
            r=json.loads((SOURCE/'model'/name/'request.json').read_text())
            with self.assertRaises(PacketLimitError):enforce(measure(role,r['prompt'],r['output_schema']),limits[role])
        pre=ROOT/'evidence/packet-sizes/prechange-prompts'
        for role,name in [('contract','contract'),('route','route'),('repair','builder-repair')]:
            d=json.loads((pre/(name+'.json')).read_text())
            with self.assertRaises(PacketLimitError):enforce(measure(role,d['prompt'],d['schema']),limits[role])

    def test_estimator_matches_recorded_decision_usage(self):
        from learning.packets import measure
        for name in ['planner','contract-1','route-1','route-2']:
            r=json.loads((SOURCE/'model'/name/'request.json').read_text())
            actual=json.loads((SOURCE/'model'/name/'invocation.json').read_text())['usage']['total']['inputTokens']
            estimate=measure('contract',r['prompt'],r['output_schema'])['estimated_tokens']
            self.assertLess(abs(estimate-actual)/actual,0.01,name)

    def test_current_packets_retain_scoring_ids_and_failures_within_limits(self):
        from learning.packet_report import current_packets
        from learning.packets import measure
        config=copy.deepcopy(DEFAULTS);packets=current_packets(config)
        suite=json.loads((SOURCE/'suites/visible-blur-v1.json').read_text())
        for role in ['planner','contract','route','builder','repair']:
            prompt,schema,supplied=packets[role];m=measure(role,prompt,schema,supplied)
            self.assertLessEqual(m['bytes'],config['packet_limits'][role]['bytes'],role)
            self.assertLessEqual(m['estimated_tokens'],config['packet_limits'][role]['tokens'],role)
        body=json.loads(packets['repair'][0].split('Packet: ',1)[1])
        self.assertEqual(body['scoring']['policy'],suite['policy'])
        self.assertEqual([i['id'] for i in body['visible_evidence']['items']],[c['id'] for c in suite['cases']])
        evaluation=json.loads((SOURCE/'evaluations/candidate-2/evaluation.json').read_text())
        failed={c['case_id']:c['reasons'] for c in evaluation['cases'] if c['status']!='passed'}
        self.assertEqual({c['id']:c['reasons'] for c in body['repair']['discrepancies']['failed_cases']},failed)
        self.assertNotIn(str(ROOT),packets['repair'][0]);self.assertNotIn('artifacts',packets['repair'][0])
        self.assertIn('workspace_operation',body['repair']);self.assertNotIn('last_rejected_operation',body['repair'])

    def test_evidence_reader_is_bounded_and_exact(self):
        from learning.packets import EvidenceReader, decode_profile
        e=saved_evidence('fresh-01')
        reader=EvidenceReader({'fresh-01':{'export':e['expected'],'input':e['input']}},2)
        out=json.loads(reader.call({'id':'fresh-01','image':'export','axis':'row','index':24})[0]['text'])
        self.assertEqual(decode_profile(out['profile']),e['export_samples']['center_row'])
        self.assertNotIn('evidence',json.dumps(out))
        for bad in [{'id':'gb999','image':'export','axis':'row','index':0},{'id':'fresh-01','image':'export','axis':'row','index':49},
                    {'id':'fresh-01','image':'candidate','axis':'row','index':0},{'id':'fresh-01','image':'export','axis':'row'}]:
            with self.assertRaises(ValueError):reader.call(bad)
        reader.call({'id':'fresh-01','image':'input','axis':'column','index':32})
        with self.assertRaises(ValueError):reader.call({'id':'fresh-01','image':'input','axis':'column','index':1})

    def test_builder_tool_call_cap_and_evidence_audit(self):
        from build_shell import ShellRuntime
        from learning.packets import EvidenceReader
        from unittest.mock import Mock
        e=saved_evidence('fresh-01')
        broker=BlurBroker(reader=EvidenceReader({'fresh-01':{'export':e['expected']}},4))
        runtime=object.__new__(ShellRuntime);runtime.broker=broker;runtime.requests=[];runtime.max_requests=2;runtime.send=Mock()
        message=lambda i:{'method':'item/tool/call','id':i,'params':{'tool':'evidence_read','arguments':{'id':'fresh-01','image':'export','axis':'row','index':0}}}
        for i in range(3):runtime.handle_request(message(i))
        self.assertEqual([r['success'] for r in runtime.requests],[True,True,False])
        self.assertEqual([a['tool'] for a in broker.audit],['evidence_read']*2)


class ResumeTests(unittest.TestCase):
    def test_relocation_rejects_unrelated_and_escaping_paths(self):
        from learning.core import relocate
        self.assertEqual(relocate(r'C:\old\checkout\evidence\learning\run\output.png'),
                         str((ROOT/'evidence/learning/run/output.png').resolve()))
        self.assertEqual(relocate('/old/checkout/fixtures/development/inputs/gb010.png'),
                         str((ROOT/'fixtures/development/inputs/gb010.png').resolve()))
        for bad in ['/unrelated/output.png', 'evidence/../../outside.png',
                    r'C:\old\evidence\..\outside.png', 'fixtures/holdout/output.png',
                    'evidence/learning/output.png:stream', 'fixtures/final_holdout/output.png']:
            with self.subTest(path=bad), self.assertRaises(ValueError): relocate(bad)
        with tempfile.TemporaryDirectory() as t:
            link = ROOT/'evidence'/'verification-relocation-link'
            try:
                link.symlink_to(t, target_is_directory=True)
            except OSError:
                return  # Windows without symlink privilege; other guards still exercised.
            try:
                with self.assertRaises(ValueError): relocate(str(link/'output.png'))
            finally:
                link.unlink()

    def test_ci_fixture_list_rejects_paths_before_copying(self):
        from learning import ci_fixtures
        with tempfile.TemporaryDirectory() as t:
            listing = Path(t)/'list.txt'
            with patch.object(ci_fixtures, 'LIST', listing):
                for bad in ['../outside.png', 'evidence/learning/../../outside.png',
                            'fixtures/development/inputs/gb010.png', 'C:/outside.png']:
                    listing.write_text(bad+'\n')
                    with self.subTest(path=bad), self.assertRaises(ValueError): ci_fixtures.listed()

    def workspace(self):
        import uuid,shutil
        ws=ROOT/'dev-workspaces'/('test-'+uuid.uuid4().hex[:8])
        manifest=json.loads((SOURCE/'checkpoints/candidate-2/manifest.json').read_text())
        for name in manifest['files']:
            (ws/name).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(SOURCE/'checkpoints/candidate-2'/name,ws/name)
        self.addCleanup(shutil.rmtree,ws,True)
        return ws

    def test_app_root_resolution(self):
        from learning.core import resolve_app
        self.assertEqual(resolve_app(ROOT/'generated-app'),(ROOT/'generated-app').resolve())
        for bad in [ROOT,ROOT/'evidence',ROOT/'dev-workspaces',ROOT/'dev-workspaces/a/b',ROOT/'fixtures/development']:
            with self.assertRaises(ValueError):resolve_app(bad)

    def test_source_loading_verifies_suite_candidate_and_contract(self):
        import shutil
        from learning.run import load_source
        source=load_source(SOURCE,'candidate-2')
        self.assertEqual([e['id'] for e in source['evidence']],['gb017','gb010','fresh-01','fresh-02','fresh-03','fresh-04'])
        self.assertEqual(source['routing_suggestion']['next_action'],'repair')
        with self.assertRaises(ValueError):load_source(SOURCE,'candidate-3')
        with tempfile.TemporaryDirectory(dir=ROOT/'evidence/learning') as t:
            copy_run=Path(t)
            for part in ['events.jsonl','suites','candidates','contracts','checkpoints/candidate-2','model/route-2']:
                src=SOURCE/part;dst=copy_run/part
                shutil.copytree(src,dst) if src.is_dir() else shutil.copyfile(src,dst)
            for i in range(1,5):
                (copy_run/f'experiments/fresh-0{i}').mkdir(parents=True)
                shutil.copyfile(SOURCE/f'experiments/fresh-0{i}/evidence.json',copy_run/f'experiments/fresh-0{i}/evidence.json')
            load_source(copy_run,'candidate-2')
            (copy_run/'checkpoints/candidate-2/src/gaussian-blur.ts').write_text('// CONTROLLED TAMPER')
            with self.assertRaises(ValueError):load_source(copy_run,'candidate-2')
            shutil.copyfile(SOURCE/'checkpoints/candidate-2/src/gaussian-blur.ts',copy_run/'checkpoints/candidate-2/src/gaussian-blur.ts')
            suite=copy_run/'suites/visible-blur-v1.json';suite.write_text(suite.read_text()+' ')
            with self.assertRaises(ValueError):load_source(copy_run,'candidate-2')

    def test_existing_workspace_must_match_selected_checkpoint(self):
        from learning.run import load_source, prepare_workspace
        source=load_source(SOURCE,'candidate-2');ws=self.workspace()
        self.assertEqual(prepare_workspace(source,ws),(ws.resolve(),False))
        (ws/'src/gaussian-blur.ts').write_text('// CONTROLLED DIVERGENT EXPERIMENT')
        with self.assertRaises(ValueError):prepare_workspace(source,ws)

    def resume(self,outcomes,prepare_only=False,candidates=2,dev=False,builder_timeout=False,focus=False):
        """Recorded attempt-2 route/builder outputs drive the resume loop; worker gates are controlled fixtures.
        dev=True adds one controlled developer-selected record (fresh-01's files under a new id)."""
        from contextlib import redirect_stdout
        import io,shutil
        from learning.run import Harness, RESUME, load_source
        source=load_source(SOURCE,'candidate-2');ws=self.workspace()
        t=tempfile.TemporaryDirectory(dir=ROOT/'evidence');self.addCleanup(t.cleanup);root=Path(t.name)
        if dev:
            source['dev_evidence']=[{**saved_evidence('fresh-01'),'id':'dev-x','selected_by':'developer'}]
            shutil.copytree(ROOT/'evaluator/policies',root/'evaluator/policies')
        contract=copy.deepcopy(source['claims']);contract[0]['supporting_evidence']=contract[0]['supporting_evidence']+['dev-x']
        for name in ['smoke.py','build_shell.py','verify_shell.py','baseline_regressions.py','workspaces.json']:
            (root/name).write_text('CONTROLLED HOST FIXTURE')
        main=root/'generated-app';(main/'src').mkdir(parents=True);(main/'src/main.tsx').write_text('// CONTROLLED MAIN APP')
        historical=json.loads((SOURCE/'evaluations/candidate-2/evaluation.json').read_text())
        route=json.loads((SOURCE/'model/route-2/invocation.json').read_text())['answer']
        recorded=(SOURCE/'checkpoints/candidate-2/src/gaussian-blur.ts').read_text(encoding='utf-8')
        calls=[];state={}
        def evaluation(label,cleanup=False):
            kind='base' if label=='resume-base' else outcomes[int(label.split('-')[1])-1]
            result=copy.deepcopy(historical);result.update(ui_valid=True,suite_sha256=state['h'].suite_hash)
            if kind=='better':result['cases'][1]=copy.deepcopy(result['cases'][0]);result['cases'][1]['case_id']='gb010'
            if kind=='accept':
                for c in result['cases']:c['status']='passed'
            if kind=='baseline_fail':result['baseline_pass']=False
            return result
        def invoke(prompt,directory,timeout,schema=None,builder=False,**kw):
            calls.append({'prompt':prompt,'builder':builder,'schema':schema,'timeout':timeout,**kw})
            if not builder and 'claims' in schema['properties']:return {'claims':contract,'decision':'CONTROLLED FIXTURE UPDATE'}
            if not builder:return route
            (ws/'src/gaussian-blur.ts').write_text(recorded+'\n// CONTROLLED FIXTURE REPAIR '+str(len(calls))+'\n',encoding='utf-8')
            if builder_timeout: raise TimeoutError('CONTROLLED BUILDER TIMEOUT')
        config=copy.deepcopy(DEFAULTS);config['candidates']=candidates
        if focus: config.update(builder_seconds=160,run_seconds=360,evidence_reads=0,builder_tool_calls=4)
        with patch('learning.run.ROOT',root),patch('learning.run.APP',main),patch('learning.run.model.invoke',side_effect=invoke),redirect_stdout(io.StringIO()):
            h=Harness(config,ws,RESUME,{'source_run':source['run_id'],'source_candidate':'candidate-2'});state['h']=h
            h.worker=lambda *a,**k:{'status':'passed'};h.baseline=lambda *a,**k:True;h.evaluate=evaluation
            if focus:
                h.repair_focus='boundary-alpha'
                folder=h.directory/'evaluations/resume-base';folder.mkdir(parents=True)
                for e in source['evidence']: shutil.copyfile(e['expected'],folder/(e['id']+'.png'))
            h.resume(source,prepare_only)
        return h,ws,calls,main,recorded

    def test_aligned_contract_reuse_requires_same_frozen_suite(self):
        from learning.run import load_source,adopt_aligned_contract
        source=load_source(SOURCE,'candidate-2')
        contract=SOURCE/'contracts/contract-1.json'
        adopt_aligned_contract(source,contract)
        self.assertEqual(source['aligned_contract']['suite_sha256'],source['suite_sha256'])
        self.assertEqual(source['aligned_suite']['cases'],source['suite']['cases'])
        source['evidence'][0]=dict(source['evidence'][0],percentage=4)
        with self.assertRaises(ValueError): adopt_aligned_contract(source,contract)

    def test_scoped_resume_packet_and_deadline_reach_runtime(self):
        h,ws,calls,main,recorded=self.resume(['baseline_fail'],candidates=1,focus=True)
        self.assertEqual(len(calls),1)
        call=calls[0];self.assertTrue(call['builder']);self.assertEqual(call['timeout'],160)
        self.assertEqual(call['max_tool_calls'],4);self.assertIsNone(call['reader'])
        self.assertEqual(call['allowed_writes'],['src/gaussian-blur.ts'])
        body=json.loads(call['prompt'].split('Packet: ',1)[1])
        self.assertEqual(body['permitted_writes'],['src/gaussian-blur.ts'])
        self.assertEqual(body['developer_guidance']['focus'],'Percentage-7 boundary alpha only')
        self.assertTrue(body['alpha_profiles'])
        self.assertEqual(body['workspace_operation']['src/gaussian-blur.ts'],recorded)
        self.assertLess(h.packet_sizes[0]['bytes'],20000)
        self.assertEqual(h.config['run_seconds'],360);self.assertEqual(h.config['reserve_seconds'],100)
        self.assertEqual((ws/'src/gaussian-blur.ts').read_text(encoding='utf-8'),recorded)

    def test_narrow_broker_denies_integration_and_documentation_writes(self):
        from learning.model import BlurBroker
        ws=self.workspace();broker=BlurBroker(root=ws,allowed_writes=['src/gaussian-blur.ts'])
        for name in ['README.md','src/main.tsx','src/current-image.ts','src/style.css']:
            with self.assertRaises(ValueError): broker.path(name,write=True)
        self.assertEqual(broker.path('src/gaussian-blur.ts',write=True),ws.resolve()/'src/gaussian-blur.ts')
        self.assertEqual(broker.path('src/current-image.ts'),ws.resolve()/'src/current-image.ts')

    def test_resume_prepare_only_sends_no_model_request(self):
        h,ws,calls,main,recorded=self.resume([],prepare_only=True)
        self.assertEqual(calls,[]);self.assertEqual(h.stop,'prepared_only_no_model_request')
        self.assertEqual([p['role'] for p in h.packet_sizes],['contract','route','repair'])
        self.assertTrue(all(p['dry_run'] and p['within_limits'] for p in h.packet_sizes))
        self.assertEqual((ws/'src/gaussian-blur.ts').read_text(encoding='utf-8'),recorded)
        self.assertFalse(h.report['provenance']['clean_start_autonomous_demonstration'])
        self.assertTrue((h.directory.parents[2]/'evidence/latest-learning-dev-resume.json').exists())
        self.assertFalse((h.directory.parents[2]/'evidence/latest-learning.json').exists())

    def test_resume_repairs_from_selected_then_best_experimental_state(self):
        h,ws,calls,main,recorded=self.resume(['better','baseline_fail'])
        builders=[c for c in calls if c['builder']]
        self.assertEqual(len(builders),2);self.assertEqual(builders[0]['app'],ws.resolve())
        self.assertEqual(builders[0]['max_tool_calls'],12);self.assertIsNotNone(builders[0]['reader'])
        first=json.loads(builders[0]['prompt'].split('Packet: ',1)[1])
        self.assertEqual(first['repair']['workspace_operation'],{'label':'candidate-2','src/gaussian-blur.ts':recorded})
        second=json.loads(builders[1]['prompt'].split('Packet: ',1)[1])
        self.assertEqual(second['repair']['workspace_operation']['label'],'candidate-1')
        self.assertIn('candidate-1',h.report['states']['experimental_base'])
        self.assertIsNone(h.report['states']['accepted_best_known']);self.assertIsNone(h.first_acceptance)
        self.assertIn('CONTROLLED FIXTURE REPAIR 1',(ws/'src/gaussian-blur.ts').read_text(encoding='utf-8'))
        self.assertTrue((h.directory/'checkpoints/candidate-2/src/gaussian-blur.ts').exists())
        self.assertEqual((main/'src/main.tsx').read_text(),'// CONTROLLED MAIN APP')
        self.assertEqual(h.stop,'candidate_budget_exhausted')
        self.assertTrue(all(p['within_limits'] for p in h.packet_sizes))

    def test_resume_without_new_evidence_keeps_the_saved_contract(self):
        h,ws,calls,main,recorded=self.resume(['baseline_fail'],candidates=1)
        self.assertFalse(any('claims' in (c['schema'] or {}).get('properties',{}) for c in calls))
        body=json.loads([c for c in calls if c['builder']][0]['prompt'].split('Packet: ',1)[1])
        self.assertNotIn('unincorporated_evidence',body);self.assertNotIn('developer_selected_evidence',body)

    def test_resume_with_developer_evidence_updates_contract_before_building(self):
        h,ws,calls,main,recorded=self.resume(['baseline_fail'],candidates=1,dev=True)
        self.assertTrue('claims' in calls[0]['schema']['properties']);self.assertFalse(calls[0]['builder'])
        self.assertIn('dev-x',calls[0]['prompt'])
        body=json.loads([c for c in calls if c['builder']][0]['prompt'].split('Packet: ',1)[1])
        self.assertEqual(body['contract_claims'][0]['supporting_evidence'][-1],'dev-x')
        self.assertNotIn('unincorporated_evidence',body);self.assertEqual(body['developer_selected_evidence'],['dev-x'])
        alignment=[e for e in h.events if e['event']=='contract_alignment']
        self.assertEqual(alignment[0]['uncited_before'],['dev-x']);self.assertEqual(alignment[1]['uncited_after'],[])

    def test_resume_prepare_only_labels_uncited_developer_evidence(self):
        h,ws,calls,main,recorded=self.resume([],prepare_only=True,dev=True)
        self.assertEqual(calls,[])
        body=json.loads(json.loads((h.directory/'packets/builder-1.json').read_text())['prompt'].split('Packet: ',1)[1])
        self.assertEqual(body['unincorporated_evidence']['ids'],['dev-x'])
        self.assertEqual([e['update'] for e in h.events if e['event']=='contract_alignment'],['contract-resume'])

    def test_resume_timeout_preserves_partial_candidate_and_restores_base(self):
        h,ws,calls,main,recorded=self.resume([],candidates=1,builder_timeout=True)
        self.assertEqual(h.stop,'budget_exhausted')
        self.assertEqual((ws/'src/gaussian-blur.ts').read_text(encoding='utf-8'),recorded)
        partial=h.directory/'checkpoints/candidate-1-partial/src/gaussian-blur.ts'
        self.assertIn('CONTROLLED FIXTURE REPAIR',partial.read_text())
        record=json.loads((h.directory/'candidates/candidate-1.json').read_text())
        self.assertEqual(record['status'],'failed');self.assertFalse(record['accepted'])
        self.assertEqual(record['error']['type'],'TimeoutError')
        self.assertEqual((main/'src/main.tsx').read_text(),'// CONTROLLED MAIN APP')

    def test_resume_acceptance_is_separate_and_never_promoted(self):
        h,ws,calls,main,recorded=self.resume(['accept'],candidates=1)
        self.assertEqual(h.report['status'],'accepted');self.assertIsNotNone(h.report['states']['accepted_best_known'])
        self.assertEqual(h.report['mode'],'development_resume')
        self.assertEqual((main/'src/main.tsx').read_text(),'// CONTROLLED MAIN APP')
        self.assertFalse((main/'src/gaussian-blur.ts').exists())

    def test_followup_design_is_bounded_with_competing_explanations(self):
        from learning.followup import EXPERIMENTS, validate_experiments
        validate_experiments(EXPERIMENTS,DEFAULTS)
        self.assertLessEqual(len(EXPERIMENTS),6)
        bad=copy.deepcopy(EXPERIMENTS)+[copy.deepcopy(EXPERIMENTS[0])]
        with self.assertRaises(ValueError):validate_experiments(bad,DEFAULTS)

    def test_resume_records_guidance_provenance_and_selection(self):
        from learning import guidance
        h,ws,calls,main,recorded=self.resume([],prepare_only=True)
        expected=guidance.provenance(guidance.load())
        self.assertEqual(h.report['provenance']['investigation_guidance'],expected)
        saved=json.loads((h.directory/'guidance-selections.json').read_text())
        route=[v for k,v in saved.items() if k.startswith('route:')]
        self.assertEqual(len(route),1);self.assertEqual(route[0]['sha256'],expected['sha256'])
        self.assertIn('G6-no-fitted-special-cases',route[0]['strategy_ids'])
        self.assertEqual(h.report['investigation_guidance_selections'],saved)


class GuidanceTests(unittest.TestCase):
    def guidance_file(self,t,mutate):
        from learning import guidance
        data=json.loads(guidance.PATH.read_text(encoding='utf-8'));mutate(data)
        path=Path(t)/'g.json';path.write_text(json.dumps(data),encoding='utf-8');return path

    def failing_result(self):
        return {'build_valid':True,'independent':True,'baseline_pass':True,'evaluator_suspect':False,
                'cases':[{'status':'passed'},{'status':'failed'}]}

    def test_planner_and_route_packets_include_selected_versioned_guidance(self):
        from learning import guidance, packets
        g=guidance.load();self.assertEqual(g['source'],'learning/investigation-guidance.json')
        self.assertEqual(g['sha256'],__import__('hashlib').sha256(guidance.PATH.read_bytes()).hexdigest())
        planner=packets.planner_prompt(DEFAULTS,guidance.section(g,'planner',{'planning'}))
        tag=f"{g['id']}@{g['version']}"
        self.assertIn(tag,planner);self.assertIn(g['sha256'][:12],planner);self.assertIn('G3-matched-experiments',planner)
        self.assertNotIn('G6-no-fitted-special-cases',planner)
        signals=guidance.route_signals(self.failing_result())
        self.assertEqual(signals,{'any_failure','behavior_mismatch','partial_progress'})
        route=packets.route_prompt(self.failing_result(),{},[],{},DEFAULTS,guidance.section(g,'route',signals))
        for i in ['G2-separate-failure-classes','G6-no-fitted-special-cases','G8-checkpoint-comparison',tag]: self.assertIn(i,route)
        passing={**self.failing_result(),'cases':[{'status':'passed'}]}
        self.assertEqual(guidance.route_signals(passing),set())
        self.assertNotIn('Investigation guidance',packets.route_prompt(passing,{},[],{},DEFAULTS,guidance.section(g,'route',set())))
        self.assertEqual(packets.planner_prompt(DEFAULTS),packets.planner_prompt(DEFAULTS,None))
        self.assertNotIn('Investigation guidance',packets.planner_prompt(DEFAULTS))

    def test_guidance_size_limits_raise_instead_of_truncating(self):
        from learning import guidance
        g=guidance.load()
        with patch('learning.guidance.MAX_SECTION_BYTES',200):
            with self.assertRaises(guidance.GuidanceError):guidance.section(g,'route',{'any_failure','behavior_mismatch','partial_progress'})
        with tempfile.TemporaryDirectory() as t:
            def long(d):d['strategies'][0]['text']='x'*(guidance.MAX_TEXT_CHARS+1)
            with self.assertRaises(guidance.GuidanceError):guidance.load(self.guidance_file(t,long))
            def huge(d):d['note']='x'*guidance.MAX_FILE_BYTES
            with self.assertRaises(guidance.GuidanceError):guidance.load(self.guidance_file(t,huge))
        from learning.packet_report import current_packets
        from learning import packets
        built=current_packets(copy.deepcopy(DEFAULTS))
        for role in ['planner','route']:
            self.assertIn('Investigation guidance',built[role][0])
            packets.enforce(packets.measure(role,*built[role]),DEFAULTS['packet_limits'][role])

    def test_global_guidance_rejects_target_claims_and_evidence_ids(self):
        from learning import guidance
        with tempfile.TemporaryDirectory() as t:
            for text in ['miniPaint rounds colour at Percentage 7.','Blur edges shift.','See dev-02 for the effect.',
                         'Use precision-01 profiles.']:
                def bad(d,text=text):d['strategies'][0]['text']=text
                with self.assertRaises(guidance.GuidanceError):guidance.load(self.guidance_file(t,bad))
            def scoped(d):d['scope']='target:minipaint'
            with self.assertRaises(guidance.GuidanceError):guidance.load(self.guidance_file(t,scoped))
            def trigger(d):d['strategies'][0]['triggers']=['model_chooses']
            with self.assertRaises(guidance.GuidanceError):guidance.load(self.guidance_file(t,trigger))
        g=guidance.load()
        every=guidance.section(g,'route',guidance.TRIGGERS)
        text=json.dumps(every)
        self.assertIsNone(guidance.TARGET_TERMS.search(text));self.assertIsNone(guidance.EVIDENCE_ID.search(text))
        self.assertIn('not target behavior evidence',every['kind'])
        findings=ROOT/'docs/target-findings/minipaint-gaussian-blur.md'
        self.assertTrue(findings.is_file())
        self.assertNotIn('target-findings/minipaint',guidance.PATH.read_text(encoding='utf-8'))

if __name__=='__main__':unittest.main()
