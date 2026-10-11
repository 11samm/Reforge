"""Versioned evidence-backed specification for one numeric raster adjustment."""
import json
import math
from learning.core import exact, strings, text

SCOPE = 'single-imported-8bit-raster-layer'
ROLES = {'menuitem', 'button', 'slider', 'spinbutton', 'textbox', 'heading'}

def request_id(request):
    if not isinstance(request, str) or request.strip().casefold() != 'implement contrast':
        raise ValueError('Supported request: Implement Contrast. Scope: one imported 8-bit raster layer and numeric image adjustments; other operations are unresolved.')
    return 'contrast'

def number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 10000:
        raise ValueError('Expected finite bounded numeric value')
    return value

def locator(value):
    exact(value, ['by', 'role', 'name'])
    if value['by'] not in ('role', 'label', 'row') or value['role'] not in ROLES:
        raise ValueError('Only visible role, label or labeled row locators supported')
    text(value['name'])
    if len(value['name']) > 160: raise ValueError('Locator name too long')
    return value

def validate(spec, observations=None, ready=False):
    if len(json.dumps(spec, allow_nan=False).encode()) > 24000: raise ValueError('Specification exceeds limit')
    exact(spec, ['schema_version', 'request', 'feature_id', 'target', 'scope', 'navigation', 'dialog', 'controls', 'parameter', 'apply', 'cancel', 'completion', 'import_procedure', 'export_procedure', 'observation_ids', 'hypotheses', 'unresolved', 'status'])
    if type(spec['schema_version']) is not int or spec['schema_version'] != 1 or request_id(spec['request']) != spec['feature_id']: raise ValueError('Unknown specification version/feature')
    exact(spec['target'], ['name', 'visible_version', 'build'])
    for v in spec['target'].values(): text(v)
    if spec['target']['name'] != 'miniPaint' or spec['scope'] != SCOPE: raise ValueError('Unsupported target/scope')
    for key in ('dialog',): text(spec[key])
    if spec['import_procedure'] != 'minipaint.reset-import.v1' or spec['export_procedure'] != 'minipaint.fresh-png.v1': raise ValueError('Unknown trusted IO procedure')
    if spec['completion'] != 'dialog-hidden-and-dimensions-unchanged': raise ValueError('Unknown completion check')
    strings(spec['observation_ids'], 1, 24); strings(spec['hypotheses'], 0, 10); strings(spec['unresolved'], 0, 20)
    if observations is not None and not set(spec['observation_ids']) <= set(observations): raise ValueError('Unknown observation IDs')
    if not isinstance(spec['navigation'], list) or not 1 <= len(spec['navigation']) <= 6: raise ValueError('Navigation limit')
    for action in spec['navigation']:
        locator(action)
        if action['role'] not in ('menuitem','button'): raise ValueError('Navigation only opens visible menus/dialogs')
    locator(spec['apply']); locator(spec['cancel'])
    if spec['apply']['role'] != 'button' or spec['cancel']['role'] != 'button': raise ValueError('Apply/cancel must be buttons')
    if not isinstance(spec['controls'], list) or not 1 <= len(spec['controls']) <= 12: raise ValueError('Control limit')
    names = []
    for c in spec['controls']:
        exact(c, ['label', 'type', 'locator', 'min', 'max', 'step', 'default', 'neutral', 'observation_ids'])
        text(c['label']); names.append(c['label']); locator(c['locator'])
        if c['type'] not in ('slider', 'spinbutton') or c['locator']['role'] != c['type']: raise ValueError('Numeric controls only')
        if c['locator']['name'] != c['label']: raise ValueError('Control locator must identify its observed label')
        strings(c['observation_ids'], 1, 24)
        if not set(c['observation_ids']) <= set(spec['observation_ids']): raise ValueError('Uncited control')
        for k in ('min', 'max', 'step', 'default', 'neutral'):
            if c[k] is not None: number(c[k])
        if None not in (c['min'], c['max'], c['step']):
            if c['min'] >= c['max'] or c['step'] <= 0 or (c['max']-c['min'])/c['step'] > 2000: raise ValueError('Unsupported domain/action count')
            for k in ('default', 'neutral'):
                if c[k] is not None: value_in_domain(c, c[k])
        if ready and any(c[k] is None for k in ('min','max','step','default')): raise ValueError('Missing observed control domain/default')
        if ready and c['label'] != spec['parameter'] and c['neutral'] is None: raise ValueError('Other control neutrality unresolved')
        if ready and c['label'] != spec['parameter'] and c['neutral'] != c['default']: raise ValueError('Only observed defaults can freeze other controls')
    if len(set(names)) != len(names) or spec['parameter'] not in names or spec['parameter'].casefold() != 'contrast': raise ValueError('Ambiguous/missing requested control')
    if spec['status'] not in ('discovered','unresolved','unsupported'): raise ValueError('Unknown discovery status')
    if ready and (spec['status'] != 'discovered' or spec['unresolved']): raise ValueError('Discovery remains unresolved')
    return spec

def parameter(spec):
    return next(c for c in spec['controls'] if c['label'] == spec['parameter'])

def value_in_domain(c, value):
    number(value)
    if any(c[k] is None for k in ('min','max','step')): raise ValueError('Unknown numeric domain')
    n = (value-c['min'])/c['step']
    if not c['min'] <= value <= c['max'] or abs(n-round(n)) > 1e-7: raise ValueError('Value outside observed domain/step')
    return value
