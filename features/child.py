"""Owned child. Only the job ID crosses the command boundary."""
import json
import sys
from adapter.png import ROOT
from learning.core import save
from .pipeline import run, continue_job
from .jobs import JobStore

def main():
    if sys.stdin.readline().strip()!='owned': raise RuntimeError('Job owner handshake missing')
    ident=sys.argv[1]
    # Read existing job without startup recovery (the parent still owns it).
    import re
    if not re.fullmatch(r'[a-f0-9]{32}',ident): raise ValueError('Invalid job ID')
    job=json.loads((ROOT/'evidence/feature-jobs'/ident/'job.json').read_text())
    import os
    os.environ['REFORGE_LIVE_JOB']=ident
    os.environ['REFORGE_LIVE_ENABLED']='1'
    def emit(kind,**data): print(json.dumps({'feature_event':True,'event':kind,'data':data}),flush=True)
    try: result=continue_job(job['resume_job'],ident,emit,request=job['request']) if job.get('resume_job') else run(job['request'],ident,emit)
    except Exception as e: result={'status':'failed','classification':type(e).__name__+': '+str(e)[:1000]}
    finally:
        from .sessions import stop_pool
        stop_pool()
    d=ROOT/'evidence/learning'/('feature-'+ident)
    usages=[]
    # Model records may live in both discovery and the reused harness's separate evidence directory.
    for p in (ROOT/'evidence/learning').glob('*/provenance.json'):
        try:
            r=json.loads(p.read_text())
            if r.get('app','').replace('\\','/').endswith('/feature-'+ident):
                for m in (p.parent/'model').glob('*/invocation.json'): usages.append(json.loads(m.read_text()).get('usage'))
        except ValueError: pass
    for p in (d/'discovery').rglob('invocation.json'): usages.append(json.loads(p.read_text()).get('usage'))
    for p in (d/'repairs').rglob('invocation.json'): usages.append(json.loads(p.read_text()).get('usage'))
    result['usage']=[u for u in usages if u is not None] or None
    save(d/'job-result.json',result)

if __name__=='__main__': main()
