# Offline verification record

Verified in the isolated `codex/feature-discovery` worktree based on `9a99b06`.
Application main remained `cf9e518`; the original dashboard stayed on its inspector
branch. Their tracked source diffs remained empty. Unrelated untracked evidence was
not moved, staged or edited. No merge or push was performed.

- 98 Python tests passed across `test_smoke`, `test_adapter`, `test_shell_boundary`,
  `test_evaluator`, `test_learning`, `test_brightness`, `test_features`, and
  `test_feature_ui`.
- 11 dashboard tests passed, including legacy normalization, reconnect deduplication,
  timed evidence availability and prevention of future terminal-state leakage.
- Dashboard TypeScript checking and production build passed.
- Existing generated editor TypeScript checking and production build passed.
- All four original exact editor baseline cases passed, with brightness UI allowed.
- 11/11 saved brightness visible/fresh cases reproduced exactly; source and fixture
  hashes were verified by the unchanged reproduction script.
- Production dashboard browser smoke passed at 1440Ã—1000 with a clearly labeled
  local fixture. Local jobs and recorded playback remained distinct, Run respected
  disabled pilot execution, and unsupported-request errors survived polling.
- Windows job-object ownership was tested with a waiting local child: closing the
  owner handle ended it promptly. Cancellation-before-launch and cancellation winning
  over an acceptance result were tested; interrupted persistent jobs recovered honestly.
- Controlled offline model/worker fixtures exercised the full adjustment learning
  loop, trusted gate composition, rejection restoration and lack of promotion.
- `git diff --check` passed. Prepare-only printed the fixed pilot budget and made
  no model call.

Local browser tests used permitted mock DOM and PNG downloads. The controlled
orchestration tests stub model/worker responses and do not constitute independent
Contrast pixel verification. The real brightness reproduction and original editor
baseline checks are separate actual offline checks.

No live Contrast discovery, real miniPaint procedure validation, model-backed
investigation/reconstruction or Contrast acceptance was performed. Provider/tool
interaction, real dialog compatibility, sufficient experimental coverage and completion
within the combined 600-second budget remain pilot questions. A documented failure is
an acceptable pipeline outcome. Setup and the fully specified unexecuted command are
in [README-features.md](../README-features.md).

## Recovery follow-up verification

104 Python tests and 11 dashboard tests passed after recovery integration; dashboard
TypeScript checking/build and diff checks passed. Tests cover correcting invalid
specifications, retaining cross-run lessons, stopping after one correction, handling
recoverable UI errors without marking them observations, and keeping capability/time
violations fatal. These tests use mocks, not live model recovery. The third live pilot
preceded these changes and is documented separately. Existing confirmed locator and
specification mistakes seeded the local procedural memory; no algorithm evidence was
copied into it. No new live pilot validated recovery in this turn.
