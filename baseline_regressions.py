"""Four exact baseline gates, reusing the trusted shell verifier's isolated mutation fixture."""
import json
from pathlib import Path
import time
import uuid
from adapter.png import ROOT
from evaluator.compare import evaluate, load_policy, write_report
import verify_shell


def main():
    run = ROOT / 'evidence/baseline-regressions' / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    run.mkdir(parents=True)
    summary = {'suite_id': 'shell-baseline-v1', 'status': 'failed', 'cases': [],
               'classification': 'infrastructure_error', 'shell_results': str(run / 'shell/results.json')}
    try:
        code = verify_shell.main(run / 'shell')
        shell = json.loads((run / 'shell/results.json').read_text())
        inputs = [('opaque-upload-export', ROOT/'fixtures/development/inputs/gb017.png', run/'shell/gb017-export.png'),
                  ('transparent-upload-export', ROOT/'fixtures/development/inputs/gb010.png', run/'shell/gb010-export.png'),
                  ('replace-uploaded-image', ROOT/'fixtures/development/inputs/gb010.png', run/'shell/replacement-export.png'),
                  ('current-state-modification', run/'shell/current-state-expected.png', run/'shell/current-state-export.png')]
        for case_id, expected, candidate in inputs:
            summary['cases'].append(evaluate(case_id, expected, candidate, run/case_id, load_policy()))
        summary['shell_status'] = shell['status']
        summary['shell_error'] = shell.get('error')
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
    (ROOT / 'evidence/latest-baseline-regressions.json').write_text(json.dumps({'status': summary['status'], 'results': str(run / 'results.json')}, indent=2) + '\n')
    print(json.dumps({'status': summary['status'], 'classification': summary['classification'], 'results': str(run / 'results.json')}))
    return 0 if summary['status'] == 'passed' else 1


if __name__ == '__main__': raise SystemExit(main())
