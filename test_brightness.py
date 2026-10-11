import unittest,tempfile,json
from pathlib import Path
from learning.brightness import BrightnessBroker,validate_plan,render,DEFINITIONS
from learning.operations import BRIGHTNESS,operation_spec
from learning.core import validate_claims
from evaluator.compare import load_policy
class BrightnessTests(unittest.TestCase):
 def test_operation_schema(self):
  self.assertEqual(BRIGHTNESS['parameter'],{'name':'Brightness','key':'brightness','min':-100,'max':100,'default':0,'step':1})
  self.assertTrue(all(v==0 for v in BRIGHTNESS['frozen_controls'].values()))
  with self.assertRaises(ValueError): operation_spec('../reference')
 def test_negative_plans_and_boundaries(self):
  p={'question':'q','hypotheses':['h1','h2'],'input':{'kind':'gray_ramp','width':33,'height':9},'brightness':-100,'predictions':['p1','p2'],'usefulness':'u'}
  validate_plan(p)
  for v in [-101,101,1.5,True]:
   with self.assertRaises(ValueError): validate_plan({**p,'brightness':v})
 def test_broker_cannot_read_evaluator_or_write_existing_operation(self):
  with tempfile.TemporaryDirectory() as d:
   b=BrightnessBroker(root=Path(d))
   for name in ['../evaluator/compare.py','src/gaussian-blur.ts','layout-packet/observation.md','src/brightness.ts:stream','C:/reference.js']:
    with self.assertRaises(ValueError): b.path(name)
   for name in ['src/current-image.ts','src/style.css','package.json']:
    with self.assertRaises(ValueError): b.path(name,True)
   self.assertEqual(b.path('src/brightness.ts',True),Path(d)/'src/brightness.ts')
 def test_coverage_and_exact_policy(self):
  for kind in DEFINITIONS:
   im=render({'kind':kind,'width':35,'height':9}); self.assertEqual(im.size,(35,9))
  alpha=render({'kind':'alpha_shapes','width':35,'height':9}).getchannel('A')
  self.assertEqual(set(alpha.get_flattened_data()),{17,128,255})
  p=load_policy(); self.assertEqual(p['rgb_mean_max'],0); self.assertEqual(p['alpha_max'],0)
 def test_claim_brightness_domain_and_evidence(self):
  c={'id':'b','statement':'Observed test','status':'OBSERVED','target_version':'4.14.3','setup':'single layer','parameter_domain':{'min':-100,'max':100},'scope':'cases','supporting_evidence':['e'],'contradicting_evidence':[],'alternatives':[],'unresolved':[],'verification_cases':[]}
  validate_claims([c],['e'],['e'],domain=(-100,100))
  with self.assertRaises(ValueError): validate_claims([c],[],[],domain=(-100,100))
class HostCorrectionTests(unittest.TestCase):
 def test_frozen_suite_uses_valid_full_region(self):
  from learning.brightness import BrightnessHarness
  from learning.core import digest
  from learning.diagnostics import describe
  from evaluator.compare import evaluate
  with tempfile.TemporaryDirectory() as temp:
   d=Path(temp); path=d/'input.png'; render({'kind':'patches','width':3,'height':5}).save(path)
   h=object.__new__(BrightnessHarness); h.events=[]; h.directory=d/'run'; h.emit=lambda *a,**kw:None
   h.evidence=[{'id':'neutral','selected_by':'test','input':str(path),'expected':str(path),'input_sha256':digest(path),'expected_sha256':digest(path),'brightness':0,'target':{'visible_about_version':'4.14.3'},'input_samples':describe(path),'export_samples':describe(path)}]
   h.freeze(); row=h.suite['cases'][0]
   self.assertEqual(row['regions'],{'full':[0,0,3,5]})
   self.assertEqual(evaluate('neutral',path,path,d/'evaluation',h.suite['policy'],row['regions'])['status'],'passed')
   self.assertEqual(h.compact()[0]['target']['visible_about_version'],'4.14.3')
 def test_brightness_baseline_flag_preserves_blur_default(self):
  from learning.run import Harness
  from learning.core import save
  with tempfile.TemporaryDirectory() as temp:
   h=object.__new__(Harness); h.directory=Path(temp); h.config={'command_seconds':30}; h.dev_app=False; h.operation='brightness'; h.emit=lambda *a,**kw:None
   calls=[]
   def process(args,d,*rest):
    calls.append(args); save(d/'baseline/results.json',{'status':'passed','classification':'match'})
   h.process=process
   self.assertTrue(h.baseline('brightness',False,allow_brightness=True))
   self.assertIn('--allow-brightness',calls[-1]); self.assertNotIn('--allow-blur',calls[-1])
   h.operation='gaussian-blur'; self.assertTrue(h.baseline('blur',True))
   self.assertIn('--allow-blur',calls[-1]); self.assertNotIn('--allow-brightness',calls[-1])
if __name__=='__main__': unittest.main()
