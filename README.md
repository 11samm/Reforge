# Reforge â€” connectivity milestone

For the current presentation, use the [demo launch guide](docs/demo-launch.md) and
[three-attempt rehearsal report](docs/demo-rehearsal-20261011.md). The October 11
rehearsal recommends recorded replay; the historical milestone notes below remain preserved.

Milestone 1 only, implemented during OCC Hacks on October 10, 2026. Design context:
`reforge_prd_v1.3.md` in ReforgerData. No dataset files or collector code were read,
copied, or changed. The editor and learning loop are deferred. Deterministic reference browser replay
was added in the next milestone; see [adapter setup and recovery](README-adapter.md).

## Setup and rerun

Requires Python 3.12+ and a native Codex executable on PATH; no Python packages.
If PATH resolves a Windows `.cmd` wrapper, set `codex_bin` in `smoke.config.json`
to an absolute `codex.exe` path. Check authentication:

```powershell
codex --version
codex login status
```

If needed, run `codex login` and complete the supported ChatGPT browser sign-in.
Codex manages credentials and refresh. Reforge never reads credential files or
prints secrets. It retains only account type and plan, not email.

```powershell
Set-Location 'D:\Samuel\Downloads\Code\Reforge'
python smoke.py
```

Exit 0 means both checks passed; exit 1 means failure. JSON results are printed
and saved in `.scratch/latest-report.json` and `.scratch/<run-id>/report.json`.
Each invocation uses a new isolated scratch directory. Scratch files are Git-ignored.

`smoke.config.json` controls executable, model, effort, check timeout (120 seconds),
and RPC timeout (20 seconds). Timeouts must be 1â€“300 seconds. Startup, pagination,
local execution, and teardown also have bounds. On turn timeout the process tree
is terminated on Windows. Raw runtime stderr/error messages are suppressed; safe
errors, error codes, completion status, elapsed time, and available usage are saved.

## Access and isolation

Uses local Codex app-server over stdio JSON-RPC. Route selected after inspecting
current [app-server docs](https://learn.chatgpt.com/docs/app-server),
[authentication docs](https://learn.chatgpt.com/docs/auth), and the
[official model catalog](https://developers.openai.com/api/docs/models).

Only managed ChatGPT authentication is accepted; API-key accounts fail before
inference. Inherited API-key environment variables are removed. Usage is through
the existing ChatGPT plan, not API-key billing. Cursor subscription access is not
assumed. Reforge does not purchase credits, enable overages, or reset quotas.
Existing user-managed account settings and subscription limits still apply.

The runtime catalog is checked for the exact model and reasoning effort. Catalog
presence alone does not prove entitlement; completed inference confirms access.
Provider fallback is disabled and the returned model/provider must match. To choose
another advertised model explicitly: `python smoke.py --model gpt-6-sol`.

Agent threads are ephemeral with `environments: []` and empty capability roots.
Shell, plugins, connectors, hooks, memories, and web search are disabled. The file
check exposes only `create_add_file`: source text in, fixed scratch `add.py` out.
It has no path/read argument and cannot overwrite. Other server requests are denied.
No dataset, collector, reference, evaluator, or final evaluation files are exposed.
This proves constrained agent file creation; broader repository/shell editing needs
separate isolation work in a later milestone.

## Checks and observed results

Successful run: `codex-cli 0.162.0-alpha.17.2`, exact model `gpt-6.1-sol`, requested
and supported effort `medium`; managed ChatGPT account, reported plan `plus`.
Both checks ran through `smoke.py` in 14.803 seconds total.

- **Structured answer â€” passed, 8.266 seconds:** output schema plus application
  validation of exactly `question`, `input_description`, `parameter_value`, and
  `competing_hypotheses`; finite numeric parameter and two distinct nonempty
  hypotheses required. Proposed a white image/radius 5 boundary experiment.
  `behavior_verified: false`: this is not verified miniPaint behavior.
- **File edit â€” passed, 5.902 seconds:** agent invoked the file tool once, creating
  `add.py`. An AST allowlist rejects imports, calls, annotations, decorators,
  defaults, external names, and extra statements before execution. Python verified
  `(2,3)`, `(-7,10)`, `(0,0)`, `(123456,-654321)` â†’ `[5,3,0,-530865]`.
- **Usage:** structured check 8,048 total tokens (7,921 input, 127 output); file
  check 15,968 (15,901 input, 67 output, 7,680 cached input). Cached tokens are
  included in input. Use `usage.total` across tool turns, not `usage.last`.

Artifacts: `.scratch/20261010-095153-5fed201b/add.py` and `report.json`.
Public runtime protocol schemas inspected during setup are in `.scratch/protocol/`.
The initial run completed inference but failed a strict conversation-event check;
that validator was corrected before the successful rerun. No runtime errors in
this successful run.

Usage is `null` if telemetry is unavailable, and is not an invoice or dollar
estimate. Account quotas/rate limits may prevent reruns. Dynamic tools and some
protocol fields are experimental; future CLI versions may require updates.

## Offline checks

```powershell
python -m unittest -v test_smoke
```

Five tests passed: structured validation, unsafe code rejection, deadlines/exits,
RPC failure and usage handling, and path/overwrite rejection. No inference needed.

## GitHub Actions

`.github/workflows/ci.yml` runs syntax checks, the offline tests, and CLI help on
pushes, pull requests, and manual dispatch. It checks Python 3.12 on Linux and
Python 3.14 on Windows with a five-minute job timeout and read-only repository
permissions. Official actions are pinned to verified commit hashes.

CI needs no Codex login, secrets, or model requests. The two live model checks
remain local: run `python smoke.py` with your ChatGPT sign-in. Deployment is
deferred until there is an application to deploy.

## Reference adapter milestone

See [README-adapter.md](README-adapter.md) for separated workspaces, the supported headed
miniPaint validation command, headless mismatch results, and recovery. The model smoke
command and authentication route above remain unchanged.

## Editor shell milestone

See [README-shell.md](README-shell.md) for the local editor, layout evidence,
restricted generation invocation, exact upload/export checks, and limitations.

## Deterministic evaluator milestone

See [README-evaluator.md](README-evaluator.md) for independent raw-RGBA metrics,
versioned exact/provisional policies, controlled examples, and the four-case baseline
command. Blur implementation and the learning loop remain deferred.

## Bounded learning harness milestone

See [README-learning.md](README-learning.md) for the sequential Gaussian Blur harness,
actual model responsibilities, supplied procedures, hard budgets, frozen visible
evaluation, restricted builder and checkpoint/restore behavior. Run
`.venv\Scripts\python.exe -m learning.run` from a genuinely unavailable blur start.
All real attempts, including rejected contracts/candidates, remain in evidence/learning.
The latest pointer is evidence/latest-learning.json. No final holdout or push.

Actual results: [milestone 5 report](evidence/milestone5-results.md). The bounded
integrated attempt completed, but blur compatibility did not pass; baseline preserved.

## Brightness second-feature milestone

See [README-brightness.md](README-brightness.md) for the explicitly scoped Color Corrections brightness procedure, bounded harness specialization, exact policy and actual-run artifacts. Blur remains experimental and isolated; brightness status is reported separately.
