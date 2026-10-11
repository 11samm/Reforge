# Actual harness browser presentation

Initial implementation: `codex/live-harness-dashboard`, based on main `4f37096`. Persistent-session update: `codex/persistent-live-browsers`, based on main `b641458`.
Original worktree: `D:/Samuel/Downloads/Code/ReforgerData/live-harness-worktree`. Use the current main checkout or `persistent-live-browsers` worktree for the updated behavior.
No AGENTS.md was found in the repository or inspected ancestor directories. Existing main work, raw evidence, candidate workspaces and source worktrees were left intact.

## Presentation and ownership

The Implement a feature screen displays miniPaint on the left and the candidate editor on the right. `features.live.Session` attaches a private Chromium DevTools Protocol (CDP) session to the **existing worker-owned Playwright page**. `Page.startScreencast` delivers JPEG compositor frames; the dashboard polls the latest frame/state at 300 ms. No browser is launched for presentation, no actions are replayed, and workers receive no visibility delays.

Two job-owned processes now retain their actual Chromium browsers throughout visible testing. Each has a single synchronous Playwright owner; the parent schedules actions separately using a private file mailbox. The candidate owner first builds and displays the prepared shell, then performs its real candidate gates in the same browser. Each reference procedure still receives a fresh context/document. Browsers are closed before final evaluation and on job completion, interruption, deadline, cancellation or owner failure. Linux owners also watch parent liveness; Windows ownership uses the existing kill-on-close Job Objects.

The reference adapter's existing headed execution is preserved. Candidate UI verification is headed when presentation is enabled by the owned feature-job child; other executions retain their previous headless mode. Both existing viewports stay 1440 × 1000 at device scale 1. CSS scales the displayed images without changing automation coordinates. Narrow screens stack the two panes.

Frames and action metadata are ephemeral, atomic latest-value snapshots under `.scratch/live/<job-id>/<role>.json`. They never enter the recorded evidence bundle, reference outputs, model packets or candidate sources. The API returns these only through the existing loopback/Host/Origin guards at `GET /api/jobs/<id>/live`. There is no exposed debugging endpoint or interaction API. Job IDs are validated by JobStore; each snapshot embeds its job identity and session generation. The client rejects the wrong job and recorded mode, clears images immediately on job switching/cancellation, aborts old requests and clears both panes on service/feed errors. Closed/crashed pages and browser disconnections update their state; dead worker PIDs are checked on the backend. Terminal jobs never return current frames, including after service recovery.

The activity panel uses the real job stage/activity events and backend elapsed time. Visible action names, parameters, input basenames and action start timestamps come directly from trusted adapter/discovery/candidate code. Experiment purpose and input generation parameters come from the validated, preregistered experiment event. No progress or actions are synthesized for ordinary jobs. Candidate build, launch, unavailable, ready, disconnected and held-out-hidden states are explicit.

## Embedding investigation

A HEAD-only inspection of hosted miniPaint on October 11, 2026 returned no X-Frame-Options or Content-Security-Policy header. This does not make an iframe suitable: navigating an iframe creates a new browsing context rather than embedding the Playwright-controlled top-level page, cookies, document and automation session. Cross-origin access also restricts dashboard control/inspection. Native browser windows cannot be adopted into HTML. A read-only stream of the existing page is the simplest reliable option here.

Protocol reference: https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-startScreencast
Embedding restrictions: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Frame-Options

## Isolation

Both actual browser sessions stay open simultaneously during visible testing. Reference and candidate actions are scheduled separately, and an idle owner pumps browser events while waiting. No retained screenshot is used to impersonate a connected browser. The separate candidate process receives no reference browser handles, controller or reference internals; its batch execution retains the input-only and network permission guards. Candidate execution metadata reports the persistent reference browser as open instead of claiming it was closed.

Once-only final evaluation calls `live.hide()` before producing fresh final inputs, then disables presentation for all subsequent workers. Cleanup gates and baseline subprocesses also do not publish frames. Reference presentation reads only visible page images; no source, network bodies, bundles, hidden state, canvas extraction, HAR or tracing is introduced. Expected PNGs, exact policies, model access boundaries and final repair isolation remain unchanged. The original recorded side-by-side evidence inspector is unchanged.

## Launch without paid calls

Use two PowerShell terminals. First, from this worktree:

```powershell
Set-Location D:/Samuel/Downloads/Code/ReforgerData/live-harness-worktree
& D:/Samuel/Downloads/Code/Reforge/.venv/Scripts/python.exe -m features.live_demo
```

Then build and open the dashboard (start this first if you want to see the entire short verification):

```powershell
Set-Location D:/Samuel/Downloads/Code/ReforgerData/live-harness-worktree/dashboard
npm.cmd run build
npm.cmd run preview
```

Open http://127.0.0.1:5181/ and select **Implement a feature**. Build/open the dashboard before launching the demonstration to observe all actions. The demonstration service uses port 5190, with pilot disabled, and runs once. It performs the existing real miniPaint Brightness import/adjustment/export procedure and the actual candidate build, saved visible exact comparisons and UI/export gate. It calls no model. Job metadata is explicitly labeled synthetic/deterministic; its frames are real browser evidence. Successful verification finishes `unresolved` with classification `deterministic_browser_checks_passed`, never an accepted new feature. It does not promote or change canonical feature code. Use a fresh command invocation to observe another execution; this is not playback. Cancel job stops its owned worker process tree.

For a passive dashboard/service review, use `python -m features.service` instead. Do not run both services on the same port. Check existing listeners before starting; do not replace unrelated processes. `--enable-pilot` remains a separate explicit paid-run authorization step and was not used here. The dashboard proxy targets 5190; `live_demo --port` exists for independent API tests, but using another port for dashboard review also requires changing that proxy. Only approved loopback dashboard origins 5180/5181 are accepted by the service.

Dependencies: existing Python environment with requirements-adapter.txt and installed Playwright Chromium, Node 24, and npm dependencies in dashboard/generated-app. Existing installed dependencies were copied into this worktree for validation; for a fresh checkout use `npm.cmd ci` in each package and `python -m playwright install chromium`. A desktop/display is required for headed mode (Linux needs a display/Xvfb). miniPaint access requires internet, but no reference source is downloaded or inspected.

## Validation

`test_live_browser.py` runs the actual reference and candidate workers while the production dashboard consumes the real loopback API. It asserts both decoded frames are displayed, multiple real actions and stage transitions are observed, completion clears frames, and narrow layouts do not overflow. It then reruns the same saved candidate inputs in headless mode, requiring exact saved-case results and UI/batch agreement in both modes. Results and screenshots are under `.scratch/live-validation/`; each invocation retains a separate `evidence/learning/offline-feature-live-<id>/` archive with worker logs and original results.

`test_live_sessions.py` covers job scope, dead worker detection, terminal/cancellation clearing, opt-out and final blackout. `test_live_ui.py` covers building/ready, selected history, incorrect job response, feed disconnect/reconnect, cancellation, 980/390px and stacking with **explicitly synthetic** metadata and image fixtures. Existing `test_feature_ui.py` still checks recorded playback and side-by-side inspector behavior. Dashboard session parsing tests explicitly label their synthetic fixtures.

Run checks from the worktree:

```powershell
& D:/Samuel/Downloads/Code/Reforge/.venv/Scripts/python.exe -m unittest test_smoke test_adapter test_shell_boundary test_evaluator test_learning test_brightness test_features test_interaction_map test_harness_repair test_live_sessions test_feature_ui test_live_ui test_live_browser
Set-Location dashboard
npm.cmd run test
npm.cmd run typecheck
npm.cmd run build
```

## Technical limits

- CDP screencasting is Chromium-specific and experimental. JPEGs are presentation only; they are not exact PNG evaluation evidence. Streams are sampled latest frames, not guaranteed recordings of every fast intermediate change. No artificial pacing was added.
- Idle owners pump callbacks independently while the parent performs model calls or runs the other role. A blocking model call inside reference discovery still blocks that reference owner until browser-tool dispatch resumes; capture timestamps disclose the latest real frame. Static pages need not produce new compositor frames. No action delays were added.
- Both browsers remain open; their diagnostic actions are scheduled separately. Browser pages/contexts can be replaced for fresh-state gates within the same owned browser. Held-out workers always run separately after both visible owners have terminated.
- No paid Contrast discovery run was performed. Discovery tool hooks are covered by existing broker tests and the same adapter transport; end-to-end streaming was verified with saved deterministic Brightness procedures. To validate a full autonomous Contrast run, obtain separate paid-run authorization and run the unchanged bounded pipeline while reviewing this screen.
- The demo needs hosted miniPaint; offline UI/isolation tests work without it. It verifies existing Brightness only, and does not expand supported learning requests.

### Verified results on October 11, 2026

- 133 Python tests passed in the full suite, including real worker/dashboard rendering and headed/headless exact parity. One additional real headed-worker cancellation test passed after finalization (134 checks total). The cancellation test observes a ready reference browser, cancels the job, verifies process-tree completion and confirms frames are cleared.
- 13 dashboard data tests passed; TypeScript, production build, Python compile checks and git diff whitespace checks passed.
- Original editor baseline regressions passed with `classification: match`, including the established Brightness shell behavior. Results: `evidence/learning/offline-feature-live-baselines/baseline/results.json`.
- Latest real-session validation: job `3a011417f1ee484991ee1e4e4d40ae89`, 15 distinct visible action snapshots, both roles displayed, zero model calls. `.scratch/live-validation/result.json` and its screenshots record this local check.
- Synthetic UI screenshots generated by existing tests were preserved under `.scratch/synthetic-ui-validation/`; committed recorded/synthetic dashboard screenshots were restored unchanged. No expected raster output, evaluation policy or generated feature source changed.
