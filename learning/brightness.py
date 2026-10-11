"""Brightness specialization of the existing bounded learning harness; no operation implementation."""
import copy,json,time
from pathlib import Path
from PIL import Image
from adapter.png import ROOT,png_info,compare_pngs
from build_shell import FileBroker,APP
from evaluator.compare import load_policy
from .run import Harness,SCOPE
from .core import save,digest,exact,integer,strings,text,validate_claims,decide,Checkpoints
from .diagnostics import describe
from .operations import BRIGHTNESS
from . import model,packets

DEFINITIONS={
 'gray_ramp':'RGBA(round(255*x/(w-1))) in RGB; alpha255; repeated rows.',
 'channel_ramps':'Each third of rows is an individual R/G/B ramp round(255*x/(w-1)); other channels0; alpha255.',
 'patches':'Columns cycle RGB grayscale levels [0,1,2,15,16,31,63,64,127,128,129,191,223,239,253,254,255]; alpha255.',
 'alpha_shapes':'Alternating green/magenta saturated columns, alpha rows cycling [255,128,17]; import-exact colors.',
}

def render(spec):
 w,h=spec['width'],spec['height']; im=Image.new('RGBA',(w,h)); data=[]
 for y in range(h):
  for x in range(w):
   v=round(255*x/(w-1)); kind=spec['kind']
   if kind=='gray_ramp': px=(v,v,v,255)
   elif kind=='channel_ramps':
    c=min(2,y*3//h); px=tuple(v if i==c else 0 for i in range(3))+(255,)
   elif kind=='patches':
    v=[0,1,2,15,16,31,63,64,127,128,129,191,223,239,253,254,255][x%17]; px=(v,v,v,255)
   elif kind=='alpha_shapes': px=((255,0,255) if x%2 else (0,255,0))+([255,128,17][y%3],)
   else: raise ValueError('Unknown brightness generator')
   data.append(px)
 im.putdata(data); return im

def validate_plan(p):
 exact(p,['question','hypotheses','input','brightness','predictions','usefulness'])
 for k in ['question','usefulness']: text(p[k])
 strings(p['hypotheses'],2,5); strings(p['predictions'],2,5)
 exact(p['input'],['kind','width','height'])
 if p['input']['kind'] not in DEFINITIONS: raise ValueError('Unknown generator')
 for k in ['width','height']: integer(p['input'][k],3,257)
 integer(p['brightness'],-100,100); return p

PLAN=model.obj({'question':model.S,'hypotheses':model.arr(model.S),'input':model.obj({'kind':{'type':'string','enum':list(DEFINITIONS)},'width':model.I,'height':model.I}),'brightness':model.I,'predictions':model.arr(model.S),'usefulness':model.S})
PLANS=model.obj({'plans':model.arr(PLAN)})

class BrightnessBroker(FileBroker):
 writable={'src/main.tsx','src/brightness.ts','README.md'}
 def __init__(self,journal=None,root=APP,reader=None,allowed_writes=None):
  super().__init__(root); self.journal=journal; self.reader=reader
  self.writable=set(allowed_writes) if allowed_writes is not None else set(type(self).writable)
  if not self.writable<=type(self).writable: raise ValueError('Invalid brightness writes')
  self.files=self.writable|{'src/current-image.ts','src/style.css'}
 def path(self,name,write=False):
  if name.startswith('layout-packet/') or write and name not in self.writable: raise ValueError('Only declared brightness app source')
  return super().path(name,write)
 def call(self,tool,args):
  if tool=='evidence_read':
   if self.reader is None: raise ValueError('Evidence reader absent')
   r=self.reader.call(args); self.audit.append({'tool':tool,'arguments':args}); return r
  r=super().call(tool,args)
  if tool=='shell_write_file' and self.journal:
   self.journal.mkdir(parents=True,exist_ok=True); p=self.journal/(str(len(self.audit)).zfill(2)+'-'+args['path'].replace('/','_')); p.write_bytes(self.path(args['path']).read_bytes()); self.audit[-1]['written_source_artifact']=str(p)
  return r

class BrightnessHarness(Harness):
 operation='brightness'; source_scope=SCOPE|{'src/brightness.ts'}
 def __init__(self,config):
  super().__init__(config)
  self.provenance.update(operation=BRIGHTNESS,brightness_absent_at_start=not (self.app/'src/brightness.ts').exists(),preparation=str(ROOT/'evidence/learning/brightness-preparation'),blur_status='experimental, preserved in isolated workspace; not accepted')
  # Frozen preparation and the experimental blur sources are outside builder access.
  for base in [ROOT/'evidence/learning/brightness-preparation',ROOT/'dev-workspaces/astra-precision-1/src']:
   for p in base.rglob('*'):
    if p.is_file(): self.protected[str(p)]=digest(p)
  save(self.directory/'protected-manifest.json',self.protected); save(self.directory/'provenance.json',self.provenance)
 def baseline(self,label,allow_blur,cleanup=False):
  return super().baseline(label,allow_blur,cleanup,allow_brightness=(self.app/'src/brightness.ts').is_file())
 def compact(self):
  return [{'id':e['id'],'selected_by':e['selected_by'],'target':e['target'],'brightness':e['brightness'],'input_spec':e.get('input_spec'),'input':packets.compact_summary(e['input_samples']),'export':('exactly equals input' if e['brightness']==0 and compare_pngs(e['input'],e['expected'])['rgba_equal'] else packets.compact_summary(e['export_samples']))} for e in self.evidence]
 def admit(self,ident,path,report,selected_by,input_spec=None):
  if report['status']!='observed' or not report['original_confirmation']['rgba_equal']: raise ValueError('No operation evidence from failed import')
  e={'id':ident,'selected_by':selected_by,'input_spec':input_spec,'input':str(path),'expected':report['output_path'],'input_sha256':digest(path),'expected_sha256':digest(report['output_path']),'brightness':report['accepted_brightness'],'target':report['target'],'input_samples':describe(path),'export_samples':describe(report['output_path'])}
  self.evidence.append(e); save(self.directory/'evidence'/(ident+'.json'),e)
 def prepared(self):
  p=ROOT/'evidence/learning/brightness-preparation'
  for ident in ['neutral-1','nonneutral-1']:
   r=json.loads((p/'experiments'/ident/'reference-record.json').read_text()); self.admit('scope-'+ident,p/'inputs/opaque.png',r,'developer scope validation')
 def validate_plans(self,answer):
  exact(answer,['plans']); plans=answer['plans']
  if not isinstance(plans,list) or not 1<=len(plans)<=4: raise ValueError('Require 1..4 plans')
  for p in plans: validate_plan(p)
  sigs=[json.dumps([p['input'],p['brightness']],sort_keys=True) for p in plans]
  if len(set(sigs))!=len(sigs): raise ValueError('Duplicate fresh plan')
  if len(plans)>self.budget.snapshot()['fresh_experiments_remaining']: raise ValueError('Too many experiments')
  return plans
 def experiment(self,p):
  self.budget.spend('experiment'); ident='brightness-fresh-'+str(self.budget.experiments).zfill(2); d=self.directory/'experiments'/ident
  path=self.directory/'inputs'/(ident+'.png'); path.parent.mkdir(exist_ok=True)
  save(d/'preregistered.json',{'selected_by':'runtime','plan':p,'before_execution':True}); render(p['input']).save(path)
  self.emit('experiment',id=ident,plan=p)
  r=self.worker('brightness-reference',{'id':ident,'brightness':p['brightness'],'input_path':str(path),'input_sha256':digest(path),'window_position':self.config['window_position']},d,self.config['reference_seconds'])
  self.admit(ident,path,r,'runtime',p['input']); self.emit('evidence',id=ident,status='OBSERVED',accepted=r['accepted_brightness'])
 def freeze(self):
  version=1+sum(e['event']=='suite_frozen' for e in self.events)
  self.suite={'id':'visible-brightness-v'+str(version),'cases':[{**{k:e[k] for k in ['id','input','expected','input_sha256','expected_sha256','brightness']},'regions':{'full':[0,0,e['input_samples']['png']['width'],e['input_samples']['png']['height']]}} for e in self.evidence],'policy':load_policy(),'operation':BRIGHTNESS,'neutral_identity_required':True,'rgb_and_alpha_scored_separately':True,'tie_policy':'retain incumbent'}
  path=self.directory/'suites'/(self.suite['id']+'.json'); save(path,self.suite); self.suite_hash=digest(path); self.emit('suite_frozen',id=self.suite['id'],sha256=self.suite_hash)
 def update_contract(self,label):
  schema=copy.deepcopy(model.CONTRACT)
  for k in ['supporting_evidence','contradicting_evidence','verification_cases']: schema['properties']['claims']['items']['properties'][k]['items']={'type':'string','enum':[e['id'] for e in self.evidence]}
  prompt='Update a concise evidence-backed brightness contract. OBSERVED claims require exact evidence IDs. No VERIFIED status before trusted acceptance. Do not infer hidden mechanism. All other Color Corrections controls frozen zero. '+json.dumps({'operation':BRIGHTNESS,'evidence':self.compact(),'previous_claims':self.claims},separators=(',',':'))
  answer=self.ask(prompt,label,schema,role='contract'); exact(answer,['claims','decision']); text(answer['decision']); self.claims=validate_claims(answer['claims'],[e['id'] for e in self.evidence],[e['id'] for e in self.evidence],domain=(-100,100)); save(self.directory/'contracts'/(label+'.json'),answer); self.emit('claim_update',decision=answer['decision'])
 def evaluate(self,label,cleanup=False):
  d=self.directory/'evaluations'/label
  r=self.worker('candidate',{'operation':'brightness','app':str(self.app),'suite':self.suite,'suite_sha256':self.suite_hash},d,self.config['command_seconds'],cleanup)
  r['baseline_pass']=self.baseline(label+'-gates',False,cleanup); r['suite_sha256']=self.suite_hash
  save(d/'evaluation.json',r); self.emit('evaluation',label=label,result=r); return r
 def builder(self,index,previous):
  sources={n:(self.app/n).read_text(encoding='utf-8') for n in ['src/main.tsx','src/current-image.ts']}
  packet={'operation':BRIGHTNESS,'claims':self.claims,'evidence':self.compact(),'policy':self.suite['policy'],'previous':previous,'implementation_present':(self.app/'src/brightness.ts').exists()}
  prompt=('Generate an independent brightness implementation from permitted observations; never access reference internals. Read src/main.tsx and src/current-image.ts. Write src/brightness.ts exporting applyBrightness(raster: Raster, brightness: number): Raster. Reject unsupported depth16 without damaging existing upload/export. Preserve neutral exact identity, source immutability, dimensions and alpha as evidence requires. Wire Image -> Color Corrections… with Brightness slider -100..100 step1 default0 and Apply/Close. Explicitly show all other dialog controls frozen0. Keep original layout/CSS and Gaussian Blur placeholder unchanged. Disable Apply and Brightness with no image. Update currentImage.raster and preview from current pixels; keep accessible image name Original image preview: filename. No other feature, dependencies/config edits, evaluator access or execution. Permitted writes src/main.tsx, src/brightness.ts, README.md only. Use shell_write_file for complete sources. Do not fit special cases to dimensions. Bounded tools, evidence_read optionally retrieves exact visible profiles. '+json.dumps(packet,separators=(',',':')))
  reader=packets.EvidenceReader({e['id']:{'input':e['input'],'export':e['expected']} for e in self.evidence},self.config['evidence_reads'])
  self.ask(prompt,'builder-'+str(index),None,True,role='repair' if previous else 'builder',supplied=sources,reader=reader)
 def finish(self,final,final_baseline):
  usage=[]
  for p in sorted((self.directory/'model').rglob('invocation.json')):
   r=json.loads(p.read_text()); usage.append({'invocation':str(p.relative_to(self.directory)),'elapsed_seconds':r['elapsed_seconds'],'usage':r.get('usage'),'model':r['model'],'effort':r['effort']})
  accepted=bool(self.first_acceptance and final_baseline and final.get('status')=='passed')
  self.report={'status':'accepted' if accepted else 'unresolved','operation':BRIGHTNESS,'provenance':self.provenance,'stop_reason':self.stop,'elapsed_seconds':round(time.monotonic()-self.budget.start,3),'fresh_reference_attempts':self.budget.experiments,'preparation_reference_operations':4,'candidate_attempts':self.attempts,'first_acceptance':self.first_acceptance,'suite_sha256':getattr(self,'suite_hash',None),'best_checkpoint':str(self.best),'final_build':final,'final_baseline_pass':final_baseline,'budget':self.budget.snapshot(),'model_usage':usage,'packet_sizes':self.packet_sizes,'guidance_selections':self.guidance_selections,'blur_status':'experimental 5/10 original, 7/14 expanded; isolated sources hash-preserved; no blur integration or promotion'}
  save(self.directory/'report.json',self.report); save(ROOT/'evidence/latest-brightness.json',{'status':self.report['status'],'report':str(self.directory/'report.json')})
  lines=['# Brightness autonomous attempt','',f"Status: {self.report['status']}; stop: {self.stop}; {self.report['elapsed_seconds']} seconds.",f"{self.budget.experiments} runtime-selected experiments; {len(self.attempts)} candidates. Preparation: 4 scope/repeat operations plus 1 import-only probe.",f"Final build {final.get('status')}; four exact baselines {final_baseline}.",f"Frozen suite: {getattr(self,'suite_hash',None)}",f"Restored checkpoint: {self.best}",'','No source/bundle/hidden-state/network-body reads. Brightness absent at start; implementation generated by the restricted runtime.','Experimental blur remains isolated and unchanged; compatibility remains rejected.','']
  for a in self.attempts:
   r=a.get('evaluation',{}); lines.append(f"{a['id']}: {a['status']}; "+str(sum(c['status']=='passed' for c in r.get('cases',[])))+'/'+str(len(r.get('cases',[])))+' exact visible cases.'); lines += [c['case_id']+': '+c['status']+' '+json.dumps(c.get('metrics')) for c in r.get('cases',[])]
  lines+=['','## Model usage',json.dumps(usage,indent=2)]
  (self.directory/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8'); self.emit('stop',reason=self.stop,status=self.report['status'],report=str(self.directory/'report.md'))
 def run(self):
  try:
   if (self.app/'src/brightness.ts').exists() or 'applyBrightness' in (self.app/'src/main.tsx').read_text(encoding='utf-8'): raise ValueError('Brightness must genuinely be absent at start')
   if self.worker('build',{'app':str(self.app)},self.directory/'initial-build',self.config['command_seconds']).get('status')!='passed' or not self.baseline('initial',False): raise ValueError('Initial baseline failed')
   if self.worker('selfcheck',{},self.directory/'evaluator-selfcheck',self.config['command_seconds']).get('status')!='passed': raise ValueError('Evaluator suspect')
   self.prepared(); g=self.guidance_section('planner',{'planning'},'planner')
   prompt='Select 1..4 fresh brightness experiments. Parameters integer -100..100, dimensions3..257. Competing hypotheses and concise numerical predictions BEFORE execution. Existing scope observations are supplied; do not merely replay them. Cover individual channels, clipping and partial-alpha where useful, and at least one negative value. All non-brightness controls frozen0. '+json.dumps({'operation':BRIGHTNESS,'generators':DEFINITIONS,'budget':self.budget.snapshot(),'global_strategy_not_target_evidence':g,'scope_observations':self.compact()},separators=(',',':'))
   answer=self.ask(prompt,'planner',PLANS,role='planner')
   for p in self.validate_plans(answer): self.experiment(p)
   self.freeze(); self.update_contract('contract-1')
   previous=None
   for index in range(1,self.config['candidates']+1):
    self.budget.spend('candidate'); label='candidate-'+str(index); record={'id':label,'status':'failed'}; self.attempts.append(record)
    try:
     self.builder(index,previous); cp=self.checkpoints.snapshot(label); r=self.evaluate(label); self.guard(); accepted,reason=decide(r)
     record.update(status='accepted' if accepted else 'rejected',reason=reason,evaluation=r,checkpoint=str(cp)); save(self.directory/'candidates'/(label+'.json'),record)
     if accepted:
      self.best=self.accepted=cp; self.first_acceptance={'candidate_id':label,'suite_sha256':self.suite_hash,'elapsed_seconds':round(time.monotonic()-self.budget.start,3)}
      self.claims.append({'id':'independent-visible-parity','statement':'Independent brightness passes every exact visible RGB/alpha and baseline gate on this frozen suite.','status':'VERIFIED_WITHIN_SCOPE','target_version':'4.14.3 hosted unpinned','setup':BRIGHTNESS['scope'],'parameter_domain':{'min':min(e['brightness'] for e in self.evidence),'max':max(e['brightness'] for e in self.evidence)},'scope':self.suite['id']+' discrete cases only','supporting_evidence':[e['id'] for e in self.evidence],'contradicting_evidence':[],'alternatives':['Hidden mechanisms may agree on these observations'],'unresolved':['Fresh evaluation and untested inputs/parameters'],'verification_cases':[e['id'] for e in self.evidence]})
      save(self.directory/'contracts/accepted.json',{'claims':self.claims,'verification':self.first_acceptance}); self.stop='first_acceptance_all_visible_gates_pass'; break
     if r.get('evaluator_suspect'):
      self.checkpoints.restore(self.best); self.stop='evaluator_defect'; break
     previous={'failure_class':reason,'discrepancies':packets.discrepancy_section(r,self.evidence,self.directory/'evaluations'/label,parameter_key='brightness'),'rejected_source':(cp/'src/brightness.ts').read_text(encoding='utf-8') if (cp/'src/brightness.ts').exists() else None}
     self.checkpoints.restore(self.best)
     if index==self.config['candidates']: self.stop='candidate_budget_exhausted'; break
     # Bounded routing chooses only repair/stop: all four fresh experiment slots already allocated.
     schema=model.obj({'classification':{'type':'string','enum':model.ROUTES},'evidence_ids':model.arr({'type':'string','enum':[e['id'] for e in self.evidence]}),'explanation':model.S,'next_action':{'type':'string','enum':['repair','stop']}})
     route=self.ask('Classify failures and choose repair or stop; no further experiments or tolerance changes. '+json.dumps({'failure':previous,'guidance':self.guidance_section('route',{'any_failure','behavior_mismatch'},'route-'+str(index))}),'route-'+str(index),schema,role='route')
     if not set(route['evidence_ids'])<={e['id'] for e in self.evidence}: raise ValueError('Unknown route evidence')
     previous['routing']=route
     if route['next_action']=='stop': self.stop=route['classification']; break
    except Exception as e:
     if not (self.directory/'checkpoints'/label).exists(): self.checkpoints.snapshot(label+'-partial')
     record['error']={'type':type(e).__name__,'message':str(e)[:2000]}; save(self.directory/'candidates'/(label+'.json'),record); raise
  except Exception as e: self.fail(e)
  finally: self.cleanup()

def main():
 import argparse
 parser=argparse.ArgumentParser(); parser.add_argument('--config',type=Path,default=ROOT/'brightness.config.json'); args=parser.parse_args()
 config=json.loads(args.config.read_text(encoding='utf-8-sig'))
 if config['fresh_experiments']>4 or config['candidates']>2: raise ValueError('Brightness cap: 4 run experiments (8 including prep), 2 candidates')
 h=BrightnessHarness(config); h.run(); return 0 if h.report['status']=='accepted' else 1
if __name__=='__main__': raise SystemExit(main())
