"""Generate reproducible controlled pass/fail reports, never blur compatibility results."""
import json
from pathlib import Path
import time
import uuid
from PIL import Image, PngImagePlugin
from evaluator.compare import evaluate, load_policy, POLICIES, write_report


def main():
    root = Path(__file__).resolve().parents[1]
    run = root/'evidence/evaluator-examples'/(time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8])
    fixtures = run/'fixtures'; fixtures.mkdir(parents=True)
    def png(name, pixels, size, **kwargs):
        path = fixtures/(name+'.png'); image = Image.new('RGBA', size)
        image.putdata(pixels); image.save(path, **kwargs); return path
    pixels = [(10, 20, 30, 0), (40, 50, 60, 128)]
    a = png('reference', pixels, (2, 1), compress_level=0)
    meta = PngImagePlugin.PngInfo(); meta.add_text('note', 'Same samples; different encoding and metadata')
    equal = png('reencoded', pixels, (2, 1), compress_level=9, pnginfo=meta)
    rgb = png('rgb-change', [(14, 22, 30, 0), pixels[1]], (2, 1))
    alpha = png('alpha-only', [(10, 20, 30, 2), pixels[1]], (2, 1))
    dimensions = png('dimensions', pixels+[pixels[0]], (3, 1))
    invalid = fixtures/'invalid.png'; invalid.write_bytes(b'not a PNG')
    empty = [(0, 0, 0, 0)]*10000
    sparse_a = png('sparse-reference', empty, (100, 100)); empty[5050]=(255, 0, 0, 0)
    sparse_b = png('sparse-candidate', empty, (100, 100))
    exact, blur = load_policy(), load_policy(POLICIES/'blur-provisional-v1.json')
    rows = [('encoding-independent', a, equal, exact, None, 'match'),
            ('known-rgb-change', a, rgb, exact, None, 'pixel_mismatch'),
            ('alpha-only-change', a, alpha, exact, None, 'pixel_mismatch'),
            ('dimension-mismatch', a, dimensions, exact, None, 'dimension_mismatch'),
            ('invalid-png', a, invalid, exact, None, 'invalid_output'),
            ('missing-png', a, fixtures/'missing.png', exact, None, 'missing_output'),
            ('sparse-full-image', sparse_a, sparse_b, blur, None, 'match'),
            ('sparse-region-gate', sparse_a, sparse_b, blur, {'informative':[50,50,51,51]}, 'pixel_mismatch')]
    results=[]
    for case_id, reference, candidate, policy, regions, expected in rows:
        r=evaluate(case_id, reference, candidate, run/case_id, policy, regions)
        r['controlled_expected_classification']=expected; results.append(r)
    expected_outcomes=all(r['classification']==r['controlled_expected_classification'] for r in results)
    summary={'suite_id':'controlled-evaluator-v1','controlled_outcomes_correct':expected_outcomes,
             'notice':'Deliberate failures verify evaluator behavior; no blur implementation evaluated.', 'cases':results}
    (run/'results.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    write_report(results,run/'report.md')
    (root/'evidence/latest-evaluator-examples.json').write_text(json.dumps({'results':str(run/'results.json'),'controlled_outcomes_correct':expected_outcomes},indent=2)+'\n')
    print(json.dumps({'results':str(run/'results.json'),'controlled_outcomes_correct':expected_outcomes}))
    return 0 if expected_outcomes else 1


if __name__=='__main__': raise SystemExit(main())
