"""Read-only, ephemeral presentation of the exact worker-owned Chromium page.
No remote debugger endpoint, reference internals or held-out outputs are published.
"""
import json
import os
import re
import time
import uuid
from pathlib import Path
from adapter.png import ROOT

ROLES = ('reference', 'candidate')
VIEWPORT = {'width': 1440, 'height': 1000}

def enabled():
    return bool(re.fullmatch(r'[a-f0-9]{32}', os.environ.get('REFORGE_LIVE_JOB', ''))) and os.environ.get('REFORGE_LIVE_ENABLED') == '1'

def directory():
    return ROOT/'.scratch/live'/os.environ['REFORGE_LIVE_JOB']

def write(role, value):
    d=directory(); d.mkdir(parents=True, exist_ok=True)
    p=d/(role+'.json'); temp=p.with_suffix('.'+uuid.uuid4().hex+'.tmp')
    temp.write_text(json.dumps(value, allow_nan=False), encoding='utf-8'); os.replace(temp,p)

def presentation_failure(role, error):
    from learning.core import save
    root=ROOT/'evidence/learning'/('feature-'+os.environ['REFORGE_LIVE_JOB'])
    failure={'at':time.time(),'role':role,'type':type(error).__name__,'message':str(error)[:2000]}
    root.mkdir(parents=True,exist_ok=True)
    with (root/'live-presentation-failures.jsonl').open('a',encoding='utf-8') as log:
        log.write(json.dumps(failure)+'\n')
    from .presentation import append_status
    append_status(root/(role+'-presentation-status.jsonl'),{'state':'degraded','failure':failure})


class Session:
    def __init__(self, role, state='launching', purpose='', parameters=None):
        self.role=role; self.cdp=None
        self.value={'job_id':os.environ.get('REFORGE_LIVE_JOB'), 'session_id':uuid.uuid4().hex,
            'pid':os.getpid(), 'state':state, 'viewport':VIEWPORT, 'purpose':purpose[:1500],
            'parameters':parameters or {}, 'action':'Starting worker', 'action_started':time.time(),
            'frame':None, 'frame_sequence':0, 'mode':'live'}
        self.publish()
    def publish(self):
        if enabled():
            try: write(self.role, self.value)
            except OSError as error: presentation_failure(self.role,error)
    def action(self, action, parameters=None):
        self.value.update(action=action[:200], action_started=time.time())
        if parameters is not None: self.value['parameters']={**self.value['parameters'],**parameters}
        self.publish()
    def attach(self, page):
        if not enabled(): return
        try:
            if self.cdp:
                try: self.cdp.detach()
                except Exception: pass
            self.value.update(session_id=uuid.uuid4().hex, frame=None, frame_sequence=0)
            generation=self.value['session_id']
            self.cdp=page.context.new_cdp_session(page)
            def frame(event):
                if self.value['session_id']!=generation: return
                try:
                    self.cdp.send('Page.screencastFrameAck', {'sessionId':event['sessionId']})
                    self.value.update(state='ready', frame=event['data'], captured_at=time.time(),
                        frame_sequence=self.value['frame_sequence']+1)
                    self.publish()
                except Exception: pass
            self.cdp.on('Page.screencastFrame', frame)
            def closed(*_):
                if self.value['session_id']==generation: self.close()
            page.on('close',closed)
            page.on('crash',closed)
            page.context.browser.on('disconnected',closed)
            self.cdp.send('Page.startScreencast', {'format':'jpeg','quality':65,
                'maxWidth':1440,'maxHeight':1000,'everyNthFrame':1})
            self.value.update(state='ready'); self.publish()
        except Exception:
            self.value.update(state='unavailable', frame=None); self.publish()
    def close(self, state='disconnected'):
        if self.cdp:
            try: self.cdp.send('Page.stopScreencast'); self.cdp.detach()
            except Exception: pass
            self.cdp=None
        self.value.update(state=state, frame=None); self.publish()

current=None

def start(kind, request):
    global current
    if not enabled(): return
    role='candidate' if kind in ('candidate','build') else 'reference'
    if kind not in ('candidate','build','feature-discovery','feature-reference','reference','brightness-reference','devreference'): return
    parameters={k:request[k] for k in ('value','brightness','percentage') if k in request}
    if 'input_path' in request: parameters['input']=Path(request['input_path']).name
    from . import sessions
    if sessions.active() and current and current.role==role:
        current.value['parameters']=parameters
        current.action('Starting '+kind)
        return
    current=Session(role,'building' if role=='candidate' else 'launching',
        {'candidate':'Independent UI/batch agreement check','build':'Build and type check',
         'feature-discovery':'Discover visible controls', 'feature-reference':'Diagnostic import, adjustment and export'}.get(kind,'Reference procedure'),parameters)

def attach(page, role):
    if enabled() and current and current.role==role: current.attach(page)

def action(name, **parameters):
    if enabled() and current:
        # Only trusted visible action arguments, never exports or DOM snapshots.
        current.action(name, parameters or None)

def close():
    if current: current.close()

def hide():
    from .sessions import stop_pool
    stop_pool()
    if enabled():
        for role in ROLES: Session(role,'hidden','Held-out evaluation is not presented').close('hidden')
    os.environ['REFORGE_LIVE_ENABLED']='0'

def alive(pid):
    if os.name=='nt':
        import ctypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.restype=ctypes.c_void_p
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle: return False
        try:
            code=ctypes.c_ulong(); kernel.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(code))
            return code.value==259
        finally: kernel.CloseHandle(ctypes.c_void_p(handle))
    try: os.kill(pid,0); return True
    except OSError: return False

def snapshot(job):
    result={'job_id':job['id'],'mode':'live','stage':job['stage'],'elapsed_seconds':job['elapsed_seconds'],'sessions':{},'experiment':job.get('experiment'), 'activity':job.get('activity','')}
    for role in ROLES:
        value={'state':'unavailable','frame':None,'viewport':VIEWPORT,'mode':'live'}
        p=ROOT/'.scratch/live'/job['id']/(role+'.json')
        try:
            if p.stat().st_size<=2500000:
                saved=json.loads(p.read_text(encoding='utf-8'))
                if saved.get('job_id')==job['id']:
                    value=saved
                    if value['state'] in ('ready','building','launching') and not alive(value['pid']):
                        value={**value,'state':'disconnected','frame':None}
        except (OSError,ValueError,KeyError): pass
        if job['status'] not in ('running','queued'):
            value={**value,'state':'disconnected','frame':None}
        if role=='candidate' and job['status']=='running' and job['stage']=='Reconstruct' and value['state'] in ('unavailable','disconnected'):
            value={**value,'state':'building','frame':None,'action':job.get('activity','Reconstructing candidate')}
        if value.get('action_started'):
            value['action_elapsed_seconds']=round(max(0,time.time()-value['action_started']),3)
        diagnostic=ROOT/'evidence/learning'/('feature-'+job['id'])/(role+'-presentation-status.jsonl')
        from .presentation import latest_status
        try: value['presentation']=latest_status(diagnostic)
        except OSError: value['presentation']={'state':'degraded','failure':{'message':'Presentation diagnostics unavailable'}}
        value.pop('pid',None)
        result['sessions'][role]=value
    return result
