"""Owned child. Only the job ID crosses the command boundary."""
import json
import sys
from pathlib import Path
from adapter.png import ROOT
from learning.core import save
from .pipeline import run, continue_job
from .jobs import JobStore

def event_emitter(directory, transport):
    """Commit stage/usage/outcome events before optional presentation transport."""
    import time
    directory = Path(directory)
    def emit(kind, **data):
        event = {'feature_event': True, 'event': kind, 'data': data, 'recorded_at': time.time()}
        with (directory / 'pipeline-events.jsonl').open('a', encoding='utf-8') as log:
            log.write(json.dumps(event, allow_nan=False) + '\n')
        try: transport(event)
        except OSError as error:
            with (directory / 'transport-failures.jsonl').open('a', encoding='utf-8') as log:
                log.write(json.dumps({'at': time.time(), 'type': type(error).__name__, 'message': str(error)}) + '\n')
    return emit


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
    emit=event_emitter(ROOT/'evidence/learning'/('feature-'+ident), lambda event: print(json.dumps(event),flush=True))
    try: result=continue_job(job['resume_job'],ident,emit,request=job['request']) if job.get('resume_job') else run(job['request'],ident,emit,prepared=job.get('prepared_demo'))
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
