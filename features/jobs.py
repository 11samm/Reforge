"""Durable local jobs, single browser owner, bounded child process and cancellation."""
import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from learning.core import save
from adapter.png import ROOT
from .spec import request_id

TERMINAL={'accepted','unresolved','failed','cancelled'}
STAGES=['Discover','Validate procedure','Investigate','Reconstruct','Verify']
ARTIFACTS={'spec.json','discovery-summary.json','validation.json','visible-report.json','final-summary.json','repair-summary.json','preparation.json'}

def scrub(value):
    s=str(value)[:1500]
    return re.sub(r'(?:[A-Za-z]:[\\/]|/(?:home|Users|tmp|workspace)/)[^\s"<>]+','[local evidence]',s)

class JobStore:
    def __init__(self, directory, recover=False):
        self.directory=Path(directory); self.directory.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock(); self.active=None; self.cancel_flags={}
        self.clock=time.monotonic; self.starts={}
        for p in self.directory.glob('*/job.json'):
            job=json.loads(p.read_text())
            if recover and job['status'] not in TERMINAL:
                job.update(status='cancelled' if job['status']=='cancelling' else 'failed',activity='Interrupted host process; acceptance not established')
                self.persist(job)
    def persist(self,job):
        p=self.directory/job['id']/'job.json'; temp=p.with_suffix('.tmp'); save(temp,job); os.replace(temp,p)
    def get(self,ident):
        if not re.fullmatch(r'[a-f0-9]{32}',ident): raise ValueError('Invalid job ID')
        with self.lock:
            job=json.loads((self.directory/ident/'job.json').read_text())
            if ident in self.starts and job['status'] not in TERMINAL: job['elapsed_seconds']=round(self.clock()-self.starts[ident],3)
            return job
    def list(self):
        return sorted([self.get(p.parent.name) for p in self.directory.glob('*/job.json')],key=lambda j:j['created'],reverse=True)[:30]
    def create(self,request):
        request_id(request)
        from .pipeline import BUDGET
        with self.lock:
            if self.active or any(j['status'] not in TERMINAL for j in self.list()): raise RuntimeError('A feature job already owns the reference browser')
            ident=uuid.uuid4().hex; self.active=ident; self.cancel_flags[ident]=threading.Event(); self.starts[ident]=self.clock()
            job={'id':ident,'request':request.strip(),'status':'queued','stage':'Discover','created':time.time(),'elapsed_seconds':0,'activity':'Queued for bounded execution','budget':BUDGET,'usage':None,'events':[],'evidence':[]}
            self.persist(job); self.event(ident,'queued',activity=job['activity']); return self.get(ident)
    def event(self,ident,kind,**data):
        with self.lock:
            job=self.get(ident)
            if job['status'] in TERMINAL: return
            elapsed=round(self.clock()-self.starts[ident],3)
            event={'sequence':len(job['events'])+1,'event':kind,'elapsed_seconds':elapsed}
            if data.get('stage') in STAGES: event['stage']=data['stage']; job['stage']=data['stage']
            if 'activity' not in data:
                activities={'experiment':'Running diagnostic experiment','evaluation':'Evaluating independent candidate execution','baseline':'Checking original editor baselines','claim_update':'Updating evidence-backed behavior contract','packet_measured':'Checking model packet budget','failure':'Recording failure: '+str(data.get('classification','unclassified')),'rejection':'Candidate rejected: '+str(data.get('reason','unclassified')),'restore':'Restoring isolated checkpoint'}
                if kind in activities: data['activity']=activities[kind]
            if kind=='experiment' and isinstance(data.get('plan'),dict):
                plan=data['plan']
                job['experiment']={k:plan[k] for k in ('question','usefulness','input','value') if k in plan}
            if 'activity' in data: job['activity']=event['activity']=scrub(data['activity'])
            if kind=='usage' and isinstance(data.get('usage'),dict):
                job['usage']=(job['usage'] or [])+[data['usage']]
            if data.get('artifact') in ARTIFACTS:
                path=ROOT/'evidence/learning'/('feature-'+ident)/data['artifact']
                # Serve only a scrubbed presentation copy, never expected PNGs or model packets.
                if path.is_file() and not path.is_symlink() and path.stat().st_size<=150000:
                    raw=json.loads(path.read_text())
                    def clean(v):
                        if isinstance(v,dict): return {k:clean(x) for k,x in v.items() if k not in ('actions','audit','records','output_path','output','values','requests','prompt')}
                        if isinstance(v,list): return [clean(x) for x in v]
                        return scrub(v) if isinstance(v,str) else v
                    save(self.directory/ident/data['artifact'],clean(raw))
                    event['artifact']='/api/jobs/'+ident+'/evidence/'+data['artifact']; job['evidence'].append({'url':event['artifact'],'available_at':elapsed,'name':data['artifact']})
            job['elapsed_seconds']=elapsed; job['events'].append(event); self.persist(job)
    def finish(self,ident,result):
        with self.lock:
            job=self.get(ident)
            if job['status'] in TERMINAL: return
            state=result.get('status')
            if state not in TERMINAL: state='failed'
            if self.cancel_flags[ident].is_set(): state='cancelled'
            self.event(ident,'stop',activity=result.get('classification',state))
            job=self.get(ident); job.update(status=state,activity=scrub(result.get('classification',state)),usage=result.get('usage'),promoted=False)
            job['events'][-1]['status']=state; self.persist(job)
            if self.active==ident: self.active=None
    def cancel(self,ident):
        with self.lock:
            job=self.get(ident)
            if job['status'] not in TERMINAL:
                self.cancel_flags[ident].set(); job['status']='cancelling'; job['activity']='Stopping owned process tree'; self.persist(job)
            return self.get(ident)

class BrowserLock:
    def __init__(self,name='feature-browser'): self.name=name
    def __enter__(self):
        p=ROOT/'.scratch'/(self.name+'.lock'); p.parent.mkdir(exist_ok=True)
        self.file=p.open('a+b'); self.file.seek(0); self.file.write(b'0'); self.file.flush(); self.file.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.file.close(); raise RuntimeError('Reference browser owned by another feature pipeline')
        return self
    def __exit__(self,*args): self.file.close()

def kill(proc):
    if proc.poll() is not None: return
    if os.name=='nt': subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
    else:
        import signal
        os.killpg(proc.pid,signal.SIGKILL)
    proc.wait(timeout=10)

def execute(store,ident):
    proc=None; tree=None; forced=False
    try:
        with BrowserLock():
            with BrowserLock('reference-browser'): pass # Reject an already active legacy reference controller.
            job=store.get(ident); store.event(ident,'start',activity='Bounded local pipeline started')
            if store.cancel_flags[ident].is_set():
                store.finish(ident,{'status':'cancelled','classification':'cancelled_before_execution'}); return
            with store.lock:
                job=store.get(ident); job['status']='running'; store.persist(job)
            proc=subprocess.Popen([sys.executable,'-m','features.child',ident],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,start_new_session=os.name!='nt')
            from .processes import OwnedTree
            tree=OwnedTree(proc)
            # Child waits for this handshake before launching browsers or model subprocesses.
            proc.stdin.write('owned\n'); proc.stdin.flush(); proc.stdin.close()
            def read():
                for line in proc.stdout:
                    if len(line)>20000: continue
                    try:
                        e=json.loads(line)
                        if e.get('feature_event'): store.event(ident,e['event'],**e.get('data',{}))
                    except (ValueError,KeyError): pass
            reader=threading.Thread(target=read,daemon=True); reader.start()
            deadline=time.monotonic()+job['budget']['seconds']
            while proc.poll() is None:
                if store.cancel_flags[ident].wait(0.2): forced=True; kill(proc); break
                if time.monotonic()>=deadline: forced=True; kill(proc); break
            reader.join(timeout=3)
            p=ROOT/'evidence/learning'/('feature-'+ident)/'job-result.json'
            result=json.loads(p.read_text()) if not forced and p.exists() and proc.returncode==0 else {'status':'failed','classification':'interrupted_or_budget_exhausted'}
            store.finish(ident,result)
    except Exception as e: store.finish(ident,{'status':'failed','classification':scrub(e)})
    finally:
        if proc is not None: kill(proc)
        if tree is not None: tree.close()
