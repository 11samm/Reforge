# Brightness second-feature milestone — final results

Date: October 10, 2026 (America/Los_Angeles).

**Brightness: usable and verified within the measured scope.** Six visible cases and five fresh cases pass exact decoded RGBA: RGB MAE 0, alpha MAE 0, maximum channel errors 0, no differing pixels. Dimensions and neutral identity pass. Build, independent execution, nonneutral UI/batch agreement, and all four exact baseline regressions pass.
**Gaussian Blur: experimental, not accepted.** Its isolated checkpoint remains 5/10 on the original and 7/14 on the expanded suite. Every declared experimental source hash is preserved. Brightness does not integrate blur. No blur held-out set was accessed.

## Reference operation and workflow

Visible operation: Image → Color Corrections ...; dialog Color Corrections; Brightness integer −100..100, step1, default/neutral0. Contrast, Saturation, Hue, Luminance, Red channel, Green channel and Blue channel are explicitly held at0. See [scope/procedure](../README-brightness.md). About4.14.3, no version discrepancy; hosted build unknown/unpinned. Headed Chromium153.0.8010.12, viewport1440×1000, scale1, en-US, Los Angeles. Only one imported raster layer is verified; no claim about multilayer behavior.
Fresh reset, native dimensions, transparent document, resolution72, layer offset0, rotation0 and opacity100; visible import; original-confirmation PNG export and exact RGBA check; visible parameter actions; Ok; new PNG export with All layers and no resize. No source, bundle, hidden state or network-body inspection.
Two neutral and two +17 repeats agreed exactly; neutral reproduced the input. The exact policy was frozen before candidate evaluation. Zero RGB and alpha tolerance, separate metrics, dimension equality and neutral identity are required. Existing blur policies and all original fixtures remain unchanged.
Partial-alpha import checks passed for the saturated17/128/255 shapes and fresh17/51/85 lattice colors. This establishes import fidelity only for those inputs; arbitrary low-alpha and invisible RGB compatibility is not claimed. No blur finding was used as brightness evidence.

## Sole autonomous attempt and host correction

[Original run](brightness/original-run-report.json) stopped after 180.309 seconds. Four runtime-selected fresh experiments, one implementation candidate, zero automatic retries or second learning run. Runtime: gpt-6.1-sol/medium. Budget600s with100s cleanup reserve, at most2 candidates and4 run reference operations (8 including4 scope/repeat operations). One import-only probe is counted separately. Existing packet ceilings and bounded deadlines remained enforced.
The planner selected −37 clipping patches, +50 individual-channel ramps, +1 fine patches and −50 partial-alpha shapes. Each experiment saved competing hypotheses and numerical predictions before execution. Original-input confirmations all passed. Global guidance version1.0.0 and its SHA256/strategy selections are in run provenance. Developer scope observations are separately labeled.
The restricted runtime wrote the independent brightness operation and UI. It inferred an opaque floor-and-clamp gain rule and a partial-alpha quantization hypothesis. Matching pixels verifies parity on tested cases, not the target’s hidden mechanism. The host did not implement or repair the transformation.
The original run did **not** accept a candidate: the new suite passed an invalid empty region mapping, a host-edit encoding defect corrupted a selector, the worker still selected the blur menu item, and the baseline verifier expected Image to be disabled. The routing response then cited an invalid evidence ID. All six independent output metrics were exactly zero, but these failed gates prevented promotion. The original run restored and rebuilt the no-brightness app with passing baselines.
After the requested pause/resume, host-only corrections supplied a valid named full-image region, selected the registered brightness menu item with correct UTF-8, and added an explicit Image-menu exception plus disabled empty-document brightness checks. All unrelated disabled-control checks and exact baseline expectations stayed intact. The corrected suite has identical input/expected hashes, parameters and exact RGB/alpha policy; the named full region duplicates the original full-image gate. It is an evaluator integration correction, not a tolerance change.
[Trusted revalidation](brightness/visible-report.json) took 11.692 seconds: unchanged candidate, zero model calls, zero new candidates, zero reference operations. All6 visible gates, build, independent execution, UI agreement and4 baselines passed. Original failed records were not rewritten. Future packets now include actual target metadata, bounded routing IDs and valid region maps.
The raw model contract used target_version brightness:1 because the packet omitted reference identity. The [canonical contract](brightness/canonical-contract.json) explicitly records the metadata correction to actual About4.14.3, links the original contract SHA256, and retains its behavior statements/statuses. It also records trusted parity separately. Source, canonical contract, policy and repair-loop closure were frozen before fresh inputs existed.

## Fresh evaluation — evaluated once, no repairs

[Fresh report](brightness/fresh-report.json):5/5 exact cases, 25.802 seconds. New geometries and RGB values, brightness−23,+33,−100,0,+100; partial-alpha lattice colors include17,51,85 and transparent black. Expected exports never entered a model/repair context. No implementation edits or additional model calls followed. This set has not been used for repair and was not the blur final_holdout.
The independently generated candidate remains in main generated-app, identical to its saved candidate checkpoint. The raster codec, CSS, dependencies, configuration and lockfile hashes match the original main checkpoint. The user-approved editor layout is preserved. No dashboard worktree was edited.

## Model usage and stop reason

Provider-reported cumulative usage (cached input included in input; not a cost estimate):
- {"totalTokens": 134571, "inputTokens": 128842, "outputTokens": 5729, "cachedInputTokens": 72960, "reasoningOutputTokens": 1267}
- {"role": "builder-1", "elapsed_seconds": 58.744, "total": {"totalTokens": 98041, "inputTokens": 95251, "cachedInputTokens": 72960, "cacheWriteInputTokens": 0, "outputTokens": 2790, "reasoningOutputTokens": 521}}
- {"role": "contract-1", "elapsed_seconds": 26.725, "total": {"totalTokens": 14651, "inputTokens": 13344, "cachedInputTokens": 0, "cacheWriteInputTokens": 0, "outputTokens": 1307, "reasoningOutputTokens": 191}}
- {"role": "planner", "elapsed_seconds": 33.541, "total": {"totalTokens": 11393, "inputTokens": 9928, "cachedInputTokens": 0, "cacheWriteInputTokens": 0, "outputTokens": 1465, "reasoningOutputTokens": 516}}
- {"role": "route-1", "elapsed_seconds": 7.023, "total": {"totalTokens": 10486, "inputTokens": 10319, "cachedInputTokens": 0, "cacheWriteInputTokens": 0, "outputTokens": 167, "reasoningOutputTokens": 39}}

Model invocations: planner, contract, builder, route. Only one generated candidate. Remaining candidate allowance was unused after the infrastructure stop. Original stop_reason remains procedure_infrastructure_failure; milestone closes after host validation and passing once-only fresh evaluation. No second learning run, provider migration or another feature followed validation.

## Checks and dashboard handoff

74 offline tests pass, including broker boundaries, negative domain validation, alpha generator coverage, exact policy, valid full-region suite construction, target metadata and operation-specific baseline flags. Syntax checks, CLI help and git diff --check pass. CI configuration includes these tests; remote CI status is reported separately after publication.
Dashboard should consume [brightness-integration.json](brightness-integration.json), render brightness and experimental blur separately, and show the original autonomous failure separately from later host validation. Suite hashes, gates, counts, timings, usage, checkpoint and contract paths are explicit. No dashboard source changes were made.

Limits: tested discrete images/parameters, 8-bit PNG, one raster layer, fixed headed browser/version. Hosted build is unpinned. No all-input, multilayer, color-managed,16-bit-operation or whole-editor claim. Builder restriction is a file/tool capability boundary; trusted host is not an OS sandbox.

Full historical run archives and source checkpoints remain local-only. Committed report snapshots label omitted absolute-path artifacts with `local-only:`; these are provenance references, not required checkout files. See [reproduction](brightness/README.md).
