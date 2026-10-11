# Integrated Brightness demo and portable replay — October 11, 2026

Integration branch: `codex/demo-replay-integration`.
Worktree: `D:/Samuel/Downloads/Code/ReforgerData/demo-replay-integration`.
Base: current `origin/main` at `f5aef7bfaadb845bcd183e46864156b4b651d729`.

Both source chats finished and pushed their commits before integration. Merged in this order, retaining ancestry:

1. `codex/live-evidence-brightness`: `c452b6bc69b9ff25d7c1268101234785e5d46437`.
2. `feat/portable-replay-evidence`: `2048b1714f2da5015d269ebb247f6af1286d798e`.

The single App conflict is resolved with the portable importer and direct, typed `<ImplementFeature onReplaySavedRun={openSavedRun} />`. The temporary compatibility cast and navigation-only callback are removed. The updated browser regression chooses a real recording from the Implement screen and asserts its identity, time-zero state, recorded label and absence of live panes. CI now covers live-results security/lifecycle tests and integrated offline dashboard/replay browser checks.

## Experience and contracts

Preparation creates a unique editor with Brightness absent, records hashes and memory policy, and invokes no model. The prepared demo ID becomes the job ID; learning validates and reuses that exact editor instead of creating another. Changed/reused preparations are rejected. These handoff paths were tested with controlled, no-model execution; no new autonomous learning run is claimed.

Actual reference and candidate browser streams remain job-scoped and labeled live. Cancellation clears frames and stops both owned process trees. Final evaluation closes visible owners first. Live evidence schema 1 uses job-scoped, hash-checked artifact URLs; portable recordings use a separate versioned manifest with integrity inventory and local blob URLs. Imported recordings never enter JobStore, model packets or repair contexts. Recorded timing controls reveal boundaries and switching resets inspector selection.

Acceptance serves the isolated candidate snapshot for unscored uploads. The real saved Brightness candidate-2 was exercised with a new image at 1440, 980 and 390px; its job records were unchanged. Old jobs lacking a captured preview state that limitation. Portable recordings are evidence, not executable candidate archives.

## Exact startup and no-model demo

PowerShell terminal 1, using the existing virtualenv:

```powershell
Set-Location D:/Samuel/Downloads/Code/ReforgerData/demo-replay-integration
npm.cmd --prefix generated-app ci
npm.cmd --prefix dashboard ci
npm.cmd --prefix dashboard run build
& D:/Samuel/Downloads/Code/Reforge/.venv/Scripts/python.exe -m features.service
```

Terminal 2:

```powershell
Set-Location D:/Samuel/Downloads/Code/ReforgerData/demo-replay-integration
npm.cmd --prefix dashboard run preview
```

Open `http://127.0.0.1:5181/`, select **Implement a feature**, then **Prepare fresh Brightness demo**. The isolated editor has no Brightness module and starts without an image. **Learn Brightness** stays disabled with this service configuration. Preparation does not require model execution opt-in. No pilot/model command is part of integration validation.

Equivalent API preparation, while that service is running:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5190/api/jobs/prepare -ContentType application/json -Headers @{'X-Reforge-Request'='1'} -Body '{"request":"Implement Brightness"}'
```

Optional deterministic live-browser demonstration, after stopping only the service you started above with Ctrl+C:

```powershell
Set-Location D:/Samuel/Downloads/Code/ReforgerData/demo-replay-integration
& D:/Samuel/Downloads/Code/Reforge/.venv/Scripts/python.exe -m features.live_demo
```

Keep dashboard preview running and open **Implement a feature**. This uses real miniPaint and candidate actions with saved visible Brightness cases, has zero model calls, and is explicitly labeled deterministic verification with synthetic job metadata. It does not establish new feature acceptance. Ctrl+C closes the demonstration service and its owned workers. Do not run alongside another harness: the shared locks must be available. Preview uses strict port 5181; the feature service uses 5190. Inspect listeners before starting; never stop an unrelated process.

For an existing source clone on another machine, create a virtualenv, install `requirements-adapter.txt`, and run `python -m playwright install chromium` before browser checks. The absolute existing-venv path above is specific to this retained Windows workspace.

## Offline replay

The backend may be stopped. Start only dashboard preview as above. Select the bundled Brightness or Contrast recording in **Run bundle**, or copy either file to another directory and use **Replay saved run** from Overview or Implement:

- `dashboard/public/runs/brightness-success.reforge.json`: 7,164,565 bytes; 47 events; 312 images; job `82b68e6daf5e41ddb7c03c13a91ba1f9`; playback duration 297.460 seconds.
- `dashboard/public/runs/contrast-success.reforge.json`: 7,137,393 bytes; 39 events; 321 images; job `9df7c33da7a5425db3934e2cd928c5ee`; final event 346.775 seconds; original summary 346.770 seconds remains preserved.

Imports start at zero. **Jump to end** reveals archived candidate/final evidence; **Candidates** provides the matching per-case inspector. **Restart replay** hides later outcomes again. Recorded browser images remain in the recorded gallery, never live panes. Opening Implement while the backend is stopped may show Service offline; importing a recording still works.

Both original archive comparisons passed with unchanged bundle SHA-256 values listed in `portable-source-validation.json`. The recordings preserve the Brightness rejection/repair history and Contrast provenance. No frozen outputs or evaluator thresholds were modified.

## Validation on the integrated worktree

153 distinct Python tests passed across sequential invocations (106 offline/contract checks, 44 feature/API/UI checks, and 3 actual worker/browser checks). The first run exposed one obsolete test expecting the old Replay navigation; it was corrected to exercise the importer and passed. All other 43 tests from that invocation passed. All 19 dashboard data tests, TypeScript checks, dashboard/editor production builds, Python compile checks and the 75-test relocated-fixture check passed.

Exact test commands, from the integration root; browser invocations must be sequential:

```powershell
& D:/Samuel/Downloads/Code/Reforge/.venv/Scripts/python.exe -m unittest -v test_smoke test_adapter test_shell_boundary test_evaluator test_learning test_brightness test_interaction_map test_harness_repair test_fresh_brightness test_live_results
& D:/Samuel/Downloads/Code/Reforge/.venv/Scripts/python.exe -m unittest -v test_features test_live_sessions test_feature_ui test_live_ui test_live_results_ui test_portable_ui
& D:/Samuel/Downloads/Code/Reforge/.venv/Scripts/python.exe -m unittest -v test_live_browser
& D:/Samuel/Downloads/Code/Reforge/.venv/Scripts/python.exe -m learning.ci_fixtures --check
npm.cmd --prefix dashboard test
npm.cmd --prefix dashboard run typecheck
npm.cmd --prefix dashboard run build
npm.cmd --prefix generated-app run build
```

The real simultaneous-stream verification job `7aa37217136a440688f2be65de575fce` observed 60 distinct action snapshots with exact headed/headless parity and zero model calls. Cancellation job `414fe7fad715498fbfb837419903591d` closed both actual owners. Final blackout passed. Artifacts remain under `.scratch/live-validation` and `evidence/learning/offline-feature-live-*` in this worktree.

Saved-real preparation/review: `.scratch/live-results-validation/result.json`, prepared demo `57a412e7efcd439cab81454e108b41b2`. `test_live_results_ui` reads the retained `contrast-brightness-worktree` archive; override `REFORGE_SAVED_BRIGHTNESS_ROOT` when relocating it. This local test requires the saved archive and candidate build and is not claimed to run in source-only CI.

`test_portable_ui` imported both real recordings from a temporary unrelated directory with all backend APIs blocked, verified image decoding/blob URLs, time-based conceal/reveal, restart, run switching, and rejected a missing asset. Dashboard tests also rejected unsafe references/traversal, unsupported schemas, bad ordering and corrupted manifests/assets. Final isolation and builder/repair access guards passed; display of completed final evidence does not grant model access.

Numerical regression commands (reserve `feature-service` and `feature-browser` locks; the retained wrapper `.scratch/integration-regressions.py` does so):

```powershell
& D:/Samuel/Downloads/Code/Reforge/.venv/Scripts/python.exe verify_adjustments.py --contrast-archive D:/Samuel/Downloads/Code/ReforgerData/feature-discovery-worktree/evidence/learning/20261011T083511Z-2d1ccba6-dev-resume
& D:/Samuel/Downloads/Code/Reforge/.venv/Scripts/python.exe baseline_regressions.py --allow-brightness --output evidence/learning/offline-feature-demo-replay-baselines
```

All 11 saved Brightness and 4 accepted Contrast visible cases passed exact RGBA, build/independence and UI/batch agreement. Original editor baselines passed all four exact comparisons (`match`). The numerical check reads the Contrast visible suite, not its held-out final outputs. Results: `evidence/learning/offline-feature-integration-d35146daaa37448286e219e3851abb17/summary.json` and `evidence/learning/offline-feature-demo-replay-baselines/results.json`.

Source validation command template:

```powershell
& D:/Samuel/Downloads/Code/Reforge/.venv/Scripts/python.exe verify_portable_source.py --repo <retained-source-checkout> --archive <original-learning-archive> --job <original-feature-learning-directory> --bundle <portable-recording>
```

Exact source paths are in `portable-replay.md`. Both calls passed in this worktree, preserving exact raw metrics, sequence/timing and usage. The Python comparator reads final metrics only for recording verification; it never calls a model or creates repair inputs.

## Limits and preservation

No functional integration blocker remains in local validation. GitHub CI must pass on the final head before merging. Main is unchanged and this PR must not be merged automatically. All source worktrees, original local changes and raw archives are retained. Test-generated screenshots/latest-summary files are backed up under `.scratch/integration-generated-reports` before restoring their tracked historical versions in this worktree only.

Actual reference verification depends on hosted miniPaint. No continuous browser video was archived; uncertain screenshot timing uses conservative section-completion boundaries. Hashes detect corruption but do not authenticate authors. No new model-based learning, repeatability claim, timing benchmark, promotion or acceptance result was created. Final evidence stays outside builder/repair contexts. Acceptance remains within the recorded tested scope.

## Hosted CI stabilization

The first PR CI run `38171237852` passed Linux and the complete dashboard/browser checks. Windows passed all 145 offline tests, 75 relocated-fixture tests and command-help checks, then exceeded the five-minute job allowance during cleanup. Windows Media Foundation installation alone took about four minutes. The offline-check job allowance is now ten minutes so dependency installation/runner cleanup have headroom. No learning deadline, evaluator criterion, test or frozen expected output is relaxed. The final-head CI result is recorded in the PR.
