# Demo rehearsal — October 11, 2026

**Recommendation: replay recommended.** Three new sequential clean-start Brightness attempts produced zero acceptances. All used the same learning code, provider and budgets. The post-rehearsal fixes below have no new model-based repeatability evidence; the three-run authorization is exhausted. Do not describe the bundled older success or deterministic browser checks as a new acceptance.

Use [the launch and presentation guide](demo-launch.md). The dashboard can present both accepted recordings while the backend is stopped. Leave a fallback tab ready before any live presentation. Next presentation action: open `http://127.0.0.1:5181/`, select **Brightness accepted real run**, press **Restart replay**, then **Play** at 20× speed. **Jump to end → Candidates** opens archived images and raw metrics.

## Rehearsal configuration and evidence

Worktree: `D:/Samuel/Downloads/Code/ReforgerData/demo-rehearsal`.
Branch: `codex/demo-rehearsal-20261011`; base: current `origin/main`, `db4894e2ba022a8731774a2dc76cc00fbb90741b`.
No existing worktree, original local change or raw archive was reset. No repository or ancestor `AGENTS.md` was found. All five requested demo documents were read.

The 47-file learning source/configuration inventory has aggregate SHA-256 `4419d8094381515eaa83f0adfec2a144498487ac48ddbd6b8f718fa18fa2e86f`. The aggregate is SHA-256 of UTF-8 `json.dumps(inventory, sort_keys=True)`. Full individual hashes and invocation hashes are in [the attempt ledger](../evidence/demo-rehearsal-20261011/attempts.json). All three captured harness `config.json` files have SHA-256 `4d490a432bcd7558385644cff0c6fda65de6f78612b99ee6447518853f9c688a`.

Each attempt used **Prepare fresh Brightness demo**, verified source hashes/file set and the missing target module, visually confirmed the absent editor, then used **Learn Brightness** on that exact demo ID. No prior attempt's learned code, contract, experiments or procedures were supplied. Starting-state manifests disclose empty job-local discovery memory and retained shared IO/general guidance/model pretraining. The existing managed provider was `openai`, `gpt-6.1-sol`, medium, with provider fallback disabled. No provider, API service, execution budget, frozen output, numerical acceptance criterion or final-evaluation isolation was changed during the three attempts.

Times below use the authoritative persisted job clock. Stage spans include work until the next emitted stage; the last stage includes cleanup. A repeated stage is listed separately. Preparation/build before clicking Learn is excluded. The ledger preserves invocation durations, reported token fields, candidate decisions and failures.

### Attempt 1 — unresolved, 91.332 s

Job/prepared demo: `ce98ea1b4ea74e6f9499047bffa8ada7`.
Archive: `evidence/learning/20261011T203326Z-273d7f90-dev-resume/`.

Discovery and diagnostic default identity/two fresh procedure replays passed. The planner proposed `height: 1`, outside the host's existing `3..257` generator bounds. No fresh experiment was admitted, no candidate ran and no final evaluation occurred. Failure: `procedure_infrastructure_failure`, `ValueError: Expected integer in 3..257`. Restoration, final build and original editor baselines passed.

Stage spans: Discover 35.789 s; Validate procedure 17.898 s; Investigate/cleanup 37.068 s. Startup before the first stage was 0.577 s.
Two model invocations: **100,167 total tokens**, 97,839 input, 72,064 cached input, 2,328 output, 333 reasoning output (a subset of output, not an additional total).

### Attempt 2 — unresolved, 260.772 s

Job/prepared demo: `fdbbb76c1ef9482dbb9d8981ccf07f4d`.
Archive: `evidence/learning/20261011T203549Z-3bcd93d3-dev-resume/`.

Discovery/default identity/replays passed; four fresh experiments were admitted. Both candidate-1 and candidate-2 built, ran independently, matched all four fresh cases exactly and passed UI/batch agreement. Both were rejected for `baseline_regression`: their empty-document operation dialog duplicated **No image loaded**, so the unchanged original shell regression found two matching nodes. Candidate-2 was the automatic repair within this run; no developer intervened. The run exhausted its two candidate attempts. No final evaluation or acceptance occurred. Restoration, final build and original editor baselines passed.

Stage spans: Discover 33.340 s; Validate procedure 17.269 s; Investigate 80.393 s; Reconstruct 54.071 s; Verify 7.473 s; Reconstruct/repair 49.414 s; Verify/cleanup 18.268 s. Startup was 0.544 s.
Five model invocations: **483,495 total tokens**, 476,409 input, 362,624 cached input, 7,086 output, 694 reasoning output.

### Attempt 3 — unresolved, 99.547 s

Job/prepared demo: `b0c13d30441a42a5993c15f35c002c2b`.
Archive: `evidence/learning/20261011T204052Z-e4367d7e-dev-resume/`.

Discovery/default identity/replays passed. Two fresh experiments were admitted; publishing the third preregistered experiment collided with a Windows results reader. `os.replace(results.tmp, results.json)` raised `PermissionError: [WinError 5] Access is denied`, propagating from presentation into the learning harness. No candidate or final evaluation ran. Failure: `procedure_infrastructure_failure`. Restoration, final build and original editor baselines passed.

Stage spans: Discover 31.667 s; Validate procedure 17.572 s; Investigate/cleanup 49.759 s. Startup was 0.549 s.
Two model invocations: **72,287 total tokens**, 69,927 input, 41,856 cached input, 2,360 output, 440 reasoning output.

### Retained artifact locations

All paths below are relative to this worktree unless stated otherwise:

- Original job state/logs: `evidence/feature-jobs/<job-id>/`.
- Preparation, discovery, procedure validation, presentation and failure summaries: `evidence/learning/feature-<job-id>/`.
- Original model invocation records, experiment outputs, checkpoints, candidate/evaluator/build logs and restoration records: each archive listed above.
- Exact prepared/restored editors: `dev-workspaces/feature-<job-id>/`; original start manifests remain there.
- Poll observations and screenshots: `.scratch/rehearsal/attempt-1-monitor.jsonl`, `attempt-2-monitor.jsonl`, `attempt-3-monitor.jsonl`, and `attempt-*-browsers.png`/terminal screenshots.
- Original-byte inventories: `.scratch/rehearsal/attempt-1-raw-sha256.json`, `attempt-2-raw-sha256.json`, `attempt-3-raw-sha256.json`; learning freeze `frozen.json`; protected editor/evaluator/fixture inventory `protected.json`.
- Sanitized, committed attempt ledger: `evidence/demo-rehearsal-20261011/attempts.json`. Raw/private invocation transcripts are retained locally and are not copied into the presentation recordings or PR.

There are **no successful new runs to export** and no accepted new candidate to exercise. The separately labeled saved-real UI regression uploaded a new image into the previously accepted isolated Brightness snapshot; that validates the exploration UI, not any of these three attempts.

## Post-rehearsal fixes and reproduction

All changes below occurred after attempt 3 finished. The original attempt count and frozen ledger remain intact.

1. **Windows results race:** poll `/api/jobs/<id>/results` while the harness publishes results. Windows readers could prevent replacement, aborting learning. The publisher now uses unique temporary files, bounded retries for external sharing conflicts, and a scratch-based cross-process lock shared with JSON readers. The previous complete snapshot remains readable; a permanently failed write retains its temporary snapshot and raises an explicit error. No expected images or acceptance gates changed. Four focused tests cover transient/permanent failures, concurrent readers and a separate service/publisher process. The initial retry-only fix failed the stress test; that failed test log is retained.
2. **Presentation scroll:** prepare an editor, then click Learn while viewing that editor. Previously the viewport remained below the actual browser panes. Successful start now scrolls to the live panel; cancellation does not change scroll position. The browser regression verifies the panel is in view after start.
3. **Planner size contract:** the schema previously permitted arbitrary integer dimensions despite host validation requiring `3..257`. Schema and planner guidance now expose the same existing range. Host validation remains unchanged. This is a declared learning-host/schema/prompt change, not a relaxation of a gate.
4. **Duplicate shell label:** candidate dialogs in attempt 2 repeated the exact empty-state shell text. Builder guidance now requires existing labels to remain unique, including hidden dialogs, and uses distinct operation guidance. The unchanged shell regression continues to reject duplicated labels. This is a declared builder-prompt change; its model behavior has not been rerun.

The post-fix inventory and changed-file hashes are in `evidence/demo-rehearsal-20261011/stabilization.json`. Earlier attempts do not establish repeatability for this changed learning host.

Remaining limits: the prompt fixes have no model rehearsal under the three-run cap; permanent filesystem permission failures are still explicit failures; hosted miniPaint is required for live execution and is unpinned. Static frames may wait during model work and retain their last-frame timestamp. Recordings contain archived screenshots, not continuous video or executable editor source. Acceptance of the older saved recordings remains within their recorded scope. If a future authorized live run fails, preserve that run and switch to replay; do not count it as accepted or hide it.

One remaining non-blocking logging issue: reload or leave the Implement screen while a results response is being sent. An aborted client connection can print `ConnectionAbortedError` in the service terminal. The request thread ends; service/job state persists. Keep the fallback in another tab and follow the job history before resubmitting after a network interruption.

## Validation

Exact commands and logs are recorded in `evidence/demo-rehearsal-20261011/validation.json`. The final no-model checks include all existing contracts/security/isolation tests, focused Windows race and planner-domain tests, dashboard UI/import/restart/switching checks, saved-candidate exploration, actual two-owner cancellation and final blackout, production builds and saved Brightness/Contrast/editor numerical regressions. New model execution was limited to the three attempts above.

Fallback filenames remain unchanged:

- `dashboard/public/runs/brightness-success.reforge.json`
- `dashboard/public/runs/contrast-success.reforge.json`

Both recordings imported from unrelated temporary directories with no backend APIs, decoded their inspector/gallery images, revealed evidence only at recorded times, hid later evidence on restart, and switched without leaking inspector selection or asset URLs. Independent source verification checked original metrics, decisions, event sequence/timing and token usage exactly. Their existing provenance preserves earlier failures and developer changes; it is not relabeled as this rehearsal.
