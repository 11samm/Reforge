# Brightness, Contrast and live browser integration

Integration branch: `codex/brightness-live-integration`, starting at main `4f37096`.
Merged `codex/contrast-brightness-demo` at `f63d3cf`, then
`codex/live-harness-dashboard` at `1c9eedf`. Both source branches and their local
run archives were preserved. No merge conflicts occurred.

## Verified combined behavior

- 140 Python tests passed, including fresh-start isolation, browser lifecycle,
  recorded inspector, final blackout, real worker cancellation, and actual
  browser frames rendered by the production dashboard.
- 13 dashboard tests and the production TypeScript/Vite build passed.
- All 11 saved Brightness cases and four accepted Contrast visible cases passed
  exact RGBA, with independent execution and UI/batch agreement.
- All original editor baselines passed with `classification: match`.
- Relocatable CI fixtures passed (75 checks, 47 fixture files).
- Real-session validation job `678a5f47b3954babbaf131b36f2cae41` displayed both
  worker roles, observed 18 distinct action snapshots, and passed exact
  headed/headless parity. It made zero model calls.
- CI now checks stream isolation on Windows/Linux and builds/tests the dashboard.

Local validation artifacts are under `.scratch/live-validation/` and
`evidence/learning/offline-feature-integration-*`. Generated synthetic screenshots
and latest baseline reports are saved under `.scratch/integration-validation/`;
the committed historical versions were restored. Frozen expected outputs and
evaluation policies were not modified.

## Review and launch

See [live browser startup](live-harness-dashboard.md) for the no-model demo and
[fresh Brightness commands](fresh-brightness-demo.md) for preparation and learning.
Use the current checkout in those commands rather than the original source worktree.

The subsequent persistent-browser update keeps both actual sessions open, with
separately scheduled actions and final-evaluation blackout. See
[persistent browser ownership](persistent-live-browsers.md). These integration checks do
not establish repeatable autonomous sub-five-minute timing: the unchanged final
Brightness configuration still needs repeat rehearsals. The existing dashboard
request form remains Contrast-only; fresh Brightness is available through the
documented CLI/backend. No new model-based learning run was performed for this merge.
