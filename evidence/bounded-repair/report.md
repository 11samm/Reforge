# Bounded blur repair result

Verdict: one completed runtime repair, rejected for compatibility; retained only as an experimental checkpoint. No retry or next milestone was started. Main generated-app remains unchanged.

## Diagnosis and preparation

See [evidence-based diagnosis](diagnosis.md). The old builder made seven successful reads and zero writes before its 160.126-second timeout; the partial snapshot equals candidate 2. Round timings are unavailable. No recorded protocol, validation, output-size or tool failure explains the timeout. Broad assignment/context growth is a possible explanation, not an established cause.

Runtime scope now addresses Percentage-7 boundary alpha only. Developer-selected scope and guidance are labeled in the packet; the runtime authored the patch. Only src/gaussian-blur.ts can be written; current-image.ts can be read for types. Source is supplied once, exact alpha profiles/points are supplied for three P7 cases, all six failing-case metrics/reasons and four passing constraints are retained. No evidence-read tool, UI/docs/dependency edits, handwritten blur repair, planner call or reference collection. Prior completed aligned contract and exact frozen ten-case suite are reused after hash/content/citation/policy/region validation.

Budgets: builder remains 160 seconds; total 600 -> 360 seconds; reserve stays 100; candidates 3 -> 1; builder calls 12 -> 4; evidence reads 6 -> 0. Other limits, provider, parameter domain and headed defaults are unchanged. Packet 43,364 -> 20,866 bytes; estimated initial input 24,411 -> 14,422 tokens. No deadlines increased.

63 offline tests and the isolated 47-fixture CI checkout pass. Fixtures verify narrowed broker permissions, actual resume timeout forwarding, packet scope, mismatch rejection, checkpoint recovery and acceptance isolation. Final preparation sent zero model requests and passed baseline/independent gates.

## One live attempt

Run `20261010T224627Z-c87f41fb-dev-resume`: 73.443 seconds overall, 41.256 builder seconds; completed. One successful write, zero reads, no runtime errors. Exactly one model invocation. No planning, contract update, reference collection or retry.

Actual provider usage: 33,156 total tokens; 31,066 input (including 14,336 cached); 2,090 output (including 516 reasoning output). Cumulative projected input was 28,844, 7.15% below observed usage. Token ceilings still measure initial packets rather than cumulative usage.

The runtime added a Percentage-7 alpha lift tapered by lost kernel coverage and alpha density, capped at two bytes. RGB uses its original denominator. This is a fitted observational correction, not a verified hidden algorithm or evidence of generalization to untested settings.

## Same-suite trusted results

Exact frozen suite SHA-256: `970c46192c2b2227dca077e33a3f6623e3ec46727e13037d28b068b6f0d49501`. Same policy, full-image gates and two regions per case. Build, independent execution, UI/batch agreement and all four exact baselines pass before/after and on final restored experimental state. All ten RGB byte arrays are unchanged.

Passes 4/10 -> 5/10. Objective [6, 1.0212165715638402] -> [5, 1.0212165715638402]; failed-case count improves, secondary worst-region loss is unchanged.

- gb017: passed -> passed; boundary alpha MAE 0.265464 -> 0.265464.
- gb010: failed -> failed; boundary alpha MAE 0.153061 -> 0.153061.
- fresh-01: passed -> passed; boundary alpha MAE 0.010204 -> 0.010204.
- fresh-02: passed -> passed; boundary alpha MAE 0.280612 -> 0.280612.
- fresh-03: failed -> failed; boundary alpha MAE 1.056122 -> 0.301020.
- fresh-04: failed -> failed; boundary alpha MAE 0.000000 -> 0.000000.
- dev-01: failed -> passed; boundary alpha MAE 1.219231 -> 0.234615.
- dev-02: failed -> failed; boundary alpha MAE 1.219231 -> 0.234615.
- dev-04: failed -> failed; boundary alpha MAE 0.295455 -> 0.295455.
- dev-06: passed -> passed; boundary alpha MAE 0.107143 -> 0.107143.

All three targeted boundary-alpha gates now pass. Remaining failures: gb010 full/boundary RGB; fresh-03 and dev-02 full/center RGB; fresh-04 and dev-04 full RGB fraction. All four previously passing cases remain passing. Compatibility requires every visible gate, so acceptance is rejected unchanged.

## Preservation and next action

39 protected files match their run-start hashes, including main-app files, trusted code, evaluator/policies and original development inputs/outputs. Candidate 2, the prior failed/partial snapshot, this completed rejected candidate, its source journal and evaluations remain preserved. Only the operation source differs between candidate checkpoints. The workspace was restored to the improved experimental checkpoint, not an accepted state. No commit or push.

Experimental checkpoint: `D:\Samuel\Downloads\Code\Reforge\evidence\learning\20261010T224627Z-c87f41fb-dev-resume\checkpoints\experimental-base-1`. Main app has no promoted blur implementation.

Concrete next action: separately authorize one Percentage-7 RGB repair targeting fresh-03/dev-02 using existing edge/impulse quantization evidence, preserving this experimental alpha correction and the ten-case suite. No additional work was launched.

## Artifacts

[Detailed paired metrics and regressions](results.json); [runtime patch](runtime-patch.diff); [live report](../learning/20261010T224627Z-c87f41fb-dev-resume/report.json); [invocation and audit](../learning/20261010T224627Z-c87f41fb-dev-resume/model/builder-1/invocation.json); [repair packet](../learning/20261010T224627Z-c87f41fb-dev-resume/packets/builder-1.json); [candidate evaluation](../learning/20261010T224627Z-c87f41fb-dev-resume/evaluations/candidate-1/evaluation.json); [completed rejected snapshot](../learning/20261010T224627Z-c87f41fb-dev-resume/checkpoints/candidate-1/manifest.json); [experimental snapshot](../learning/20261010T224627Z-c87f41fb-dev-resume/checkpoints/experimental-base-1/manifest.json); [preparation](preparation.json); [configuration](config.json).
