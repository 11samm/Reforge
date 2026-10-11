"""Loopback-only JSON job API. No user-supplied commands, paths or scripts."""
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from adapter.png import ROOT
from .jobs import ARTIFACTS, JobStore, execute, BrowserLock

def server(store,port=5190,enabled=False):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def reply(self,code,value):
            data=json.dumps(value,allow_nan=False).encode(); self.send_response(code)
            self.send_header('Content-Type','application/json'); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
        def dispatch(self,write=False):
            try:
                # Defeat DNS rebinding and cross-origin POSTs (dev requests arrive through Vite proxy).
                host=self.headers.get('Host','')
                if host!=f'127.0.0.1:{self.server.server_port}': return self.reply(403,{'error':'Loopback host required'})
                origin=self.headers.get('Origin')
                if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}','http://127.0.0.1:5180','http://127.0.0.1:5181'): return self.reply(403,{'error':'Same-origin local request required'})
                route=urlsplit(self.path).path.split('/')
                if route[:3]!=['','api','jobs']: return self.reply(404,{'error':'Unknown endpoint'})
                if write:
                    if self.headers.get('X-Reforge-Request')!='1' or self.headers.get('Content-Type')!='application/json': return self.reply(403,{'error':'Explicit JSON action required'})
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=1000: return self.reply(400,{'error':'Invalid request size'})
                    body=json.loads(self.rfile.read(size))
                    if len(route)==3:
                        if not enabled: return self.reply(409,{'error':'Pilot disabled. Start service with --enable-pilot after explicit authorization.'})
                        if not isinstance(body,dict) or set(body)!={'request'}: raise ValueError('Only feature request accepted')
                        job=store.create(body['request']); threading.Thread(target=execute,args=(store,job['id']),daemon=True).start(); return self.reply(201,job)
                    if len(route)==5 and route[4]=='cancel' and body=={}: return self.reply(200,store.cancel(route[3]))
                    raise ValueError('Unknown action')
                if len(route)==3: return self.reply(200,{'jobs':store.list(),'pilot_enabled':enabled})
                if len(route)==4: return self.reply(200,store.get(route[3]))
                if len(route)==5 and route[4]=='live':
                    from .live import snapshot
                    return self.reply(200,snapshot(store.get(route[3])))
                if len(route)==6 and route[4]=='evidence' and route[5] in ARTIFACTS:
                    job=store.get(route[3]); url='/api/jobs/'+route[3]+'/evidence/'+route[5]
                    if not any(e['url']==url for e in job['evidence']): return self.reply(404,{'error':'Evidence not yet available'})
                    return self.reply(200,json.loads((store.directory/route[3]/route[5]).read_text()))
                return self.reply(404,{'error':'Unknown endpoint'})
            except RuntimeError as e: return self.reply(409,{'error':str(e)})
            except (ValueError,KeyError,FileNotFoundError) as e: return self.reply(400,{'error':'Invalid or missing job/request'})
        def do_GET(self): self.dispatch()
        def do_POST(self): self.dispatch(True)
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--port',type=int,default=5190); p.add_argument('--enable-pilot',action='store_true'); a=p.parse_args()
    if not 1024<=a.port<=65535: raise ValueError('Invalid local port')
    with BrowserLock('feature-service'):
        store=JobStore(ROOT/'evidence/feature-jobs',recover=True); s=server(store,a.port,a.enable_pilot)
        print(f'Feature API http://127.0.0.1:{a.port}; pilot enabled: {a.enable_pilot}',flush=True)
        try: s.serve_forever()
        finally:
            if store.active: store.cancel(store.active)
            s.server_close()

if __name__=='__main__': main()
