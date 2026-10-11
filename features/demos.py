"""No-model prepared editors and immutable, sandboxed interactive previews."""
import re
import shutil
import time
import uuid
from pathlib import Path
from adapter.png import ROOT
from learning.core import digest
from .presentation import safe_file, read, atomic


def validate(request, ident, record):
    from .spec import request_id
    if not re.fullmatch('[a-f0-9]{32}', ident): raise ValueError('Invalid demo')
    app = ROOT / 'dev-workspaces' / ('feature-' + ident)
    if record.get('feature') != request_id(request) or record.get('app') != str(app) or record.get('model_invoked') is not False or record.get('target_absent') is not True:
        raise ValueError('Demo provenance differs')
    actual = {p.relative_to(app).as_posix() for p in app.rglob('*') if p.is_file() and not {'node_modules', 'dist'}.intersection(p.relative_to(app).parts) and p.name != 'start-manifest.json'}
    if actual != set(record['files']): raise ValueError('Prepared editor file set changed')
    for name, expected in record['files'].items():
        if digest(safe_file(app, name)) != expected: raise ValueError('Prepared editor changed')
    return app


class Demos:
    def __init__(self, directory):
        self.directory = Path(directory); self.directory.mkdir(parents=True, exist_ok=True)
    def get(self, ident):
        if not re.fullmatch('[a-f0-9]{32}', ident): raise ValueError('Invalid demo')
        value = read(self.directory, ident + '/demo.json')
        if not value or value.get('id') != ident: raise ValueError('Unknown demo')
        return value
    def list(self):
        return sorted([self.get(p.parent.name) for p in self.directory.glob('*/demo.json')], key=lambda x: x['created'], reverse=True)[:30]
    def prepare(self, request):
        from .preparation import prepare
        ident = uuid.uuid4().hex
        app, record = prepare(request, ident)
        root = self.directory / ident; root.mkdir()
        value = {'id': ident, 'request': request, 'created': time.time(), 'preparation': record, 'preview_status': 'building', 'model_invoked': False}
        atomic(root / 'demo.json', value)
        # Fixed trusted build, no package scripts or model/browser invocation.
        try:
            from learning.worker import build
            build(root, app)
            self.snapshot(root, app, ident)
            value.update(preview_status='ready', preview_url=f'/api/jobs/demos/{ident}/preview/index.html')
        except Exception as e:
            value.update(preview_status='failed', preview_error=str(e)[:1500])
        atomic(root / 'demo.json', value)
        return value
    @staticmethod
    def snapshot(root, app, ident):
        target = root / 'preview'; target.mkdir(exist_ok=True)
        files = {}
        for p in sorted((app / 'dist').rglob('*')):
            if not p.is_file(): continue
            name = p.relative_to(app / 'dist').as_posix()
            source = safe_file(app / 'dist', name)
            if source.suffix not in ('.html', '.js', '.css', '.png', '.svg', '.woff2') or source.stat().st_size > 20 * 1024 * 1024: continue
            destination = safe_file(target, name); destination.parent.mkdir(parents=True, exist_ok=True)
            if name == 'index.html':
                destination.write_text(source.read_text(encoding='utf-8').replace('"/assets/', '"./assets/'), encoding='utf-8')
            else: shutil.copyfile(source, destination)
            files[name] = digest(destination)
        if 'index.html' not in files: raise ValueError('No built editor')
        atomic(root / 'preview-manifest.json', {'job_id': ident, 'files': files})
    @staticmethod
    def preview_file(root, ident, name):
        manifest = read(root, 'preview-manifest.json') or {}
        if manifest.get('job_id') != ident or name not in manifest.get('files', {}): raise ValueError('Unknown preview artifact')
        path = safe_file(root / 'preview', name)
        if digest(path) != manifest['files'][name]: raise ValueError('Preview artifact changed')
        return path


def accepted_preview(store, ident):
    job = store.get(ident)
    if job['status'] != 'accepted' or job.get('promoted') is not False: raise ValueError('Accepted isolated candidate required')
    root = store.directory / ident
    if not (root / 'preview-manifest.json').exists():
        return {'job_id': ident, 'status': 'missing', 'reason': job.get('preview_error','Accepted build preview was not recorded')}
    return {'job_id': ident, 'status': 'ready', 'url': f'/api/jobs/{ident}/preview/index.html', 'scored': False, 'label': 'Interactive exploration; uploads are not scored acceptance evidence. No promotion or merge.'}
