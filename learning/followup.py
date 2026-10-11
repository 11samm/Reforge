"""Developer-selected follow-up reference experiments for candidate-2 failures (not model-planned).

Each experiment states the competing explanations its export can distinguish. The same headed
reference procedure verifies an exact original-input export before applying blur; collection
failures are preserved and admit no behavior claim. Historical suites/results are not modified.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
from adapter.png import ROOT
from .core import digest, save, validate_config
from .diagnostics import ALL_DEFINITIONS, describe, write_input

SOURCE_RUN = '20261010T184129Z-78c8e934'
EXPERIMENTS = [
    {'id': 'dev-01', 'spec': {'kind': 'impulse_center', 'width': 65, 'height': 65}, 'percentage': 7,
     'question': 'What is the Percentage-7 point response away from boundaries: support, shape, symmetry and row/column agreement?',
     'hypotheses': [
         'Sigma-equals-Percentage Gaussian with float accumulation and final rounding (candidate-2 assumption): 2D peak ~0.83, so a near-circular disc of value 1 of radius ~7 around a 0/1 field.',
         'Per-pass 8-bit quantization: horizontal pass peak ~14.5 is stored as bytes before the vertical pass, giving a support shape that is not circular (square/cross-like) and row/column differences.',
         'Narrower or box-like effective kernel at Percentage 7: larger peak and smaller support than the sigma-7 prediction (would also explain fresh-03 center 130 vs candidate 135).',
         'Even-length or offset kernel: response asymmetric about the impulse (left/right or up/down counts differ).'],
     'predictions': [
         'Float+round: values only 0/1, support radius ~7, rows equal to columns.',
         'Per-pass bytes: support boundary follows separable thresholds; center row and column differ or the footprint is axis-aligned.',
         'Narrower: peak >=2 and support radius clearly below 7.',
         'Offset: footprint centroid shifted by >=0.5 px from (32,32).'],
     'usefulness': 'Direct Percentage-7 kernel probe for the fresh-03 center/boundary failures; matched with dev-02.',
     'compare_with': ['dev-02', 'fresh-03', 'fresh-01']},
    {'id': 'dev-02', 'spec': {'kind': 'edge', 'width': 65, 'height': 65}, 'percentage': 7,
     'question': 'Does the matched Percentage-7 edge equal the cumulative of the matched impulse, and is it independent of image height?',
     'hypotheses': [
         'Linear separable filter: center-row edge profile equals 255 x cumulative sum of the dev-01 row response within rounding.',
         'Nonlinear/precision effect: edge profile deviates from the impulse cumulative beyond rounding (e.g. intermediate quantization or gamma).',
         'Height-independent horizontal response: center row equals fresh-03 (65x49, same setting) exactly.',
         'Dimension-dependent mapping or boundary coverage reaching the center: center row differs from fresh-03.'],
     'predictions': [
         'Linear: the step transition midpoint and slope follow the integrated dev-01 response.',
         'Nonlinear: systematic deviation (e.g. the +4 midpoint offset seen in candidate 2) persists in reference-vs-cumulative comparison.',
         'Height-independent: identical center-row RGB to fresh-03.',
         'Dependent: any center-row RGB difference from fresh-03.'],
     'usefulness': 'Separates kernel-shape errors from edge-specific nonlinearity; tests dimension dependence against fresh-03.',
     'compare_with': ['dev-01', 'fresh-03']},
    {'id': 'dev-03', 'spec': {'kind': 'dev_uniform_low_alpha', 'width': 33, 'height': 33}, 'percentage': 3,
     'question': 'How is low-alpha color stored and re-exported when the blur cannot change interior values?',
     'hypotheses': [
         'Straight-alpha float processing: interior stays exactly RGBA(200,100,50,10).',
         'Premultiplied bytes with round-trip rounding: interior RGB becomes (204,102,51) at alpha 10.',
         'Premultiplied bytes with floor/truncation: interior RGB becomes about (178,76,25) at alpha 10.',
         'Import itself quantizes low-alpha color: original-confirmation export already differs (limitation; no blur claim).'],
     'predictions': [
         'Unchanged interior.', '(204,102,51,10) interior.', '(178,76,25,10)-like interior.', 'Confirmation mismatch recorded.'],
     'usefulness': 'Isolates low-alpha color conversion behind the fresh-04 RGB-fraction and gb010 low-alpha failures.',
     'compare_with': ['fresh-04', 'gb010']},
    {'id': 'dev-04', 'spec': {'kind': 'dev_adjacent_alpha', 'width': 33, 'height': 33}, 'percentage': 3,
     'question': 'Is color mixed with alpha weighting across a seam between opaque red and alpha-40 blue?',
     'hypotheses': [
         'Alpha-weighted (premultiplied) mixing: seam pixels on the blue side are strongly red (red weight 255 vs blue 40).',
         'Unweighted straight-RGB mixing: seam colors are near-symmetric purple blends.',
         'Alpha channel blurred linearly and independently of color in both cases.'],
     'predictions': [
         'Premultiplied: x=16..18 red share far above 50%.', 'Straight: red/blue near 50% at the seam.',
         'Alpha center row matches a linear blur of the 255/40 step.'],
     'usefulness': 'Tests color/alpha coupling with a larger alpha contrast than fresh-04.',
     'compare_with': ['fresh-04']},
    {'id': 'dev-05', 'spec': {'kind': 'dev_hidden_rgb', 'width': 33, 'height': 33}, 'percentage': 3,
     'question': 'Do fully transparent pixels with nonzero RGB survive import, and do they contribute color after blur?',
     'hypotheses': [
         'Import normalizes hidden RGB to black: original-confirmation fails (limitation; no blur claim).',
         'Hidden RGB preserved and ignored by premultiplied filtering: no green appears in opaque/partial pixels.',
         'Hidden RGB preserved and bleeds via straight filtering: green appears in the red side.',
         'Zero-alpha outputs export as black versus retaining the hidden green.'],
     'predictions': ['Confirmation mismatch.', 'No green at alpha>0.', 'Green >0 near the seam at alpha>0.',
                     'RGB at alpha 0 is (0,0,0) or (0,255,0).'],
     'usefulness': 'Tests the hidden-RGB behavior candidate 2 assumed (canonical black at alpha 0).',
     'compare_with': ['gb010', 'fresh-04']},
    {'id': 'dev-06', 'spec': {'kind': 'impulse_center', 'width': 9, 'height': 7}, 'percentage': 3,
     'question': 'With an odd image smaller than the expected Percentage-3 support, how are boundaries and parameter scale handled?',
     'hypotheses': [
         'Transparent exterior without renormalization: alpha drops at every pixel (alpha_sum well below 63*255).',
         'Clamp/replicate or renormalized kernel at borders: alpha stays 255 everywhere.',
         'Percentage relative to image size: near-identity (peak close to 255) on this tiny image, unlike 65x49 cases.',
         'Absolute Percentage-3 spread truncated by the image: low peak spread over the whole image.'],
     'predictions': ['Low uniform-ish alpha with strongest center.', 'All alpha 255.',
                     'Peak remains near white.', 'Peak far below fresh-01 41/255 at a smaller setting.'],
     'usefulness': 'Odd-size boundary/normalization and scale-dependence probe relevant to boundary-region failures.',
     'compare_with': ['fresh-02', 'gb010']},
]


def validate_experiments(experiments, config):
    if not 1 <= len(experiments) <= 6: raise ValueError('At most six developer follow-up experiments')
    ids = [e['id'] for e in experiments]
    if len(set(ids)) != len(ids): raise ValueError('Duplicate follow-up IDs')
    for e in experiments:
        if e['spec']['kind'] not in ALL_DEFINITIONS or not config['percentage_min'] <= e['percentage'] <= config['percentage_max']:
            raise ValueError('Follow-up outside declared generators/domain')
        if len(e['hypotheses']) < 2 or len(e['predictions']) < 2: raise ValueError('Competing explanations required')
    return experiments


def run_worker(request, directory, timeout):
    directory.mkdir(parents=True, exist_ok=True); save(directory / 'request.json', request)
    started = time.monotonic()
    with (directory / 'worker.log').open('w', encoding='utf-8') as log:
        proc = subprocess.Popen([sys.executable, '-m', 'learning.worker', 'devreference', str(directory / 'request.json'), str(directory)],
                                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try: proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == 'nt': subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], timeout=10, capture_output=True)
            else: proc.kill()
            proc.wait(timeout=5)
            return {'status': 'infrastructure_failure', 'error': {'type': 'TimeoutError', 'message': 'Worker deadline; process tree terminated'}}
    save(directory / 'process.json', {'exit': proc.returncode, 'elapsed_seconds': round(time.monotonic() - started, 3)})
    return json.loads((directory / 'result.json').read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'learning.config.json')
    parser.add_argument('--only', nargs='*', help='Subset of experiment IDs')
    args = parser.parse_args()
    config = validate_config(json.loads(args.config.read_text(encoding='utf-8-sig')))
    selected = validate_experiments([e for e in EXPERIMENTS if not args.only or e['id'] in args.only], config)
    out = ROOT / 'evidence/learning' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8] + '-dev-followup')
    (out / 'inputs').mkdir(parents=True)
    summary = {'kind': 'developer-selected follow-up evidence', 'selected_by': 'developer', 'source_run': SOURCE_RUN,
               'source_candidate': 'candidate-2', 'model_requests': 0, 'historical_suite_modified': False,
               'experiments': [], 'note': 'Ordinary-code selection; observations do not establish an algorithm.'}
    for e in selected:
        input_path = out / 'inputs' / (e['id'] + '.png')
        info = write_input(e['spec'], input_path)
        request = {'id': e['id'], 'config': config, 'spec': e['spec'], 'percentage': e['percentage'],
                   'input_path': str(input_path), 'input_sha256': digest(input_path)}
        d = out / 'experiments' / e['id']
        print(json.dumps({'experiment': e['id'], 'spec': e['spec'], 'percentage': e['percentage']}), flush=True)
        report = run_worker(request, d, config['reference_seconds'] + 30)
        save(d / 'reference-record.json', report)
        plan = {'question': e['question'], 'hypotheses': e['hypotheses'], 'input': e['spec'], 'percentage': e['percentage'],
                'predictions': e['predictions'], 'usefulness': e['usefulness']}
        row = {'id': e['id'], 'status': report['status'], 'requested': e['percentage'],
               'accepted': report.get('accepted_percentage'), 'original_confirmation': report.get('original_confirmation'),
               'error': report.get('error')}
        if report['status'] == 'observed' and report.get('accepted_percentage') == e['percentage']:
            record = {'id': e['id'], 'selected_by': 'developer', 'plan': plan, 'compare_with': e['compare_with'],
                      'input': str(input_path), 'expected': report['output_path'],
                      'accepted_input_spec': {**e['spec'], 'definition': ALL_DEFINITIONS[e['spec']['kind']]},
                      'input_sha256': info['png_sha256'], 'expected_sha256': report['output']['png_sha256'],
                      'percentage': report['accepted_percentage'], 'target': report['target'],
                      'procedure_record': str(d / 'reference-record.json'),
                      'input_samples': describe(input_path), 'export_samples': describe(report['output_path'])}
            save(out / 'evidence' / (e['id'] + '.json'), record)
        else:
            confirmation = d / 'original-confirmation.png'
            if confirmation.exists(): row['original_confirmation_export'] = str(confirmation)
            save(out / 'failures' / (e['id'] + '.json'), {**row, 'plan': plan, 'behavior_claim': 'none; collection failure preserved'})
        summary['experiments'].append(row)
        save(out / 'summary.json', summary)
        print(json.dumps(row), flush=True)
    print(json.dumps({'output': str(out)}), flush=True)
    return 0


if __name__ == '__main__': raise SystemExit(main())
