"""Small parameterized adjustment harness built on existing trusted learning gates."""
import json
from learning.run import Harness, SCOPE
from learning.brightness import BrightnessBroker, DEFINITIONS, render
from learning.core import exact, strings, text, integer, save, digest, validate_claims, decide
from learning.operations import operation_spec
from learning.diagnostics import describe
from learning import model, packets
from evaluator.compare import load_policy
from .spec import validate, parameter, value_in_domain

class AdjustmentBroker(BrightnessBroker):
    writable={'src/main.tsx','src/contrast.ts','README.md'}

PLAN=model.obj({'question':model.S,'hypotheses':model.arr(model.S),'input':model.obj({'kind':{'type':'string','enum':list(DEFINITIONS)},'width':model.I,'height':model.I}),'value':{'type':'number'},'predictions':model.arr(model.S),'usefulness':model.S})

class AdjustmentHarness(Harness):
    operation='contrast'; source_scope=SCOPE|{'src/brightness.ts','src/contrast.ts'}
    def __init__(self, config, app, spec, validated, notify=lambda *a,**k:None):
        self.spec=validate(spec,ready=True); self.domain=parameter(spec); self.notify=notify
        if validated.get('status')!='validated' or validated.get('spec_sha256')!=__import__('hashlib').sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest(): raise ValueError('Procedure validation required')
        super().__init__(config,app=app,mode='development_resume',provenance={'feature_spec':spec,'procedure_validation':validated,'isolated':True,'promoted':False})
        from build_shell import APP
        from adapter.png import ROOT
        for path in (ROOT/'features').glob('*'):
            if path.is_file(): self.protected[str(path)]=digest(path)
        for base in (APP, self.app):
            for name in ('src/brightness.ts','src/current-image.ts'):
                if (base/name).is_file(): self.protected[str(base/name)]=digest(base/name)
        save(self.directory/'protected-manifest.json',self.protected)
        self.op=operation_spec('contrast',spec)
    def ask(self,*args,**kwargs):
        try: return super().ask(*args,**kwargs)
        finally:
            if len(args)>1:
                path=self.directory/'model'/args[1]/'invocation.json'
                if path.is_file(): self.notify('usage',usage=json.loads(path.read_text()).get('usage'))
    def emit(self,kind,**data):
        super().emit(kind,**data)
        self.notify(kind,**data)
    def baseline(self,label,allow_blur=False,cleanup=False):
        return super().baseline(label,False,cleanup,allow_brightness=True)
    def compact(self):
        return [{'id':e['id'],'value':e['value'],'input_spec':e['input_spec'],'input':packets.compact_summary(e['input_samples']),'export':packets.compact_summary(e['export_samples'])} for e in self.evidence]
    def experiment(self,p):
        exact(p,['question','hypotheses','input','value','predictions','usefulness'])
        for k in ('question','usefulness'): text(p[k])
        strings(p['hypotheses'],2,5); strings(p['predictions'],2,5)
        exact(p['input'],['kind','width','height'])
        if p['input']['kind'] not in DEFINITIONS: raise ValueError('Unsupported bounded diagnostic generator')
        for k in ('width','height'): integer(p['input'][k],3,257)
        value_in_domain(self.domain,p['value']); self.budget.spend('experiment')
        ident='adjustment-'+str(self.budget.experiments); d=self.directory/'experiments'/ident
        path=self.directory/'inputs'/(ident+'.png'); path.parent.mkdir(exist_ok=True)
        save(d/'preregistered.json',p); render(p['input']).save(path); self.emit('experiment',id=ident,plan=p)
        r=self.worker('feature-reference',{'spec':self.spec,'input_path':str(path),'input_sha256':digest(path),'value':p['value']},d,self.config['reference_seconds'])
        if r['status']!='observed' or r['accepted']!=p['value']: raise ValueError('Procedure failed; no behavior evidence admitted')
        e={'id':ident,'value':p['value'],'input_spec':p['input'],'input':str(path),'expected':r['output_path'],'input_sha256':digest(path),'expected_sha256':digest(r['output_path']),'input_samples':describe(path),'export_samples':describe(r['output_path'])}
        self.evidence.append(e); save(self.directory/'evidence'/(ident+'.json'),e); self.emit('evidence',id=ident,status='OBSERVED')
    def freeze(self):
        self.suite={'id':'visible-contrast-v1','cases':[{**{k:e[k] for k in ('id','input','expected','input_sha256','expected_sha256','value')},'regions':{'full':[0,0,e['input_samples']['png']['width'],e['input_samples']['png']['height']]}} for e in self.evidence],'policy':load_policy(),'operation':self.op}
        save(self.directory/'suite.json',self.suite); self.suite_hash=digest(self.directory/'suite.json'); self.emit('suite_frozen',id=self.suite['id'],sha256=self.suite_hash)
    def evaluate(self,label,cleanup=False):
        r=self.worker('candidate',{'operation':'contrast','spec':self.spec,'app':str(self.app),'suite':self.suite,'suite_sha256':self.suite_hash},self.directory/'evaluations'/label,self.config['command_seconds'],cleanup)
        r['baseline_pass']=self.baseline(label+'-gates',cleanup=cleanup)
        # Existing brightness behavior is a regression gate, outside all builder/repair evidence.
        from adapter.png import ROOT
        regression=[]
        for row in json.loads((ROOT/'evidence/brightness/visible-suite.json').read_text())['cases']:
            target=self.directory/'brightness-regression/inputs'/(row['id']+'.png'); target.parent.mkdir(parents=True,exist_ok=True)
            source=ROOT/row['input']; __import__('shutil').copyfile(source,target)
            regression.append({**row,'input':str(target),'expected':str(ROOT/row['expected'])})
        suite={'id':'existing-brightness-baseline','cases':regression,'policy':load_policy()}
        result=self.worker('candidate',{'operation':'brightness','app':str(self.app),'suite':suite,'suite_sha256':__import__('hashlib').sha256(json.dumps(suite,sort_keys=True).encode()).hexdigest()},self.directory/'brightness-regression'/label,self.config['command_seconds'],cleanup)
        r['baseline_pass']=r['baseline_pass'] and result.get('build_valid',False) and result.get('independent',False) and result.get('ui_valid',False) and bool(result.get('cases')) and all(c['status']=='passed' for c in result['cases'])
        save(self.directory/'evaluations'/label/'evaluation.json',r)
        self.emit('evaluation',label=label,result=r); return r
    def builder(self,index,previous):
        sources={n:(self.app/n).read_text(encoding='utf-8') for n in ('src/main.tsx','src/current-image.ts')}
        prompt='Implement Contrast independently from only supplied evidence and contract. No brightness formula or neutral assumption. Write src/contrast.ts exporting applyContrast(raster: Raster, value: number): Raster. Preserve input immutability, dimensions, codec, brightness and every existing baseline. Wire Image -> Contrast… with accessible Contrast slider and Apply/Close; disable with no image. Source/config/dependency restrictions apply. No reference internals, execution or other tools. Only src/main.tsx, src/contrast.ts and README.md writable. '+json.dumps({'observed_domain':self.domain,'claims':self.claims,'evidence':self.compact(),'previous':previous,'policy':self.suite['policy']},separators=(',',':'))
        reader=packets.EvidenceReader({e['id']:{'input':e['input'],'export':e['expected']} for e in self.evidence},self.config['evidence_reads'])
        self.ask(prompt,'builder-'+str(index),None,True,role='repair' if previous else 'builder',supplied=sources,reader=reader)
    def finish(self,final,final_baseline):
        self.report={'status':'accepted' if self.first_acceptance and final_baseline and final.get('status')=='passed' else 'unresolved','first_acceptance':self.first_acceptance,'stop_reason':self.stop,'final_build':final,'final_baseline_pass':final_baseline,'candidate_attempts':self.attempts,'evidence_ids':[e['id'] for e in self.evidence],'suite_sha256':getattr(self,'suite_hash',None),'budget':self.budget.snapshot(),'promoted':False,'scope':'frozen visible suite only; final evaluation separate'}
        save(self.directory/'report.json',self.report); self.emit('stop',status=self.report['status'],reason=self.stop)
    def run(self):
        try:
            if (self.app/'src/contrast.ts').exists() or 'applyContrast' in (self.app/'src/main.tsx').read_text(): raise ValueError('Contrast must be absent')
            if self.worker('build',{'app':str(self.app)},self.directory/'initial-build',self.config['command_seconds'])['status']!='passed' or not self.baseline('initial'): raise ValueError('Initial baseline failed')
            if self.worker('selfcheck',{},self.directory/'selfcheck',self.config['command_seconds'])['status']!='passed': raise ValueError('Evaluator suspect')
            self.notify('stage',stage='Investigate')
            # Supplied generators are bounded image probes, not Contrast evidence or algorithm assumptions.
            answer=self.ask('Plan 2..4 bounded experiments distinguishing competing Contrast hypotheses. Choose values from the observed domain; at least two distinct values. Choose diagnostic images for the questions, not brightness formula assumptions. '+json.dumps({'spec':self.spec,'generators':DEFINITIONS,'budget':self.budget.snapshot()}),'planner',model.obj({'plans':model.arr(PLAN)}),role='planner')
            plans=answer['plans']
            if not 2<=len(plans)<=self.config['fresh_experiments'] or len({p['value'] for p in plans})<2: raise ValueError('Require distinguishing bounded experiments')
            for p in plans: self.experiment(p)
            self.freeze()
            answer=self.ask('Build evidence-backed claims. No VERIFIED status before independent acceptance. Separate observed behavior from hypotheses; cite exact evidence IDs. '+json.dumps({'spec':self.spec,'evidence':self.compact()}),'contract',model.CONTRACT,role='contract')
            self.claims=validate_claims(answer['claims'],[e['id'] for e in self.evidence],[e['id'] for e in self.evidence],domain=(self.domain['min'],self.domain['max']))
            save(self.directory/'contract.json',answer); self.emit('claim_update',decision=answer['decision'])
            previous=None
            for index in range(1,self.config['candidates']+1):
                self.budget.spend('candidate'); label='candidate-'+str(index); self.notify('stage',stage='Reconstruct')
                record={'id':label,'status':'started'}; self.attempts.append(record)
                self.builder(index,previous); cp=self.checkpoints.snapshot(label); self.notify('stage',stage='Verify')
                r=self.evaluate(label); self.guard(); accepted,reason=decide(r)
                record.update(status='accepted' if accepted else 'rejected',reason=reason,checkpoint=str(cp))
                if accepted:
                    self.best=self.accepted=cp; self.first_acceptance={'candidate_id':label,'suite_sha256':self.suite_hash}; self.stop='all_frozen_visible_and_baseline_gates'; break
                self.emit('rejection',candidate_id=label,reason=reason)
                if r.get('evaluator_suspect'): self.stop='evaluator_defect'; break
                previous={'classification':reason,'discrepancies':packets.discrepancy_section(r,self.evidence,self.directory/'evaluations'/label,parameter_key='value')}
                self.checkpoints.restore(self.best); self.stop='candidate_budget_exhausted'
        except Exception as e:
            if self.attempts and self.attempts[-1]['status']=='started':
                self.attempts[-1].update(status='failed',error={'type':type(e).__name__,'message':str(e)[:1000]})
                self.checkpoints.snapshot(self.attempts[-1]['id']+'-partial')
            self.fail(e)
        finally: self.cleanup()
