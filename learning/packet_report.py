"""Offline packet-size report from saved evidence: historical prompts, pre-change host and current host.

No model requests. Estimates use learning.packets.ESTIMATOR and include fixed instructions, output
schemas and the source files a builder is instructed to read (supplied tool responses).
"""
import argparse
import copy
import json
from pathlib import Path
from adapter.png import ROOT
from .core import DEFAULTS, Budget, relocated
from . import packets
from .run import CLEAN, RESUME, Harness

SOURCE = ROOT / 'evidence/learning/20261010T184129Z-78c8e934'
PRECHANGE = ROOT / 'evidence/packet-sizes/prechange-prompts'
OUT = ROOT / 'evidence/packet-sizes'
HISTORICAL = {'planner': 'planner', 'contract': 'contract-1', 'route': 'route-2', 'builder': 'builder-1', 'repair': 'builder-3'}


def reads(directory):
    return {n: (directory / n).read_text(encoding='utf-8') for n in ['src/main.tsx', 'src/current-image.ts']}


def source_harness(config):
    h = object.__new__(Harness)
    h.config = config; h.budget = Budget(config); h.directory = SOURCE; h.mode = CLEAN
    h.evidence = []; h.prepared()
    for i in range(1, 5): h.evidence.append(relocated(json.loads((SOURCE / f'experiments/fresh-0{i}/evidence.json').read_text())))
    h.claims = json.loads((SOURCE / 'contracts/contract-1.json').read_text())['claims']
    h.suite = json.loads((SOURCE / 'suites/visible-blur-v1.json').read_text())
    h.suite['cases'] = [relocated(row) for row in h.suite['cases']]
    h.incumbent = None; h.first_acceptance = None; h.base_result = None; h.base_label = None
    h.app = SOURCE / 'checkpoints/no-blur-start'; h.best = h.app
    return h


def current_packets(config):
    evaluation = json.loads((SOURCE / 'evaluations/candidate-2/evaluation.json').read_text())
    # Historical host lacked ui_valid; its recorded ui_check shows UI/batch export agreement.
    evaluation = {**evaluation, 'ui_valid': bool(evaluation.get('ui_check'))}
    route2 = json.loads((SOURCE / 'model/route-2/invocation.json').read_text())['answer']
    h = source_harness(config); out = {}
    out['planner'] = (packets.planner_prompt(config, h.guidance_section('planner', {'planning'}, 'planner')),
                      __import__('learning.model').model.PLANS, {})
    out['contract'] = (h.contract_packet(), h.contract_schema(), {})
    prompt, schema = h.route_request(evaluation, 'candidate-2'); out['route'] = (prompt, schema, {})
    _, prompt, supplied, _, _ = h.builder_request(1, None); out['builder'] = (prompt, None, supplied)
    previous = {'evaluation': evaluation, 'label': 'candidate-2', 'routing_suggestion': route2,
                'rejected_operation_source': (SOURCE / 'checkpoints/candidate-2/src/gaussian-blur.ts').read_text(encoding='utf-8'),
                'note': 'Rejected workspace restored; repair must regenerate from best-known state.'}
    _, prompt, supplied, _, _ = h.builder_request(3, previous); out['repair_clean_mode'] = (prompt, None, supplied)
    r = source_harness(config); r.mode = RESUME; r.app = r.best = SOURCE / 'checkpoints/candidate-2'
    r.base_result = evaluation; r.base_label = 'candidate-2'
    previous = {**previous, 'note': 'Development resume from saved rejected candidate-2; the workspace contains it as the experimental base.'}
    _, prompt, supplied, _, _ = r.builder_request(1, previous); out['repair'] = (prompt, None, supplied)
    return out


def measured(role, prompt, schema, supplied):
    m = packets.measure(role, prompt, schema, supplied)
    return {k: m[k] for k in ['bytes', 'estimated_tokens', 'expected_tool_rounds', 'projected_cumulative_input_tokens']} | {
        'parts': {k: v['bytes'] for k, v in m['parts'].items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'learning.config.json')
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    no_blur = reads(SOURCE / 'checkpoints/no-blur-start')
    report = {'method': packets.ESTIMATOR, 'source_run': SOURCE.name, 'model_requests': 0,
              'limits': config['packet_limits'], 'builder_tool_calls': config['builder_tool_calls'],
              'evidence_reads': config['evidence_reads'], 'roles': {}}
    current = current_packets(config)
    for role in ['planner', 'contract', 'route', 'builder', 'repair']:
        row = {}
        request = json.loads((SOURCE / 'model' / HISTORICAL[role] / 'request.json').read_text())
        invocation = json.loads((SOURCE / 'model' / HISTORICAL[role] / 'invocation.json').read_text())
        supplied = no_blur if role in ['builder', 'repair'] else {}
        usage = invocation.get('usage') or {}
        row['historical'] = measured(role, request['prompt'], request['output_schema'], supplied) | {
            'invocation': 'model/' + HISTORICAL[role], 'actual_total_input_tokens': usage.get('total', {}).get('inputTokens'),
            'actual_last_round_input_tokens': usage.get('last', {}).get('inputTokens'),
            'actual_tool_calls': len(invocation.get('audit') or []), 'saved_packet_file_bytes': None}
        if role in ['builder', 'repair']:
            name = {'builder': 'candidate-1', 'repair': 'candidate-3'}[role]
            row['historical']['saved_packet_file_bytes'] = (SOURCE / 'packets' / (name + '.json')).stat().st_size
        pre = PRECHANGE / ({'repair': 'builder-repair', 'builder': 'builder-initial'}.get(role, role) + '.json')
        if pre.exists():
            d = json.loads(pre.read_text())
            row['prechange_host'] = measured(role, d['prompt'], d.get('schema', d.get('output_schema')), supplied)
        prompt, schema, supplied_now = current[role]
        row['current_host'] = measured(role, prompt, schema, supplied_now)
        row['current_host']['within_limits'] = (row['current_host']['bytes'] <= config['packet_limits'][role]['bytes'] and
                                                row['current_host']['estimated_tokens'] <= config['packet_limits'][role]['tokens'])
        if role == 'repair':
            prompt, schema, supplied_clean = current['repair_clean_mode']
            row['current_host_clean_mode_repair'] = measured(role, prompt, schema, supplied_clean)
        report['roles'][role] = row
    latest = ROOT / 'evidence/latest-learning-dev-resume.json'
    if latest.exists():
        run = Path(json.loads(latest.read_text())['report']).parent
        sizes = json.loads((run / 'packet-sizes.json').read_text())['packets']
        report['latest_dev_resume_packets'] = {'run': run.name, 'packets': [
            {k: p[k] for k in ['label', 'role', 'bytes', 'estimated_tokens', 'projected_cumulative_input_tokens', 'within_limits', 'dry_run']}
            for p in sizes]}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    lines = ['# Model packet sizes (offline, no model requests)', '', 'Estimator: ' + packets.ESTIMATOR, '',
             'Each figure is one request context: instructions + payload + output schema + source files the builder is told to read. '
             '"Projected cumulative" multiplies by expected tool rounds (builder 6, repair 2, decisions 1). '
             'Historical "actual" columns are recorded runtime usage from attempt 2.', '',
             '| Role | Historical bytes / est. tokens (actual) | Pre-change host | Current host | Limit bytes / tokens |',
             '|---|---|---|---|---|']
    for role, row in report['roles'].items():
        h, c, lim = row['historical'], row['current_host'], config['packet_limits'][role]
        actual = h['actual_last_round_input_tokens']
        pre = row.get('prechange_host')
        lines.append(f"| {role} | {h['bytes']:,} / {h['estimated_tokens']:,} ({actual:,} last round; {h['actual_total_input_tokens']:,} total) | "
                     + (f"{pre['bytes']:,} / {pre['estimated_tokens']:,}" if pre else 'n/a') +
                     f" | {c['bytes']:,} / {c['estimated_tokens']:,} | {lim['bytes']:,} / {lim['tokens']:,} |")
    lines += ['', 'Clean-mode repair (workspace restored to no-blur; builder must re-read integration files): '
              f"{report['roles']['repair']['current_host_clean_mode_repair']['bytes']:,} bytes / "
              f"{report['roles']['repair']['current_host_clean_mode_repair']['estimated_tokens']:,} est. tokens.",
              f"Builder tool calls capped at {config['builder_tool_calls']} (was 24); evidence_read calls capped at {config['evidence_reads']}."]
    if 'latest_dev_resume_packets' in report:
        lines += ['', f"Actual next packets measured by the prepare-only development resume {report['latest_dev_resume_packets']['run']} "
                  '(10-case expanded suite, no model request):', '']
        lines += [f"- {p['label']} ({p['role']}): {p['bytes']:,} bytes / {p['estimated_tokens']:,} est. tokens; "
                  f"projected cumulative {p['projected_cumulative_input_tokens']:,}; within limits: {p['within_limits']}"
                  for p in report['latest_dev_resume_packets']['packets']]
    (OUT / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({r: {k: v['bytes'] for k, v in row.items() if isinstance(v, dict) and 'bytes' in v} for r, row in report['roles'].items()}, indent=1))
    return 0


if __name__ == '__main__': raise SystemExit(main())
