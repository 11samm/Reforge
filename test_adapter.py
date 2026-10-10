"""Offline integrity and boundary checks for reference replay."""
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from adapter.png import ROOT, FIXTURES, fixture_path, within, png_info, compare_pngs
from adapter.minipaint import MiniPaintAdapter
from adapter.validate import cases


class AdapterTests(unittest.TestCase):
    def test_only_selected_development_fixtures_and_original_hashes(self):
        selected=cases()
        self.assertEqual({c['case_id'] for c in selected},{'gb010','gb017'})
        for case in selected:
            for path_key,hash_key in (('input_path','input'),('output_path','output')):
                info=png_info(fixture_path(case[path_key]))
                self.assertEqual(info['png_sha256'],case['hashes'][hash_key+'_png_sha256'])
                self.assertEqual(info['rgba_sha256'],case['hashes'][hash_key+'_decoded_rgba_sha256'])
        self.assertEqual(png_info(fixture_path(selected[0]['input_path']))['alpha_extrema'],[255,255])
        self.assertEqual(png_info(fixture_path(selected[1]['input_path']))['alpha_extrema'],[0,255])

    def test_path_guards_reject_other_splits_and_escaping_paths(self):
        for path in ('holdout/inputs/secret.png','final_holdout/inputs/secret.png',
                     'development/../../collector/secret.png','development/inputs/../../../smoke.py'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                fixture_path(path)
        with self.assertRaises(ValueError):
            within(ROOT/'adapter/minipaint.py',ROOT/'generated-app')
        with self.assertRaises(ValueError):
            MiniPaintAdapter(ROOT/'generated-app')

    def test_exact_rgba_comparison_checks_transparent_rgb_and_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            a,b,c=[Path(directory)/name for name in ('a.png','b.png','c.png')]
            Image.new('RGBA',(2,1),(10,20,30,0)).save(a)
            Image.new('RGBA',(2,1),(11,20,30,0)).save(b)
            Image.new('RGBA',(1,1),(10,20,30,0)).save(c)
            result=compare_pngs(a,b)
            self.assertFalse(result['rgba_equal'])
            self.assertEqual(result['different_pixels'],2)
            self.assertEqual(result['max_channel_delta'],1)
            self.assertFalse(compare_pngs(a,c)['dimensions_equal'])
            self.assertTrue(compare_pngs(a,a)['rgba_equal'])

    def test_preconditions_reject_operation_before_import(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'evidence') as directory:
            adapter=MiniPaintAdapter(directory)
            with self.assertRaises(ValueError):
                adapter.apply_operation({'Percentage':3})
            adapter.phase='imported'
            for params in ({'radius':3},{'Percentage':True},{'Percentage':1.5},{'Percentage':51}):
                with self.subTest(params=params), self.assertRaises(ValueError):
                    adapter.apply_operation(params)
            with self.assertRaises(ValueError):
                adapter.import_image(FIXTURES/'inputs/gb017.png')

    def test_export_cannot_escape_artifacts_or_overwrite(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'evidence') as directory:
            adapter=MiniPaintAdapter(directory)
            adapter.phase='imported'
            with self.assertRaises(ValueError):
                adapter.export_png(ROOT/'generated-app/output.png')
            existing=Path(directory)/'output.png'
            existing.write_bytes(b'prior experiment')
            with self.assertRaises(ValueError):
                adapter.export_png(existing)
            self.assertEqual(existing.read_bytes(),b'prior experiment')


if __name__=='__main__':
    unittest.main()
