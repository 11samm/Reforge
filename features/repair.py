"""Restricted host-function patches, isolated replay gates and bounded live retry."""
import ast
import copy
import hashlib
import inspect
import json
import subprocess
import sys
import time
from pathlib import Path
from learning.core import save
from learning import model
from adapter.png import ROOT, within

FUNCTIONS={'output_schema':('features.discovery', {'copy.deepcopy'}),
           'resolve':('features.browser', {'locator','re.compile','re.escape','root.get_by_role','root.get_by_label','found.count','found.nth','is_visible','get_by_role'})}
SAFE={'len','range','str','float','int','list','dict','set','enumerate','ValueError'}
METHODS={'get_by_role','get_by_label','count','nth','is_visible','rstrip','removesuffix','deepcopy','compile','escape'}
SCHEMA=model.obj({'diagnosis':model.S,'functions':model.arr(model.obj({'name':model.S,'source':model.S}))})

def check_patch(value):
    if not isinstance(value,dict) or set(value)!={'diagnosis','functions'} or not isinstance(value['diagnosis'],str) or len(value['diagnosis'])>1500: raise ValueError('Invalid repair record')
    if not isinstance(value['functions'],list) or not 1<=len(value['functions'])<=2: raise ValueError('Repair function limit')
    names=set()
    for row in value['functions']:
        if set(row)!={'name','source'} or row['name'] not in FUNCTIONS or row['name'] in names or not isinstance(row['source'],str) or len(row['source'])>6000: raise ValueError('Repair outside allowlist')
        names.add(row['name']); tree=ast.parse(row['source'])
        if len(tree.body)!=1 or not isinstance(tree.body[0],ast.FunctionDef) or tree.body[0].name!=row['name']: raise ValueError('Only the declared function may change')
        fn=tree.body[0]
        expected=['request'] if row['name']=='output_schema' else ['root','strategy']
        if [a.arg for a in fn.args.args]!=expected or fn.decorator_list or fn.args.defaults or fn.args.kwonlyargs or fn.args.vararg or fn.args.kwarg or fn.returns or any(a.annotation for a in fn.args.args): raise ValueError('Function interface changed')
        for node in ast.walk(tree):
            if isinstance(node,(ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal,ast.While,ast.With,ast.Try,ast.ClassDef,ast.Lambda,ast.AsyncFunctionDef,ast.Delete,ast.Await,ast.Yield)): raise ValueError('Forbidden repair syntax')
            if isinstance(node,ast.FunctionDef) and node is not fn: raise ValueError('Nested function denied')
            if isinstance(node,ast.Attribute) and (node.attr.startswith('_') or node.attr not in METHODS): raise ValueError('Forbidden repair attribute')
            if isinstance(node,ast.Name) and (node.id.startswith('__') or node.id in {'open','exec','eval','compile','getattr','setattr','globals','locals','__import__'}): raise ValueError('Forbidden repair name')
            if isinstance(node,ast.Call):
                if isinstance(node.func,ast.Name) and node.func.id not in SAFE|{'locator'}: raise ValueError('Forbidden repair call')
                if not isinstance(node.func,(ast.Name,ast.Attribute)): raise ValueError('Indirect repair call denied')
            if isinstance(node,(ast.Assign,ast.AugAssign,ast.AnnAssign)):
                targets=node.targets if isinstance(node,ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target,ast.Attribute): raise ValueError('Global attribute mutation denied')
                    base=target
                    while isinstance(base,ast.Subscript): base=base.value
                    if isinstance(base,ast.Name) and base.id in {'SCHEMA','root','strategy','copy','re','locator'}: raise ValueError('Protected input mutation denied')
    return value

def install(value):
    check_patch(value)
    import importlib
    for row in value['functions']:
        module=importlib.import_module(FUNCTIONS[row['name']][0])
        # AST restrictions remove execution/file/network/reflection capabilities.
        namespace={k:module.__dict__[k] for k in ('copy','SCHEMA','locator','re') if k in module.__dict__}
        namespace['__builtins__']={k:__builtins__[k] for k in SAFE} if isinstance(__builtins__,dict) else {k:getattr(__builtins__,k) for k in SAFE}
        exec(compile(row['source'],'<isolated-harness-patch>','exec'),namespace)
        setattr(module,row['name'],namespace[row['name']])

def install_file(path):
    path=within(path,ROOT/'evidence/learning')
    if path.name!='validated-patch.json' or path.stat().st_size>16000: raise ValueError('Invalid patch artifact')
    install(json.loads(path.read_text(encoding='utf-8')))

def classify(directory,result):
    if result.get('status')=='unresolved': return None
    record=directory/'discovery-record.json'
    if not record.is_file(): return None
    data=json.loads(record.read_text(encoding='utf-8'))
    # Only faults with an independent, reference-free reproducer are repairable.
    for invocation in directory.rglob('invocation.json'):
        report=json.loads(invocation.read_text(encoding='utf-8'))
        message=(report.get('turn_failure') or {}).get('message') or ''
        if 'invalid_json_schema' in message:
            return {'kind':'schema','error':message[:1500]}
    for row in data.get('audit',[]):
        if row.get('status')!='failed' or not row.get('error',{}).get('message','').startswith('Ambiguous or missing visible control:'): continue
        args=row.get('arguments',{}); strategy=args.get('locator',{})
        if strategy.get('by')!='row' or strategy.get('role') not in {'slider','spinbutton'}: continue
        name=strategy.get('name','').rstrip().removesuffix(':').rstrip()
        for obs in directory.glob('observation-*.json'):
            visible=json.loads(obs.read_text(encoding='utf-8'))
            rows=[c for c in visible.get('controls',[]) if c.get('dialog')==args.get('dialog') and (c.get('row') or '').startswith(name+':') and c.get('type') in {'range','number'}]
            if len(rows)==1:
                return {'kind':'row','strategy':strategy,'label':name,'type':rows[0]['type'],'error':row['error']['message']}
    return None

def gate(case,directory,patch=None,regressions=False,timeout=35):
    directory.mkdir(parents=True,exist_ok=True); request=directory/'gate-request.json'
    save(request,{'case':case,'patch':patch,'regressions':regressions})
    try:
        proc=subprocess.run([sys.executable,'-m','features.repair_checks',str(request)],cwd=ROOT,capture_output=True,text=True,timeout=timeout)
        result={'passed':proc.returncode==0,'output':(proc.stdout+proc.stderr)[-12000:]}
    except subprocess.TimeoutExpired: result={'passed':False,'output':'Gate timeout'}
    save(directory/'gate-result.json',result); return result['passed']

def repair(case,directory,emit,remaining,prior=None):
    if remaining<45: return None
    # A failure must reproduce before the model is invoked.
    previous=json.loads(Path(prior).read_text(encoding='utf-8')) if prior else None
    if gate(case,directory/'before',previous,timeout=min(25,remaining)):
        save(directory/'stop.json',{'reason':'Failure does not reproduce offline'}); return None
    source={name:inspect.getsource(__import__(module,fromlist=[name]).__dict__[name]) for name,(module,_) in FUNCTIONS.items()}
    if previous:
        source.update({row['name']:row['source'] for row in previous['functions']})
    prompt='Repair only the supplied harness function definitions. No environment tools. Return a minimal patch, not an evaluator or capability change. This is procedural infrastructure, not target algorithm evidence. Existing failure and independent reproducer: '+json.dumps(case)+' Current functions: '+json.dumps(source)+'. Preserve interfaces, uniqueness checks, input validation and unrelated schema fields. No imports, hidden state, filesystem, networking, reflection or evaluation. Allowed functions output_schema and resolve only.'
    try:
        emit('activity',activity='Harness repair: offline reproducer failed; proposing isolated function patch')
        value=model.invoke(prompt,directory/'model',min(60,max(10,remaining-35)),SCHEMA,operation='discovery')
        check_patch(value)
        if previous:
            combined={row['name']:row for row in previous['functions']}
            combined.update({row['name']:row for row in value['functions']})
            value={**value,'functions':list(combined.values())}; check_patch(value)
        save(directory/'proposed-patch.json',value)
        if not gate(case,directory/'after',value,True,timeout=min(40,max(5,remaining-60))): return None
        path=directory/'validated-patch.json'; save(path,value)
        emit('activity',activity='Harness repair passed offline reproducer and regression gates; bounded discovery retry')
        return path
    except Exception as error:
        save(directory/'stop.json',{'reason':str(error)[:1500]}); return None

class RepairBudget:
    def __init__(self,seconds=300,attempts=5): self.started=time.monotonic(); self.seconds=seconds; self.attempts=attempts; self.used=0; self.repeats={}
    def admit(self,case):
        fingerprint=hashlib.sha256(json.dumps(case,sort_keys=True).encode()).hexdigest()
        self.repeats[fingerprint]=self.repeats.get(fingerprint,0)+1
        if self.repeats[fingerprint]>2 or self.used>=self.attempts or self.remaining()<45: return False
        self.used+=1; return True
    def remaining(self): return max(0,self.seconds-(time.monotonic()-self.started))

def host_hashes():
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('features/browser.py','features/discovery.py','features/repair.py','features/repair_checks.py')}

def remember(path,case):
    path=within(path,ROOT/'evidence/learning')
    save(ROOT/'evidence/feature-memory/validated-host-patch.json',
         {'schema':1,'host_hashes':host_hashes(),'patch':path.relative_to(ROOT).as_posix(),
          'patch_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'case':case,
          'scope':'offline gates and subsequent live discovery; not behavior acceptance'})

def recall(directory,emit):
    memory=ROOT/'evidence/feature-memory/validated-host-patch.json'
    if not memory.exists(): return None
    try:
        if memory.stat().st_size>8000: return None
        data=json.loads(memory.read_text(encoding='utf-8'))
        if data.get('schema')!=1 or data.get('host_hashes')!=host_hashes(): return None
        path=within(ROOT/data['patch'],ROOT/'evidence/learning')
        if path.name!='validated-patch.json' or path.stat().st_size>16000 or hashlib.sha256(path.read_bytes()).hexdigest()!=data['patch_sha256']: return None
        value=check_patch(json.loads(path.read_text(encoding='utf-8')))
        if not gate(data['case'],directory/'recall-gate',value,True): return None
        copied=directory/'recalled'/'validated-patch.json'; save(copied,value)
        emit('activity',activity='Recalled matching-host patch passed fresh offline regression gates')
        return copied
    except (ValueError,KeyError,OSError): return None
