# miniPaint adapter milestone

Deterministic reference replay only. The working `smoke.py` Codex integration is
unchanged. No model requests are used for browser actions. A standalone editor shell was added
in milestone 3; see README-shell.md. No blur implementation, candidate evaluator,
dashboard, or learning loop is included.

## Setup and validation

From `D:\Samuel\Downloads\Code\Reforge`:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-adapter.txt
.venv\Scripts\python.exe -m playwright install chromium
.venv\Scripts\python.exe -m adapter.validate
```

The default is **headed Chromium**, 1440x1000, device scale 1, en-US, Los Angeles
timezone. One controller owns each browser session. The batch runs exactly two
selected development cases three times each, sequentially, with a fresh browser
session/document for every run. It also saves an initial interface observation.
Exit 0 requires six exact reference matches and decoded repeat agreement; exit 1
reports infrastructure failures, reference mismatches, or repeat disagreements.
`evidence/latest-batch.json` points to the current batch's `summary.json`.

Ordinary actions have 8-second timeouts; navigation/launch 30 seconds, file chooser
5 seconds, download event 15 seconds. The parent limits each controller to 120
seconds and terminates its process tree on timeout. `--case-timeout` permits
30â€“180 seconds. No arbitrary sleeps, model actions, or open-ended retries.

## Separated workspaces

- `generated-app/`: independently runnable generated React editor shell.
- `adapter/`: reference adapter, PNG integrity/comparison, and bounded batch runner.
- `fixtures/development/`: only gb010 and gb017, their original PNG pairs and metadata.
- `evidence/`: layout observations, run records, screenshots, and result summaries.
- `.scratch/`: existing model smoke artifacts and fresh selector-discovery work.
- `.venv/`: local dependencies, outside all future generated-code boundaries.

`workspaces.json` declares these roots. The shell builder has no environment tools
and uses an allowlisted read/write file broker. Layout packet files are read-only;
links, junctions, hard links, traversal and other server requests are rejected.
This is a tool capability restriction, not an OS sandbox for the trusted host.
Build and browser verification run separately outside the coding-agent invocation.

## Adapter API and verified procedure

`adapter.minipaint.MiniPaintAdapter` provides `reset_reference(document_setup)`,
`import_image(input_path)`, `apply_operation(parameters)`, `export_png(output_path)`,
`capture_screenshot(output_path)`, and `run_experiment(case)`.
`capture_initial_interface()` and `read_visible_dom(output_path)` provide bounded
layout observations (48,000 accessibility characters and 250 visible controls).

Replay uses the visible File â†’ New dialog for matching dimensions and transparency,
then Fit to refresh the rendered Information panel. It verifies resolution 72.
Import uses File â†’ Open â†’ Open File; it verifies one imported layer, matching
width/height, offset (0,0), rotation 0, and opacity 100. An extra fresh PNG export
must exactly reproduce the original decoded input **before** blur is applied.

The operation is Effects â†’ Common Filters â†’ **Gaussian Blur ...**, dialog **Blur**,
control **Percentage**. Keyboard slider actions set the integer UI value, verify
the control and displayed number, then accept it. Completion requires dialog closure
and the visible Blur layer label. Percentage is not interpreted as a pixel radius.

Exports explicitly select PNG and All layers, confirm resolution 72 and no resize
controls, then wait for a newly triggered download. The requested unique filename
must match that download. Saved PNGs are decoded, dimension-checked, and hashed.
Existing output paths are rejected. Run records include UTC timestamps, case ID,
requested/accepted parameters, target identity, action statuses, hashes, errors,
original-input confirmation, and exact prepared-reference comparison.

Only rendered screenshots, visible DOM/accessibility, user input actions, and
user-visible exports are observed. No source, bundles, source maps, application
objects, canvas pixels, network response bodies, HARs, or browser traces are read.

## Recovery

Inspect the failed run's `report.json`, incremental `actions.json`, failure screenshot,
visible-DOM JSON, and `worker.log`. Original failures and partial artifacts are retained.
Auto import permits at most two routes: file chooser, then a fresh reset and the
visible Open Data URL dialog. The Data URL is made only from the allowed original
fixture. Both routes were independently exercised successfully during development.
To select the alternate route explicitly for a six-run batch:

```powershell
.venv\Scripts\python.exe -m adapter.validate --import-route data_url
```

After fixing a selector or infrastructure issue, rerun to get a new batch directory.
Never replace expected PNGs to make comparison pass. A reference mismatch is a
reference/environment/setup observation, not proof of a generated implementation bug.
If neither import route works, keep diagnostics and stop before changing targets.
`--headed` explicitly selects the supported default for debugging/presentation.
`--headless` is explicitly unverified for reference equivalence and diagnostic only: milestone 3 found reproducible exact RGBA
mismatches in all six runs, while a fresh headed rerun passed all six. Do not have another controller or human edit the
reference window during a run.

## Observed results and limits

See `evidence/milestone2-results.md` and the linked six-run JSON summary. About version
4.14.3 matched the collected version in every run. Hosted build remains **unknown and
unpinned**. The validated scope is two development images at Percentage 3 on local
Chromium 153.0.8010.12, Playwright 1.63.0, Pillow 12.3.0. The visible range 0â€“50/step 1
is checked, but behavior at other values or other browsers is not established.

Only two development cases were imported and original hashes verified. ReforgerData
was read-only; collector code, holdout, and final_holdout were not accessed. Fixtures
and expected outputs are unchanged. Earlier development batches failed UI preconditions;
their diagnostics are retained separately from the successful six-run batch.

Offline verification (no browser or model request):

```powershell
.venv\Scripts\python.exe -m unittest -v test_smoke test_adapter
```

Ten checks cover existing model integration boundaries plus fixture integrity,
path/overwrite guards, exact RGBA comparison, and adapter preconditions. CI was
extended locally for these offline checks; no code was pushed in this milestone.

## Headless equivalence result (milestone 3)

Headless batch `20261010-103335-dbb864d9`: correct original imports, accepted
Percentage 3, fresh dimensions and three identical repeats per case; **0/6 exact
reference matches**. gb017: 9,122 differing pixels, maximum channel delta 9;
gb010: 1,977 differing pixels, maximum channel delta 255. Headed recheck
`20261010-103724-0ce76cc5`: **6/6 exact matches** and repeat agreement. Same visible
version 4.14.3 and Chromium 153.0.8010.12. The cause is unestablished; no reference
internals were inspected. Headed stays default; comparisons and fixtures unchanged.
Full diagnostic batches remain in evidence/runs/. See evidence/milestone3-results.md.

## Headed window placement

The optional desktop origin keeps the reference browser away from the main work area:

```powershell
.venv\Scripts\python.exe -m adapter.validate --headed --window-position=1600,0
```

Choose coordinates on a spare monitor or clear area of your desktop. Negative
coordinates use the equals form, e.g. `--window-position=-1600,0`. Omit the flag
for normal placement. `--window-position` is rejected with `--headless`.
Only Chromium's window-position launch argument changes. Viewport stays
1440x1000, device scale 1, en-US and America/Los_Angeles; there are no GPU,
rendering, occlusion, resize, minimize or maximize switches. Position is passed
to every fresh worker and recorded in evidence. The OS/window manager may clamp
coordinates; verify the browser is actually out of your work area before use.

**Do not click, type, drag, resize, minimize or otherwise interact with the
reference browser during experiments.** Do not let another controller use it.
Placement reduces accidental interaction; it does not lock out users.

The positioned headed batch `20261010-105508-083356f7` passed all six exact
comparisons and repeat agreement. An OS-only geometry probe observed the requested
origin (1600,0), outer bounds 1600,0..3056,1088, and a 1440x1000 screenshot at scale 1.
See [geometry evidence](evidence/window-position-observation.json). No reference
application state was read. Other monitor configurations may behave differently.
