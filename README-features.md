# Implement a feature

Worktree branch: `codex/feature-discovery`, based on dashboard inspector commit
`9a99b06`. Application main and the original dashboard checkout were preserved.
No merge, push or live model-backed run is part of this implementation.

Architecture/supported limitations: [docs/feature-pipeline.md](docs/feature-pipeline.md).
Offline results: [docs/feature-pipeline-verification.md](docs/feature-pipeline-verification.md).
Schema: [features/feature-spec.schema.json](features/feature-spec.schema.json), with
additional evidence/domain validation in `features/spec.py`.

## Setup

From this worktree, use Python with the repository's existing dependencies installed
(`Pillow` and `playwright`, plus installed Chromium). Use Node 24 and install the
existing lockfile dependencies for `generated-app` and `dashboard`:

```powershell
python -m pip install Pillow playwright
python -m playwright install chromium
Push-Location generated-app
npm.cmd ci
Pop-Location
Push-Location dashboard
npm.cmd ci
Pop-Location
```

The implementation verification reused already installed dependencies locally.
No API key or different provider is introduced; the same signed-in `codex` app-server
configuration in `smoke.config.json` is used by an authorized pilot.

Start the API with pilot execution disabled:

```powershell
python -m features.service
```

In another terminal, start the dashboard:

```powershell
Push-Location dashboard
npm.cmd run dev
```

Open http://127.0.0.1:5180 and choose **Implement a feature**. The Run action is
disabled until the service is explicitly started with `--enable-pilot`. Recorded
playback is a separate view. Production preview also proxies `/api/jobs` to 5190;
a deployed static dashboard alone cannot execute jobs. The supported request is
`Implement Contrast`. Cancellation, progress and completed jobs persist under
`evidence/feature-jobs`; full private observations are under `evidence/learning`.
Evidence and isolated candidates are retained for review; they are not bundled
into the recorded sample or automatically promoted.

## Offline verification

```powershell
python -m unittest test_smoke test_adapter test_shell_boundary test_evaluator test_learning test_brightness test_features
python evidence/brightness/reproduce.py
python -m features.pipeline
Push-Location dashboard
npm.cmd test
npm.cmd run typecheck
npm.cmd run build
Pop-Location
python -m unittest test_feature_ui
git diff --check
```

`python -m features.pipeline` prints the fixed budget and exits without a model call.
Browser tests use local mock pages. They do not establish real-reference Contrast
behavior. Original evaluator policies, expected fixtures, collected data and
protected holdouts are unchanged.

## Future authorized Contrast pilot â€” do not run during implementation

From this worktree with dependencies and managed sign-in ready, exactly one CLI job:

```powershell
python -m features.pipeline --pilot --request "Implement Contrast"
```

Fixed budget: 1200 seconds total; up to five isolated harness repairs within a shared 300-second repair window; stop after two repeated failures; at most two discovery invocations sharing 90 seconds / 20 UI
actions / 24 observations; at most two recoverable UI-action corrections and one specification correction; zero fresh-browser/reference retries; one diagnostic default
setup check and two fresh-document procedure replays; at most four fresh investigation
experiments; two candidates; 12 builder calls and six evidence reads per candidate;
two final cases evaluated once, with no further repair. Headed reference configuration
remains 1440Ã—1000, scale 1, en-US, America/Los_Angeles, window position 1600,0.
Per-model packet and worker limits remain the existing harness defaults. Actual
provider tokens are recorded, without a promised hard token/cost ceiling.

For the dashboard pilot instead, start `python -m features.service --enable-pilot`,
enter `Implement Contrast`, review the displayed budget and click Run once. Do not
also start the CLI pilot. Do not interact with the controlled reference browser.

Success means discovery and validation without supplied Contrast reference selectors,
followed by independently passing frozen visible, original baseline, brightness and
once-only final checks. An unresolved specification, procedure failure, mismatch,
timeout or cancelled job is an honest outcome, never a working-feature claim.
Acceptance remains scoped to recorded cases and an isolated candidate workspace;
promoting it requires a separate later action.

Harness repair is limited to output_schema and visible row resolution. It requires a
trusted reproducer failing before the patch and passing afterward, plus regression
checks. Model patches remain isolated artifacts; no canonical source is promoted.
Unknown faults stop. Evaluators, thresholds, expected outputs and capability brokers
cannot be patched. Tested patches can be recalled only with matching host hashes and
fresh offline regression gates; live discovery must still validate the procedure.

Interaction map and bounded inspection: see docs/interaction-map.md. No live pilot was run for this addition.
