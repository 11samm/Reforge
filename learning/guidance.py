"""Versioned global investigation guidance: loading, deterministic selection and packet sections.

Guidance is target-independent strategy text, never behavior evidence. Selection is ordinary code over
signals derived from the trusted result; the model cannot choose or extend it.
"""
import hashlib
import json
from pathlib import Path
import re

PATH = Path(__file__).resolve().parent / 'investigation-guidance.json'
SCHEMA = 'reforge-investigation-guidance/1'
ROLES = {'planner', 'route'}
TRIGGERS = {'planning', 'infrastructure', 'any_failure', 'behavior_mismatch', 'partial_progress',
            'baseline_regression', 'evaluator_suspect'}
MAX_FILE_BYTES = 8000
MAX_TEXT_CHARS = 260
MAX_SECTION_BYTES = 2600
# Target/operation vocabulary and evidence-ID shapes that would make global guidance a behavior claim.
TARGET_TERMS = re.compile(r'minipaint|gaussian|blur|percentage|sigma|kernel|premultipl', re.I)
EVIDENCE_ID = re.compile(r'\b(?:fresh|dev|gb|precision|exp|resume-fresh)-?\d', re.I)
SECTION_KIND = 'global investigation strategy; not target behavior evidence and not contract claims'


class GuidanceError(ValueError):
    pass


def load(path=PATH):
    path = Path(path); raw = path.read_bytes()
    if len(raw) > MAX_FILE_BYTES: raise GuidanceError('Guidance file exceeds size limit')
    data = json.loads(raw.decode('utf-8'))
    if data.get('schema') != SCHEMA or data.get('scope') != 'global' or not data.get('version'):
        raise GuidanceError('Unsupported guidance schema/scope/version')
    ids = set()
    for s in data['strategies']:
        if set(s) != {'id', 'lesson', 'roles', 'triggers', 'text'} or s['id'] in ids: raise GuidanceError('Invalid strategy entry')
        if not set(s['roles']) <= ROLES or not set(s['triggers']) <= TRIGGERS or not s['roles'] or not s['triggers']:
            raise GuidanceError('Unknown strategy role/trigger: ' + s['id'])
        if len(s['text']) > MAX_TEXT_CHARS: raise GuidanceError('Strategy text too long: ' + s['id'])
        if TARGET_TERMS.search(s['text']) or EVIDENCE_ID.search(s['text']):
            raise GuidanceError('Target-specific term or evidence ID in global guidance: ' + s['id'])
        ids.add(s['id'])
    try: source = path.resolve().relative_to(Path(__file__).resolve().parents[1]).as_posix()
    except ValueError: source = path.name
    return {**data, 'source': source, 'sha256': hashlib.sha256(raw).hexdigest()}


def provenance(guidance):
    return {k: guidance[k] for k in ['id', 'version', 'source', 'sha256']}


def route_signals(result):
    cases = result.get('cases') or []
    failed = [c for c in cases if c.get('status') != 'passed']
    signals = set()
    if result.get('error'): signals.add('infrastructure')
    if result.get('baseline_pass') is False: signals.add('baseline_regression')
    if result.get('evaluator_suspect'): signals.add('evaluator_suspect')
    if failed: signals.add('behavior_mismatch')
    if failed and len(failed) < len(cases): signals.add('partial_progress')
    if signals or not result.get('build_valid') or not result.get('independent'): signals.add('any_failure')
    return signals


def select(guidance, role, signals):
    return [s for s in guidance['strategies'] if role in s['roles'] and set(s['triggers']) & set(signals)]


def section(guidance, role, signals):
    """Compact packet section; raises rather than truncating when over budget."""
    chosen = select(guidance, role, signals)
    out = {'kind': SECTION_KIND, 'guidance': f"{guidance['id']}@{guidance['version']}",
           'sha256_prefix': guidance['sha256'][:12], 'strategies': {s['id']: s['text'] for s in chosen}}
    if len(json.dumps(out, separators=(',', ':')).encode('utf-8')) > MAX_SECTION_BYTES:
        raise GuidanceError(f'{role} guidance section exceeds {MAX_SECTION_BYTES} bytes')
    return out


def prompt_suffix(section_value):
    if not section_value or not section_value['strategies']: return ''
    return (' Investigation guidance (global strategy only; it is not evidence about this target, cite only '
            'exact evidence IDs for behavior): ' + json.dumps(section_value, separators=(',', ':')))
