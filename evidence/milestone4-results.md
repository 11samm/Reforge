# Milestone 4: independent deterministic evaluation

October 10, 2026. Completed evaluator and baseline regressions. Stopped before blur,
accept/revert orchestration, autonomous planning or a learning loop. No model requests,
reference-site calls, commits or pushes. No new dashboard or editing UI.

## Deliverables

- `evaluator/compare.py`: reusable Python/Pillow API and CLI, exact raw decoded RGBA
  metrics, dimension gate, explicit named regions, validation and failure reasons.
- `evaluator/policies/exact-rgba-v1.json`: exact baseline acceptance policy.
- `evaluator/policies/blur-provisional-v1.json`: configurable initial RGB/alpha targets,
  explicitly provisional and not established compatibility standards.
- `baseline_regressions.py`: four independent exact gates over fresh shell exports,
  reusing the existing safe isolated current-state mutation fixture.
- `evaluator/examples.py`: reproducible controlled pass/fail reports and artifacts.
- [Instructions and orchestrator interface](../README-evaluator.md).

## Verification results

24 offline tests passed: 16 existing smoke/adapter/boundary tests and 8 evaluator tests.
Includes PNG reencoding/metadata equality, known RGB/alpha errors and artifact samples,
dimension/invalid/missing/16-bit rejection, localized errors and region gates, inclusive
mean/pixel/fraction/alpha tolerance boundaries, invalid policies/regions, no artifact
reuse, infrastructure copy failure classification, and CLI exit codes 0/1/2.
Boundary tests explicitly reject evaluator, policy, expected fixture and baseline paths.
Syntax and CLI help checks passed. Production TypeScript/Vite build passed.

Final fresh baseline: **4/4 pass exact decoded RGBA equality**. Every case has matching
dimensions, RGB per-channel/combined mean and maximum 0, alpha mean/maximum 0,
RGB/alpha fractions 1, and differing-pixel count 0:

- Opaque upload/export: gb017, 129x97 (12,513 pixels).
- Transparent upload/export: gb010, 65x49 (3,185 pixels).
- Replacement: upload opaque then transparent on the same document, one current layer,
  export transparent, 65x49 (3,185 pixels).
- Current-state modification: 4x3 (12 pixels), export exactly equals independently
  constructed expected samples after one known RGB change at (2,1). All alpha and
  the other 11 pixels remain equal; the normal production export action is used.

[Final baseline JSON](baseline-regressions/20261010-111958-b460f848/results.json) ·
[Readable baseline](baseline-regressions/20261010-111958-b460f848/report.md) ·
[Full affected shell checks](baseline-regressions/20261010-111958-b460f848/shell/results.json).
Existing empty/error states, unavailable blur, disabled controls, preview checks,
invisible RGB/partial alpha, JPEG export and no external requests/browser errors passed.
The production test hook is absent. Two preceding successful baseline runs are retained.

Controlled examples: **8/8 expected outcomes** (two tolerance/exact passes and six
deliberate failures). These counts validate the evaluator; they are not blur compatibility.

- Different PNG encoding/metadata, identical samples: exact pass.
- RGB change: per-channel MAE [2,1,0], combined mean 1, max 4, one differing pixel;
  alpha unchanged. Exact failure even though the change is invisible at alpha 0.
- Alpha-only change: RGB error 0, alpha mean 1/max 2, one differing pixel. Exact failure.
- Dimension mismatch: explicit failure, no pixel metrics invented.
- Invalid PNG and missing PNG: distinct output failure classifications.
- Mostly empty 100x100 image with one RGB error 255: provisional whole-image pass
  (mean 0.0085, fraction 0.9999) with raw max 255 still reported. Explicit 1x1 informative
  region fails (mean 85, fraction 0). Full-image metrics remain identical in both cases.

[Controlled JSON](evaluator-examples/20261010-111957-1384f482/results.json) ·
[Readable controlled report](evaluator-examples/20261010-111957-1384f482/report.md).
Raw files, x16 RGB and alpha differences, checkerboard previews and display-only
changed-bounds crops are retained in the corresponding case directories. A sparse RGB
difference was visually inspected: a red changed pixel on opaque black remains visible;
alpha does not mask the raw RGB difference.

## Preserved work and failure history

Generated-app sources/dependencies, builder/model configuration, reference adapter,
original inputs and prepared reference outputs are unchanged. Browser mode/position
checks still pass. No development source import was needed; only the two previously
imported allowed development fixtures were read. Collector/holdout/final_holdout were
not accessed. Evaluator, policies and expectations remain outside the builder allowlist.
The trusted host/build/verification processes remain outside any OS sandbox claim.

Initial baseline `20261010-111703-28e4676d` failed before image checks because a verifier
selector acquired a Unicode encoding error during host integration. The selector was
corrected; that infrastructure failure and all evidence remain, with no reference or
app changes to force a pass. Current baseline reports retain per-case missing-output
results alongside a shell infrastructure error if a future browser run stops early.

## Limits

Single-frame 8-bit RGBA PNG scoring only; native 16-bit/APNG are explicitly rejected.
No color-managed perceptual comparison. Invisible RGB counts in raw metrics. Sparse
whole-image tolerance passes require deliberate named region gates when localized
fidelity matters; diagnostic crops never silently change scoring. Alpha thresholds
are provisional engineering choices. No blur candidate has been evaluated or accepted.
Full parameter coverage, alternate browsers/decoders, larger inputs and OS sandboxing
remain unestablished. Baseline coverage is two selected development inputs plus the
controlled current-state fixture, not whole-application compatibility.
