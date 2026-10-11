# Fresh Brightness through feature discovery

The feature pipeline now accepts `Implement Brightness` in addition to
`Implement Contrast`. Requests remain bounded to one imported 8-bit raster layer
and one numeric image adjustment. Arbitrary feature discovery is not supported.

## Starting state and memory

`features.preparation.prepare()` creates a new `dev-workspaces/feature-<id>/`
directory. It copies only the upload/export shell, codec, styles, dependencies and
fixed build configuration. Brightness uses the reviewed
`features/templates/brightness/main.tsx`, with Image disabled and an unavailable
Brightness message. No learned Brightness or Contrast module is copied.

Preparation saves a start manifest with source hashes and disclosed memory policy.
It never overwrites the stable generated editor or previous workspaces. Reusing an
existing ID fails instead of resetting it.

Fresh Brightness discovery uses empty job-local procedural memory and a new
interaction map. It does not recall old shared harness patches. Its builder has
only allowlisted candidate source tools and evidence from this run; previous
Brightness code, contracts, experiments, procedures, and expected fixtures are
not readable through that capability. Shared trusted import/export procedures,
codec/scaffold, general guidance configuration and model pretraining remain.
This is not a knowledge-free model or a memory ablation benchmark.

The internal base harness still calls the isolated-workspace mode
`development_resume`. Provenance separately records fresh discovery/experiments,
target absence and no saved target evidence. No `--resume-job` is used for these
demonstrations.

Contrast also starts without Contrast, even after its accepted implementation is
promoted into the canonical editor. It retains established Brightness and its
regression gate.

## Commands

Run from the worktree root with Python from the existing Reforge virtualenv.

```powershell
# Budget/request inspection only: no model or browser invocation.
python -m features.pipeline --request "Implement Brightness"

# Creates an isolated source workspace and prints its path/manifest. No models.
python -m features.pipeline --prepare-demo --request "Implement Brightness"

# Build that printed workspace and preview it to inspect the missing operation.
npm.cmd --prefix "<printed app path>" run build
npm.cmd --prefix "<printed app path>" run preview -- --port 5182

# Explicit bounded learning run; consumes the configured subscription allowance.
python -m features.pipeline --pilot --request "Implement Brightness"
```

CLI pilots create a new independent workspace; CLI `--prepare-demo` remains a
separate preview/preflight and is not resumed by `--pilot`. The dashboard's
**Prepare fresh Brightness demo** creates and builds an isolated editor without
models. **Learn Brightness** submits the selected prepared-demo ID. The service
checks its starting source hashes and exact file set, uses that same workspace and
ID for fresh discovery/learning, and rejects changed or previously used demos.
Learning still requires the existing explicit pilot-enable gate and budgets.
See [live results integration](live-results-ui.md) for API and replay contracts.

## Execution and evaluation

The run discovers visible menu/dialog controls, grounds their domains/defaults in
current observations, verifies diagnostic default identity and two fresh-document
replays, then chooses fresh experiments. The candidate is implemented from this
run's evidence and evaluated independently with exact RGBA and UI/batch agreement.
Original shell regressions remain mandatory. The discovered numeric domain is
used; the older supplied Brightness procedure is not the reference executor.

Frozen controls are checked against current defaults and domain attributes, left
untouched, then checked again after changing the requested parameter. This avoids
unnecessary slider actions without relaxing postconditions or scoring.

Fresh final cases are collected once after model repairs finish. Final outputs
remain outside builder context. Acceptance retains an isolated candidate and does
not automatically replace the canonical editor.

## Validation

- Fresh shell build and original exact baseline gates passed.
- Isolation tests cover contaminated prior source/memory, unchanged canonical
  files, duplicate IDs, builder path restrictions and discovered-domain dispatch.
- A browser regression test verifies frozen controls are untouched and changed
  domains still stop execution.
- Saved Contrast and Brightness integration checks can be repeated without models:

```powershell
python verify_adjustments.py --contrast-archive "<original accepted Contrast archive>"
python baseline_regressions.py --allow-brightness --output "evidence/learning/offline-feature-baselines-<unique name>"
```

## Run records

The first fresh Brightness attempt, job `de3c5c64f434456eae1e3a904c10759a`, stopped
unresolved after 172.417 seconds. Discovery, default identity and both procedure
replays passed. Two experiments were admitted; experiment three failed while
redundantly setting the Green-channel frozen default. No candidate or final
evaluation occurred. The isolated starting editor was restored and baseline gates
passed. Original events, requests and results remain local and unchanged.

The subsequent host fix is a developer change between runs, not an autonomous
repair within the first run. Success and timing of later runs must be reported
separately. One successful run does not establish reliable sub-five-minute timing.

The second attempt, job `69730c0aeaa64b10a8e03aaa1b84f8eb`, stopped unresolved
after 288.171 seconds. Discovery/replay and three fresh experiments succeeded.
Candidate one matched the pixel cases but failed UI/baseline checks after changing
an existing preview label and disabling the empty-document operation menu.
Candidate two was rejected because its model invocation attempted a read of the
target module after restoration had removed it. The capability-denial policy was
preserved. No final evaluation occurred; restoration and baseline gates passed.

Before the third fresh attempt, the builder prompt was clarified to preserve
accessible labels, keep the empty-document menu openable while operation controls
are disabled, and avoid reading a missing target module. These are declared shell
requirements, not changes to numerical criteria or expected fixtures. The earlier
experiments and patches were not supplied to the new run.

The third attempt, job `82b68e6daf5e41ddb7c03c13a91ba1f9`, was accepted after
297.460 seconds (4 minutes 57.46 seconds), without manual intervention during
execution. It discovered the procedure, passed diagnostic identity and two
replays, collected four fresh experiments, rejected candidate one and accepted
candidate two through automatic repair. All four visible cases and both once-only
fresh final cases passed exact RGBA with zero differing pixels. UI/batch agreement
and original editor baselines passed. No harness repair was used during this run.

The accepted candidate remains isolated at
`dev-workspaces/feature-82b68e6daf5e41ddb7c03c13a91ba1f9/`; its learning archive is
`evidence/learning/20261011T183641Z-73504a72-dev-resume/`. Its job artifacts are
`evidence/learning/feature-82b68e6daf5e41ddb7c03c13a91ba1f9/`.

Five model invocations used 409,928 total tokens: 402,821 input (including 297,088
cached input) and 7,107 output. These are actual reported usage counts, not a dollar
estimate. The canonical editor was not replaced by this newly generated candidate.

All three attempt summaries are committed in
`evidence/brightness-discovery-20261011/attempts.json`. Two unresolved attempts
preceded the success, with developer host/prompt fixes between runs. This is one
sub-five-minute success, not three repeatable successes or a controlled comparison
with the earlier three-minute Brightness system. Rehearsals of the unchanged final
configuration are still needed before relying on a live demo.
