"""Reference-free isolated repair gates; no provider calls."""
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from features.repair import check_patch, gate, classify, RepairBudget, repair
from features.discovery import output_schema

class RepairTests(unittest.TestCase):
    def test_schema_reproducer_fails_broken_and_passes_current(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); case={'kind':'schema'}
            broken={'diagnosis':'Aliased schema','functions':[{'name':'output_schema','source':"def output_schema(request):\n    schema=copy.deepcopy(SCHEMA)\n    schema['properties']['request']['const']=request\n    schema['properties']['parameter']['enum']=['Contrast','Contrast:']\n    return schema\n"}]}
            self.assertFalse(gate(case,root/'broken',broken))
            good={'diagnosis':'Independent fields','functions':[{'name':'output_schema','source':inspect.getsource(output_schema)}]}
            self.assertTrue(gate(case,root/'fixed',good))
    def test_forbidden_repairs_never_execute(self):
        for source in ['def output_schema(request):\n import os\n return {}',
                       'def output_schema(request):\n return open(request).read()',
                       'def output_schema(request):\n SCHEMA.clear()\n return {}',
                       'def output_schema(request):\n return copy.__dict__',
                       'def output_schema(request):\n SCHEMA["x"]=1\n return {}']:
            with self.subTest(source=source), self.assertRaises(ValueError):
                check_patch({'diagnosis':'test','functions':[{'name':'output_schema','source':source}]})
        with self.assertRaises(ValueError): check_patch({'diagnosis':'test','functions':[{'name':'evaluate','source':'def evaluate(): return True'}]})
    def test_two_repeats_and_five_repairs_limit(self):
        budget=RepairBudget(); case={'kind':'schema','error':'same'}
        self.assertTrue(budget.admit(case)); self.assertTrue(budget.admit(case)); self.assertFalse(budget.admit(case))
        budget=RepairBudget()
        for i in range(5): self.assertTrue(budget.admit({'kind':'schema','error':str(i)}))
        self.assertFalse(budget.admit({'kind':'schema','error':'six'}))
        budget.started-=301; self.assertFalse(budget.admit({'kind':'row'}))
    def test_classification_does_not_repair_behavior_or_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'discovery-record.json').write_text(json.dumps({'error':{'message':'unknown'}}))
            self.assertIsNone(classify(p,{'status':'unresolved'}))
            self.assertIsNone(classify(p,{'status':'failed'}))
            (p/'invocation.json').write_text(json.dumps({'turn_failure':{'message':'invalid_json_schema'}}))
            self.assertEqual(classify(p,{'status':'failed'})['kind'],'schema')
    def test_recall_requires_matching_hashes_and_fresh_gate(self):
        from features.repair import remember, recall
        with tempfile.TemporaryDirectory() as d, patch('features.repair.ROOT',Path(d)):
            root=Path(d); artifact=root/'evidence/learning/repair/validated-patch.json'; artifact.parent.mkdir(parents=True)
            artifact.write_text(json.dumps({'diagnosis':'fixed','functions':[{'name':'output_schema','source':inspect.getsource(output_schema)}]}))
            with patch('features.repair.host_hashes',return_value={'host':'a'}):
                remember(artifact,{'kind':'schema'})
                with patch('features.repair.gate',return_value=False): self.assertIsNone(recall(root/'evidence/learning/new',lambda *a,**k:None))
                with patch('features.repair.gate',return_value=True): self.assertIsNotNone(recall(root/'evidence/learning/new',lambda *a,**k:None))
            with patch('features.repair.host_hashes',return_value={'host':'b'}), patch('features.repair.gate') as gate_mock:
                self.assertIsNone(recall(root/'evidence/learning/new',lambda *a,**k:None)); gate_mock.assert_not_called()

    def test_no_model_call_without_reproducer_failure(self):
        with tempfile.TemporaryDirectory() as d, patch('features.repair.gate',return_value=True), patch('features.repair.model.invoke') as invoke:
            self.assertIsNone(repair({'kind':'schema'},Path(d),lambda *a,**k:None,100))
            invoke.assert_not_called()
    def test_failed_regression_rejects_patch(self):
        good={'diagnosis':'Independent fields','functions':[{'name':'output_schema','source':inspect.getsource(output_schema)}]}
        with tempfile.TemporaryDirectory() as d, patch('features.repair.gate',side_effect=[False,False]), patch('features.repair.model.invoke',return_value=good):
            self.assertIsNone(repair({'kind':'schema'},Path(d),lambda *a,**k:None,100))
            self.assertFalse((Path(d)/'validated-patch.json').exists())
    def test_validated_patch_retained_without_modifying_repository(self):
        good={'diagnosis':'Independent fields','functions':[{'name':'output_schema','source':inspect.getsource(output_schema)}]}
        before=inspect.getsource(output_schema)
        with tempfile.TemporaryDirectory() as d, patch('features.repair.gate',side_effect=[False,True]), patch('features.repair.model.invoke',return_value=good):
            result=repair({'kind':'schema'},Path(d),lambda *a,**k:None,100)
            self.assertEqual(json.loads(result.read_text()),good)
        self.assertEqual(inspect.getsource(output_schema),before)
