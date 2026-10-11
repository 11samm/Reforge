import hashlib
import json
from pathlib import Path
import shutil
import time

STATUSES = ['UNKNOWN', 'HYPOTHESIS', 'OBSERVED', 'VERIFIED_WITHIN_SCOPE', 'CONTRADICTED']
ROUTES = ['procedure_infrastructure', 'missing_evidence_or_hypothesis', 'implementation_defect',
          'evaluator_defect', 'baseline_regression', 'ambiguous_budget_exhausted']
KINDS = ['impulse_center', 'impulse_boundary', 'edge', 'gradient', 'checkerboard', 'rgb', 'alpha']

def save(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'Expected integer in {low}..{high}')
    return value

def text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 3000:
        raise ValueError('Expected bounded nonempty text')

def exact(obj, fields):
    if not isinstance(obj, dict) or set(obj) != set(fields):
        raise ValueError('Unexpected schema fields')

def strings(values, minimum=0, maximum=20):
    if not isinstance(values, list) or not minimum <= len(values) <= maximum:
        raise ValueError('Invalid bounded list')
    for value in values: text(value)
    if len(set(values)) != len(values): raise ValueError('Duplicate list entries')

PACKET_ROLES = ['planner', 'contract', 'route', 'builder', 'repair']
DEFAULTS = {'fresh_experiments': 12, 'candidates': 3, 'run_seconds': 600,
            'reserve_seconds': 100, 'model_seconds': 120, 'builder_seconds': 160,
            'reference_seconds': 60, 'command_seconds': 60, 'retries': 0,
            'percentage_min': 0, 'percentage_max': 10, 'window_position': [1600, 0],
            'builder_tool_calls': 12, 'evidence_reads': 6,
            'packet_limits': {'planner': {'bytes': 8000, 'tokens': 11000},
                              'contract': {'bytes': 40000, 'tokens': 26000},
                              'route': {'bytes': 32000, 'tokens': 22000},
                              'builder': {'bytes': 60000, 'tokens': 30000},
                              'repair': {'bytes': 60000, 'tokens': 30000}}}

def validate_config(c):
    exact(c, DEFAULTS)
    for k, bounds in {'fresh_experiments':(1,20), 'candidates':(1,5), 'run_seconds':(120,600),
                      'reserve_seconds':(30,180), 'model_seconds':(10,180), 'builder_seconds':(10,240),
                      'reference_seconds':(10,120), 'command_seconds':(10,120), 'retries':(0,1),
                      'percentage_min':(0,50), 'percentage_max':(0,50),
                      'builder_tool_calls':(2,24), 'evidence_reads':(0,12)}.items(): integer(c[k], *bounds)
    if c['percentage_min'] > c['percentage_max'] or c['reserve_seconds'] >= c['run_seconds']:
        raise ValueError('Invalid domain or reserve')
    p = c['window_position']
    if p is not None:
        if not isinstance(p, list) or len(p) != 2: raise ValueError('Invalid window position')
        for v in p: integer(v,-32768,32767)
    exact(c['packet_limits'], PACKET_ROLES)
    for role in PACKET_ROLES:
        exact(c['packet_limits'][role], ['bytes', 'tokens'])
        integer(c['packet_limits'][role]['bytes'], 1000, 400000)
        integer(c['packet_limits'][role]['tokens'], 1000, 200000)
    if c['evidence_reads'] >= c['builder_tool_calls']: raise ValueError('Evidence reads must leave builder file-tool calls')
    return dict(c)

def resolve_app(path):
    """Builds/gates may target the main generated app or an isolated development workspace only."""
    from adapter.png import ROOT
    app = Path(path).resolve()
    if app == (ROOT / 'generated-app').resolve(): return app
    workspaces = (ROOT / 'dev-workspaces').resolve()
    if app.parent != workspaces: raise ValueError('App root must be generated-app or dev-workspaces/<name>')
    for node in [Path(path), *Path(path).parents]:
        if node.is_symlink() or (hasattr(node, 'is_junction') and node.is_junction()):
            raise ValueError('App root cannot contain links or junctions')
    return app

RELOCATABLE = ('evidence', 'fixtures')
RECORD_PATHS = ('input', 'expected', 'procedure_record')

def relocate(path):
    """Saved records hold absolute paths from the checkout that wrote them; map evidence/ and fixtures/ paths
    onto this checkout so committed fixtures verify on any machine (hashes are still checked by callers)."""
    from pathlib import PurePosixPath, PureWindowsPath
    from adapter.png import ROOT
    text_path = str(path)
    pure = PureWindowsPath(text_path) if '\\' in text_path or ':' in text_path[:3] else PurePosixPath(text_path)
    parts = pure.parts
    for i, part in enumerate(parts):
        if part in RELOCATABLE:
            suffix = parts[i:]
            if any(p in ('..', '.') or ':' in p or p.casefold() in
                   ('collector', 'holdout', 'final_holdout') for p in suffix):
                raise ValueError('Invalid recorded evidence/fixture path')
            root = ROOT / part
            target = ROOT.joinpath(*suffix)
            for node in [target, *target.parents]:
                if node.is_symlink() or (hasattr(node, 'is_junction') and node.is_junction()):
                    raise ValueError('Recorded paths cannot contain links or junctions')
            target = target.resolve()
            if not target.is_relative_to(root.resolve()):
                raise ValueError('Recorded path escapes evidence/fixture root')
            return str(target)
    raise ValueError('Recorded path must belong to evidence or fixtures')


def relocated(record):
    """Copy of an evidence or suite-case record with its file paths mapped by relocate()."""
    return {**record, **{k: relocate(record[k]) for k in RECORD_PATHS if isinstance(record.get(k), str)}}

def validate_plan(p, c):
    exact(p, ['question','hypotheses','input','percentage','predictions','usefulness'])
    for key in ['question','usefulness']: text(p[key])
    strings(p['hypotheses'],2,5); strings(p['predictions'],2,5)
    exact(p['input'], ['kind','width','height'])
    if p['input']['kind'] not in KINDS: raise ValueError('Unknown generator')
    for k in ['width','height']: integer(p['input'][k],3,257)
    if p['input']['width'] * p['input']['height'] > 66049: raise ValueError('Input area too large')
    integer(p['percentage'], c['percentage_min'], c['percentage_max'])
    return p

def validate_claims(claims, evidence_ids, case_ids, accepted=(), domain=(0,50)):
    if not isinstance(claims, list) or not 1 <= len(claims) <= 16: raise ValueError('Invalid claims')
    ids=[]
    for claim in claims:
        exact(claim,['id','statement','status','target_version','setup','parameter_domain','scope',
                     'supporting_evidence','contradicting_evidence','alternatives','unresolved','verification_cases'])
        for k in ['id','statement','target_version','setup','scope']: text(claim[k])
        ids.append(claim['id'])
        if claim['status'] not in STATUSES: raise ValueError('Unknown claim status')
        exact(claim['parameter_domain'],['min','max'])
        integer(claim['parameter_domain']['min'],*domain); integer(claim['parameter_domain']['max'],*domain)
        if claim['parameter_domain']['min'] > claim['parameter_domain']['max']: raise ValueError('Invalid claim domain')
        for k in ['supporting_evidence','contradicting_evidence','alternatives','unresolved','verification_cases']:
            strings(claim[k])
        if not set(claim['supporting_evidence'] + claim['contradicting_evidence']) <= set(evidence_ids):
            raise ValueError('Claim cites unknown evidence')
        if not set(claim['verification_cases']) <= set(case_ids): raise ValueError('Claim cites unknown case')
        if claim['status'] in ['OBSERVED','VERIFIED_WITHIN_SCOPE'] and not claim['supporting_evidence']:
            raise ValueError('Observation requires evidence')
        if claim['status'] == 'CONTRADICTED' and not claim['contradicting_evidence']:
            raise ValueError('Contradiction requires evidence')
        if claim['status'] == 'VERIFIED_WITHIN_SCOPE' and (not claim['verification_cases'] or
                not set(claim['verification_cases']) <= set(accepted)):
            raise ValueError('Trusted verification cases have not passed; model confidence is insufficient')
    if len(set(ids)) != len(ids): raise ValueError('Duplicate claim IDs')
    return claims

class Budget:
    def __init__(self, config, clock=time.monotonic):
        self.config, self.clock, self.start = validate_config(config), clock, clock()
        self.experiments = self.candidates = 0

    def remaining(self): return max(0, self.config['run_seconds'] - (self.clock() - self.start))

    def timeout(self, seconds, cleanup=False):
        available = self.remaining() - (0 if cleanup else self.config['reserve_seconds'])
        if available < 1: raise TimeoutError('Learning budget reserved for final evaluation and cleanup')
        return min(seconds, available)

    def spend(self, kind):
        field, limit = ('experiments','fresh_experiments') if kind == 'experiment' else ('candidates','candidates')
        if getattr(self,field) >= self.config[limit]: raise TimeoutError(kind+' count budget exhausted')
        self.timeout(1)
        setattr(self,field,getattr(self,field)+1)

    def snapshot(self):
        return {'remaining_seconds':round(self.remaining(),3),
                'fresh_experiments_remaining':self.config['fresh_experiments']-self.experiments,
                'candidates_remaining':self.config['candidates']-self.candidates}

class Checkpoints:
    """Copies only declared generated sources; never restores evidence or trusted code."""
    def __init__(self, app, directory, names):
        self.app, self.directory, self.names = Path(app), Path(directory), tuple(sorted(names))
        self.directory.mkdir(parents=True, exist_ok=True)

    def snapshot(self, name):
        from build_shell import FileBroker
        broker = FileBroker(self.app, self.directory)
        broker.files = set(self.names)
        target = self.directory / name
        target.mkdir(exist_ok=False)
        files={}
        for n in self.names:
            p=broker.path(n)
            if p.exists():
                dst=target/n; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(p,dst)
                files[n]=digest(p)
        save(target/'manifest.json', {'files':files,'scope':list(self.names)})
        return target

    def restore(self, checkpoint):
        from build_shell import FileBroker
        m=json.loads((Path(checkpoint)/'manifest.json').read_text())
        if m['scope'] != list(self.names): raise ValueError('Checkpoint scope mismatch')
        # Validate every source and destination before mutating any file.
        broker=FileBroker(self.app,self.directory); broker.files=set(self.names)
        for n,h in m['files'].items():
            if n not in self.names or digest(Path(checkpoint)/n) != h: raise ValueError('Corrupt checkpoint')
        targets={n:broker.path(n,True) for n in self.names}
        for n,p in targets.items():
            if n in m['files']:
                p.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(Path(checkpoint)/n,p)
            elif p.exists(): p.unlink()

def objective(results):
    """Smaller is better. Equal case weight; worst region participates in each case."""
    if not results: return None  # Unavailable operation has no pixel score.
    failed=sum(r['status'] != 'passed' for r in results)
    losses=[]
    for r in results:
        all_m=[r.get('metrics'), *[v['metrics'] for v in r.get('regions',{}).values()]]
        losses.append(max(((3*m['rgb_mae']+m['alpha_mae'])/4 for m in all_m if m),default=255))
    return [failed, sum(losses)/len(losses) if losses else 255]

def decide(candidate, incumbent=None):
    if candidate.get('evaluator_suspect'): return False,'evaluator_defect'
    if candidate.get('procedure_failure'): return False,'procedure_infrastructure'
    if not candidate.get('build_valid') or not candidate.get('independent'): return False,'implementation_defect'
    if not candidate.get('baseline_pass'): return False,'baseline_regression'
    if not candidate.get('ui_valid',True): return False,'implementation_defect'
    if not candidate.get('cases') or any(r['status']!='passed' for r in candidate['cases']):
        return False,'missing_evidence_or_hypothesis'
    if incumbent is not None:
        if candidate['suite_sha256'] != incumbent['suite_sha256']: raise ValueError('Compare the same frozen suite')
        if objective(candidate['cases']) >= objective(incumbent['cases']): return False,'tie_or_no_improvement'
    return True,'all_gates_pass'
