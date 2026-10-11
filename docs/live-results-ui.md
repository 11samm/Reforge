# Live results and prepared Brightness editors

Branch `codex/live-evidence-brightness` starts at main `f5aef7b`. No model-based
learning run is launched by this change's validation. Existing raw evidence,
canonical generated source, source worktrees, policies and expected PNGs are
preserved. Acceptance never promotes or merges a candidate.

## Startup

From `D:/Samuel/Downloads/Code/ReforgerData/live-evidence-brightness`, run:

```powershell
& D:/Samuel/Downloads/Code/Reforge/.venv/Scripts/python.exe -m features.service
```

In a second terminal:

```powershell
Set-Location D:/Samuel/Downloads/Code/ReforgerData/live-evidence-brightness/dashboard
npm.cmd ci
npm.cmd run build
npm.cmd run preview
```

Use http://127.0.0.1:5181/ and **Implement a feature**. Fresh checkouts also need
`npm.cmd ci` in `generated-app`. Preparation copies those installed dependencies
using the existing preparation function, builds with fixed trusted TypeScript and
Vite commands, and invokes neither a model nor a reference browser. Its editor
starts with no image, disabled Image menu and unavailable Brightness message.
The manifest discloses retained shared IO, general guidance and model pretraining.

Choose a prepared demo before learning. The service remains disabled for model
execution by default. Separately authorized service execution uses the existing
`--enable-pilot`; all existing budgets and final isolation remain in force. CLI
prepare/pilot behavior is unchanged. Dashboard learning reuses the selected demo
ID and exact workspace after validating source hashes and the file set. A used
demo cannot start another run, and edited demos require fresh preparation.

## Job API contract

All routes retain the loopback Host and approved Origin checks. Mutations require
`Content-Type: application/json` and `X-Reforge-Request: 1`; bodies remain bounded
to 1000 bytes. No paths, commands, source archive IDs or scripts are accepted.

- `POST /api/jobs/prepare` with `{ "request": "Implement Brightness" }` returns
  `{id, request, preparation, model_invoked:false, preview_status, preview_url?}`.
  Preparation is available while the pilot gate is disabled, but never during an
  active learning job. Build failure is explicit and preserves the prepared state.
- `GET /api/jobs` also returns `prepared_demos`. Existing `jobs` and
  `pilot_enabled` fields are unchanged.
- `POST /api/jobs` with `{request, prepared_demo_id}` starts fresh discovery in
  that editor. Existing `{request}` callers retain their fresh-workspace behavior.
  Both paths require opt-in. This is never saved-evidence continuation.
- `POST /api/jobs/<id>/cancel` retains owned-process-tree cancellation and clears
  both live panes immediately through the existing cancelling state.
- `GET /api/jobs/<id>/results` returns schema 1 with `job_id`, `experiments`,
  `candidates`, recorded `events`, `report` and terminal-only `final`. Candidate
  results contain actual build/UI/batch flags, errors, logs, baseline records,
  established Brightness regressions, case reasons and raw recorded metrics.
  Absent records are null/empty; the UI explicitly describes missing evidence.
- Image descriptors are `{id?, label, status, url?, reason?}`. Available images
  use `/api/jobs/<id>/artifacts/<64-hex-id>.png`; missing descriptors have no URL.
  Experiment inputs/reference outputs and per-candidate reference/candidate/RGB
  and alpha difference images are copied from the trusted harness's own archive.
  Difference gain is display-only; numerical criteria are unchanged.
- `GET /api/jobs/<id>/preview` returns the accepted candidate snapshot URL, or
  an explicit missing-preview reason. It cannot create a later build from mutable
  sources. Snapshots are captured when acceptance finishes.
- Prepared preview files use `/api/jobs/demos/<demo-id>/preview/<allowlisted-name>`;
  accepted preview files use `/api/jobs/<id>/preview/<allowlisted-name>`. Only
  hashed built assets are served, never arbitrary source or directory listings.

Artifact and preview lookups reject traversal, symlinks, junctions, hard links,
changed hashes and mismatched job IDs. Presentation copies contain no private
model transcripts. Held-out artifacts are not supplied to builder or repair
capabilities. Final summary reads occur only for terminal jobs. Final workers still
start after live owners close; the actual two browser streams are unchanged.

Preview frames have an opaque sandbox origin, scripts and local downloads only,
and a restrictive CSP denying network connections/forms/frames. Module assets
allow CORS for that opaque origin; Origin `null` is accepted only for immutable
preview GETs, never job JSON or mutations. Uploads remain browser-local editor
state. Interactive exploration is explicitly unscored and never edits job records.
Editor frames fit the viewport and scroll into view on load, so native operation
dialogs remain reachable inside the dashboard's scroll area.

## Agent 2 integration

Agent 2 owns App's portable file importer/exporter and recorded inspector. The
only ImplementFeature integration is:

```tsx
<ImplementFeature onReplaySavedRun={openSavedRun} />
```

`onReplaySavedRun?: () => void` is called by **Replay saved run**. This branch's
one-line App wiring opens the existing recorded overview. During integration,
replace its `() => setView('overview')` with Agent 2's `openSavedRun` file-picker
callback. Agent 2's `data/portable.ts` owns bundle validation/import and enters
recorded mode without any backend. Do not reuse the live-results endpoint as a
portable format, duplicate the exporter, or import bundles into JobStore.

Cherry-pick each branch's commits onto a separate integration branch. The expected
App conflict is this single callback line; retain Agent 2's App/importer logic and
the new ImplementFeature prop. Live `data/jobs.ts`, `LiveEvidence.tsx`, prepared
controls and Python APIs belong to this branch; recorded normalizer/inspector and
portable integrity logic belong to Agent 2. CSS additions here use only
`.candidate-review`, `.feature-evidence`, `.feature-compose`, `.evidence-images`.

Agent 2's completed commit is `2048b1714f2da5015d269ebb247f6af1286d798e`
(`feat/portable-replay-evidence`). Exact integration sequence in a separate checkout:

```powershell
git switch -c integration/live-results-replay f5aef7b
git cherry-pick codex/live-evidence-brightness
git cherry-pick 2048b1714f2da5015d269ebb247f6af1286d798e
```

Resolve `dashboard/src/App.tsx` using Agent 2's importer/state logic and
`onReplaySavedRun={openSavedRun}`. Their `ReplayImplementFeature` compatibility alias may be
removed in favor of direct `<ImplementFeature onReplaySavedRun={openSavedRun} />`.
After resolving, run `git add dashboard/src/App.tsx` and `git cherry-pick --continue`.
Run dashboard test/typecheck/build and sequential `test_feature_ui`,
`test_portable_ui`, `test_live_results_ui` checks on that integration branch. Do
not merge main. The two `.reforge.json` recordings and `importPortable(value)`
(`{run, dispose}` with local URLs) come entirely from Agent 2's commit.

## Validation and limits

Offline presentation fixtures are explicitly synthetic in `test_live_results.py`.
`test_live_results_ui.py` reads the original accepted Brightness job and archive
from the retained `contrast-brightness-worktree` (override with
`REFORGE_SAVED_BRIGHTNESS_ROOT`). It copies presentation data to temporary storage,
prepares a real absent-feature editor, uploads a new unscored image into the saved
accepted editor, and exercises Brightness with no model. Saved evidence is never
rewritten. Screenshots/results are local under `.scratch/live-results-validation`.

Existing `test_feature_ui`, `test_live_ui`, `test_live_sessions` and
`test_live_browser` cover recorded separation, synthetic states, actual two-owner
streams, cancellation and final blackout. Browser checks run sequentially.
Worktree BrowserLock now resolves to the canonical repository's `.scratch` locks,
so worktrees coordinate with main's legacy reference/service ownership locks.
Only owned processes are stopped.

Validated October 11, 2026, in separate sequential invocations:

- All 146 selected Python checks passed, including 8 new offline security/lifecycle
  fixtures and the saved-real evidence/preparation/exploration browser check.
- All 13 dashboard data tests, TypeScript checks, production build, Python compile
  checks and diff whitespace checks passed.
- Saved-real review applied Brightness to a new upload at 1440, 980 and 390px;
  sandbox isolation prevented access to the dashboard DOM. Original job/evidence
  records were unchanged.
- Real verification job `a812200f9147474198d94a4d45a7ea6f` displayed both worker
  streams simultaneously, observed 53 action snapshots, passed headed/headless exact
  parity, and made zero model calls. Cancellation job
  `c9c3758ae07047f8bc7aa4a5eff363f3` terminated both owned processes. Final blackout
  also passed. These deterministic checks are not new feature acceptance.
- All 11 saved Brightness cases and 4 accepted Contrast visible cases passed exact
  RGBA and UI/batch agreement. Original editor baseline classification was `match`.
  Artifacts: `evidence/learning/offline-feature-integration-48f35f4bf8d54958b44c1769ab6594ea`
  and `evidence/learning/offline-feature-live-results-baselines`.
- New synthetic screenshots/reports were saved under
  `.scratch/live-results-generated-reports` before restoring tracked historical
  versions. Main's tracked files have no diff; candidate sources, fixtures and
  numerical policies have no changes.

Re-run without models (reserve browser ownership before these checks):

```powershell
& D:/Samuel/Downloads/Code/Reforge/.venv/Scripts/python.exe -m unittest test_smoke test_adapter test_shell_boundary test_evaluator test_learning test_brightness test_features test_interaction_map test_harness_repair test_live_sessions test_feature_ui test_live_ui test_live_browser test_live_results test_live_results_ui
```

Old accepted jobs without a captured preview report that absence. Old jobs without
published live evidence also report missing records; use Agent 2's saved portable
replay for those archives. Preparation builds synchronously and may take several
seconds copying dependencies. New learning handoff is validated offline; no new
paid learning run or speed benchmark is claimed. Hosted miniPaint is still required
for actual reference browser verification. Acceptance scope remains recorded cases.
