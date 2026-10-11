# miniPaint brightness investigation

This milestone adds a brightness specialization to the existing bounded learning harness.
Gaussian Blur defaults, policies and isolated experimental sources remain unchanged.
Brightness source is generated only by a real restricted runtime invocation, never by the host.

## Verified reference scope

Observed October 10, 2026 in headed Chromium 153.0.8010.12, 1440×1000,
scale 1, en-US, America/Los_Angeles. Visible About 4.14.3, no discrepancy;
hosted build is unpinned. Evidence: `evidence/learning/brightness-preparation/`.

Image → Color Corrections ... opens **Color Corrections** after raster import.
Brightness: integer −100..100, step 1, default/neutral 0. Contrast, Saturation,
Hue, Luminance, Red channel, Green channel and Blue channel are explicitly verified
at zero. Hue domain −180..180, RGB-channel domains −255..255, the other domains
−100..100; each has step 1. These controls are frozen, not reconstructed.

The scope is one imported raster layer in a fresh transparent document at the
input's native dimensions, offset (0,0), rotation 0, opacity 100, resolution 72.
Broader multilayer scope is untested. Each experiment resets, imports through
File → Open → Open File, exports an original confirmation, checks exact decoded
RGBA, applies the settings with visible keyboard actions, then exports a newly
triggered PNG download. Export explicitly chooses PNG and All layers, resolution
72, with no resize. Failed imports support no operation claims.

Two neutral exports reproduced the original and each other exactly; two +17
exports also agreed exactly. The exact RGB/alpha policy was frozen before any
candidate. Zero tolerance, native dimensions, neutral identity and separate RGB
and alpha gates are required. Blur tolerances are never reused or tuned.
A separate import-only probe at alpha 17/128/255 with saturated green/magenta
was exact. This does not establish lossless arbitrary low-alpha color import.

## Architecture and run

`learning/operations.py` declares the operation and candidate interface.
`adapter/brightness.py` extends the existing visible-UI adapter.
`learning/brightness.py` specializes the existing Harness and reuses Budget,
checkpoints, deadline-controlled subprocesses, packet measurement, guidance,
restricted runtime, independent batch worker, RGBA evaluator and exact baselines.
The shared worker selects a registered operation; its blur default is unchanged.
No reference source, bundles, hidden state or network bodies are read.

```powershell
.venv\Scripts\python.exe -m unittest -v test_smoke test_adapter test_shell_boundary test_evaluator test_learning test_brightness
.venv\Scripts\python.exe -m learning.brightness --config brightness.config.json
```

The live command is not an automatic retry: it requires a genuinely absent
`src/brightness.ts` and no existing applyBrightness UI binding. The requested
milestone authorizes one invocation only. At most four runtime-selected fresh
experiments (eight operations including the four preparatory scope/repeat checks),
two candidates, 600 seconds total and a 100-second cleanup reserve. An import-only
probe is separately counted. Existing model/tool deadlines and packet ceilings apply.
No provider fallback, model migration, delegation or automatic second learning run.

Generators cover grayscale/individual-channel ramps, dark/mid/light and clipping
patches, and import-exact partial-alpha colors. Planner supplies questions,
competing hypotheses and predictions before experiments execute. Developer-selected
scope observations are labeled separately. Global guidance id/version/hash and
per-packet selected strategy IDs are recorded; no blur finding enters brightness packets.

Builder writes only main.tsx, brightness.ts and the app README; raster codec and
CSS are read-only. No dependencies/configuration/evaluator/reference-file access
is granted. Existing path, traversal, stream, link/hardlink and tool restrictions
apply. Bounded evidence_read returns only exact admitted visible profiles.
Trusted host processes are not an OS sandbox.

All candidates are checked on the same frozen suite. Build and independent Node
execution are gates; fresh output is scored by the trusted evaluator. The worker
verifies a nonneutral UI export against independent batch output, blocks external
UI requests and checks empty-document disablement. Four original exact shell
regressions must pass. Rejected and partial candidates are saved; the appropriate
checkpoint is restored and rebuilt during cleanup. No blur implementation is
integrated, so its isolated metrics are preserved through unchanged source hashes.

## Artifacts and dashboard integration

`evidence/latest-brightness.json` locates the sole actual attempt. Its report,
events, frozen suite, contracts, candidate checkpoints, model invocation audits,
usage and independent evaluations are the durable records. Expected PNGs and
trusted evaluator files remain outside the builder's source capability.

Dashboard work is separate. Read `evidence/brightness-integration.json` and the
report path it names; display brightness and blur statuses separately. Do not
infer acceptance from build or visual similarity. The JSON describes exported
integration fields without changing the dashboard worktree.

Fresh evaluation is conditional on exact visible acceptance. Freeze source,
contract, suite and policy, then evaluate different inputs/parameters once with
no model/repair access to expected exports. A failing fresh set is not repaired
within this milestone; if later used for repair, it becomes development evidence.
No existing blur holdout is used. Publication is handled separately from learning.

## Final measured outcome

Brightness is usable within the tested scope: six visible and five fresh exact RGBA
cases pass, as do independent execution, UI/batch agreement and four exact baselines.
The sole autonomous run stopped on host integration defects; the unchanged candidate
passed later trusted revalidation with no model calls or implementation repairs.
See [final report](evidence/brightness-results.md) for the distinction, usage and limits.
74 offline tests pass. Blur stays experimental at 5/10 and 7/14; source hashes preserved.

To verify the current implemented app, use
`.venv\Scripts\python.exe baseline_regressions.py --allow-brightness`.
A future clean-start learning invocation still requires brightness to be absent;
the baseline host only allows the Image-menu exception when an implementation exists.

## Committed evidence

The [minimal evidence bundle](evidence/brightness/README.md) contains relocatable input/expected PNGs and reports. Full run archives mentioned above are local-only and are not required to reproduce pixel checks.
