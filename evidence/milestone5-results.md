# Milestone 5: bounded autonomous Gaussian Blur learning

October 10, 2026. The integrated learning harness is implemented and exercised.
Blur compatibility remains unresolved, so **no candidate was promoted**. The app
is restored to its genuine no-blur starting state, with exact source hashes,
production build and all four exact baseline regressions passing. No push, other
operation, final holdout, or whole-editor claim.

## Runnable harness

```powershell
Set-Location 'D:\Samuel\Downloads\Code\Reforge'
.venv\Scripts\python.exe -m learning.run
```

[Instructions and actual autonomy](../README-learning.md) ·
[Configuration](../learning.config.json) ·
[Aggregate machine-readable summary](milestone5/summary.json).

The verified runtime is unchanged: local Codex app-server, `gpt-6.1-sol`, medium,
managed ChatGPT Plus sign-in, no provider fallback or API-key authentication.
The sequential trusted host validates the planner, generates bounded diagnostic
PNGs, drives the headed reference procedure, verifies an original-input export,
stores actual reference PNGs, updates structured claims, runs restricted builder
turns, builds independently, evaluates frozen visible cases, runs exact baselines
and restores only generated sources. There are no parallel agents or open-ended
unattended loops. The builder has only allowlisted file tools; the host is not an
OS sandbox.

## Every real attempt

**Attempt 1 — 117.7 seconds, four fresh reference experiments, no candidate.**
The planner selected center/boundary impulses at Percentage 2 and opaque/alpha
patterns at Percentage 7. Reset, original import/export confirmation, accepted
parameters and actual reference exports all succeeded. Two question descriptions
did not match their selected fixed generator: the boundary impulse was the left
midpoint rather than a corner, and alpha used three bands rather than hidden blue.
The exported samples accurately recorded the executed inputs. The model then
returned explanatory sentences in evidence-ID fields. Trusted contract validation
rejected the response; it was never admitted as a valid contract. The no-blur
checkpoint was restored, rebuilt, and passed all exact baselines.

[Preserved attempt report](learning/20261010T183813Z-8b39a334/report.md) ·
[Rejected contract invocation](learning/20261010T183813Z-8b39a334/model/contract-1/invocation.json).

Between attempts, the host supplied exact generator definitions and restricted
claim/evidence/case references to enums of known IDs. No reference expectation or
scoring threshold changed.

**Attempt 2 — 508.5 seconds, four fresh reference experiments, three builder turns.**
The model selected a center impulse at Percentage 1, a left-boundary impulse at 3,
an opaque edge at 7, and partial-alpha bands at 3. All four procedures succeeded
with exact requested/accepted integers and original-import confirmation. These
experiments added actual new information beyond prepared gb010/gb017: low-setting
activation, boundary coverage loss, a higher-setting edge profile and color/alpha
transitions. The accepted contract retained supported observations, mechanism
hypotheses and unknown rounding; no claim was marked VERIFIED_WITHIN_SCOPE.

The six-case visible suite froze the two prepared development cases plus those
four fresh exports, existing `blur-provisional-v1`, exact baseline policy and fixed
center/left-boundary region gates **before candidate comparison**. No suite
expansion occurred in this attempt; both failure-route decisions selected repair.

[Integrated attempt report](learning/20261010T184129Z-78c8e934/report.md) ·
[Contract](learning/20261010T184129Z-78c8e934/contracts/contract-1.json) ·
[Frozen suite](learning/20261010T184129Z-78c8e934/suites/visible-blur-v1.json).

- **Candidate 1:** production build and input-only Node batch execution succeeded,
  including three denied network probes. Three of six blur cases passed. The UI
  and baseline verifier stopped because they expected accessible `Percentage:`
  while the new control was labeled `Percentage`. This infrastructure selector
  failure establishes no baseline pixel regression. It was rejected and restored.
- **Candidate 2:** build, independent guarded batch execution, actual production
  UI Blur/export agreement and all four exact baseline regressions passed. Three
  of six blur cases passed; the remaining gates failed on genuine pixel errors.
  It is the first independently executable feasible blur candidate, **not an
  accepted compatibility implementation**. It was rejected and restored.
- **Candidate 3:** its turn reached the learning-work deadline at 500 seconds,
  preserving the 100-second cleanup reserve. It did not complete or receive an
  evaluation; no success or improvement is assigned. Final build/baseline cleanup
  finished at 508.5 seconds. Stop reason: budget exhausted.

First acceptance: **none**. Later improvements: **none**. The objective retains
ties and permits promotion only after valid build/output, independent execution,
all exact baselines and every frozen blur/region gate. A rejected candidate never
replaced the best checkpoint.

[Candidate 1 blur metrics](milestone5/candidate-1-blur-report.md) ·
[Candidate 2 blur metrics](milestone5/candidate-2-blur-report.md) ·
[Candidate 2 complete evaluation](learning/20261010T184129Z-78c8e934/evaluations/candidate-2/evaluation.json) ·
[Candidate 2 source checkpoint](learning/20261010T184129Z-78c8e934/checkpoints/candidate-2/manifest.json) ·
[Best no-blur checkpoint](learning/20261010T184129Z-78c8e934/checkpoints/no-blur-start/manifest.json).

## Precise unresolved behavior

Candidate 2 passes gb017 and both impulse probes. Its full-image RGB MAE is
0.0671 on gb017, 0.000628 on the Percentage-1 center impulse, and 0.001256 on the
Percentage-3 boundary impulse. All alpha maxima in those comparisons are <=1.

The transparent gb010 case fails RGB mean/fraction gates: mean 1.6612 and only
94.16% of pixels within tolerance 3; its left-boundary RGB mean is 3.7925.
The Percentage-7 edge fails full-image/center RGB and boundary-alpha mean gates:
center RGB mean 3.8182, center sample 135 versus actual reference 130.
The partial-alpha bands fail the RGB fraction gate: 97.02% within tolerance 3
against the frozen 99% requirement. Large low-alpha RGB errors remain despite
small alpha deltas. These observations do not establish one hidden algorithm.
Precision, quantization/pass ordering, low-alpha color conversion and the
higher-percentage spatial response remain unresolved.

Useful future experiments would compare a Percentage-7 centered impulse with the
same-setting edge, test uniform low-alpha colors/nonzero invisible RGB, and vary
small odd dimensions. Those experiments were **not** run. Broader parameters,
large images, other browsers and zero-setting identity remain unverified.

## Artifact and telemetry limits

Both runs retain events, prompts, concise model outputs, usage, tool audits,
requested/accepted parameters, screenshots, action records, actual reference PNGs,
sample evidence, policy/suite hashes, candidate 1/2 source snapshots and independent
evaluations. The reference controller closes before candidate execution. Candidate
2's batch uses only inputs and bundled independent code; its normal editor export
exactly matches the batch result. External UI HTTP requests are blocked and recorded.
No reference source, bundle, source map, hidden state or response body was read.

Available runtime totals across both attempts: **1,313,222 total tokens**,
1,293,764 input, 19,458 output; 903,552 cached input is included in input. Reasoning
token telemetry is a count only; raw reasoning is not stored. These are usage
observations, not an invoice or dollar estimate. Repeated large packets made the
first live builders expensive; the current host losslessly compresses profile
runs and omits irrelevant evaluation paths from repair packets.

Two historical record details are documented rather than rewritten:
candidate 1's `independent=false` also reflects the subsequent UI-selector failure,
although its batch had succeeded; the unavailable incumbent's `[0,255]` objective
was a bookkeeping sentinel, not scored pixels or passing blur cases. The current
host separates batch independence, UI validity and infrastructure failure, and
leaves unavailable output unscored.

Candidate 3's final incomplete operation hash/tool audit survived, but its last
partial operation text was lost during restore. The supplemental early source
audit contains baseline files and is explicitly provisional; it is not presented
as the missing completed candidate. The current host now journals every permitted
write and snapshots partial failures before restore. It also archives trusted
source/policy versions for future runs. These fixes were verified with clearly
labeled controlled fixtures, without launching another live learning trajectory.

## Final validation and preservation

**38 offline tests pass**, including schema/domain/budget checks, evidence/claim
references, source-capability restrictions, same-suite acceptance/ties, controlled
accept/reject/timeout orchestration, rollback integrity, partial-write journaling,
lossless profile compression and trusted-code provenance. Existing 24 tests remain
passing. Syntax/help checks and `git diff --check` pass. The final restored app
passes production TypeScript/Vite build and all four exact baseline cases.

[Post-run exact baseline](learning/post-run-validation/baseline/results.json) ·
[Post-run readable baseline](learning/post-run-validation/baseline/report.md).

Generated-app source hashes match the starting checkpoint exactly. Original
development PNGs, evaluator and policy files have no diff. Layout, upload/export,
current-state export and the unavailable blur UI remain preserved. Headed reference
viewport is still 1440x1000 at scale 1; validated optional position (1600,0) was used.
Hosted About version was 4.14.3; exact build remains unknown/unpinned. Builder
boundaries remain allowlisted tools and application/process restrictions, with no
OS sandbox claim. Collector, holdout and final_holdout were not accessed.
