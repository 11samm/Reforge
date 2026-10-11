"""Fresh-demo isolation and discovered Brightness dispatch; no model calls."""
import copy
import json
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from features.preparation import COMMON, prepare
from features.spec import request_id, validate
from features.discovery import output_schema
from learning.operations import operation_spec
from learning.brightness import BrightnessBroker
from features.interaction_map import InteractionMap
from test_features import specification
from features.browser import FeatureAdapter, set_numeric

def brightness_spec():
    spec = specification()
    spec.update(request='Implement Brightness', feature_id='brightness', parameter='Brightness')
    spec['controls'][0].update(label='Brightness', locator={'by':'row','role':'slider','name':'Brightness'})
    return spec

class FreshBrightnessTests(unittest.TestCase):
    def test_discovered_domain_used_without_supplied_brightness_procedure(self):
        spec = brightness_spec(); validate(spec, ready=True)
        op = operation_spec('brightness', spec)
        self.assertEqual(op['parameter']['min'], -10)
        self.assertEqual(op['parameter']['key'], 'value')
        self.assertEqual(op['export'], 'applyBrightness')
        self.assertEqual(request_id(' implement BRIGHTNESS '), 'brightness')
        with self.assertRaises(ValueError): operation_spec('contrast', spec)
        for request, feature, label in [('Implement Brightness','brightness','Brightness'),('Implement Contrast','contrast','Contrast')]:
            schema = output_schema(request)
            self.assertEqual(schema['properties']['feature_id']['const'], feature)
            self.assertEqual(schema['properties']['parameter']['enum'], [label,label+':'])

    def test_preparation_excludes_learned_sources_and_memory_preserves_canonical(self):
        templates = Path(__file__).parent/'features/templates'
        with tempfile.TemporaryDirectory() as temp, patch('features.preparation.ROOT', Path(temp)):
            root = Path(temp); app = root/'generated-app'
            for name in COMMON:
                path=app/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text('common fixture')
            for name in ('brightness.ts','contrast.ts'):
                (app/'src'/name).write_text('POISON: previous implementation')
            for feature in ('brightness','contrast'):
                target=root/'features/templates'/feature; target.mkdir(parents=True)
                (target/'main.tsx').write_bytes((templates/feature/'main.tsx').read_bytes())
            memory=root/'evidence/feature-memory/discovery.json'; memory.parent.mkdir(parents=True)
            memory.write_text('POISON: previous procedure')
            before={p:p.read_bytes() for p in app.rglob('*') if p.is_file()}
            fresh, record=prepare('Implement Brightness','a'*32)
            self.assertTrue(record['target_absent'])
            self.assertFalse((fresh/'src/brightness.ts').exists())
            self.assertFalse((fresh/'src/contrast.ts').exists())
            self.assertNotIn('applyBrightness',(fresh/'src/main.tsx').read_text())
            self.assertNotIn('POISON',''.join(p.read_text() for p in fresh.rglob('*') if p.is_file()))
            self.assertEqual(record['memory']['discovery_memory'],'job-local empty')
            self.assertEqual(before,{p:p.read_bytes() for p in app.rglob('*') if p.is_file()})
            self.assertEqual(memory.read_text(),'POISON: previous procedure')
            contrast, contrast_record=prepare('Implement Contrast','b'*32)
            self.assertTrue(contrast_record['target_absent'])
            self.assertFalse((contrast/'src/contrast.ts').exists())
            self.assertNotIn('applyContrast',(contrast/'src/main.tsx').read_text())
            self.assertEqual((contrast/'src/brightness.ts').read_bytes(),(app/'src/brightness.ts').read_bytes())
            with self.assertRaises(FileExistsError): prepare('Implement Brightness','a'*32)
            with self.assertRaises(ValueError): prepare('Implement Brightness','../escape')

    def test_brightness_builder_cannot_read_prior_feature_or_expected_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            broker=BrightnessBroker(root=Path(temp))
            for name in ('src/contrast.ts','../generated-app/src/brightness.ts','../evidence/brightness/canonical-contract.json','layout-packet/reference.png'):
                with self.assertRaises(ValueError): broker.path(name)
            self.assertEqual(broker.path('src/brightness.ts',True),(Path(temp)/'src/brightness.ts').resolve())

    def test_resume_cannot_relabel_a_different_feature(self):
        from features.pipeline import continue_job
        with tempfile.TemporaryDirectory() as temp, patch('features.pipeline.ROOT',Path(temp)):
            old=Path(temp)/'evidence/learning'/('feature-'+'a'*32); old.mkdir(parents=True)
            (old/'spec.json').write_text(json.dumps(brightness_spec()))
            with self.assertRaisesRegex(ValueError,'Resume request differs'):
                continue_job('a'*32,'b'*32,lambda *a,**k:None,request='Implement Contrast')

    def test_job_local_map_starts_empty_and_can_record_brightness(self):
        with tempfile.TemporaryDirectory() as temp:
            spec=brightness_spec(); m=InteractionMap(Path(temp)/'map.json',spec['target'])
            self.assertIsNone(m.route('brightness'))
            m.record_route(spec)
            self.assertEqual(m.route('brightness')['controls'][0]['label'],'Brightness')

    def test_reference_leaves_frozen_defaults_untouched_and_checks_them(self):
        from playwright.sync_api import sync_playwright
        spec=brightness_spec()
        frozen=copy.deepcopy(spec['controls'][0])
        frozen.update(label='Green channel',locator={'by':'role','role':'slider','name':'Green channel'})
        spec['controls'].append(frozen)
        markup='''<button role="menuitem">Image</button><button role="menuitem">Adjust</button>
        <div role="dialog"><h2>Adjust</h2><table><tr><td>Brightness:</td><td><input type="range" min="-10" max="10" step="1" value="0"></td></tr></table>
        <input aria-label="Green channel" type="range" min="-10" max="10" step="1" value="0">
        <button onclick="this.closest('[role=dialog]').style.display='none'">Apply</button><button>Cancel</button></div><div id="layer_name">fixture</div>'''
        with sync_playwright() as pw, tempfile.TemporaryDirectory() as temp:
            browser=pw.chromium.launch(headless=True); page=browser.new_page(); page.set_content(markup)
            adapter=object.__new__(FeatureAdapter); adapter.page=page; adapter.phase='imported'; adapter.artifact_dir=Path(temp)
            adapter.dialog=lambda name:page.get_by_role('dialog')
            adapter.capture_screenshot=lambda *a:None; adapter.assert_dimensions=lambda:None
            @contextmanager
            def action(*a,**kw): yield {}
            adapter.action=action
            with patch('features.browser.set_numeric',wraps=set_numeric) as setter:
                values=adapter.apply_feature(spec,4)
            self.assertEqual(setter.call_count,1)
            self.assertEqual(values['Green channel']['accepted'],0)
            page.set_content(markup.replace('aria-label="Green channel" type="range" min="-10"','aria-label="Green channel" type="range" min="-9"'))
            adapter.phase='imported'
            with self.assertRaisesRegex(ValueError,'Observed domain changed'): adapter.apply_feature(spec,4)
            browser.close()

if __name__=='__main__': unittest.main()
