# Independent Reforge verification — October 10, 2026

Verdict: blocked for the next feature milestone. Offline and preparation checks pass, but the one authorized live attempt timed out before any repaired candidate completed. No blur improvement or acceptance is established.

## Commands actually run

- `.venv\Scripts\python.exe -m unittest -v test_smoke test_adapter test_shell_boundary test_evaluator test_learning`: original 57 tests passed. After hardening, the same suite without `-v` passed 60 tests.
- `.venv\Scripts\python.exe -m learning.ci_fixtures --check`: original 57 and final 60 tests passed in separate temporary checkouts, with 47 listed saved fixtures (406 other code/tracked files). This copies no unlisted learning/packet run archives or development workspace.
- `.venv\Scripts\python.exe -m learning.run --resume-from evidence/learning/20261010T184129Z-78c8e934 --candidate candidate-2 --workspace dev-workspaces/candidate-2 --dev-evidence evidence/learning/20261010T213804Z-09ff82cb-dev-followup --prepare-only`: exit 1, expected harness unresolved status; stop `prepared_only_no_model_request`; preparation succeeded. Model request records: zero. Mocked request assertions also pass.
- `.venv\Scripts\python.exe -m learning.run --resume-from evidence/learning/20261010T184129Z-78c8e934 --candidate candidate-2 --workspace dev-workspaces/candidate-2 --dev-evidence evidence/learning/20261010T213804Z-09ff82cb-dev-followup`: run exactly once; exit 1, unresolved; per-builder 160-second deadline, reported stop `budget_exhausted`; total run 222.39 seconds with 377.61 seconds remaining. No retry.
- `git diff --check`: passed before and after verification.

## Fixes

- Hardened `learning.core.relocate`: reject unrelated paths, traversal, alternate streams, protected split components and links/junctions; mapped paths must stay under evidence/fixtures. Hash checks remain active.
- Validated fixture-list entries before CI copy, restricted them to saved learning/packet evidence roots, and rejected duplicates.
- Added traversal/list regressions and a mocked resume timeout test preserving partial sources, failed candidate records and restoring the experimental base.
- Corrected README packet-limit scope and current offline test count. No evaluator, threshold, reference-output or main app changes.

## Evidence and result

- Candidate 2 reproduces all six historical full-image AND region metrics exactly. Re-evaluated on the same expanded ten-case suite before any repair: four passes, six failures; objective `[6, 1.0212165715638402]`.
- Failing cases: gb010 (full/boundary RGB); fresh-03 (full/center RGB, boundary alpha mean); fresh-04 (full RGB fraction); dev-01 (boundary alpha mean); dev-02 (full/center RGB, boundary alpha mean); dev-04 (full RGB fraction). All metrics/reasons are in results.json and the live resume-base evaluation.
- Preparation contract/route/repair estimates: 18,125 / 14,219 / 23,820 tokens, all within initial-packet ceilings. Developer evidence was accurately labeled raw/unincorporated.
- Live contract-resume preceded the builder and incorporated citations for dev-01, dev-02, dev-04 and dev-06. No claim is VERIFIED_WITHIN_SCOPE.
- Builder used seven allowed reads (one operation-source read and six exact evidence-profile reads), made no writes, then timed out. The partial checkpoint is byte-for-byte the original candidate, not a new repaired implementation. No candidate evaluation exists.
- Contract actual input: 18,181 versus estimate 18,125 (estimate low 0.31%). Builder observed input: 78,677 versus cumulative projection 48,822 (estimate low 37.95%); initial estimate was 24,411. Limits do not cap cumulative actual usage.
- Observed provider usage: 102,028 total tokens, 96,858 input, 5,170 output; 50,560 cached input included in input. Interrupted final-round usage may be missing from telemetry. Remaining supported allowance: 89% five-hour, 72% weekly.
- Final isolated build and all four exact baselines pass. Candidate/base and failed/partial checkpoint records are preserved. All 20 independently captured main-app, evaluator and development fixture hashes remain unchanged; main blur module remains absent.
- Reviewed 72 proposed code/docs/fixture paths; no credential pattern detected and no protected dataset content found. No files are staged. Full run archives and dev-workspaces are local artifacts outside the 47-file CI selection; do not stage the entire untracked tree.
- No miniPaint source/hidden state, collector, holdout or final_holdout was accessed. No smoke.py/live smoke execution, commit or push.

## Exact artifacts

- [Preparation](../learning/20261010T223144Z-35dc162f-dev-resume/report.json)
- [Live report](../learning/20261010T223237Z-e74d8c50-dev-resume/report.json)
- [Events](../learning/20261010T223237Z-e74d8c50-dev-resume/events.jsonl)
- [Updated contract](../learning/20261010T223237Z-e74d8c50-dev-resume/contracts/contract-resume.json)
- [Same-suite base evaluation](../learning/20261010T223237Z-e74d8c50-dev-resume/evaluations/resume-base/evaluation.json)
- [Failed candidate](../learning/20261010T223237Z-e74d8c50-dev-resume/candidates/candidate-1.json)
- [Partial checkpoint](../learning/20261010T223237Z-e74d8c50-dev-resume/checkpoints/candidate-1-partial/manifest.json)
- [Final baselines](../learning/20261010T223237Z-e74d8c50-dev-resume/final/baseline/results.json)
- [Machine-readable independent findings](results.json)

Recommended next milestone: diagnose bounded builder completion and resolve Gaussian Blur parity on this same ten-case visible suite. Keep main generated-app at the no-blur baseline until all gates pass. Verification is complete; no further run started.
