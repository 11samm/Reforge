"""No-model deterministic browser verification; synthetic job metadata, real actions.
Uses existing visible Brightness inputs/gates. Does not implement/promote a feature.
"""
import argparse
import json
import os
import shutil
import threading
from adapter.png import ROOT
from learning.core import digest, save
from evaluator.compare import load_policy
from .jobs import JobStore, BrowserLock
from .service import server

LABEL='Deterministic browser verification: synthetic job metadata, real harness actions; no learning run or model calls.'

def prepare(store):
    job=store.create('Implement Contrast')
    job.update(request='Saved Brightness browser verification',presentation_label=LABEL,status='running')
    store.persist(job); store.event(job['id'],'start',activity=LABEL)
    return job['id']

def _run(store,ident,owners):
    d=ROOT/'evidence/learning'/('offline-feature-live-'+ident)
    d.mkdir(parents=True)
    rows=json.loads((ROOT/'evidence/brightness/visible-suite.json').read_text())['cases'][:2]
    for row in rows:
        path=d/'inputs'/(row['id']+'.png'); path.parent.mkdir(exist_ok=True)
        shutil.copyfile(ROOT/row['input'],path); row['input']=str(path); row['expected']=str(ROOT/row['expected'])
    def worker(kind,request,path):
        return owners.worker(kind,request,path,120)
    try:
        store.event(ident,'stage',stage='Validate procedure',activity='Real miniPaint import, Brightness adjustment and export on saved diagnostic')
        neutral=worker('brightness-reference',{'id':rows[0]['id'],'input_path':rows[0]['input'],'input_sha256':rows[0]['input_sha256'],'brightness':rows[0]['brightness'],'window_position':[0,0]},d/'experiments/neutral')
        ref=worker('brightness-reference',{'id':rows[1]['id'],'input_path':rows[1]['input'],'input_sha256':rows[1]['input_sha256'],'brightness':rows[1]['brightness'],'window_position':[0,0]},d/'experiments/reference')
        save(d/'neutral-result.json',neutral)
        save(d/'reference-result.json',ref)
        store.event(ident,'stage',stage='Verify',activity='Real candidate build, exact visible batch comparison and UI/export agreement')
        suite={'id':'saved-visible-brightness-live-check','cases':rows,'policy':load_policy()}
        result=worker('candidate',{'operation':'brightness','app':str(ROOT/'generated-app'),'suite':suite,'suite_sha256':digest(ROOT/'evidence/brightness/visible-suite.json')},d/'candidate')
        save(d/'candidate-result.json',result)
        passed=neutral.get('status')=='observed' and ref.get('status')=='observed' and result.get('ui_valid') and all(c['status']=='passed' for c in result.get('cases',[]))
        # Verification fixture is never an accepted feature job.
        store.finish(ident,{'status':'unresolved' if passed else 'failed','classification':'deterministic_browser_checks_passed' if passed else 'deterministic_browser_checks_failed'})
    except Exception as e: store.finish(ident,{'status':'failed','classification':str(e)})
    print(json.dumps({'job_id':ident,'label':LABEL,'result':store.get(ident)['activity'],'artifacts':str(d)}),flush=True)

def run(store,ident):
    from .sessions import Pool, job_environment
    with job_environment(ident):
        try:
            with Pool(ROOT/'generated-app',store.cancel_flags[ident]) as owners:
                _run(store,ident,owners)
        except Exception as e:
            store.finish(ident,{'status':'failed','classification':str(e)})

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--port',type=int,default=5190); a=p.parse_args()
    with BrowserLock('feature-service'), BrowserLock():
        store=JobStore(ROOT/'evidence/feature-jobs',recover=True)
        api=server(store,a.port,enabled=False)
        ident=prepare(store)
        runner=threading.Thread(target=run,args=(store,ident),daemon=True); runner.start()
        print('No-model verification API at http://127.0.0.1:'+str(a.port)+'; open Implement a feature',flush=True)
        try: api.serve_forever()
        except KeyboardInterrupt: pass
        finally:
            if store.active: store.cancel(store.active)
            runner.join(timeout=15)
            api.server_close()

if __name__=='__main__': main()
