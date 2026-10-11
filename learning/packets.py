"""Model packet assembly, lossless compact encodings, size measurement and hard pre-request limits."""
import json
from pathlib import Path
import re
from PIL import Image
from .diagnostics import ALL_DEFINITIONS, DEFINITIONS, render

# Estimation method: a BPE-like regex piece count (letters runs with optional leading space,
# 1..3 digit groups, punctuation runs, whitespace runs) plus a fixed runtime overhead.
# Calibrated against recorded single-turn decision invocations (no tools) in attempts 1 and 2:
# planner prompts give overhead 7,721/7,726 tokens; contract/route predictions land within 0.6%.
TOKEN_PATTERN = re.compile(r' ?[A-Za-z]+|\d{1,3}| ?[^\sA-Za-z\d]+|\s+')
RUNTIME_OVERHEAD_TOKENS = 7720
ESTIMATOR = ('regex-piece estimate + 7720 fixed runtime/system overhead; calibrated on recorded '
             'gpt-6.1-sol decision-call inputTokens (planner, contract-1, route-1/2; <=0.6% error). '
             'Not the provider tokenizer; tool-loop cumulative input is a projection.')
METRIC_DIGITS = 6
EXPECTED_ROUNDS = {'planner': 1, 'contract': 1, 'route': 1, 'builder': 6, 'repair': 2}


class PacketLimitError(ValueError):
    pass


def estimate_tokens(text):
    return len(TOKEN_PATTERN.findall(text))


def measure(role, prompt, schema=None, supplied=None):
    """Context for one request: fixed instructions + payload, output schema, and supplied source/tool text."""
    parts = {'prompt': prompt, 'output_schema': json.dumps(schema) if schema else ''}
    parts |= {'supplied:' + k: v for k, v in (supplied or {}).items()}
    sizes = {k: {'bytes': len(v.encode('utf-8')), 'tokens': estimate_tokens(v)} for k, v in parts.items()}
    context = RUNTIME_OVERHEAD_TOKENS + sum(s['tokens'] for s in sizes.values())
    rounds = EXPECTED_ROUNDS[role]
    return {'role': role, 'bytes': sum(s['bytes'] for s in sizes.values()), 'estimated_tokens': context,
            'parts': sizes, 'expected_tool_rounds': rounds,
            'projected_cumulative_input_tokens': context * rounds, 'method': ESTIMATOR}


def enforce(measurement, limits):
    over = [f"{k} {measurement[m]} > {limits[k]}" for k, m in [('bytes', 'bytes'), ('tokens', 'estimated_tokens')]
            if measurement[m] > limits[k]]
    if over:
        raise PacketLimitError(f"{measurement['role']} packet exceeds configured limit ({'; '.join(over)}); "
                               'no model request was sent. Evidence is never truncated: reduce scope or raise '
                               'packet_limits explicitly.')
    return measurement


# Lossless channel-planar run encoding. "v*n" is value v repeated n times; identical channels share a key.
def encode_channel(values):
    out, i = [], 0
    while i < len(values):
        j = i
        while j < len(values) and values[j] == values[i]: j += 1
        out.append(str(values[i]) if j - i == 1 else f'{values[i]}*{j - i}')
        i = j
    return ' '.join(out)


def decode_channel(text):
    values = []
    for token in text.split(' '):
        value, _, count = token.partition('*')
        values.extend([int(value)] * (int(count) if count else 1))
    return values


def encode_profile(pixels):
    channels = [[p[c] for p in pixels] for c in range(4)]
    groups = []
    for name, values in zip('RGBA', channels):
        match = next((g for g in groups if g[1] == values), None)
        if match: match[0] += name
        else: groups.append([name, values])
    return {'n': len(pixels), **{name: encode_channel(values) for name, values in groups}}


def decode_profile(profile):
    channels = {}
    for key, text in profile.items():
        if key == 'n': continue
        for name in key: channels[name] = decode_channel(text)
    if sorted(channels) != ['A', 'B', 'G', 'R'] or any(len(v) != profile['n'] for v in channels.values()):
        raise ValueError('Invalid encoded profile')
    return [[channels[c][i] for c in 'RGBA'] for i in range(profile['n'])]


def checked_profile(pixels):
    encoded = encode_profile(pixels)
    if decode_profile(encoded) != [list(p) for p in pixels]: raise ValueError('Lossless profile round trip failed')
    return encoded


def compact_summary(samples):
    """Exact export/input samples: axis profiles, corner/center points and channel sums."""
    w, h = samples['png']['width'], samples['png']['height']
    return {'size': [w, h], 'alpha_extrema': samples['png']['alpha_extrema'],
            f'row_y{h // 2}': checked_profile(samples['center_row']),
            f'column_x{w // 2}': checked_profile(samples['center_column']),
            'row_y0': checked_profile(samples['top_row']),
            'points': {f"{s['xy'][0]},{s['xy'][1]}": s['rgba'] for s in samples['samples']},
            'alpha_sum': samples['alpha_sum'], 'red_sum': samples['red_sum']}


def expand_summary(summary):
    """Inverse of compact_summary for the profile/point fields; used by tests and round-trip validation."""
    w, h = summary['size']
    return {'center_row': decode_profile(summary[f'row_y{h // 2}']),
            'center_column': decode_profile(summary[f'column_x{w // 2}']),
            'top_row': decode_profile(summary['row_y0']),
            'samples': [{'xy': [int(v) for v in k.split(',')], 'rgba': rgba} for k, rgba in summary['points'].items()],
            'alpha_sum': summary['alpha_sum'], 'red_sum': summary['red_sum']}


def generated_input_matches(e):
    """True when the recorded input PNG decodes exactly to the deterministic generator output."""
    spec = (e.get('plan') or {}).get('input')
    if not spec or spec['kind'] not in ALL_DEFINITIONS or not e.get('input'): return False
    with Image.open(e['input']) as raw:
        recorded = raw.convert('RGBA').tobytes()
    return render(spec['kind'], spec['width'], spec['height']).tobytes() == recorded


TARGET_FIELDS = ['name', 'visible_about_version', 'build', 'chromium_version', 'headed', 'viewport', 'device_scale_factor']


def evidence_table(evidence, with_plans=False):
    """One compact row per visible evidence item; paths, timestamps and full hashes stay in records."""
    rows, targets, kinds = [], [], set()
    for e in evidence:
        row = {'id': e['id'], 'percentage': e['percentage']}
        if e.get('prepared_development'):
            row['source'] = 'prepared development fixture'
            row['input'] = compact_summary(e['input_samples'])
            target = {'reference_application': e['target']}
        else:
            if e.get('selected_by') == 'developer': row['source'] = 'developer-selected follow-up (not model-planned)'
            spec = e['plan']['input']
            if generated_input_matches(e):
                row['input'] = {'generator': spec['kind'], 'width': spec['width'], 'height': spec['height']}
                kinds.add(spec['kind'])
            else:
                row['input'] = compact_summary(e['input_samples'])
            target = {k: e['target'].get(k) for k in TARGET_FIELDS}
            if with_plans:
                row['plan'] = {k: e['plan'][k] for k in ['question', 'hypotheses', 'predictions', 'usefulness']}
        if target not in targets: targets.append(target)
        row['target'] = 'T' + str(targets.index(target) + 1)
        row['export'] = compact_summary(e['export_samples'])
        row['sha256_prefix'] = {'input': e['input_sha256'][:12], 'export': e['expected_sha256'][:12]}
        rows.append(row)
    return {'encoding': 'Profiles are exact: channel keys (e.g. RGB when equal) hold space-separated values; '
                        "'v*n' repeats v n times; n is profile length. row_yK is row y=K; column_xK is column x=K. "
                        'points map "x,y" to exact RGBA. Generated inputs are exact by generator definition.',
            'generator_definitions': {k: ALL_DEFINITIONS[k] for k in sorted(kinds)},
            'targets': {'T' + str(i + 1): t for i, t in enumerate(targets)},
            'hash_note': '12-hex SHA-256 prefixes; full hashes are in the frozen suite and evidence records.',
            'items': rows}


def round_metrics(metrics):
    return {k: (float(f'{v:.{METRIC_DIGITS}g}') if isinstance(v, float) else v)
            for k, v in metrics.items() if k != 'rgb_mae_per_channel'} | (
        {'rgb_mae_per_channel': [float(f'{v:.{METRIC_DIGITS}g}') for v in metrics['rgb_mae_per_channel']]}
        if 'rgb_mae_per_channel' in metrics else {})


def case_loss(case):
    all_m = [case.get('metrics'), *[v['metrics'] for v in case.get('regions', {}).values()]]
    return max(((3 * m['rgb_mae'] + m['alpha_mae']) / 4 for m in all_m if m), default=255)


def worst_pixels(expected, candidate, source, limit=8):
    """Largest absolute channel errors; deterministic tie-break by error then row-major position."""
    with Image.open(expected) as a, Image.open(candidate) as b, Image.open(source) as c:
        ref, out, inp = a.convert('RGBA'), b.convert('RGBA'), c.convert('RGBA')
        w, h = ref.size
        ref_d, out_d, inp_d = ref.tobytes(), out.tobytes(), inp.tobytes()
    errors = []
    for i in range(w * h):
        r, o = ref_d[4 * i:4 * i + 4], out_d[4 * i:4 * i + 4]
        e = max(abs(r[k] - o[k]) for k in range(4))
        if e: errors.append((-e, i))
    errors.sort()
    return [{'xy': [i % w, i // w], 'expected': list(ref_d[4 * i:4 * i + 4]), 'candidate': list(out_d[4 * i:4 * i + 4]),
             'input': list(inp_d[4 * i:4 * i + 4])} for _, i in errors[:limit]], len(errors)


def delta_profile(expected, candidate):
    """candidate minus expected per channel, exactly run-encoded; zeros dominate near-matches."""
    return checked_profile([[c - e for c, e in zip(cp, ep)] for cp, ep in zip(candidate, expected)])


def scoring_section(suite):
    policy = suite['policy']
    return {'suite_id': suite['id'], 'policy': policy, 'region_rule': suite['region_rule'],
            'objective': suite['objective'], 'tie_policy': suite['tie_policy']}


def discrepancy_section(result, evidence, evaluation_dir, top_pixels=8, parameter_key="percentage"):
    """Failure metrics and informative samples for failed cases; passing cases only as a summary line."""
    from .diagnostics import describe
    by_id = {e['id']: e for e in evidence}
    gates = {k: result.get(k) for k in ['build_valid', 'independent', 'ui_valid', 'baseline_pass', 'baseline_classification', 'error']}
    passed, failed = [], []
    for case in result.get('cases', []):
        if case['status'] == 'passed':
            passed.append({'id': case['case_id'], 'worst_region_loss': float(f'{case_loss(case):.{METRIC_DIGITS}g}')})
            continue
        e = by_id[case['case_id']]
        row = {'id': case['case_id'], parameter_key: e[parameter_key], 'reasons': case['reasons'],
               'full_image': round_metrics(case['metrics']),
               'failing_regions': {n: {'box': r['box'], 'metrics': round_metrics(r['metrics'])}
                                   for n, r in case['regions'].items() if not r['passed']},
               'passing_regions': [n for n, r in case['regions'].items() if r['passed']]}
        out = Path(evaluation_dir) / (case['case_id'] + '.png')
        if out.exists():
            row['worst_pixels'], row['differing_pixels'] = worst_pixels(e['expected'], out, e['input'], top_pixels)
            got = describe(out); exp = e['export_samples']
            w, h = got['png']['width'], got['png']['height']
            row['candidate_minus_expected'] = {f'row_y{h // 2}': delta_profile(exp['center_row'], got['center_row']),
                                               f'column_x{w // 2}': delta_profile(exp['center_column'], got['center_column']),
                                               'row_y0': delta_profile(exp['top_row'], got['top_row'])}
        failed.append(row)
    return {'gates': gates, 'failed_cases': failed, 'passed_cases': passed,
            'metric_precision': f'{METRIC_DIGITS} significant digits; violation reasons and evaluation.json keep full values.',
            'sample_note': 'worst_pixels: largest absolute channel errors (expected=reference export). '
                           'candidate_minus_expected: exact signed per-channel deltas on the evidence profile axes.'}


class EvidenceReader:
    """Bounded read-only retrieval of exact visible profiles; never paths, never hidden or holdout data."""
    def __init__(self, sources, max_calls, max_chars=24000):
        self.sources, self.max_calls, self.max_chars = sources, max_calls, max_chars
        self.calls, self.chars = 0, 0

    def call(self, args):
        if not isinstance(args, dict) or set(args) != {'id', 'image', 'axis', 'index'}: raise ValueError('Unexpected arguments')
        if self.calls >= self.max_calls: raise ValueError('Evidence read budget exhausted')
        source = self.sources.get(args['id'], {}).get(args['image'])
        if not source or args['axis'] not in ['row', 'column'] or type(args['index']) is not int:
            raise ValueError('Unknown evidence image or axis')
        with Image.open(source) as raw:
            image = raw.convert('RGBA'); w, h = image.size
            limit = h if args['axis'] == 'row' else w
            if not 0 <= args['index'] < limit: raise ValueError('Index outside image')
            pixels = [list(image.getpixel((x, args['index']) if args['axis'] == 'row' else (args['index'], x)))
                      for x in range(w if args['axis'] == 'row' else h)]
        text = json.dumps({**args, 'size': [w, h], 'profile': checked_profile(pixels)})
        if self.chars + len(text) > self.max_chars: raise ValueError('Evidence read size budget exhausted')
        self.calls += 1; self.chars += len(text)
        return [{'type': 'inputText', 'text': text}]


EVIDENCE_TOOL = {'type': 'function', 'name': 'evidence_read',
                 'description': 'Read one exact visible-evidence row or column profile (same run encoding as packet). '
                                'image: input, export (reference), or candidate (last evaluated candidate output). Bounded call count.',
                 'inputSchema': {'type': 'object', 'properties': {
                     'id': {'type': 'string'}, 'image': {'type': 'string', 'enum': ['input', 'export', 'candidate']},
                     'axis': {'type': 'string', 'enum': ['row', 'column']}, 'index': {'type': 'integer'}},
                     'required': ['id', 'image', 'axis', 'index'], 'additionalProperties': False}}


def planner_prompt(config, guidance_section=None):
    from .guidance import prompt_suffix
    return ('Select 4 NEW discriminating Gaussian Blur reference experiments. '
            'Prepared visible development cases gb010 transparent shapes 65x49 and gb017 opaque poster129x97 use Percentage3. '
            'We need competing hypotheses, input specification, exact integer Percentage, predicted distinguishing observations and usefulness. '
            'Exact generator definitions ' + json.dumps(DEFINITIONS) + '. Dimensions 3..257, prefer33x33/65x49. '
            'Input specification is the selected fixed generator plus dimensions. Do not describe a different pattern in question or predictions. '
            'Declared Percentage domain ' + str(config['percentage_min']) + '..' + str(config['percentage_max']) + '. '
            'Choose impulse/boundary/edge/alpha evidence and at least two percentages to distinguish scaling; no familiar formula assumed. '
            'Only rendered UI actions and actual PNG exports will be observed. '
            'Opaque prepared gb017 export alpha extrema [82,255] suggests boundary alpha behavior needs testing. '
            'No tools, concise schema decisions only.' + prompt_suffix(guidance_section))


def contract_prompt(evidence, claims, accepted):
    packet = {'evidence': evidence_table(evidence, with_plans=True), 'previous_claims': claims,
              'accepted_verification_cases': accepted}
    return ('Summarize actual exported evidence and update structured behavioral claims. '
            'UNKNOWN/HYPOTHESIS for untested mechanism; OBSERVED for supported sample observations. '
            'No VERIFIED_WITHIN_SCOPE before trusted acceptance. Percentage is a UI integer, not assumed pixel radius. '
            'Scope each mechanism to tested inputs/parameters/version; include alternatives and unresolved alpha/edge/rounding behavior. '
            'supporting_evidence, contradicting_evidence and verification_cases contain ONLY exact IDs, never sentences. '
            'Put sample explanations in statement/scope. Link relevant visible verification_cases even before they have passed; '
            'OBSERVED status means reference evidence only. Do not invent evidence. Concise decisions only. Packet: ' + json.dumps(packet, separators=(',', ':')))


def route_prompt(result, discrepancies, evidence, budget, config, guidance_section=None):
    from .guidance import prompt_suffix
    index = [{'id': e['id'], 'percentage': e['percentage'],
              'input': (e.get('plan') or {}).get('input') or 'prepared development fixture'} for e in evidence]
    actual = {'build_valid': result['build_valid'], 'independent': result['independent'],
              'baseline_pass': result['baseline_pass'], 'error': result.get('error'), 'discrepancies': discrepancies,
              'evidence_index': index}
    return ('Suggest failure classification backed by exact evidence IDs, concise explanation and next action. '
            'Trusted code owns acceptance. Evaluator suspicion must STOP. Can propose 1..4 NEW experiments using allowed schema or repair. '
            'Do not manufacture failure; this is actual candidate evidence. Expected exports are summarized via worst_pixels and exact '
            'candidate_minus_expected deltas only. Remaining budget ' + json.dumps(budget) +
            '. Exact generator definitions ' + json.dumps(DEFINITIONS) + '; parameter domain ' +
            json.dumps({'percentage_min': config['percentage_min'], 'percentage_max': config['percentage_max']}) +
            '. Actual result ' + json.dumps(actual, separators=(',', ':')) + prompt_suffix(guidance_section))


BUILDER_RULES = ('Preserve approved layout, uploads, exact untouched exports, current-image state and all unrelated disabled controls. '
    'Use ONLY shell_read_file/shell_write_file (and evidence_read if supplied); no shell/browser/evaluator tools, no delegation. '
    'Allowed writes src/gaussian-blur.ts, src/main.tsx, src/current-image.ts, README.md. No dependencies/config/CSS changes. '
    'Create exported synchronous applyGaussianBlur(raster: Raster, percentage: number): Raster in src/gaussian-blur.ts; '
    'use type-only Raster import from current-image; independent pure transformation, no DOM/network/reference files. '
    'Validate integers, 8-bit dimensions/data and Percentage. Support bounded declared learning domain and reject unsupported values visibly. '
    'Keep dialog control exact Percentage label, observed min0/max50/step1; disable Apply and slider until image loaded; '
    'Apply transforms CURRENT raster and updates document raster, preview object URL and export state; close on success. '
    'Initial image preview accessible name stays Original image preview: filename for baseline. Update preview after blur without changing layout. '
    'Reject 16-bit blur without damaging existing upload/export support. Do not substitute a library blur or assume Percentage equals radius. '
    'Use evidence to infer parameter scaling, alpha handling, boundaries and rounding. Do not hard-code specific fixture outputs. '
    'Build host runs fixed build/batch commands after your turn; evaluator/expected outputs/policies are inaccessible. ')


def uncited_evidence(claims, evidence):
    cited = {i for c in claims for k in ['supporting_evidence', 'contradicting_evidence', 'verification_cases'] for i in c.get(k, [])}
    return [e['id'] for e in evidence if e['id'] not in cited]


def builder_prompt(claims, evidence, suite, config, repair=None):
    """repair: None for a clean candidate, else dict(discrepancies, base_source, base_label, rejected_source,
    rejected_label, routing_suggestion, mode_note, integration_passed)."""
    packet = {'contract_claims': claims, 'visible_evidence': evidence_table(evidence),
              'scoring': scoring_section(suite) if suite else None,
              'permitted_writes': ['README.md', 'src/current-image.ts', 'src/gaussian-blur.ts', 'src/main.tsx'],
              'parameter_domain': [config['percentage_min'], config['percentage_max']]}
    unincorporated = uncited_evidence(claims, evidence)
    if unincorporated:
        packet['unincorporated_evidence'] = {'ids': unincorporated, 'note': (
            'Not cited by any contract claim: exact visible observations only, not contract knowledge; '
            'any mechanism you infer from them is an untested hypothesis.')}
    developer = [e['id'] for e in evidence if e.get('selected_by') == 'developer']
    if developer:
        packet['developer_selected_evidence'] = developer
    calls = 'One bounded turn; at most ' + str(config['builder_tool_calls']) + ' tool calls'
    if config['evidence_reads']:
        calls += ', including at most ' + str(config['evidence_reads']) + ' evidence_read calls for additional exact rows/columns'
    if repair is None:
        head = 'Implement miniPaint Gaussian Blur from supplied observations. Read src/main.tsx and src/current-image.ts first. '
    else:
        packet['repair'] = {k: repair[k] for k in ['discrepancies', 'routing_suggestion', 'mode_note']}
        packet['repair']['workspace_operation'] = {'label': repair['base_label'], 'src/gaussian-blur.ts': repair['base_source']}
        if repair.get('rejected_source') is not None and repair['rejected_source'] != repair['base_source']:
            packet['repair']['last_rejected_operation'] = {'label': repair['rejected_label'], 'src/gaussian-blur.ts': repair['rejected_source']}
        head = ('Repair miniPaint Gaussian Blur from supplied observations and actual discrepancies. ')
        if repair.get('integration_passed'):
            head += ('The workspace already contains workspace_operation verbatim, and its main.tsx/current-image.ts '
                     'integration passed build, independent batch execution, UI/batch export agreement and all exact baselines. '
                     'Do not read or rewrite main.tsx/current-image.ts unless the fix requires it; write the complete patched '
                     'src/gaussian-blur.ts with shell_write_file. ')
        else:
            head += 'Read src/main.tsx and src/current-image.ts first. '
    return head + BUILDER_RULES + calls + '. Packet: ' + json.dumps(packet, separators=(',', ':'))


def boundary_alpha_prompt(claims, evidence, suite, config, repair, evaluation_dir):
    """Developer-scoped assignment; samples come only from frozen visible PNG exports."""
    selected = [e for e in evidence if e['percentage'] == 7]
    profiles = []
    for e in selected:
        with Image.open(e['expected']) as ref, Image.open(Path(evaluation_dir)/(e['id']+'.png')) as out:
            ref, out = ref.convert('RGBA'), out.convert('RGBA')
            w, h = ref.size
            axes = [('row', h//2), ('row', 0), ('column', 0)]
            samples = []
            for axis, index in axes:
                coords = [(x,index) for x in range(w)] if axis == 'row' else [(index,y) for y in range(h)]
                samples.append({'axis':axis,'index':index,
                    'expected_alpha':encode_channel([ref.getpixel(xy)[3] for xy in coords]),
                    'candidate_alpha':encode_channel([out.getpixel(xy)[3] for xy in coords])})
            points = [[0,0],[0,h//2],[1,h//2],[2,h//2],[3,h//2],[w//2,h//2]]
            profiles.append({'id':e['id'],'percentage':7,'size':[w,h],
                'input':(e.get('plan') or {}).get('input'), 'profiles':samples,
                'points':[{'xy':xy,'expected':list(ref.getpixel(tuple(xy))),
                           'candidate':list(out.getpixel(tuple(xy)))} for xy in points]})
    discrepancies=repair['discrepancies']
    # Preserve metrics/reasons for all ten cases, but omit unrelated RGB error profiles.
    metrics=[{k:v for k,v in row.items() if k in
              ['id','percentage','reasons','full_image','failing_regions','passing_regions']}
             for row in discrepancies['failed_cases']]
    packet={'developer_guidance':{'focus':'Percentage-7 boundary alpha only',
        'provenance':'Developer-selected scope and supplied analysis; runtime model must produce the patch.',
        'observation':'P7 boundary alpha errors exceed mean 1 on three cases, with max error 2. P1/P3 cases already constrain spread.',
        'uncertainties':'Kernel scale/shape, boundary handling and quantization are hypotheses. No hidden algorithm has been verified.',
        'preserve':'Existing RGB processing, P1/P3 behavior, public interface, validation, domain 0..10, zero setting identity and canonical zero-alpha RGB.',
        'decision':'Choose one small general correction to alpha behavior supported by these profiles. Do not attempt remaining RGB discrepancies.'},
        'contract_claims':[c for c in claims if c['id'] in
            ['boundary_export','kernel_and_parameter_mapping','rounding_precision','matched_edge_height']],
        'scoring':scoring_section(suite),'failed_case_constraints':metrics,
        'passing_case_constraints':discrepancies['passed_cases'],
        'alpha_profiles':profiles,'profile_encoding':"Space-separated byte values; v*n repeats v n times.",
        'developer_selected_evidence':[e['id'] for e in evidence if e.get('selected_by')=='developer'],
        'parameter_domain':[config['percentage_min'],config['percentage_max']],
        'permitted_writes':['src/gaussian-blur.ts'],
        'workspace_operation':{'label':repair['base_label'],'src/gaussian-blur.ts':repair['base_source']}}
    return ('Complete ONE small boundary-alpha repair promptly. The exact operation source is supplied below; '
        'do not reread it unless necessary. Read each relevant file once where practical. '
        'Use only shell_read_file and shell_write_file; no execution, browser, network, delegation or reference files. '
        'Write the complete patched src/gaussian-blur.ts once, then briefly state the change and uncertainty. '
        'No UI, documentation, dependencies or unrelated edits. Preserve applyGaussianBlur(raster: Raster, percentage: number): Raster '
        'and all input validation/domain. No case IDs, fixture outputs or dimension-specific lookup patches. '
        'Build, independent execution, evaluation and regressions belong to trusted host code after completion. '
        'At most '+str(config['builder_tool_calls'])+' tool calls. Packet: '+json.dumps(packet,separators=(',',':')))
