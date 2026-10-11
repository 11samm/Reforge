"""Job-owned, separate reference/candidate processes with one Playwright owner each.

Only trusted parent code submits worker requests. Browser handles and reference
state never cross into the candidate process. The idle loop pumps real frames.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from adapter.png import ROOT, EVIDENCE, within
from learning.core import save
from . import live

runtime=None
pool=None
REFERENCE={'reference','brightness-reference','feature-reference','feature-discovery','devreference'}

def active():
    return runtime is not None

@contextmanager
def job_environment(ident):
    values={'REFORGE_LIVE_JOB':ident,'REFORGE_LIVE_ENABLED':'1'}
    previous={key:os.environ.get(key) for key in values}
    os.environ.update(values)
    try: yield
    finally:
        for key,value in previous.items():
            if value is None: os.environ.pop(key,None)
            else: os.environ[key]=value

def replace_page(page):
    if runtime is not None:
        previous=runtime.get('page'); runtime['page']=page
        if previous and previous!=page:
            previous.context.close()

@contextmanager
def candidate_browser():
    if active():
        if runtime['role']!='candidate': raise ValueError('Wrong browser owner')
        yield runtime['browser']
    else:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=not live.enabled(),timeout=30000)
            try: yield browser
            finally: live.close(); browser.close()

class Pool:
    def __init__(self,app,cancel=None):
        self.app=Path(app).resolve(); self.cancel=cancel; self.workers={}; self.closed=False
    def __enter__(self):
        global pool
        if pool is not None: raise RuntimeError('Browser pool already owned')
        pool=self
        try:
            for role in live.ROLES:
                folder=live.directory()/('owner-'+role+'-'+uuid.uuid4().hex)
                folder.mkdir(parents=True)
                log=(folder/'worker.log').open('w',encoding='utf-8')
                proc=subprocess.Popen([sys.executable,'-m','features.sessions',role,str(folder),str(self.app)],cwd=ROOT,
                    env={**os.environ,'REFORGE_SESSION_PARENT':str(os.getpid())},stdout=log,stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,
                    start_new_session=os.name!='nt')
                from .processes import OwnedTree
                try: tree=OwnedTree(proc)
                except Exception:
                    proc.kill(); proc.wait(); log.close(); raise
                self.workers[role]=(proc,tree,folder,log)
            return self
        except Exception:
            self.close(); raise
    def worker(self,kind,request,directory,timeout):
        if self.closed: raise RuntimeError('Browser pool closed')
        role='reference' if kind in REFERENCE else 'candidate'
        if kind not in REFERENCE|{'candidate','build'}: raise ValueError('Unsupported persistent worker')
        proc,tree,folder,log=self.workers[role]
        directory=within(directory,EVIDENCE/'learning'); directory.mkdir(parents=True,exist_ok=True)
        save(directory/'request.json',request)
        token=uuid.uuid4().hex; temporary=folder/'next.tmp'
        temporary.write_text(json.dumps({'token':token,'kind':kind,'directory':str(directory)}),encoding='utf-8')
        os.replace(temporary,folder/'command.json')
        start=time.monotonic()
        while time.monotonic()-start<timeout:
            if self.cancel is not None and self.cancel.is_set(): self.close(); raise RuntimeError('Browser job cancelled')
            if proc.poll() is not None: self.close(); raise RuntimeError('Browser owner exited; inspect '+str(folder/'worker.log'))
            done=folder/'done.json'
            if done.exists():
                result=json.loads(done.read_text(encoding='utf-8'))
                if result['token']==token:
                    save(directory/'process.json',{'exit':result['exit'],'persistent_owner_pid':proc.pid,'elapsed_seconds':round(time.monotonic()-start,3)})
                    return json.loads((directory/'result.json').read_text(encoding='utf-8'))
            time.sleep(.02) # Parent observes completion; actions are never paced.
        self.close(); raise TimeoutError('Persistent worker deadline; both browser owners terminated')
    def close(self):
        global pool
        if self.closed: return
        self.closed=True
        for proc,tree,folder,log in self.workers.values():
            (folder/'stop').touch()
        deadline=time.monotonic()+5
        for proc,tree,folder,log in self.workers.values():
            try: proc.wait(timeout=max(.1,deadline-time.monotonic()))
            except subprocess.TimeoutExpired:
                from .jobs import kill
                kill(proc)
            finally: tree.close(); log.close()
        if pool is self: pool=None
    def __exit__(self,*args): self.close()

def start_pool(app):
    if live.enabled() and pool is None: Pool(app).__enter__()

def stop_pool():
    if pool is not None: pool.close()

def serve(role,folder,app):
    global runtime
    from playwright.sync_api import sync_playwright
    from .jobs import BrowserLock
    from contextlib import nullcontext
    from learning.worker import execute, build
    from functools import partial
    from http.server import ThreadingHTTPServer
    from verify_shell import QuietHandler
    import threading
    # Linux owners use their own process groups for bounded termination. Also
    # terminate that group if the parent disappears while a command is blocked.
    if os.name!='nt':
        def watch_parent():
            while live.alive(int(os.environ['REFORGE_SESSION_PARENT'])): time.sleep(.25)
            import signal
            os.killpg(os.getpid(),signal.SIGKILL)
        threading.Thread(target=watch_parent,daemon=True).start()
    api=None
    with BrowserLock('reference-browser') if role=='reference' else nullcontext():
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=False,timeout=30000)
            runtime={'role':role,'pw':pw,'browser':browser,'page':None}
            try:
                live.start('feature-reference' if role=='reference' else 'build',{})
                page=browser.new_page(viewport=live.VIEWPORT,device_scale_factor=1,accept_downloads=True)
                replace_page(page)
                if role=='reference':
                    live.attach(page,role)
                    from adapter.minipaint import URL
                    page.goto(URL,wait_until='domcontentloaded')
                else:
                    # The actual candidate owner first displays the absent-feature shell.
                    preview=ROOT/'evidence/learning'/('offline-feature-preview-'+os.environ['REFORGE_LIVE_JOB'])
                    preview.mkdir(parents=True,exist_ok=True); build(preview,app)
                    api=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(app/'dist')))
                    threading.Thread(target=api.serve_forever,daemon=True).start()
                    page.route('**/*',lambda r:r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{api.server_port}/') else r.abort())
                    page.goto(f'http://127.0.0.1:{api.server_port}',wait_until='networkidle')
                    live.attach(page,role)
                live.action('Waiting for scheduled harness actions'); last=None
                while not (folder/'stop').exists() and live.alive(int(os.environ['REFORGE_SESSION_PARENT'])):
                    command=folder/'command.json'
                    data=json.loads(command.read_text(encoding='utf-8')) if command.exists() else None
                    if data and data['token']!=last:
                        kind=data['kind']
                        if kind not in REFERENCE|{'candidate','build'} or (kind in REFERENCE)!=(role=='reference'): raise ValueError('Wrong role request')
                        d=within(data['directory'],EVIDENCE/'learning')
                        request=json.loads((d/'request.json').read_text(encoding='utf-8'))
                        code=execute(kind,request,d)
                        last=data['token']; pending=folder/'done.tmp'
                        pending.write_text(json.dumps({'token':last,'exit':code}),encoding='utf-8'); os.replace(pending,folder/'done.json')
                        live.action('Waiting for scheduled harness actions')
                    # Pump callbacks on the single owning thread while this role is idle.
                    runtime['page'].wait_for_timeout(50)
            finally:
                live.close(); browser.close(); runtime=None
                if api: api.shutdown(); api.server_close()

if __name__=='__main__':
    sys.modules['features.sessions']=sys.modules[__name__]
    role,folder,app=sys.argv[1:]
    if role not in live.ROLES or not live.enabled(): raise ValueError('Invalid browser owner')
    folder=within(folder,ROOT/'.scratch/live'/os.environ['REFORGE_LIVE_JOB'])
    serve(role,folder,Path(app))
