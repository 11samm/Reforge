"""Compare raw 8-bit RGBA samples, with separate display-only artifacts."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import struct
from PIL import Image, ImageChops, ImageDraw

POLICIES = Path(__file__).parent / 'policies'
NUMERIC = {'rgb_mean_max': (0, 255), 'rgb_pixel_tolerance': (0, 255),
           'rgb_fraction_min': (0, 1), 'alpha_mean_max': (0, 255),
           'alpha_max': (0, 255), 'alpha_pixel_tolerance': (0, 255),
           'alpha_fraction_min': (0, 1)}


def validate_policy(policy):
    if not isinstance(policy, dict) or set(policy) != {*NUMERIC, 'id', 'version', 'mode', 'description'}:
        raise ValueError('Policy must have exactly the declared v1 fields')
    if not isinstance(policy['id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]+', policy['id']):
        raise ValueError('Invalid policy id')
    if type(policy['version']) is not int or policy['version'] != 1:
        raise ValueError('Unsupported policy schema version')
    if policy['mode'] not in ('exact', 'tolerance') or not isinstance(policy['description'], str) or not policy['description'].strip():
        raise ValueError('Invalid policy mode or description')
    for name, (low, high) in NUMERIC.items():
        value = policy[name]
        if type(value) not in (int, float) or not low <= value <= high or not math.isfinite(value):
            raise ValueError(f'Invalid policy value: {name}')
    if policy['mode'] == 'exact' and any(policy[k] != (1 if 'fraction_min' in k else 0) for k in NUMERIC):
        raise ValueError('Exact policy requires zero errors and fractions of one')
    return dict(policy)


def load_policy(path=POLICIES / 'exact-rgba-v1.json'):
    return validate_policy(json.loads(Path(path).read_text(encoding='utf-8-sig')))


def decode(path):
    with Image.open(path) as image:
        if image.format != 'PNG' or getattr(image, 'n_frames', 1) != 1:
            raise ValueError('Expected a single-frame PNG')
        # Pillow RGBA conversion is 8-bit. Refuse native 16-bit rather than silently lose precision.
        header = Path(path).read_bytes()[:29]
        if len(header) < 29 or header[24] == 16:
            raise ValueError('Evaluator v1 supports 8-bit or lower PNG samples, not 16-bit')
        image.verify()
    with Image.open(path) as image:
        image.load()
        return image.convert('RGBA')


def metrics(reference, candidate, policy):
    delta = ImageChops.difference(reference, candidate)
    count = reference.width * reference.height
    totals = [0, 0, 0, 0]; maxima = [0, 0, 0, 0]
    rgb_ok = alpha_ok = different = 0
    for pixel in delta.get_flattened_data():
        for channel, value in enumerate(pixel):
            totals[channel] += value
            maxima[channel] = max(maxima[channel], value)
        rgb_ok += max(pixel[:3]) <= policy['rgb_pixel_tolerance']
        alpha_ok += pixel[3] <= policy['alpha_pixel_tolerance']
        different += any(pixel)
    return {'pixel_count': count, 'rgb_mae_per_channel': [x / count for x in totals[:3]],
            'rgb_mae': sum(totals[:3]) / (3 * count), 'rgb_max': max(maxima[:3]),
            'alpha_mae': totals[3] / count, 'alpha_max': maxima[3],
            'rgb_fraction_within_tolerance': rgb_ok / count,
            'alpha_fraction_within_tolerance': alpha_ok / count,
            'different_pixels': different}


def failures(m, policy):
    if policy['mode'] == 'exact':
        return [f"{m['different_pixels']} pixels differ in raw RGBA"] if m['different_pixels'] else []
    reasons = []
    for metric, limit, relation in [('rgb_mae', 'rgb_mean_max', 'max'),
                                  ('rgb_fraction_within_tolerance', 'rgb_fraction_min', 'min'),
                                  ('alpha_mae', 'alpha_mean_max', 'max'), ('alpha_max', 'alpha_max', 'max'),
                                  ('alpha_fraction_within_tolerance', 'alpha_fraction_min', 'min')]:
        if (m[metric] > policy[limit] if relation == 'max' else m[metric] < policy[limit]):
            reasons.append(f'{metric}={m[metric]} violates {limit}={policy[limit]}')
    return reasons


def composite(image):
    board = Image.new('RGBA', image.size)
    draw = ImageDraw.Draw(board)
    for y in range(0, image.height, 8):
        for x in range(0, image.width, 8):
            gray = 192 if (x // 8 + y // 8) % 2 else 240
            draw.rectangle((x, y, x + 7, y + 7), fill=(gray, gray, gray, 255))
    return Image.alpha_composite(board, image).convert('RGB')


def previews(reference, candidate, directory, prefix):
    left, right = composite(reference), composite(candidate)
    preview = Image.new('RGB', (left.width + right.width + 8, max(left.height, right.height)), 'gray')
    preview.paste(left, (0, 0)); preview.paste(right, (left.width + 8, 0))
    preview.save(directory / f'{prefix}side-by-side.png')
    if reference.size == candidate.size:
        delta = ImageChops.difference(reference, candidate)
        channels = delta.split()
        rgb = Image.merge('RGB', channels[:3]).point(lambda v: min(v * 16, 255))
        alpha = channels[3].point(lambda v: min(v * 16, 255))
        rgb.save(directory / f'{prefix}rgb-difference-x16.png')
        alpha.save(directory / f'{prefix}alpha-difference-x16.png')
        # Display-only crop makes sparse differences discoverable; never changes scoring.
        mask = channels[0]
        for channel in channels[1:]: mask = ImageChops.lighter(mask, channel)
        box = mask.getbbox()
        if box:
            rgb.crop(box).save(directory / f'{prefix}changed-bounds-rgb-x16.png')
            alpha.crop(box).save(directory / f'{prefix}changed-bounds-alpha-x16.png')


def evaluate(case_id, reference_path, candidate_path, output_dir, policy=None, regions=None):
    """Fresh output directory required. Named [left,top,right,bottom] regions are additional gates."""
    if not isinstance(case_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', case_id):
        raise ValueError('Case id must contain only letters, digits, underscore or hyphen')
    policy = validate_policy(load_policy() if policy is None else policy)
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=False)
    result = {'schema_version': 1, 'case_id': case_id, 'status': 'failed', 'classification': None,
              'policy': policy, 'policy_sha256': hashlib.sha256(json.dumps(policy, sort_keys=True, allow_nan=False).encode()).hexdigest(),
              'dimensions_equal': None, 'dimensions': {}, 'metrics': None, 'regions': {},
              'reasons': [], 'artifacts': {}, 'display': {'checker_size': 8, 'difference_gain': 16,
              'side_by_side_order': ['reference', 'candidate'], 'scoring': 'raw unpremultiplied 8-bit RGBA; no compositing'}}
    images = {}
    for role, path in [('reference', reference_path), ('candidate', candidate_path)]:
        path = Path(path)
        result[role + '_path'] = str(path.resolve())
        try:
            raw = directory / f'{role}-raw.png'
            shutil.copyfile(path, raw)
            result['artifacts'][role + '_raw'] = raw.name
        except PermissionError as error:
            result['reasons'].append(f'{role}: infrastructure read failure ({error})')
            result['classification'] = 'infrastructure_error'
        except FileNotFoundError:
            result['reasons'].append(f'{role}: missing output')
            result['classification'] = 'missing_output' if result['classification'] is None else result['classification']
        except OSError as error:
            result['reasons'].append(f'{role}: infrastructure copy failure ({error})')
            result['classification'] = 'infrastructure_error'
        else:
            try:
                images[role] = decode(raw)
                result['dimensions'][role] = list(images[role].size)
            except (ValueError, SyntaxError, struct.error, OSError, Image.DecompressionBombError) as error:
                result['reasons'].append(f'{role}: invalid PNG ({type(error).__name__}: {error})')
                result['classification'] = 'invalid_output' if result['classification'] is None else result['classification']
    if len(images) == 2:
        reference, candidate = images['reference'], images['candidate']
        result['dimensions_equal'] = reference.size == candidate.size
        previews(reference, candidate, directory, '')
        if not result['dimensions_equal']:
            result['classification'] = 'dimension_mismatch'
            result['reasons'].append('Reference and candidate dimensions differ; pixel metrics not computed')
        else:
            delta = ImageChops.difference(reference, candidate).split()
            mask = delta[0]
            for channel in delta[1:]: mask = ImageChops.lighter(mask, channel)
            result['display']['changed_bounds'] = mask.getbbox()
            result['metrics'] = metrics(reference, candidate, policy)
            result['reasons'] += ['full_image: ' + r for r in failures(result['metrics'], policy)]
            try:
                if regions is not None and (not isinstance(regions, dict) or not regions):
                    raise ValueError('Regions must be a nonempty named mapping')
                for name, box in (regions or {}).items():
                    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', name) or name == 'full_image':
                        raise ValueError('Invalid region name')
                    if not isinstance(box, (list, tuple)) or len(box) != 4 or any(type(v) is not int for v in box):
                        raise ValueError('Region boxes require four integer coordinates')
                    l, t, r, b = box
                    if not (0 <= l < r <= reference.width and 0 <= t < b <= reference.height):
                        raise ValueError('Region must be nonempty and inside the image')
                    a, c = reference.crop(box), candidate.crop(box)
                    m = metrics(a, c, policy)
                    reasons = failures(m, policy)
                    result['regions'][name] = {'box': list(box), 'metrics': m, 'passed': not reasons, 'reasons': reasons}
                    result['reasons'] += [name + ': ' + reason for reason in reasons]
                    previews(a, c, directory, 'region-' + name + '-')
                result['classification'] = 'pixel_mismatch' if result['reasons'] else 'match'
                if not result['reasons']: result['status'] = 'passed'
            except ValueError as error:
                result['classification'] = 'invalid_region'
                result['reasons'].append(str(error))
    result['artifacts'].update({p.stem: p.name for p in sorted(directory.glob('*.png'))})
    (directory / 'result.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    write_report([result], directory / 'report.md')
    return result


def write_report(results, path):
    lines = ['# Deterministic RGBA evaluation', '', f"Passed {sum(r['status']=='passed' for r in results)}/{len(results)} cases.", '',
             'Scoring uses raw RGBA. Checkerboard compositing is display only. Differences are amplified x16.', '']
    for result in results:
        lines += [f"## {result['case_id']}: {result['status']} ({result['classification']})", '',
                  f"Policy: {result['policy']['id']}. {result['policy']['description']}",
                  f"Dimensions agree: {result['dimensions_equal']}; {result['dimensions']}",
                  'Reasons: ' + ('; '.join(result['reasons']) or 'All declared criteria satisfied'), '']
        for name, m in [('full_image', result['metrics']), *[(n, r['metrics']) for n, r in result['regions'].items()]]:
            if m is not None:
                lines += [f"{name}: RGB per-channel MAE {m['rgb_mae_per_channel']}; RGB mean {m['rgb_mae']}, max {m['rgb_max']}; alpha mean {m['alpha_mae']}, max {m['alpha_max']}; RGB fraction {m['rgb_fraction_within_tolerance']}, alpha fraction {m['alpha_fraction_within_tolerance']}; differing pixels {m['different_pixels']}/{m['pixel_count']}.", '']
        lines += ['Artifacts: ' + ', '.join(result['artifacts'].values()), '']
    Path(path).write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case-id', required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--policy', type=Path, default=POLICIES / 'exact-rgba-v1.json')
    parser.add_argument('--regions', type=Path, help='JSON mapping of named half-open rectangle coordinates')
    args = parser.parse_args()
    try:
        result = evaluate(args.case_id, args.reference, args.candidate, args.output,
                          load_policy(args.policy), json.loads(args.regions.read_text()) if args.regions else None)
    except (ValueError, OSError) as error:
        classification = 'configuration_error' if isinstance(error, ValueError) else 'infrastructure_error'
        print(json.dumps({'status': 'failed', 'classification': classification, 'case_id': args.case_id, 'reason': str(error)}))
        return 2
    print(json.dumps({'case_id': result['case_id'], 'status': result['status'], 'classification': result['classification'], 'report': str(args.output / 'result.json')}))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__': raise SystemExit(main())
