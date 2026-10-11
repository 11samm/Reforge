"""Trusted isolated starting editors; this module never calls a model or reference."""
import re
import shutil
from adapter.png import ROOT
from learning.core import digest, save
from .spec import request_id

COMMON = ('index.html', 'package.json', 'package-lock.json', 'tsconfig.json',
          'vite.config.ts', 'src/style.css', 'src/current-image.ts')

def prepare(request, ident):
    feature = request_id(request)
    if not re.fullmatch(r'[a-f0-9]{32}', ident): raise ValueError('Invalid demo ID')
    app = ROOT/'dev-workspaces'/('feature-'+ident)
    app.mkdir(parents=True, exist_ok=False)
    canonical = ROOT/'generated-app'
    for name in COMMON:
        target = app/name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(canonical/name, target)
    shutil.copyfile(ROOT/'features/templates'/feature/'main.tsx', app/'src/main.tsx')
    # Contrast preserves accepted Brightness as a regression baseline. Fresh
    # Brightness contains no learned feature source, procedure, or evidence.
    if feature == 'contrast': shutil.copyfile(canonical/'src/brightness.ts', app/'src/brightness.ts')
    (app/'README.md').write_text('Isolated '+feature+' demo starting shell. Target operation is absent.\n', encoding='utf-8')
    if (canonical/'node_modules').is_dir(): shutil.copytree(canonical/'node_modules', app/'node_modules')
    files = {p.relative_to(app).as_posix():digest(p) for p in app.rglob('*') if p.is_file() and 'node_modules' not in p.parts}
    record = {'feature':feature, 'app':str(app), 'target_absent':not (app/'src'/ (feature+'.ts')).exists(),
              'files':files, 'memory':{'prior_target_code':False, 'prior_target_contracts':False,
              'prior_target_experiments':False, 'prior_target_procedures':False if feature=='brightness' else 'configured shared discovery routes may be available',
              'discovery_memory':'job-local empty' if feature=='brightness' else 'configured shared memory',
              'shared_io_procedures':True, 'general_investigation_guidance':True,
              'model_pretraining':'unchanged; not knowledge-free'}, 'model_invoked':False}
    save(app/'start-manifest.json', record)
    return app, record
