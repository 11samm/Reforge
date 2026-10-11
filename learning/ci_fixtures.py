"""Developer tool: list the saved evidence files test_learning reads, and check that the tests pass from a
clean copy holding only those files (no model requests, no browser). Not an input to any runtime builder.

  python -m learning.ci_fixtures            # rewrite fixtures/learning-ci-files.txt
  python -m learning.ci_fixtures --check    # copy code + listed fixtures elsewhere and run the offline tests
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from adapter.png import ROOT

LIST = ROOT / 'fixtures/learning-ci-files.txt'
HEADER = ('# Saved evidence files read by test_learning (attempt-2 run subset + pre-change prompts). Commit exactly these;\n'
          '# the rest of each run archive stays local. Regenerate the list with: python -m learning.ci_fixtures\n')
TESTS = ['test_smoke', 'test_adapter', 'test_shell_boundary', 'test_evaluator', 'test_learning']
LOCAL_ONLY = ('evidence/learning/', 'evidence/packet-sizes/', 'evidence/milestone5/', 'dev-workspaces/')


def listed():
    from .core import relocate
    names = [line for line in LIST.read_text(encoding='utf-8').splitlines() if line and not line.startswith('#')]
    for name in names:
        if not name.startswith(('evidence/learning/', 'evidence/packet-sizes/')) or '\\' in name:
            raise ValueError('CI fixture must belong to a declared saved-evidence root')
        relocate(name)  # Reject traversal, links, and unrelated filesystem paths before copying.
    if len(names) != len(set(names)):
        raise ValueError('Duplicate CI fixture')
    return names


def record():
    """Runs test_learning in-process and records opened files under evidence/ that git does not track."""
    import unittest
    seen = set()

    def hook(event, args):
        if event != 'open' or not args or not isinstance(args[0], (str, bytes, os.PathLike)): return
        try: rel = Path(os.fsdecode(args[0])).resolve().relative_to(ROOT)
        except (ValueError, OSError): return
        if rel.parts and rel.parts[0] == 'evidence': seen.add(rel.as_posix())
    sys.addaudithook(hook)
    result = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromName('test_learning'))
    if not result.wasSuccessful(): raise SystemExit('test_learning failed; fixture list not written')
    tracked = set(subprocess.run(['git', 'ls-files', 'evidence'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split())
    files = sorted(s for s in seen if s not in tracked and (ROOT / s).is_file()
                   and s.startswith(('evidence/learning/', 'evidence/packet-sizes/')))
    LIST.write_text(HEADER + '\n'.join(files) + '\n', encoding='utf-8')
    print(f'{len(files)} files, {sum((ROOT / f).stat().st_size for f in files)} bytes -> {LIST.relative_to(ROOT)}')


def check():
    """Clean-checkout simulation at a different absolute path: code files plus listed fixtures only."""
    out = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard'], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout.split('\n')
    code = [f for f in out if f and not f.startswith(LOCAL_ONLY) and (ROOT / f).is_file()]
    with tempfile.TemporaryDirectory() as t:
        copy = Path(t) / 'checkout'
        for name in code + listed():
            (copy / name).parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT / name, copy / name)
        run = subprocess.run([sys.executable, '-m', 'unittest', *TESTS], cwd=copy, capture_output=True, text=True)
        print(run.stderr[-3000:])
        if run.returncode: raise SystemExit('Offline tests fail from a clean copy with only the listed fixtures')
        print(json.dumps({'copied_code_files': len(code), 'fixtures': len(listed()), 'path': str(copy)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    check() if parser.parse_args().check else record()


if __name__ == '__main__':
    main()
