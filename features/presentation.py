"""Read-only presentation copies. No model capability reads this directory."""
import hashlib
import json
import os
import re
import shutil
import time
import uuid
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from adapter.png import ROOT
from learning.core import save, digest


def safe_file(root, name):
    root = Path(root)
    if not isinstance(name, str) or '\\' in name or ':' in name:
        raise ValueError('Relative paths required')
    parts = PurePosixPath(name)
    if parts.is_absolute() or '..' in parts.parts or str(parts) != name:
        raise ValueError('Invalid artifact path')
    target = root / name
    for node in [target, *target.parents]:
        if node.is_symlink() or (hasattr(node, 'is_junction') and node.is_junction()):
            raise ValueError('Linked artifacts forbidden')
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('Artifact escapes root')
    if target.exists() and target.stat().st_nlink > 1:
        raise ValueError('Hard linked artifacts forbidden')
    return target


@contextmanager
def snapshot_access(path):
    if os.name != 'nt':
        yield
        return
    import msvcrt
    # Reader and publisher are different processes. Locks stay in scratch,
    # outside raw archives and immutable preview inventories.
    directory = ROOT / '.scratch/presentation-locks'
    directory.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(str(path.resolve()).casefold().encode()).hexdigest()
    with (directory / (key + '.lock')).open('a+b') as lock:
        if os.fstat(lock.fileno()).st_size == 0:
            lock.write(b'0'); lock.flush()
        deadline = time.monotonic() + 2
        while True:
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.monotonic() >= deadline: raise TimeoutError('Presentation snapshot busy')
                time.sleep(.005)
        try: yield
        finally:
            lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def atomic(path, value):
    # Windows readers can briefly hold a file without delete sharing. Keep the
    # previous complete snapshot readable and retry only the atomic replacement.
    # Separate writers must never share a temporary file. Failed writes retain
    # their temporary snapshot as evidence, rather than overwriting the old one.
    temp = path.with_suffix('.' + uuid.uuid4().hex + '.tmp')
    save(temp, value)
    with snapshot_access(path):
        for delay in (0, .01, .02, .04, .08, .16):
            if delay: time.sleep(delay)
            try:
                os.replace(temp, path)
                return
            except PermissionError:
                if delay == .16: raise


def read(root, name):
    p = safe_file(root, name)
    with snapshot_access(p):
        return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else None


def clean(value):
    from .jobs import scrub
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if k not in ('prompt', 'requests', 'actions', 'audit', 'execution', 'app', 'reference_path', 'candidate_path', 'output_path', 'input', 'expected')}
    if isinstance(value, list): return [clean(v) for v in value]
    return scrub(value) if isinstance(value, str) else value


def publish(job_root, archive, events=()):
    """Called by the trusted harness, with its own archive; never accepts API paths."""
    job_root, archive = Path(job_root), Path(archive)
    ident = job_root.name.removeprefix('feature-')
    if not re.fullmatch('[a-f0-9]{32}', ident): raise ValueError('Invalid presentation job')
    output = job_root / 'presentation'; output.mkdir(exist_ok=True)
    assets = output / 'assets'; assets.mkdir(exist_ok=True)
    allowed = {}
    def artifact(label, path=None):
        missing = {'label': label, 'status': 'missing', 'reason': 'Not yet produced or not recorded'}
        if path is None: return missing
        path = Path(path)
        try:
            relative = path.relative_to(archive).as_posix()
            source = safe_file(archive, relative)
            if not source.is_file() or source.suffix != '.png' or source.stat().st_size > 20 * 1024 * 1024: return missing
            key = hashlib.sha256((ident + '\0' + relative).encode()).hexdigest() + '.png'
            target = safe_file(assets, key)
            shutil.copyfile(source, target)
            allowed[key] = digest(target)
            return {'id': key, 'label': label, 'status': 'available', 'url': f'/api/jobs/{ident}/artifacts/{key}'}
        except (ValueError, OSError): return missing
    experiments = []
    for p in sorted((archive / 'experiments').glob('*/preregistered.json')):
        case = p.parent.name
        if not re.fullmatch('[A-Za-z0-9_-]+', case): continue
        plan = read(archive, f'experiments/{case}/preregistered.json')
        evidence = read(archive, f'evidence/{case}.json') or {}
        experiments.append({'id': case, 'plan': {**clean(plan), 'input': clean(plan.get('input'))}, 'artifacts': [artifact('Input', archive / 'inputs' / (case + '.png')), artifact('Reference output', Path(evidence['expected']) if evidence.get('expected') else archive / 'experiments' / case / 'output.png')]})
    candidates = []
    for p in sorted((archive / 'evaluations').glob('*/evaluation.json')):
        label = p.parent.name
        if not re.fullmatch('[A-Za-z0-9_-]+', label): continue
        result = read(archive, f'evaluations/{label}/evaluation.json')
        cases = []
        for row in result.get('cases', []):
            case = row.get('case_id', '')
            if not re.fullmatch('[A-Za-z0-9_-]+', case): continue
            base = archive / 'evaluations' / label / 'evaluation' / case
            cases.append({**clean(row), 'artifacts': [artifact(title, base / filename) for title, filename in [('Reference output', 'reference-raw.png'), ('Candidate output', 'candidate-raw.png'), ('RGB difference ×16', 'rgb-difference-x16.png'), ('Alpha difference ×16', 'alpha-difference-x16.png')]]})
        logs = {}
        for name in ('typecheck.log', 'build.log', 'batch-build.log', 'batch-execution.log'):
            path = safe_file(archive, f'evaluations/{label}/{name}')
            if path.is_file(): logs[name] = clean(path.read_text(encoding='utf-8')[-8000:])
        baseline = read(archive, f'{label}-gates/baseline/results.json')
        candidates.append({'id': label, 'result': clean({k: v for k, v in result.items() if k != 'cases'}), 'cases': cases, 'logs': logs, 'baseline': clean(baseline), 'brightness_regression': clean(read(archive, f'brightness-regression/{label}/result.json'))})
    atomic(output / 'manifest.json', {'job_id': ident, 'assets': allowed})
    atomic(output / 'results.json', {'schema_version': 1, 'job_id': ident, 'experiments': experiments, 'candidates': candidates, 'events': clean(list(events)), 'report': clean(read(archive, 'report.json'))})


def results(job_root, ident):
    value = read(Path(job_root) / 'presentation', 'results.json')
    if value and value.get('job_id') != ident: raise ValueError('Cross-job evidence')
    return value or {'schema_version': 1, 'job_id': ident, 'experiments': [], 'candidates': [], 'report': None, 'events': []}


def asset(job_root, ident, name):
    if not re.fullmatch('[a-f0-9]{64}\\.png', name): raise ValueError('Unknown artifact')
    root = Path(job_root) / 'presentation'
    manifest = read(root, 'manifest.json') or {}
    if manifest.get('job_id') != ident or name not in manifest.get('assets', {}): raise ValueError('Artifact not in this job')
    path = safe_file(root / 'assets', name)
    if digest(path) != manifest['assets'][name]: raise ValueError('Artifact changed')
    return path
