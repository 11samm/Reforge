"""Four exact baseline gates, reusing the trusted shell verifier's isolated mutation fixture."""
import argparse
import json
from pathlib import Path
import time
import uuid
from adapter.png import ROOT
from evaluator.compare import evaluate, load_policy, write_report
import verify_shell


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--allow-blur', action='store_true', help='Blur UI implemented; empty document must still disable it')
    parser.add_argument('--allow-brightness',action='store_true',help='Brightness enables Image; empty operation controls must remain disabled')
    parser.add_argument('--app', type=Path, help='Isolated dev-workspaces/<name> app root; default generated-app')
    args=parser.parse_args()
    from adapter.png import within
    from learning.core import resolve_app
    app = resolve_app(args.app) if args.app else None
    run = within(args.output, ROOT/'evidence') if args.output else ROOT / 'evidence/baseline-regressions' / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    run.mkdir(parents=True)
    summary = {'suite_id': 'shell-baseline-v1', 'status': 'failed', 'cases': [], 'app': str(app or ROOT / 'generated-app'),
               'classification': 'infrastructure_error', 'shell_results': str(run / 'shell/results.json')}
    try:
        code = verify_shell.main(run / 'shell', allow_blur=args.allow_blur, app=app, allow_brightness=args.allow_brightness)
        shell = json.loads((run / 'shell/results.json').read_text())
        inputs = [('opaque-upload-export', ROOT/'fixtures/development/inputs/gb017.png', run/'shell/gb017-export.png'),
                  ('transparent-upload-export', ROOT/'fixtures/development/inputs/gb010.png', run/'shell/gb010-export.png'),
                  ('replace-uploaded-image', ROOT/'fixtures/development/inputs/gb010.png', run/'shell/replacement-export.png'),
                  ('current-state-modification', run/'shell/current-state-expected.png', run/'shell/current-state-export.png')]
        for case_id, expected, candidate in inputs:
            summary['cases'].append(evaluate(case_id, expected, candidate, run/case_id, load_policy()))
        summary['shell_status'] = shell['status']
        summary['shell_error'] = shell.get('error')
        summary['shell_diagnostic'] = shell.get('diagnostic')
        if code or shell['status'] != 'passed':
            summary['classification'] = shell.get('classification', 'infrastructure_error')
            summary['reason'] = 'Shell verification stopped; missing downstream exports do not establish pixel behavior. See shell_error and per-case evidence.'
        else:
            summary['status'] = 'passed' if all(c['status'] == 'passed' for c in summary['cases']) else 'failed'
            summary['classification'] = 'match' if summary['status'] == 'passed' else 'regression_failure'
        write_report(summary['cases'], run/'report.md')
    except Exception as error:
        summary['reason'] = f'{type(error).__name__}: {error}'
    (run / 'results.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    if app is None: (ROOT / 'evidence/latest-baseline-regressions.json').write_text(json.dumps({'status': summary['status'], 'results': str(run / 'results.json')}, indent=2) + '\n')
    print(json.dumps({'status': summary['status'], 'classification': summary['classification'], 'results': str(run / 'results.json')}))
    return 0 if summary['status'] == 'passed' else 1


if __name__ == '__main__': raise SystemExit(main())
