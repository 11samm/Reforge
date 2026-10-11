"""Trusted bounded pipeline; CLI requires an explicit --pilot switch."""
import argparse
import copy
import hashlib
import json
import shutil
import time
import uuid
from pathlib import Path
from PIL import Image
from adapter.png import ROOT, compare_pngs
from learning.core import DEFAULTS, save, digest, decide
from .spec import request_id, parameter, value_in_domain, default_setup
from .learning import AdjustmentHarness

BUDGET={'seconds':1200,'harness_repairs':5,'repair_seconds':300,'same_failure_limit':2,'discovery_seconds':90,'discovery_invocations':2,'action_corrections':2,'discovery_actions':20,'observations':24,'validation_replays':2,'default_check':1,'experiments':4,'candidates':2,'reference_retries':0,'builder_tool_calls':12,'evidence_reads':6,'final_cases':2}

def diagnostic(path):
    im=Image.new('RGBA',(17,9)); im.putdata([(v,v,v,255) for y in range(9) for v in (0,1,2,15,31,63,64,127,128,129,191,223,239,253,254,255,32)])
    path.parent.mkdir(parents=True,exist_ok=True); im.save(path)

def validate_procedure(spec, path, directory, worker):
    setup=default_setup(spec)
    p=parameter(spec); value=p['min']+p['step']*max(1,round((p['max']-p['min'])/p['step']/3))
    value_in_domain(p,value)
    default=worker('feature-reference',{'spec':spec,'input_path':str(path),'input_sha256':digest(path),'value':p['default']},directory/'validation'/'defaults',60)
    if default.get('status')!='observed' or default.get('accepted')!=p['default'] or not default.get('original_confirmation',{}).get('rgba_equal'): return {'status':'procedure_failure','records':[default]}
    if not compare_pngs(path,default['output_path'])['rgba_equal']:
        return {'status':'behavior_mismatch','reason':'Observed defaults not identity on diagnostic; neutral setup unresolved','records':[default]}
    records=[]
    for i in range(2):
        r=worker('feature-reference',{'spec':spec,'input_path':str(path),'input_sha256':digest(path),'value':value},directory/'validation'/('replay-'+str(i)),60)
        if r.get('status')!='observed' or r.get('accepted')!=value or not r.get('original_confirmation',{}).get('rgba_equal'):
            return {'status':'procedure_failure','records':records+[r]}
        records.append(r)
    if not compare_pngs(records[0]['output_path'],records[1]['output_path'])['rgba_equal']:
        return {'status':'behavior_mismatch','reason':'Fresh-document replay outputs differ','records':records}
    result={'status':'validated','spec_sha256':hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest(),'records':records,'requested':value,'default_setup':{**setup,'status':'verified_on_diagnostic','input_sha256':digest(path),'output_sha256':digest(default['output_path']),'identity_rgba_equal':True},'default_record':default}
    save(directory/'validation.json',result); return result

def run(request, job_id, emit):
    feature=request_id(request)
    start=time.monotonic(); directory=ROOT/'evidence/learning'/('feature-'+job_id)
    directory.mkdir(parents=True,exist_ok=False)
    from .preparation import prepare
    app, preparation=prepare(request,job_id)
    save(directory/'preparation.json',preparation)
    emit('evidence',artifact='preparation.json',activity='Isolated editor prepared; target operation absent')
    # Harness process/deadline helper, without constructing or modifying an accepted workspace.
    from learning.run import Harness
    from learning.core import Budget
    control=object.__new__(Harness); control.config=copy.deepcopy(DEFAULTS); control.config.update(run_seconds=600,reserve_seconds=100)
    control.budget=Budget(control.config); control.directory=directory
    patch=None
    def worker(kind,request,d,timeout):
        if patch and kind in ('feature-discovery','feature-reference'): request={**request,'harness_patch':str(patch)}
        return Harness.worker(control,kind,request,d,timeout)
    path=directory/'inputs/diagnostic.png'; diagnostic(path)
    emit('stage',stage='Discover',activity='Inspecting visible menus and adjustment controls')
    from .repair import classify, repair, RepairBudget, recall, remember
    patch=recall(directory/'repairs',emit) if feature=='contrast' else None
    repairs=RepairBudget(seconds=300,attempts=5); history=[]; latest_case=None
    for attempt in range(6):
        attempt_dir=directory/'discovery'/('attempt' if attempt==0 else 'attempt-'+str(attempt+1))
        r=worker('feature-discovery',{'request':request,'input_path':str(path),'input_sha256':digest(path),'timeout':90},attempt_dir,100)
        history.append({'attempt':attempt+1,'status':r.get('status'),'error':r.get('error')})
        save(directory/'repair-summary.json',{'attempts':history,'repairs_used':repairs.used,'host_modified':bool(patch),'canonical_host_modified':False})
        if r.get('status')=='discovered':
            if patch and latest_case and feature=='contrast': remember(patch,latest_case)
            break
        case=classify(attempt_dir,r)
        if case is None or not repairs.admit(case): break
        emit('activity',activity='Classified reproducible harness defect; isolated repair '+str(repairs.used)+'/5')
        candidate=repair(case,directory/'repairs'/str(repairs.used),emit,min(repairs.remaining(),control.budget.remaining()-100),prior=patch)
        if candidate is None: break
        patch=candidate; latest_case=case
    emit('evidence',artifact='repair-summary.json',activity='Original attempts and repair history retained')
    save(directory/'discovery-summary.json',{'status':r.get('status'),'error':r.get('error'),'unresolved':r.get('spec',{}).get('unresolved',[]),'observation_ids':r.get('observation_ids',[])})
    emit('evidence',artifact='discovery-summary.json',activity='Discovery outcome recorded')
    if r.get('spec'):
        save(directory/'spec.json',r['spec']); emit('evidence',artifact='spec.json',activity='Observed facts and unresolved questions recorded')
    if r.get('status')!='discovered': return {'status':'unresolved' if r.get('status')=='unresolved' else 'failed','classification':'discovery_failure','detail':r.get('error',r.get('spec',{}).get('unresolved',[]))}
    spec=r['spec']
    invocation=directory/'discovery/attempt/model/invocation.json'
    if invocation.is_file(): emit('usage',usage=json.loads(invocation.read_text()).get('usage'))
    p=parameter(spec)
    if any(type(p[k]) is not int and (type(p[k]) is not float or not p[k].is_integer()) for k in ('min','max','step')):
        return {'status':'unresolved','classification':'Noninteger discovered domain is outside initial learning contract support'}
    emit('stage',stage='Validate procedure',activity='Validating import, accepted values, fresh export and replay')
    validation=validate_procedure(spec,path,directory,worker)
    emit('evidence',artifact='validation.json',activity=validation['status'])
    if validation['status']!='validated':
        save(directory/'validation.json',validation)
        return {'status':'failed','classification':validation['status']}
    # Never copy old evidence/final outputs or mutate the accepted editor.
    config=copy.deepcopy(DEFAULTS); config.update(fresh_experiments=4,candidates=2,retries=0,run_seconds=max(120,min(600,int(1200-(time.monotonic()-start)))),reserve_seconds=100,command_seconds=90)
    h=AdjustmentHarness(config,app,spec,validation,notify=emit)
    h.provenance.update(preparation=preparation,feature_absent_at_start=True,
                        clean_start_autonomous_demonstration=True,
                        learning_origin='fresh_discovery_and_experiments')
    save(h.directory/'provenance.json',h.provenance)
    h.harness_patch=patch
    # Save presentation records under the job root; only explicitly copied artifacts are served.
    h.run(); save(directory/'visible-report.json',h.report); emit('evidence',artifact='visible-report.json',activity='Frozen visible gate outcome recorded')
    if h.report['status']!='accepted': return {'status':'unresolved','classification':h.report['stop_reason']}
    return final_check(spec,app,h,directory,emit,patch)

def final_check(spec,app,control,directory,emit,patch=None):
    from learning.run import Harness
    from .live import hide
    hide()
    # One final set, after all repair/model calls finish. Never supplied to a model.
    emit('stage',stage='Verify',activity='Once-only fresh final evaluation, with no repair context')
    from learning.brightness import render
    from evaluator.compare import load_policy
    rows=[]; p=parameter(spec)
    for i,kind in enumerate(('channel_ramps','patches')):
        ident='final-'+str(i); final_input=directory/'final/inputs'/(ident+'.png'); final_input.parent.mkdir(parents=True,exist_ok=True)
        render({'kind':kind,'width':43+i*4,'height':13+i*4}).save(final_input)
        value=p['min']+p['step']*round((p['max']-p['min'])/p['step']*(0.2 if i==0 else 0.8))
        r=Harness.worker(control,'feature-reference',{'spec':spec,'input_path':str(final_input),'input_sha256':digest(final_input),'value':value,**({'harness_patch':str(patch)} if patch else {})},directory/'final/experiments'/ident,60,cleanup=True)
        if r.get('status')!='observed': return {'status':'failed','classification':'final_procedure_failure'}
        rows.append({'id':ident,'value':value,'input':str(final_input),'expected':r['output_path'],'input_sha256':digest(final_input),'expected_sha256':digest(r['output_path']),'regions':{'full':[0,0,43+i*4,13+i*4]}})
    feature=spec['feature_id']
    suite={'id':'final-'+feature+'-v1','policy':load_policy(),'cases':rows}; save(directory/'final/suite.json',suite)
    result=Harness.worker(control,'candidate',{'operation':feature,'spec':spec,'app':str(app),'suite':suite,'suite_sha256':digest(directory/'final/suite.json')},directory/'final/evaluation',90,cleanup=True)
    result['baseline_pass']=control.report['final_baseline_pass']; accepted,reason=decide(result)
    save(directory/'final-summary.json',{'status':'accepted' if accepted else 'unresolved','classification':reason,'cases':[{k:c.get(k) for k in ('case_id','status','classification','metrics')} for c in result.get('cases',[])],'promoted':False})
    emit('evidence',artifact='final-summary.json',activity='Independent final evaluation complete')
    return {'status':'accepted' if accepted else 'unresolved','classification':reason,'promoted':False,'harness_repaired':bool(patch),'scope':'frozen visible and two once-only fresh cases; isolated workspace'}

def continue_job(source_job,job_id,emit,request=None):
    import re
    from adapter.png import within
    if not re.fullmatch(r'[a-f0-9]{32}',source_job): raise ValueError('Invalid resume job ID')
    directory=ROOT/'evidence/learning'/('feature-'+job_id); directory.mkdir(parents=True,exist_ok=False)
    old=ROOT/'evidence/learning'/('feature-'+source_job)
    spec=json.loads((old/'spec.json').read_text(encoding='utf-8'))
    if request is not None and request_id(request)!=spec['feature_id']: raise ValueError('Resume request differs from source feature')
    validation=json.loads((old/'validation.json').read_text(encoding='utf-8'))
    # Find only the visible learning record tied to this exact isolated source job.
    sources=[]
    source_app=ROOT/'dev-workspaces'/('feature-'+source_job)
    for item in (ROOT/'evidence/learning').glob('*/provenance.json'):
        provenance=json.loads(item.read_text(encoding='utf-8'))
        if provenance.get('app','').replace('\\','/')==source_app.as_posix(): sources.append(item.parent)
    if len(sources)!=1: raise ValueError('Ambiguous resume source')
    source=sources[0]
    manifest=json.loads((source/'checkpoints/experimental-base-start/manifest.json').read_text(encoding='utf-8'))
    for name,expected in manifest['files'].items():
        path=within(source_app/name,source_app)
        if expected is None:
            if path.exists(): raise ValueError('Resume workspace differs from restored checkpoint')
        elif not path.is_file() or digest(path)!=expected: raise ValueError('Resume workspace changed')
    app=ROOT/'dev-workspaces'/('feature-'+job_id)
    shutil.copytree(source_app,app,ignore=shutil.ignore_patterns('node_modules','dist'))
    shutil.copytree(source_app/'node_modules',app/'node_modules')
    save(directory/'spec.json',spec); save(directory/'validation.json',validation)
    save(directory/'continuation.json',{'source_job':source_job,'mode':'development_resume_saved_evidence','new_reference_experiments':0})
    config=copy.deepcopy(DEFAULTS); config.update(fresh_experiments=4,candidates=2,retries=0,run_seconds=600,reserve_seconds=100,command_seconds=90)
    h=AdjustmentHarness(config,app,spec,validation,notify=emit); h.resume_source=source
    h.provenance.update(source_job=source_job,resume_source=source.name,clean_start_autonomous_demonstration=False)
    save(h.directory/'provenance.json',h.provenance)
    emit('stage',stage='Investigate',activity='Resuming saved visible experiments; no new reference investigation')
    h.run(); save(directory/'visible-report.json',h.report); emit('evidence',artifact='visible-report.json',activity='Continuation gate outcome recorded')
    if h.report['status']!='accepted': return {'status':'unresolved','classification':h.report['stop_reason'],'mode':'development_resume_saved_evidence'}
    result=final_check(spec,app,h,directory,emit)
    result['mode']='development_resume_saved_evidence'; return result

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--pilot',action='store_true'); parser.add_argument('--prepare-demo',action='store_true'); parser.add_argument('--request',default='Implement Contrast'); parser.add_argument('--resume-job'); args=parser.parse_args()
    request_id(args.request)
    if args.prepare_demo:
        if args.pilot or args.resume_job: parser.error('--prepare-demo cannot invoke or resume a learning run')
        from .preparation import prepare
        app,record=prepare(args.request,uuid.uuid4().hex)
        print(json.dumps(record)); return 0
    if not args.pilot:
        print(json.dumps({'mode':'prepare-only','budget':BUDGET,'model_invoked':False})); return 0
    from .jobs import JobStore, execute
    from .jobs import BrowserLock
    with BrowserLock('feature-service'):
        store=JobStore(ROOT/'evidence/feature-jobs',recover=True); job=store.create(args.request)
        if args.resume_job:
            import re
            if not re.fullmatch(r'[a-f0-9]{32}',args.resume_job): raise ValueError('Invalid resume job ID')
            job['resume_job']=args.resume_job; store.persist(job)
        execute(store,job['id'])
    print(json.dumps(store.get(job['id']))); return 0 if store.get(job['id'])['status']=='accepted' else 1

if __name__=='__main__': raise SystemExit(main())
