"""Small parameterized adjustment harness built on existing trusted learning gates."""
import json
import copy
import shutil
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

def contract_schema(evidence_ids,case_ids):
    schema=copy.deepcopy(model.CONTRACT)
    claims=schema['properties']['claims']; claims['minItems']=1; claims['maxItems']=16
    props=claims['items']['properties']
    for field in ('supporting_evidence','contradicting_evidence'):
        props[field]={'type':'array','items':{'type':'string','enum':list(evidence_ids)}}
    props['verification_cases']={'type':'array','items':{'type':'string','enum':list(case_ids)}}
    props['status']={'type':'string','enum':[v for v in model.STATUSES if v!='VERIFIED_WITHIN_SCOPE']}
    return schema

class AdjustmentHarness(Harness):
    operation='contrast'; source_scope=SCOPE|{'src/brightness.ts','src/contrast.ts'}
    def __init__(self, config, app, spec, validated, notify=lambda *a,**k:None):
        self.spec=validate(spec,ready=True); self.domain=parameter(spec); self.notify=notify
        self.operation=self.spec['feature_id']
        if validated.get('status')!='validated' or validated.get('spec_sha256')!=__import__('hashlib').sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest(): raise ValueError('Procedure validation required')
        if validated.get('default_setup',{}).get('status')!='verified_on_diagnostic' or validated['default_setup'].get('identity_rgba_equal') is not True: raise ValueError('Diagnostic default identity gate required')
        super().__init__(config,app=app,mode='development_resume',provenance={'feature_spec':spec,'procedure_validation':validated,'isolated':True,'promoted':False})
        from build_shell import APP
        from adapter.png import ROOT
        for path in (ROOT/'features').glob('*'):
            if path.is_file(): self.protected[str(path)]=digest(path)
        for base in (APP, self.app):
            for name in ('src/brightness.ts','src/contrast.ts','src/current-image.ts'):
                if base == self.app and name == 'src/'+self.operation+'.ts': continue
                if (base/name).is_file(): self.protected[str(base/name)]=digest(base/name)
        save(self.directory/'protected-manifest.json',self.protected)
        self.op=operation_spec(self.operation,spec)
    def worker(self,kind,request,directory,timeout,*args,**kwargs):
        patch=getattr(self,'harness_patch',None)
        if patch and kind=='feature-reference': request={**request,'harness_patch':str(patch)}
        return super().worker(kind,request,directory,timeout,*args,**kwargs)
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
        return super().baseline(label,False,cleanup,allow_brightness=(self.app/'src/brightness.ts').is_file())
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
        self.suite={'id':'visible-'+self.operation+'-v1','cases':[{**{k:e[k] for k in ('id','input','expected','input_sha256','expected_sha256','value')},'regions':{'full':[0,0,e['input_samples']['png']['width'],e['input_samples']['png']['height']]}} for e in self.evidence],'policy':load_policy(),'operation':self.op}
        save(self.directory/'suite.json',self.suite); self.suite_hash=digest(self.directory/'suite.json'); self.emit('suite_frozen',id=self.suite['id'],sha256=self.suite_hash)
    def evaluate(self,label,cleanup=False):
        r=self.worker('candidate',{'operation':self.operation,'spec':self.spec,'app':str(self.app),'suite':self.suite,'suite_sha256':self.suite_hash},self.directory/'evaluations'/label,self.config['command_seconds'],cleanup)
        r['baseline_pass']=self.baseline(label+'-gates',cleanup=cleanup)
        if self.operation=='brightness':
            save(self.directory/'evaluations'/label/'evaluation.json',r)
            self.emit('evaluation',label=label,result=r); return r
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
        name=self.operation.title()
        prompt='Implement '+name+' independently from only supplied evidence and contract. Do not assume a formula or neutral behavior. Write '+self.op['source']+' exporting '+self.op['export']+'(raster: Raster, value: number): Raster. Preserve input immutability, dimensions, codec and every existing baseline. Wire Image -> '+self.op['ui_item']+' with accessible '+name+' slider and Apply/Close; disable with no image and unsupported depth16. Source/config/dependency restrictions apply. No reference internals, execution or other tools. Only src/main.tsx, '+self.op['source']+' and README.md writable. '+json.dumps({'observed_domain':self.domain,'claims':self.claims,'evidence':self.compact(),'previous':previous,'policy':self.suite['policy']},separators=(',',':'))
        prompt += ' Make minimal changes to the supplied shell. Preserve all existing accessible names exactly, including Original image preview: <filename>, Original image thumbnail: <filename>, and No image loaded. The operation menu must open on an empty document; disable its slider and Apply, not its menu item. The target module is absent in this starting/restored workspace: do not read a missing file. Write the complete module. A denied tool request invalidates the invocation. Preserve original PNG/JPEG import/export and all unavailable tools.'
        reader=packets.EvidenceReader({e['id']:{'input':e['input'],'export':e['expected']} for e in self.evidence},self.config['evidence_reads'])
        self.ask(prompt,'builder-'+str(index),None,True,role='repair' if previous else 'builder',supplied=sources,reader=reader)
    def finish(self,final,final_baseline):
        self.report={'status':'accepted' if self.first_acceptance and final_baseline and final.get('status')=='passed' else 'unresolved','first_acceptance':self.first_acceptance,'stop_reason':self.stop,'final_build':final,'final_baseline_pass':final_baseline,'candidate_attempts':self.attempts,'evidence_ids':[e['id'] for e in self.evidence],'suite_sha256':getattr(self,'suite_hash',None),'budget':self.budget.snapshot(),'promoted':False,'scope':'frozen visible suite only; final evaluation separate'}
        save(self.directory/'report.json',self.report); self.emit('stop',status=self.report['status'],reason=self.stop)
    def build_contract(self):
        ids=[e['id'] for e in self.evidence]; schema=contract_schema(ids,ids)
        prompt='Build evidence-backed claims. No VERIFIED status before independent acceptance. Cite exact IDs only in supporting_evidence, contradicting_evidence and verification_cases. verification_cases may be empty; future test descriptions belong in unresolved, never case IDs. '+json.dumps({'spec':self.spec,'evidence':self.compact(),'allowed_case_ids':ids})
        failures=[]
        for index in range(2):
            answer=self.ask(prompt,'contract' if index==0 else 'contract-correction',schema,role='contract')
            try:
                claims=validate_claims(answer['claims'],ids,ids,domain=(self.domain['min'],self.domain['max']))
            except ValueError as error:
                failures.append({'attempt':index+1,'error':str(error)[:1000]})
                save(self.directory/'contract-failures.json',failures)
                self.emit('contract_validation_failure',attempt=index+1,error=str(error)[:1000])
                if index: raise
                prompt += ' Correct this rejected contract using the same frozen evidence. Validation error: '+str(error)[:1000]+' Previous contract: '+json.dumps(answer)
            else:
                self.claims=claims; save(self.directory/'contract.json',answer)
                self.emit('claim_update',decision=answer['decision']); return

    def reuse_evidence(self,source):
        from adapter.png import within
        from build_shell import APP
        from evaluator.compare import load_policy
        from learning.diagnostics import describe
        source=within(source,APP.parent/'evidence/learning')
        report=json.loads((source/'report.json').read_text(encoding='utf-8'))
        if digest(source/'suite.json')!=report['suite_sha256']: raise ValueError('Resume suite hash changed')
        suite=json.loads((source/'suite.json').read_text(encoding='utf-8'))
        if suite['policy']!=load_policy(): raise ValueError('Resume evaluator policy changed')
        if report['candidate_attempts'] or report['first_acceptance'] or report['stop_reason']!='procedure_infrastructure_failure': raise ValueError('Only pre-candidate contract failure can resume here')
        provenance=json.loads((source/'provenance.json').read_text(encoding='utf-8'))
        if provenance.get('feature_spec')!=self.spec: raise ValueError('Resume feature specification changed')
        ids=[row['id'] for row in suite['cases']]
        if ids!=report['evidence_ids'] or not 2<=len(ids)<=4 or len(set(ids))!=len(ids): raise ValueError('Resume evidence IDs invalid')
        for row in suite['cases']:
            import re
            if not re.fullmatch(r'adjustment-[1-4]',row['id']): raise ValueError('Resume evidence ID invalid')
            record=json.loads((source/'evidence'/(row['id']+'.json')).read_text(encoding='utf-8'))
            if record['id']!=row['id'] or record['value']!=row['value']: raise ValueError('Resume case metadata changed')
            value_in_domain(self.domain,record['value'])
            for field in ('input','expected'):
                path=within(row[field],source)
                if digest(path)!=row[field+'_sha256'] or record[field+'_sha256']!=row[field+'_sha256']: raise ValueError('Resume evidence hash changed')
                target=self.directory/('inputs' if field=='input' else 'reused-visible')/(row['id']+'.png')
                target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(path,target); record[field]=str(target)
            record['input_samples']=describe(record['input']); record['export_samples']=describe(record['expected'])
            self.evidence.append(record); save(self.directory/'evidence'/(record['id']+'.json'),record)
        self.budget.experiments=len(self.evidence)
        self.freeze()
        save(self.directory/'continuation.json',{'mode':'development_resume_saved_evidence','source':source.name,'source_suite_sha256':report['suite_sha256'],'new_reference_experiments':0,'source_untouched':True})
        self.guard()

    def run(self):
        try:
            if (self.app/self.op.get('source','src/'+self.operation+'.ts')).exists() or self.op.get('export','apply'+self.operation.title()) in (self.app/'src/main.tsx').read_text(): raise ValueError(self.operation.title()+' must be absent')
            if self.worker('build',{'app':str(self.app)},self.directory/'initial-build',self.config['command_seconds'])['status']!='passed' or not self.baseline('initial'): raise ValueError('Initial baseline failed')
            if self.worker('selfcheck',{},self.directory/'selfcheck',self.config['command_seconds'])['status']!='passed': raise ValueError('Evaluator suspect')
            self.notify('stage',stage='Investigate')
            if getattr(self,'resume_source',None):
                self.reuse_evidence(self.resume_source)
            else:
                # Supplied generators are probes, not Contrast evidence.
                answer=self.ask('Plan 2..4 bounded experiments distinguishing competing '+self.operation.title()+' hypotheses. Choose values from the observed domain; at least two distinct values. '+json.dumps({'spec':self.spec,'generators':DEFINITIONS,'budget':self.budget.snapshot()}),'planner',model.obj({'plans':model.arr(PLAN)}),role='planner')
                plans=answer['plans']
                if not 2<=len(plans)<=self.config['fresh_experiments'] or len({p['value'] for p in plans})<2: raise ValueError('Require distinguishing bounded experiments')
                for p in plans: self.experiment(p)
                self.freeze()
            self.build_contract()
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
