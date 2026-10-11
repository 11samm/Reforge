"""Compare a portable presentation with its untouched source job/archive, without models."""
import argparse, hashlib, json
from pathlib import Path


def verify(repo, archive, job, bundle):
    envelope = json.loads(bundle.read_text(encoding='utf8'))
    manifest = json.loads(envelope['manifest'])
    assert hashlib.sha256(envelope['manifest'].encode()).hexdigest() == envelope['manifest_sha256']
    events = [json.loads(line) for line in (archive / 'events.jsonl').read_text().splitlines()]
    for candidate in manifest['candidates']:
        original = next(e['result'] for e in events if e['event'] == 'evaluation' and e['label'] == candidate['id'])
        for actual, expected in zip(candidate['cases'], original['cases'], strict=True):
            for key in ['metrics', 'regions', 'dimensions', 'dimensions_equal', 'status', 'classification', 'reasons']:
                assert actual.get(key) == expected.get(key), (candidate['id'], key)
        for key in ['build_valid', 'independent', 'baseline_pass']:
            assert candidate.get(key) == original.get(key)
    for baseline in manifest['baselines']:
        original = json.loads((archive / baseline['label'] / 'baseline/results.json').read_text())
        for actual, expected in zip(baseline['cases'], original['cases'], strict=True):
            assert actual['metrics'] == expected['metrics']
    final = json.loads((job / 'final-summary.json').read_text())
    for actual, expected in zip(manifest['recording']['final']['cases'], final['cases'], strict=True):
        assert actual['metrics'] == expected['metrics']
    state = json.loads((repo / 'evidence/feature-jobs' / manifest['run']['id'] / 'job.json').read_text())
    assert [(e['sequence'], e['elapsed_seconds']) for e in manifest['events']] == [(e['sequence'], e['elapsed_seconds']) for e in state['events']]
    totals = manifest['recording']['usage_totals']
    # Original invocation order differs from final job summary order. Compare actual counts as a multiset.
    assert sorted(t['usage']['total_tokens'] for t in manifest['telemetry']) == sorted(u['total']['totalTokens'] for u in totals)
    assert not any(marker in envelope['manifest'] for marker in ['D:\\\\Samuel', '"thread_id"', '"prompt"', '"answer"'])
    return dict(feature=manifest['run']['operation'].lower(), job=manifest['run']['id'], bundle_bytes=bundle.stat().st_size,
                bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(), events=len(manifest['events']), assets=len(envelope['assets']),
                original_metrics_and_checks='exact equality', original_job_sequence_and_timing='exact equality',
                invocation_total_tokens=sum(t['usage']['total_tokens'] for t in manifest['telemetry']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ['repo', 'archive', 'job', 'bundle']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.repo, args.archive, args.job, args.bundle), indent=2))
