"""Sequential experiment -> evidence -> contract -> build -> independent evaluation.

Default: clean-start autonomous attempt from the genuine no-blur generated-app.
--resume-from: explicit development resume of a saved failed candidate in an isolated
dev-workspaces/<name> copy; never a clean-start demonstration and never promotes into generated-app.
"""
import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import uuid
from adapter.png import ROOT, fixture_path, png_info, within
from adapter.validate import cases as development_cases
from build_shell import APP, FILES
from evaluator.compare import load_policy
from .core import (DEFAULTS, Budget, Checkpoints, ROUTES, decide, digest, exact, objective, relocated, resolve_app, save,
                   strings, text, validate_claims, validate_config, validate_plan)
from .diagnostics import DEFINITIONS, generate, describe
from . import guidance, model, packets

SCOPE = FILES | {'package-lock.json', 'src/gaussian-blur.ts'}
CLEAN, RESUME = 'clean_start', 'development_resume'


class Harness:
    def __init__(self, config, app=None, mode=CLEAN, provenance=None):
        self.config=validate_config(config); self.budget=Budget(config)
        self.repair_focus=None
        self.dev_app=app is not None; self.app=resolve_app(app) if self.dev_app else Path(APP); self.mode=mode
        if mode==RESUME and (not self.dev_app or self.app==Path(APP).resolve()):
            raise ValueError('Development resume must use an isolated dev workspace')
        suffix='-dev-resume' if mode==RESUME else ''
        self.directory=ROOT/'evidence/learning'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]+suffix)
        self.directory.mkdir(parents=True); self.owns_directory=True
        self.checkpoints=Checkpoints(self.app,self.directory/'checkpoints',getattr(self,'source_scope',SCOPE))
        self.best=self.checkpoints.snapshot('no-blur-start' if mode==CLEAN else 'experimental-base-start')
        self.accepted=None; self.base_result=None; self.base_label=None; self.packet_sizes=[]
        self.events=[]; self.evidence=[]; self.claims=[]; self.attempts=[]; self.suite=None; self.incumbent=None
        self.stop='not_started'; self.first_acceptance=None; self.prefix='fresh-' if mode==CLEAN else 'resume-fresh-'
        self.guidance=guidance.load(); self.guidance_selections={}
        self.provenance={'mode':mode,'clean_start_autonomous_demonstration':mode==CLEAN,'app':str(self.app),
                         'investigation_guidance':guidance.provenance(self.guidance),**(provenance or {})}
        # Protect trusted code, original development files, and policies through all model turns.
        protected=[ROOT/'smoke.py',ROOT/'build_shell.py',ROOT/'verify_shell.py',ROOT/'baseline_regressions.py',ROOT/'workspaces.json']
        for folder in ['adapter','evaluator','learning','fixtures/development']:
            protected.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
        if mode==RESUME:
            # The main generated app is outside a development resume; any change stops promotion.
            protected.extend(APP/n for n in sorted(SCOPE) if (APP/n).is_file())
        self.protected={str(p):digest(p) for p in protected}
        save(self.directory/'protected-manifest.json',self.protected)
        # Archive trusted code/policy versions so later host fixes do not erase run provenance.
        for path in protected:
            if path.suffix in ['.py','.json'] and not path.is_relative_to(APP):
                archived=self.directory/'executed-host-source'/path.relative_to(ROOT)
                archived.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(path,archived)
        save(self.directory/'config.json',config)
        save(self.directory/'provenance.json',self.provenance)
        self.emit('checkpoint',state='no-blur-start' if mode==CLEAN else 'experimental-base-start',checkpoint=str(self.best),mode=mode)

    def emit(self, kind, **data):
        event={'sequence':len(self.events)+1,'event':kind,'elapsed_seconds':round(time.monotonic()-self.budget.start,3),
               'budget':self.budget.snapshot(),**data}
        self.events.append(event)
        with (self.directory/'events.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(event,allow_nan=False)+'\n')
        print(json.dumps(event,allow_nan=False),flush=True)

    def guard(self):
        changed=[p for p,h in self.protected.items() if not Path(p).is_file() or digest(p)!=h]
        if changed: raise ValueError('Protected host/evaluator/expected files changed; promotion stopped: '+str(changed))
        if self.suite:
            for row in self.suite['cases']:
                if digest(row['expected'])!=row['expected_sha256'] or digest(row['input'])!=row['input_sha256']:
                    raise ValueError('Frozen visible suite changed; promotion stopped')

    def process(self, args, directory, timeout, cleanup=False):
        directory.mkdir(parents=True,exist_ok=True)
        timeout=self.budget.timeout(timeout,cleanup)
        started=time.monotonic()
        with (directory/'worker.log').open('w',encoding='utf-8') as log:
            proc=subprocess.Popen(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,
                                  start_new_session=os.name!='nt')
            try: proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                if os.name=='nt': subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],timeout=10,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                else: os.killpg(proc.pid,signal.SIGKILL)
                proc.wait(timeout=5)
                save(directory/'process.json',{'exit':proc.returncode,'timeout':timeout,'elapsed_seconds':time.monotonic()-started})
                raise TimeoutError('Worker deadline; process tree terminated')
        save(directory/'process.json',{'exit':proc.returncode,'timeout':timeout,'elapsed_seconds':round(time.monotonic()-started,3)})
        return proc.returncode

    def worker(self, kind, request, directory, timeout, cleanup=False):
        directory.mkdir(parents=True,exist_ok=True); save(directory/'request.json',request)
        self.process([sys.executable,'-m','learning.worker',kind,str(directory/'request.json'),str(directory)],directory,timeout,cleanup)
        return json.loads((directory/'result.json').read_text())

    def baseline(self,label,allow_blur,cleanup=False,allow_brightness=False):
        d=self.directory/label
        args=[sys.executable,str(ROOT/'baseline_regressions.py'),'--output',str(d/'baseline')]
        if allow_blur: args.append('--allow-blur')
        if allow_brightness: args.append('--allow-brightness')
        if self.dev_app: args+=['--app',str(self.app)]
        self.process(args,d,self.config['command_seconds'],cleanup)
        result=json.loads((d/'baseline/results.json').read_text())
        self.emit('baseline',label=label,status=result['status'],classification=result['classification'])
        self.last_baseline=result
        return result['status']=='passed'

    def ask(self,prompt,label,schema,builder=False,role=None,supplied=None,reader=None,dry=False):
        """Measures every packet and enforces hard limits before any model request is made."""
        role=role or ('builder' if builder else 'contract')
        measurement=packets.measure(role,prompt,schema,supplied)
        limits=self.config['packet_limits'][role]
        record={'label':label,**measurement,'limits':limits,'within_limits':True,'dry_run':dry}
        try: packets.enforce(measurement,limits)
        except packets.PacketLimitError:
            record['within_limits']=False; self.record_packet(record); raise
        self.record_packet(record)
        if dry: return None
        timeout=self.budget.timeout(self.config['builder_seconds' if builder else 'model_seconds'])
        try: return model.invoke(prompt,self.directory/'model'/label,timeout,schema,builder,app=self.app,reader=reader,
                                 max_tool_calls=self.config['builder_tool_calls'] if builder else 24,operation=getattr(self,'operation','gaussian-blur'),
                                 **({'allowed_writes':['src/gaussian-blur.ts']} if builder and getattr(self,'repair_focus',None) else {}))
        finally: self.guard()

    def guidance_section(self,role,signals,label):
        """Code-selected global strategies for one packet; selection and provenance are saved with the run."""
        if not hasattr(self,'guidance'): self.guidance=guidance.load()
        if not hasattr(self,'guidance_selections'): self.guidance_selections={}
        value=guidance.section(self.guidance,role,signals)
        self.guidance_selections[label]={'role':role,'signals':sorted(signals),'strategy_ids':sorted(value['strategies']),
                                         **guidance.provenance(self.guidance)}
        if getattr(self,'owns_directory',False): save(self.directory/'guidance-selections.json',self.guidance_selections)
        return value

    def record_packet(self,record):
        self.packet_sizes.append(record)
        save(self.directory/'packet-sizes.json',{'method':packets.ESTIMATOR,'packets':self.packet_sizes})
        self.emit('packet_measured',label=record['label'],role=record['role'],bytes=record['bytes'],
                  estimated_tokens=record['estimated_tokens'],within_limits=record['within_limits'],limits=record['limits'])

    def validate_plans(self, answer):
        exact(answer,['plans'])
        plans=answer['plans']
        if not isinstance(plans,list) or not 1<=len(plans)<=4: raise ValueError('Planner must propose 1..4 bounded experiments')
        for plan in plans: validate_plan(plan,self.config)
        signatures=[json.dumps({'input':p['input'],'percentage':p['percentage']},sort_keys=True) for p in plans]
        previous=[json.dumps({'input':e['plan']['input'],'percentage':e['plan']['percentage']},sort_keys=True) for e in self.evidence if 'plan' in e]
        if len(set(signatures))!=len(signatures) or any(s in previous for s in signatures):
            raise ValueError('Planner replay is not a fresh informative experiment')
        if len(plans)>self.budget.snapshot()['fresh_experiments_remaining']: raise TimeoutError('Requested experiments exceed remaining budget')
        return plans

    def experiment(self,plan):
        self.budget.spend('experiment')
        ident=self.prefix+str(self.budget.experiments).zfill(2); d=self.directory/'experiments'/ident
        (self.directory/'inputs').mkdir(exist_ok=True)
        input_path=self.directory/'inputs'/(ident+'.png')
        info=generate(plan,input_path,self.config)
        self.emit('experiment',id=ident,current_question=plan['question'],plan=plan)
        request={'id':ident,'config':self.config,'plan':plan,'input_path':str(input_path),'input_sha256':digest(input_path)}
        report=None
        for retry in range(self.config['retries']+1):
            if retry: self.budget.spend('experiment')
            attempt=d if retry==0 else d.parent/(ident+'-retry'+str(retry))
            try: report=self.worker('reference',request,attempt,self.config['reference_seconds'])
            except TimeoutError as error: report={'status':'infrastructure_failure','error':{'type':'TimeoutError','message':str(error)}}
            save(attempt/'reference-record.json',report)
            if report['status']=='observed': break
            self.emit('failure',classification='procedure_infrastructure',id=ident,attempt=retry,record=report)
        if not report or report['status']!='observed':
            raise RuntimeError('Reference procedure failed; no behavioral evidence admitted')
        record={'id':ident,'plan':plan,'input':str(input_path),'expected':report['output_path'],
                'accepted_input_spec':{**plan['input'],'definition':DEFINITIONS[plan['input']['kind']]},
                'input_sha256':info['png_sha256'],'expected_sha256':report['output']['png_sha256'],
                'percentage':report['accepted_percentage'],'target':report['target'],'procedure_record':str(attempt/'reference-record.json'),
                'input_samples':describe(input_path),'export_samples':describe(report['output_path'])}
        save(attempt/'evidence.json',record); self.evidence.append(record)
        self.emit('evidence',id=ident,status='OBSERVED',requested=plan['percentage'],accepted=report['accepted_percentage'])

    def prepared(self):
        for row in development_cases():
            input_path,expected=fixture_path(row['input_path']),fixture_path(row['output_path'])
            if digest(input_path)!=row['hashes']['input_png_sha256'] or digest(expected)!=row['hashes']['output_png_sha256']:
                raise ValueError('Original development fixture integrity mismatch')
            self.evidence.append({'id':row['case_id'],'input':str(input_path),'expected':str(expected),
                 'input_sha256':digest(input_path),'expected_sha256':digest(expected),'percentage':3,
                 'target':row['reference_application'],'prepared_development':True,
                 'input_samples':describe(input_path),'export_samples':describe(expected)})

    def freeze(self):
        rows=[]
        for e in self.evidence:
            w,h=e['input_samples']['png']['width'],e['input_samples']['png']['height']
            rows.append({k:e[k] for k in ['id','input','expected','input_sha256','expected_sha256','percentage']})
            cx,cy=w//2,h//2
            rows[-1]['regions']={'center':[max(0,cx-5),max(0,cy-5),min(w,cx+6),min(h,cy+6)],
                                 'boundary':[0,0,min(4,w),h]}
        version=sum(e['event']=='suite_frozen' for e in self.events)+1
        suite={'id':('visible-blur-v' if self.mode==CLEAN else 'resume-visible-v')+str(version),
               'run_dir':str(self.directory),'cases':rows,'policy':load_policy(ROOT/'evaluator/policies/blur-provisional-v1.json'),
               'exact_baseline_policy':load_policy(),
               'objective':'Lexicographically minimize failed blur gates then mean of case worst-region raw RGBA MAE. '
                           'Only all-gate-passing feasible candidates can promote. Equal scores retain incumbent.',
               'tie_policy':'retain incumbent','region_rule':'For every case, center 11x11 clipped to image plus full-height left 4px border; fixed before candidate comparison.'}
        save(self.directory/'suites'/(suite['id']+'.json'),suite)
        self.suite=suite; self.suite_hash=digest(self.directory/'suites'/(suite['id']+'.json'))
        self.emit('suite_frozen',id=suite['id'],sha256=self.suite_hash,case_ids=[r['id'] for r in rows],policy=suite['policy'])

    def accepted_cases(self):
        return [] if self.incumbent is None or not self.first_acceptance else [r['case_id'] for r in self.incumbent['cases']]

    def contract_packet(self):
        return packets.contract_prompt(self.evidence,self.claims,self.accepted_cases())

    def contract_schema(self):
        schema=copy.deepcopy(model.CONTRACT)
        for key in ['supporting_evidence','contradicting_evidence','verification_cases']:
            schema['properties']['claims']['items']['properties'][key]['items']={'type':'string','enum':[e['id'] for e in self.evidence]}
        return schema

    def update_contract(self,label):
        accepted=self.accepted_cases()
        answer=self.ask(self.contract_packet(),label,self.contract_schema(),role='contract')
        exact(answer,['claims','decision']); text(answer['decision'])
        self.claims=validate_claims(answer['claims'],[e['id'] for e in self.evidence],[e['id'] for e in self.evidence],accepted)
        save(self.directory/'contracts'/(label+'.json'),answer)
        self.emit('claim_update',decision=answer['decision'],claims=[{'id':c['id'],'status':c['status'],'statement':c['statement']} for c in self.claims])

    def evaluate(self,label,cleanup=False):
        d=self.directory/'evaluations'/label
        result=self.worker('candidate',{'suite':self.suite,'suite_sha256':self.suite_hash,'app':str(self.app)},d,self.config['command_seconds'],cleanup)
        result.setdefault('build_valid',False);result.setdefault('independent',False); result.setdefault('cases',[])
        result['baseline_pass']=self.baseline(label+'-gates',(self.app/'src/gaussian-blur.ts').exists(),cleanup)
        result['baseline_classification']=self.last_baseline['classification']
        if not result['baseline_pass'] and result['baseline_classification']=='infrastructure_error':
            result['procedure_failure']=True
        result['suite_sha256']=self.suite_hash
        save(d/'evaluation.json',result)
        self.emit('evaluation',label=label,build_valid=result['build_valid'],independent=result['independent'],
                  baseline_pass=result['baseline_pass'],objective=objective(result['cases']),
                  cases=[{'id':r['case_id'],'status':r['status'],'metrics':r['metrics'],'reasons':r['reasons']} for r in result['cases']],error=result.get('error'))
        return result

    def source_of(self,checkpoint):
        p=Path(checkpoint)/'src/gaussian-blur.ts'
        return p.read_text(encoding='utf-8') if p.exists() else None

    def builder_request(self,index,previous):
        """Returns (label, prompt, supplied tool-response estimate, evidence reader) without any model call."""
        repair=None; supplied={}
        reads={n:(self.app/n).read_text(encoding='utf-8') for n in ['src/main.tsx','src/current-image.ts'] if (self.app/n).exists()}
        candidates={}
        if previous:
            result=previous['evaluation']; eval_dir=self.directory/'evaluations'/previous['label']
            candidates={e['id']:eval_dir/(e['id']+'.png') for e in self.evidence if (eval_dir/(e['id']+'.png')).exists()}
            base=self.base_result or {}
            integration=self.mode==RESUME and all(base.get(k) for k in ['build_valid','independent','ui_valid','baseline_pass'])
            repair={'discrepancies':packets.discrepancy_section(result,self.evidence,eval_dir),
                    'routing_suggestion':previous.get('routing_suggestion'),'mode_note':previous['note'],
                    'base_label':self.base_label or 'no-blur best-known state','base_source':self.source_of(self.best),
                    'rejected_label':previous['label'],'rejected_source':previous.get('rejected_operation_source'),
                    'integration_passed':integration}
            if not integration: supplied=reads
        else:
            supplied=reads
        if getattr(self,'repair_focus',None):
            if not repair or not integration: raise ValueError('Narrow repair requires passing resume integration')
            prompt=packets.boundary_alpha_prompt(self.claims,self.evidence,self.suite,self.config,repair,eval_dir)
        else:
            prompt=packets.builder_prompt(self.claims,self.evidence,self.suite,self.config,repair)
        sources={e['id']:{'input':e['input'],'export':e['expected'],**({'candidate':str(candidates[e['id']])} if e['id'] in candidates else {})}
                 for e in self.evidence}
        reader=packets.EvidenceReader(sources,self.config['evidence_reads']) if self.config['evidence_reads'] and not getattr(self,'repair_focus',None) else None
        return 'builder-'+str(index),prompt,supplied,reader,'repair' if repair else 'builder'

    def builder(self,index,previous,dry=False):
        label,prompt,supplied,reader,role=self.builder_request(index,previous)
        save(self.directory/'packets'/(label+'.json'),{'role':role,'prompt':prompt,
             'supplied_tool_response_estimate':sorted(supplied)})
        self.ask(prompt,label,None,True,role=role,supplied=supplied,reader=reader,dry=dry)

    def route_request(self,result,label):
        discrepancies=packets.discrepancy_section(result,self.evidence,self.directory/'evaluations'/label)
        schema=copy.deepcopy(model.ROUTE)
        schema['properties']['evidence_ids']['items']={'type':'string','enum':[e['id'] for e in self.evidence]}
        section=self.guidance_section('route',guidance.route_signals(result),'route:'+label)
        return packets.route_prompt(result,discrepancies,self.evidence,self.budget.snapshot(),self.config,section),schema

    def route(self,result,index,label=None,dry=False):
        prompt,schema=self.route_request(result,label or 'candidate-'+str(index))
        answer=self.ask(prompt,'route-'+str(index),schema,role='route',dry=dry)
        if dry: return None
        exact(answer,['classification','evidence_ids','explanation','next_action','plans'])
        if answer['classification'] not in ROUTES or answer['next_action'] not in ['experiment','repair','stop']: raise ValueError('Invalid route')
        strings(answer['evidence_ids']); text(answer['explanation'])
        if not set(answer['evidence_ids']) <= {e['id'] for e in self.evidence}: raise ValueError('Unknown classification evidence')
        if answer['next_action']=='experiment': self.validate_plans({'plans':answer['plans']})
        elif answer['plans']: raise ValueError('Unexpected route plans')
        self.emit('failure_routing',suggestion=answer,trusted_acceptance=False)
        return answer

    def feasible(self,result):
        return all(result.get(k) for k in ['build_valid','independent','ui_valid','baseline_pass']) and \
            not result.get('procedure_failure') and not result.get('evaluator_suspect')

    def candidates_loop(self,previous):
        for index in range(1,self.config['candidates']+1):
            self.budget.spend('candidate'); label='candidate-'+str(index)
            self.emit('candidate',id=label,packet='packets/builder-'+str(index)+'.json',
                      starts_from=self.base_label or 'best-known')
            record={'id':label,'suite_sha256':self.suite_hash,'status':'failed','started_seconds':round(time.monotonic()-self.budget.start,3),
                    'starts_from':self.base_label or 'best-known'}
            self.attempts.append(record)
            try:
                self.builder(index,previous)
                self.checkpoints.snapshot(label)
                result=self.evaluate(label)
                self.guard()
                accepted,reason=decide(result,self.incumbent if self.first_acceptance else None)
                record.update(evaluation=result,accepted=accepted,reason=reason,status='accepted' if accepted else 'rejected')
                save(self.directory/'candidates'/(label+'.json'),record)
                self.emit('acceptance' if accepted else 'rejection',id=label,reason=reason,objective=objective(result['cases']))
                if accepted:
                    self.accepted=self.best=self.checkpoints.snapshot('best-known-'+str(index)); self.incumbent=result
                    self.first_acceptance={'candidate_id':label,'elapsed_seconds':round(time.monotonic()-self.budget.start,3),
                                           'suite_sha256':self.suite_hash,'objective':objective(result['cases'])}
                    # Parity is verified; a matching implementation does not prove a hidden mechanism.
                    self.claims.append({'id':'implementation-visible-parity','statement':'Independent implementation passes all frozen visible RGBA and region gates.',
                        'status':'VERIFIED_WITHIN_SCOPE','target_version':'miniPaint visible About 4.14.3; hosted build unknown',
                        'setup':'Validated headed 1440x1000 single-layer procedure; independent Node execution',
                        'parameter_domain':{'min':min(e['percentage'] for e in self.evidence),'max':max(e['percentage'] for e in self.evidence)},
                        'scope':'Only discrete inputs and Percentage values in '+self.suite['id']+'; no interpolation or mechanism proof.',
                        'supporting_evidence':[e['id'] for e in self.evidence],'contradicting_evidence':[],
                        'alternatives':['Several mechanisms may agree within these tolerances'],
                        'unresolved':['Untested inputs/parameters/browsers and exact hosted build'],
                        'verification_cases':[r['case_id'] for r in result['cases']]})
                    save(self.directory/'contracts/accepted.json',{'claims':self.claims,'verification':self.first_acceptance})
                    self.stop='first_acceptance_all_visible_gates_pass'; break
                if result.get('evaluator_suspect'):
                    self.stop='evaluator_defect'; break
                if self.mode==RESUME and self.feasible(result) and self.base_result and \
                        result['suite_sha256']==self.base_result['suite_sha256'] and \
                        objective(result['cases']) < objective(self.base_result['cases']):
                    # Experimental (not accepted) state: repairs continue from the best feasible rejected candidate.
                    self.best=self.checkpoints.snapshot('experimental-base-'+str(index))
                    self.base_result,self.base_label=result,label
                    self.emit('experimental_base_updated',id=label,objective=objective(result['cases']),accepted=False)
                self.checkpoints.restore(self.best)
                note=('Rejected workspace restored; repair must regenerate from best-known state.' if self.mode==CLEAN else
                      'Development resume: workspace restored to experimental base '+str(self.base_label)+'; it is not accepted.')
                previous={'evaluation':result,'label':label,'rejected_operation_source':self.source_of(self.directory/'checkpoints'/label),
                          'note':note}
                if index==self.config['candidates']: self.stop='candidate_budget_exhausted'; break
                route=self.route(result,index)
                previous['routing_suggestion']=route
                if route['classification']=='evaluator_defect' or route['next_action']=='stop':
                    self.stop=route['classification']; break
                if route['next_action']=='experiment':
                    for plan in route['plans']: self.experiment(plan)
                    self.freeze(); self.update_contract('contract-'+str(index+1))
                    # Both current incumbent/base and next candidate rerun on the same expanded frozen suite.
                    self.incumbent=self.evaluate('incumbent-v'+str(index+1))
                    if self.mode==RESUME: self.base_result=self.incumbent
            except Exception as error:
                # Preserve even partially written sources from a timed-out/failed builder.
                if not (self.directory/'checkpoints'/label).exists():
                    self.checkpoints.snapshot(label+'-partial')
                record.update(status='failed',accepted=False,error={'type':type(error).__name__,'message':str(error)[:2000]})
                save(self.directory/'candidates'/(label+'.json'),record)
                self.emit('failure',id=label,classification='ambiguous_budget_exhausted' if isinstance(error,TimeoutError) else 'procedure_infrastructure',error=record['error'])
                raise

    def run(self):
        try:
            # No-blur snapshot precedes every model and experiment. Baselines prove actual unavailable UI.
            if (self.app/'src/gaussian-blur.ts').exists(): raise ValueError('Start state must genuinely have no blur module')
            build=self.worker('build',{'app':str(self.app)},self.directory/'initial-build',self.config['command_seconds'])
            if build.get('status')!='passed' or not self.baseline('initial',False): raise ValueError('No-blur start build/baseline failed')
            check=self.worker('selfcheck',{},self.directory/'evaluator-selfcheck',self.config['command_seconds'])
            if check.get('status')!='passed': self.stop='evaluator_defect'; return
            self.prepared()
            planner_guidance=self.guidance_section('planner',{'planning'},'planner')
            answer=self.ask(packets.planner_prompt(self.config,planner_guidance),'planner',model.PLANS,role='planner')
            for p in self.validate_plans(answer): self.experiment(p)
            self.freeze(); self.update_contract('contract-1')
            self.incumbent=self.evaluate('incumbent-v1')
            self.candidates_loop(None)
        except Exception as error:
            self.fail(error)
        finally:
            self.cleanup()

    def resume(self, source, prepare_only=False):
        """source: dict from load_source(); evidence/contract/suite reused, never re-frozen silently."""
        try:
            self.evidence=source['evidence']; self.claims=source['claims']
            if source.get('aligned_suite_path'):
                self.evidence=self.evidence+source['dev_evidence']
                copied=self.directory/'suites'/(source['aligned_suite']['id']+'.json')
                copied.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source['aligned_suite_path'],copied)
                self.suite=source['aligned_suite']; self.suite_hash=digest(copied)
                if self.suite_hash!=source['aligned_contract']['suite_sha256']: raise ValueError('Aligned suite copy mismatch')
                self.emit('suite_adopted',id=self.suite['id'],sha256=self.suite_hash,source=str(source['aligned_suite_path']))
            elif source['dev_evidence']:
                self.evidence=self.evidence+source['dev_evidence']; self.freeze()
                self.emit('suite_expanded',source_suite=source['suite']['id'],id=self.suite['id'],
                          added=[e['id'] for e in source['dev_evidence']],note='Base and every candidate run on this same suite.')
            else:
                copied=self.directory/'suites'/(source['suite']['id']+'.json')
                copied.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source['suite_path'],copied)
                self.suite=source['suite']; self.suite_hash=digest(copied)
                if self.suite_hash!=source['suite_sha256']: raise ValueError('Adopted suite hash mismatch')
                self.emit('suite_adopted',id=self.suite['id'],sha256=self.suite_hash,source=str(source['suite_path']))
            self.guard()
            check=self.worker('selfcheck',{},self.directory/'evaluator-selfcheck',self.config['command_seconds'])
            if check.get('status')!='passed': self.stop='evaluator_defect'; return
            self.base_label=source['candidate']
            self.base_result=self.evaluate('resume-base')
            historical={r['case_id']:r['metrics'] for r in source['candidate_evaluation']['cases']}
            reproduced={r['case_id']:r['metrics']==historical[r['case_id']] for r in self.base_result['cases'] if r['case_id'] in historical}
            self.emit('resume_base_evaluated',candidate=source['candidate'],reproduces_historical_metrics=reproduced,
                      feasible=self.feasible(self.base_result),objective=objective(self.base_result['cases']))
            if not self.feasible(self.base_result): raise ValueError('Selected base candidate is not feasible in the isolated workspace')
            previous={'evaluation':self.base_result,'label':'resume-base','rejected_operation_source':self.source_of(self.best),
                      'routing_suggestion':source['routing_suggestion'],
                      'note':'Development resume from saved rejected '+source['candidate']+' of '+source['run_id']+
                             '; the workspace contains it as the experimental base. It is not accepted.'}
            uncited=packets.uncited_evidence(self.claims,self.evidence)
            self.emit('contract_alignment',source_contract=str(source['contract_path']),uncited_before=uncited,
                      update='contract-resume' if uncited else None)
            if prepare_only:
                # Measure the exact next packets and enforce limits; no model request.
                self.ask(self.contract_packet(),'contract-resume-dry',self.contract_schema(),role='contract',dry=True)
                self.route(self.base_result,0,'resume-base',dry=True)
                self.builder(1,previous,dry=True)
                self.stop='prepared_only_no_model_request'; return
            if uncited:
                self.update_contract('contract-resume')
                self.emit('contract_alignment',uncited_after=packets.uncited_evidence(self.claims,self.evidence),
                          note='Any ids still uncited are labelled unincorporated_evidence in builder packets.')
            self.candidates_loop(previous)
        except Exception as error:
            self.fail(error)
        finally:
            self.cleanup()

    def fail(self,error):
        if isinstance(error,packets.PacketLimitError): self.stop='packet_limit_exceeded'
        else: self.stop='budget_exhausted' if isinstance(error,TimeoutError) else 'procedure_infrastructure_failure'
        self.emit('failure',classification=self.stop,error={'type':type(error).__name__,'message':str(error)[:2000]})

    def cleanup(self):
        self.checkpoints.restore(self.best)
        self.emit('restore',checkpoint=str(self.best),preserved_failure_records=True)
        try:
            final=self.worker('build',{'app':str(self.app)},self.directory/'final-build',self.config['command_seconds'],True)
            final_baseline=self.baseline('final',(self.app/'src/gaussian-blur.ts').exists(),True)
            self.guard()
        except Exception as error:
            final={'status':'failed','error':str(error)}; final_baseline=False
            self.stop+='; final_validation_failed'
        self.finish(final,final_baseline)

    def finish(self, final, final_baseline):
        report={'run_id':self.directory.name,'mode':self.mode,'provenance':self.provenance,
                'status':'accepted' if self.first_acceptance and final_baseline and final.get('status')=='passed' else 'unresolved',
                'stop_reason':self.stop,'first_acceptance':self.first_acceptance,'later_improvements':[],
                'evidence_ids':[e['id'] for e in self.evidence],'fresh_reference_attempts':self.budget.experiments,
                'candidate_attempts':self.attempts,'best_checkpoint':str(self.best),
                'states':{'accepted_best_known':str(self.accepted) if self.accepted else None,
                          'experimental_base':self.base_label if self.mode==RESUME else None,
                          'workspace_restored_to':str(self.best)},
                'final_build':final,'final_baseline_pass':final_baseline,'budget':self.budget.snapshot(),
                'elapsed_seconds':round(time.monotonic()-self.budget.start,3),
                'packet_sizes':[{k:p[k] for k in ['label','role','bytes','estimated_tokens','within_limits','dry_run']} for p in self.packet_sizes],
                'investigation_guidance_selections':getattr(self,'guidance_selections',{}),
                'limitations':['Visible suite only; no held-out evaluation. Hosted reference build unknown/unpinned.',
                               'Concise decisions only, no raw chain-of-thought. Trusted host is not OS sandboxed.',
                               'Input generator, browser procedure, evaluator, policy and acceptance rule supplied by ordinary code.',
                               'No other operation or whole-editor reconstruction.']}
        if self.mode==RESUME:
            report['limitations'].append('Development resume from a developer-selected failed candidate (and any developer-selected '
                                         'follow-up evidence); not a clean-start autonomous learning demonstration. Nothing is '
                                         'promoted into generated-app.')
        report['model_usage']=[{'invocation':str(p.relative_to(self.directory)),
                               'usage':json.loads(p.read_text()).get('usage'),
                               'elapsed_seconds':json.loads(p.read_text()).get('elapsed_seconds')} for p in sorted((self.directory/'model').rglob('invocation.json'))]
        for row,full in zip(report['packet_sizes'],self.packet_sizes):
            p=self.directory/'model'/row['label']/'invocation.json'
            usage=(json.loads(p.read_text()).get('usage') or {}) if p.exists() and not row['dry_run'] else {}
            actual=(usage.get('total') or {}).get('inputTokens')
            # Builder usage totals every tool round, so compare it with the cumulative projection.
            estimate=full.get('projected_cumulative_input_tokens') or row['estimated_tokens']
            row.update(actual_input_tokens=actual,compared_estimate=estimate)
            if actual: row['estimate_error']=round((estimate-actual)/actual,4)
        save(self.directory/'report.json',report)
        lines=['# Bounded Gaussian Blur learning run','',f"Mode: {self.mode}. Status: {report['status']}. Stop: {self.stop}.",'',
               f"Elapsed {report['elapsed_seconds']}s; {self.budget.experiments} fresh reference attempts; {len(self.attempts)} candidates.",
               f"First acceptance: {json.dumps(self.first_acceptance)}. Later improvements: none.",'',
               f"Final build: {final.get('status')}. Four exact baseline gates: {'pass' if final_baseline else 'fail'}.",
               f"Best checkpoint: {self.best}.",'', '## Actual trajectory','']
        for event in self.events:
            lines.append(f"- {event['elapsed_seconds']}s {event['event']}: "+json.dumps({k:v for k,v in event.items() if k not in ['event','elapsed_seconds','budget','sequence']},ensure_ascii=False))
        lines+=['','## Estimated vs actual input tokens','',
                'Estimates are calibrated on historical calls only; actual usage is the provider-reported total.','']
        lines+=[f"- {p['label']} ({p['role']}): estimated {p['compared_estimate']}, actual {p['actual_input_tokens']}"
                +(f", error {p['estimate_error']:+.1%}" if p.get('estimate_error') is not None else '') for p in report['packet_sizes']]
        lines+=['','## Remaining limits','']+['- '+s for s in report['limitations']]
        (self.directory/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        self.emit('stop',reason=self.stop,status=report['status'],report=str(self.directory/'report.md'))
        latest='latest-learning.json' if self.mode==CLEAN else 'latest-learning-dev-resume.json'
        save(ROOT/'evidence'/latest,{'status':report['status'],'mode':self.mode,'report':str(self.directory/'report.json')})
        self.report=report


def load_source(run, candidate, dev_evidence=None):
    """Verifies and loads a saved run's last frozen suite, contract, evidence and rejected candidate."""
    run=within(run,ROOT/'evidence/learning')
    events=[json.loads(line) for line in (run/'events.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    frozen=[e for e in events if e['event']=='suite_frozen']
    if not frozen: raise ValueError('Source run has no frozen suite')
    suite_path=run/'suites'/(frozen[-1]['id']+'.json')
    if digest(suite_path)!=frozen[-1]['sha256']: raise ValueError('Source suite hash does not match its frozen event')
    suite=json.loads(suite_path.read_text(encoding='utf-8'))
    suite['cases']=[relocated(row) for row in suite['cases']]
    for row in suite['cases']:
        if digest(row['input'])!=row['input_sha256'] or digest(row['expected'])!=row['expected_sha256']:
            raise ValueError('Source suite file changed: '+row['id'])
    record=json.loads((run/'candidates'/(candidate+'.json')).read_text(encoding='utf-8'))
    if record.get('status')!='rejected' or record.get('suite_sha256')!=frozen[-1]['sha256'] or 'evaluation' not in record:
        raise ValueError('Resume requires a fully evaluated rejected candidate on the source suite')
    checkpoint=run/'checkpoints'/candidate
    manifest=json.loads((checkpoint/'manifest.json').read_text())
    if sorted(manifest['scope'])!=sorted(SCOPE): raise ValueError('Checkpoint scope mismatch')
    for name,h in manifest['files'].items():
        if digest(checkpoint/name)!=h: raise ValueError('Corrupt candidate checkpoint: '+name)
    holder=object.__new__(Harness); holder.evidence=[]; holder.prepared()
    prepared={e['id']:e for e in holder.evidence}
    evidence=[]
    for row in suite['cases']:
        e=prepared.get(row['id']) or relocated(json.loads((run/'experiments'/row['id']/'evidence.json').read_text(encoding='utf-8')))
        if e['input_sha256']!=row['input_sha256'] or e['expected_sha256']!=row['expected_sha256']: raise ValueError('Evidence/suite mismatch: '+row['id'])
        evidence.append(e)
    contracts=sorted((run/'contracts').glob('contract-*.json'),key=lambda p:int(p.stem.split('-')[1]))
    if not contracts: raise ValueError('Source run has no accepted contract')
    claims=json.loads(contracts[-1].read_text(encoding='utf-8'))['claims']
    ids=[e['id'] for e in evidence]; validate_claims(claims,ids,ids)
    index=int(candidate.split('-')[1]); route=run/'model'/('route-'+str(index))/'invocation.json'
    routing=json.loads(route.read_text()).get('answer') if route.exists() else None
    dev=load_dev_evidence(dev_evidence,ids) if dev_evidence else []
    return {'run_id':run.name,'run':run,'candidate':candidate,'checkpoint':checkpoint,'manifest':manifest,
            'suite':suite,'suite_path':suite_path,'suite_sha256':frozen[-1]['sha256'],'evidence':evidence,'claims':claims,
            'contract_path':contracts[-1],'candidate_evaluation':record['evaluation'],'routing_suggestion':routing,'dev_evidence':dev,
            'dev_evidence_dir':str(within(dev_evidence,ROOT/'evidence/learning')) if dev_evidence else None}


def adopt_aligned_contract(source, path):
    """Verify prior contract bytes and exact suite identity before avoiding a paid alignment call."""
    path=within(path,ROOT/'evidence/learning')
    prior=path.parent.parent
    events=[json.loads(line) for line in (prior/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    frozen=[e for e in events if e['event']=='suite_frozen'][-1]
    suite_path=prior/'suites'/(frozen['id']+'.json')
    if digest(suite_path)!=frozen['sha256']: raise ValueError('Aligned suite changed')
    suite=json.loads(suite_path.read_text())
    expected=source['evidence']+source['dev_evidence']
    signature=lambda rows:[(e['id'],e['percentage'],e['input_sha256'],e['expected_sha256']) for e in rows]
    if signature(suite['cases'])!=signature(expected): raise ValueError('Aligned contract suite mismatch')
    for key in ['policy','exact_baseline_policy','region_rule','objective','tie_policy']:
        if suite[key]!=source['suite'][key]: raise ValueError('Aligned contract scoring mismatch')
    request=prior/'model'/path.stem/'invocation.json'
    invocation=json.loads(request.read_text())
    contract=json.loads(path.read_text())
    if invocation.get('status')!='passed' or invocation.get('answer')!=contract: raise ValueError('Aligned contract differs from recorded completion')
    ids=[e['id'] for e in expected]
    validate_claims(contract['claims'],ids,ids)
    if packets.uncited_evidence(contract['claims'],expected): raise ValueError('Aligned contract lacks evidence citations')
    for row,e in zip(suite['cases'],expected):
        w,h=e['input_samples']['png']['width'],e['input_samples']['png']['height']; cx,cy=w//2,h//2
        regions={'center':[max(0,cx-5),max(0,cy-5),min(w,cx+6),min(h,cy+6)],'boundary':[0,0,min(4,w),h]}
        if row['regions']!=regions: raise ValueError('Aligned suite region mismatch')
    source['aligned_suite_path']=suite_path; source['aligned_suite']={**suite,'cases':[relocated(row) for row in suite['cases']]}
    source['claims']=contract['claims']; source['contract_path']=path
    source['aligned_contract']={'path':str(path),'sha256':digest(path),'suite_sha256':frozen['sha256'],
                                'reason':'Same ten visible cases and unchanged scoring; prior successful alignment reused.'}


def load_dev_evidence(directory, existing_ids):
    directory=within(directory,ROOT/'evidence/learning')
    records=[]
    for path in sorted((directory/'evidence').glob('*.json')):
        e=relocated(json.loads(path.read_text(encoding='utf-8')))
        if e.get('selected_by')!='developer' or e['id'] in existing_ids: raise ValueError('Unexpected development evidence '+path.name)
        if digest(e['input'])!=e['input_sha256'] or digest(e['expected'])!=e['expected_sha256']: raise ValueError('Development evidence changed: '+e['id'])
        records.append(e)
    if not records: raise ValueError('No observed development evidence records')
    return records


def prepare_workspace(source, workspace):
    """Creates (or verifies) an isolated copy of the saved candidate; generated-app is never written."""
    workspace=Path(workspace)
    if not workspace.is_absolute(): workspace=ROOT/workspace
    if workspace.exists():
        app=resolve_app(workspace)
        for name,h in source['manifest']['files'].items():
            if not (app/name).is_file() or digest(app/name)!=h:
                raise ValueError('Existing workspace diverges from '+source['candidate']+' ('+name+'); use a new --workspace')
        extra=[n for n in SCOPE if n not in source['manifest']['files'] and (app/n).exists()]
        if extra: raise ValueError('Existing workspace has undeclared extra sources: '+str(extra))
        return app,False
    workspace.mkdir(parents=True); app=resolve_app(workspace)
    if digest(APP/'package-lock.json')!=source['manifest']['files']['package-lock.json']:
        raise ValueError('Installed dependencies do not match the candidate lockfile')
    for name in source['manifest']['files']:
        (app/name).parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source['checkpoint']/name,app/name)
    shutil.copytree(APP/'node_modules',app/'node_modules',symlinks=False)
    save(app.parent/(app.name+'.workspace.json'),{'source_run':source['run_id'],'source_candidate':source['candidate'],
         'checkpoint':str(source['checkpoint']),'files':source['manifest']['files'],
         'node_modules':'copied from generated-app/node_modules; package-lock hash matches the checkpoint',
         'created':datetime.now(timezone.utc).isoformat()})
    return app,True


def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--config',type=Path,default=ROOT/'learning.config.json')
    parser.add_argument('--resume-from',type=Path,help='Saved run directory under evidence/learning (development resume)')
    parser.add_argument('--candidate',help='Rejected candidate label in that run, e.g. candidate-2')
    parser.add_argument('--workspace',type=Path,help='Isolated dev-workspaces/<name> for the resumed candidate')
    parser.add_argument('--dev-evidence',type=Path,help='Developer follow-up evidence directory; expands the suite for base and candidates')
    parser.add_argument('--repair-focus',choices=['boundary-alpha'],help='Developer-scoped one-candidate alpha repair')
    parser.add_argument('--aligned-contract',type=Path,help='Reuse a hash-verified prior resume contract on this same suite')
    parser.add_argument('--prepare-only',action='store_true',help='Verify, evaluate base, measure/enforce packets; never contacts a model')
    args=parser.parse_args()
    config=json.loads(args.config.read_text(encoding='utf-8-sig'))
    if args.resume_from is None:
        if args.candidate or args.workspace or args.dev_evidence or args.prepare_only or args.repair_focus or args.aligned_contract:
            parser.error('--candidate/--workspace/--dev-evidence/--prepare-only require --resume-from')
        harness=Harness(config); harness.run()
    else:
        if not args.candidate or not args.workspace: parser.error('--resume-from requires --candidate and --workspace')
        source=load_source(args.resume_from,args.candidate,args.dev_evidence)
        if args.repair_focus and config['candidates']!=1: parser.error('Scoped repair requires candidates=1')
        if args.aligned_contract: adopt_aligned_contract(source,args.aligned_contract)
        app,created=prepare_workspace(source,args.workspace)
        provenance={'source_run':source['run_id'],'source_candidate':source['candidate'],
                    'source_checkpoint_manifest_sha256':digest(source['checkpoint']/'manifest.json'),
                    'source_suite':{'id':source['suite']['id'],'sha256':source['suite_sha256']},
                    'source_contract':{'path':str(source['contract_path']),'sha256':digest(source['contract_path'])},
                    'source_candidate_record_sha256':digest(source['run']/'candidates'/(source['candidate']+'.json')),
                    'dev_evidence':{'directory':source['dev_evidence_dir'],'ids':[e['id'] for e in source['dev_evidence']],
                                    'selected_by':'developer'} if source['dev_evidence'] else None,
                    'workspace_created':created,'prepare_only':args.prepare_only,
                    'repair_focus':args.repair_focus,'aligned_contract':source.get('aligned_contract'),
                    'clean_start_checkpoint_preserved':str(source['run']/'checkpoints/no-blur-start'),
                    'main_generated_app':'protected and unchanged; nothing is promoted implicitly',
                    'note':'Developer-initiated continuation from a saved rejected candidate. Same independent execution, '
                           'exact baseline and frozen-suite scoring gates. Not a clean-start autonomous demonstration.'}
        harness=Harness(config,app,RESUME,provenance); harness.repair_focus=args.repair_focus; harness.resume(source,args.prepare_only)
    return 0 if harness.report['status']=='accepted' else 1

if __name__=='__main__': raise SystemExit(main())
