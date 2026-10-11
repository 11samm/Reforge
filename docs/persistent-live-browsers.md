# Both actual browser sessions remain open

Implemented on `codex/persistent-live-browsers`, based on main `b641458`.

`features.sessions.Pool` owns two separate processes, one for miniPaint and one
for the candidate editor. Each process owns exactly one Playwright instance and
Chromium browser. Both start during preparation; the candidate first builds and
displays the prepared editor. The same owners then execute the existing trusted
worker functions. This is live execution, not a second presentation browser or
replayed activity.

The parent schedules reference and candidate actions separately through private,
job-scoped file mailboxes. Each reference procedure still opens a fresh context
and document. Candidate checks retain their independent batch, network guards,
exact comparisons and UI/export agreement. Reference handles/controller state
never cross to the candidate process. Worker provenance explicitly reports the
reference browser as open when persistent owners are in use.

Idle owners process browser callbacks independently of parent model calls and the
other role's execution. Pages may be replaced within the same browser to preserve
fresh-state gates. Old-page callbacks cannot disconnect a replacement page.
Both panes clear on terminal jobs, feed failure or owner death. Final blackout
first terminates both owners, then hides both panes and disables presentation;
held-out workers remain separate and never reuse these browser sessions.

Completion, cancellation and command deadlines close both process trees. Existing
Windows Job Objects handle abrupt owner interruption; Linux owners monitor parent
liveness and terminate their own process groups when the parent disappears.
Worker completion uses unique command tokens, not leftover result files.

## Validation

- 143 Python tests, 13 dashboard data tests and the production build passed.
- Real dashboard/browser validation displayed both streams simultaneously and
  kept miniPaint visible during actual candidate actions. Exact headed/headless
  parity passed. Job `eb8934938f8748cfa88bb4cebdd74242` observed 63 action snapshots
  and made zero model calls.
- Two reference requests used the same owner with fresh document/context state.
- Cancellation terminated both actual owner processes. A separate real blackout
  check verified both processes had exited before final-evaluation presentation
  was disabled and both hidden panes had no frames.
- All 11 saved Brightness cases, four accepted Contrast visible cases, original
  editor baselines and relocatable fixtures passed. Expected outputs and numerical
  acceptance criteria were not changed.

Real screenshots/results are under `.scratch/live-validation/`, including
`both-real.png`. Job-scoped mailbox and owner logs are under `.scratch/live/`.
Each gate retains its request, result and owner PID/process timing in the normal
learning archive. Synthetic screenshot updates and latest baseline reports are
saved separately before restoring the committed historical versions.

Use the [existing startup commands](live-harness-dashboard.md) from this worktree
or the updated main checkout. No-model verification now performs two reference
procedures before candidate tests. It remains explicitly labeled deterministic
verification rather than an accepted newly learned feature.

Static browser pages need not emit new compositor frames. A blocking model call
inside reference discovery can still pause that owner's callbacks until a browser
tool executes; timestamps disclose the last actual frame. Parent-side builder
calls do not block the idle browser owners. No new model-based learning run or
autonomous timing benchmark was performed for this lifecycle change.
