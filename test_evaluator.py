"""Controlled examples and exact expected metric checks; no model or reference browser."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image, PngImagePlugin
from evaluator.compare import evaluate, load_policy, validate_policy, POLICIES


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.exact = load_policy()
        self.blur = load_policy(POLICIES / 'blur-provisional-v1.json')
        self.counter = 0

    def tearDown(self): self.tmp.cleanup()

    def png(self, name, pixels, size=None, **kwargs):
        path = self.root / (name + '.png')
        im = Image.new('RGBA', size or (len(pixels), 1)); im.putdata(pixels); im.save(path, **kwargs)
        return path

    def compare(self, a, b, policy=None, regions=None):
        self.counter += 1
        return evaluate('controlled', a, b, self.root / str(self.counter), policy or self.exact, regions)

    def test_equal_pixels_different_encoding_metadata(self):
        pixels = [(1, 2, 3, 0), (4, 5, 6, 128)]
        metadata = PngImagePlugin.PngInfo(); metadata.add_text('note', 'different encoding')
        a = self.png('a', pixels, compress_level=0)
        b = self.png('b', pixels, compress_level=9, pnginfo=metadata)
        self.assertNotEqual(a.read_bytes(), b.read_bytes())
        result = self.compare(a, b)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['metrics']['different_pixels'], 0)
        self.assertEqual(result['metrics']['rgb_mae_per_channel'], [0, 0, 0])

    def test_rgb_and_alpha_metrics_and_artifacts(self):
        a = self.png('a', [(10, 20, 30, 0), (10, 20, 30, 128)])
        b = self.png('b', [(14, 22, 30, 0), (10, 20, 30, 128)])
        r = self.compare(a, b); m = r['metrics']
        self.assertEqual(r['classification'], 'pixel_mismatch')
        self.assertEqual(m['rgb_mae_per_channel'], [2, 1, 0]); self.assertEqual(m['rgb_mae'], 1)
        self.assertEqual(m['rgb_max'], 4); self.assertEqual(m['alpha_mae'], 0)
        self.assertEqual(m['different_pixels'], 1); self.assertEqual(m['rgb_fraction_within_tolerance'], .5)
        with Image.open(self.root/'1/rgb-difference-x16.png') as im: self.assertEqual(im.getpixel((0, 0)), (64, 32, 0))
        b = self.png('alpha', [(10, 20, 30, 2), (10, 20, 30, 128)])
        r = self.compare(a, b); m = r['metrics']
        self.assertEqual(m['rgb_max'], 0); self.assertEqual(m['alpha_mae'], 1); self.assertEqual(m['alpha_max'], 2)
        self.assertEqual(m['alpha_fraction_within_tolerance'], .5)
        with Image.open(self.root/'2/alpha-difference-x16.png') as im: self.assertEqual(im.getpixel((0, 0)), 32)

    def test_dimensions_invalid_missing_and_16_bit(self):
        a = self.png('a', [(1, 2, 3, 255)])
        b = self.png('b', [(1, 2, 3, 255)] * 2)
        r = self.compare(a, b); self.assertEqual(r['classification'], 'dimension_mismatch'); self.assertIsNone(r['metrics'])
        b.write_bytes(b'not PNG'); self.assertEqual(self.compare(a, b)['classification'], 'invalid_output')
        self.assertEqual(self.compare(a, self.root/'missing.png')['classification'], 'missing_output')
        b = self.root/'16.png'; Image.new('I;16', (1, 1), 1000).save(b)
        self.assertEqual(self.compare(a, b)['classification'], 'invalid_output')

    def test_localized_error_additional_region_gate(self):
        pixels = [(0, 0, 0, 0)] * 10000
        a = self.png('a', pixels, (100, 100))
        pixels[5050] = (255, 0, 0, 0)
        b = self.png('b', pixels, (100, 100))
        full = self.compare(a, b, self.blur)
        self.assertEqual(full['status'], 'passed')
        r = self.compare(a, b, self.blur, {'informative': [50, 50, 51, 51]})
        self.assertEqual(r['status'], 'failed'); self.assertEqual(r['metrics'], full['metrics'])
        self.assertEqual(r['regions']['informative']['metrics']['rgb_max'], 255)
        with Image.open(self.root/'2/region-informative-rgb-difference-x16.png') as im: self.assertEqual(im.getpixel((0, 0)), (255, 0, 0))

    def test_inclusive_mean_fraction_and_alpha_boundaries(self):
        a = self.png('a', [(0, 0, 0, 0)] * 100)
        p = [(1, 1, 1, 1)] * 100
        b = self.png('b', p)
        self.assertEqual(self.compare(a, b, self.blur)['status'], 'passed')
        p[0] = (2, 1, 1, 1); b = self.png('over-mean', p)
        self.assertEqual(self.compare(a, b, self.blur)['status'], 'failed')
        p = [(0, 0, 0, 0)] * 100; p[0] = (4, 0, 0, 3); b = self.png('fraction', p)
        self.assertEqual(self.compare(a, b, self.blur)['status'], 'passed')
        p[1] = (4, 0, 0, 0); b = self.png('fraction-fail', p)
        self.assertEqual(self.compare(a, b, self.blur)['status'], 'failed')
        p[0] = (3, 0, 0, 4); b = self.png('alpha-fail', p)
        self.assertEqual(self.compare(a, b, self.blur)['status'], 'failed')
        p = [(3, 3, 3, 3)]; a = self.png('zero', [(0, 0, 0, 0)]); b = self.png('three', p)
        policy = copy.deepcopy(self.blur); policy['rgb_mean_max'] = policy['alpha_mean_max'] = 3
        self.assertEqual(self.compare(a, b, policy)['status'], 'passed')

    def test_reject_invalid_policies_regions_and_reused_artifacts(self):
        for key in self.blur:
            if isinstance(self.blur[key], (int, float)):
                for invalid in (float('nan'), float('inf'), -1, True, '1', None):
                    policy = copy.deepcopy(self.blur); policy[key] = invalid
                    with self.subTest(key=key, invalid=invalid), self.assertRaises(ValueError): validate_policy(policy)
        policy = copy.deepcopy(self.blur); policy['rgb_fraction_min'] = 1.01
        with self.assertRaises(ValueError): validate_policy(policy)
        a = self.png('a', [(0, 0, 0, 0)])
        for regions in ({}, {'empty': [0, 0, 0, 1]}, {'outside': [0, 0, 2, 1]}, {'bad': [False, 0, 1, 1]}, {'../x': [0, 0, 1, 1]}):
            self.assertEqual(self.compare(a, a, regions=regions)['classification'], 'invalid_region')
        with self.assertRaises(FileExistsError): evaluate('controlled', a, a, self.root/'1')

    def test_infrastructure_copy_error_is_not_pixel_failure(self):
        from unittest.mock import patch
        a = self.png('a', [(0, 0, 0, 0)])
        with patch('evaluator.compare.shutil.copyfile', side_effect=OSError('disk unavailable')):
            r = self.compare(a, a)
        self.assertEqual(r['classification'], 'infrastructure_error')
        self.assertIsNone(r['metrics'])

    def test_cli_exit_codes(self):
        import contextlib
        import io
        from unittest.mock import patch
        from evaluator.compare import main
        a = self.png('a', [(0, 0, 0, 0)])
        b = self.png('b', [(1, 0, 0, 0)])
        for index, candidate, policy, code in [(1, a, None, 0), (2, b, None, 1), (3, a, 'bad-policy.json', 2)]:
            if policy: (self.root/policy).write_text('{"invalid":true}')
            args = ['compare', '--case-id', 'cli-test', '--reference', str(a), '--candidate', str(candidate), '--output', str(self.root/f'cli-{index}')]
            if policy: args += ['--policy', str(self.root/policy)]
            with patch('sys.argv', args), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), code)


if __name__ == '__main__': unittest.main()
