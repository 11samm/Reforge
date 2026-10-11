# Bounded Gaussian Blur learning harness

This milestone uses a sequential deterministic Python orchestrator around the verified
local Codex app-server, headed miniPaint adapter, restricted generated-app file broker,
and independent raw-RGBA evaluator. Only Gaussian Blur is in scope. No parallel agents,
new provider/framework, protected data access, final holdout, or push is involved.

## Run

From `D:\Samuel\Downloads\Code\Reforge`, with the existing signed-in Codex runtime,
Node 24 and installed `.venv`/generated-app dependencies:

```powershell
.venv\Scripts\python.exe -m learning.run
.venv\Scripts\python.exe -m learning.run --config learning.config.json
.venv\Scripts\python.exe -m unittest -v test_smoke test_adapter test_shell_boundary test_evaluator test_learning
```

The learning command requires a genuinely unavailable blur start state: no
`src/gaussian-blur.ts`, and the existing unavailable-dialog verification must pass.
It snapshots the generated workspace before any model invocation or reference
experiment. It refuses to silently restart from an implemented blur state.
Checkpoint manifests preserve the start and every completed candidate. Restoring
a checkpoint changes only the declared generated sources, not evidence, policies,
expected exports, the evaluator, or trusted host code. Production `dist` is rebuilt.

Exit 0 means the first candidate accepted on every visible blur gate and all exact
baseline gates, with final build/baseline checks passing. Exit 1 means unresolved
behavior or an infrastructure/budget stop, with baseline/best-known state restored.
The printed JSON events contain remaining budgets and link the readable report.
`evidence/latest-learning.json` points to the latest real attempt.

## Packet limits and measurement

Every initial model invocation packet is measured before sending (`learning/packets.py`). The measurement covers fixed instructions,
payload, output schema and the source files a builder is told to read. Tokens are estimated with a
regex piece count plus a fixed 7,720-token runtime overhead. Calibrated on recorded attempt 1/2
decision calls, it lands within 0.6% of actual `inputTokens`. That is accuracy on historical calls,
not a guarantee for future requests, and it is not the provider tokenizer. Limits leave headroom over
current packets. Each run's `report.json`/`report.md` puts the provider-reported input tokens beside
every estimate (builder usage is compared with the cumulative multi-round projection).
`packet_limits` in the config sets hard per-role byte/token ceilings (planner, contract, route,
builder, repair). An oversized initial packet stops the run with `packet_limit_exceeded` and sends no request. These ceilings cover the initial assembled context for each invocation, not every subsequent tool round or cumulative invocation/run usage. Tool responses and conversation growth are bounded separately by file sizes, evidence-read sizes and call counts; projected cumulative tokens are telemetry estimates, not enforced quotas.
Evidence is never silently truncated. `builder_tool_calls` (default 12, was 24) caps builder tool rounds.
`evidence_reads` (default 6) caps a bounded read-only `evidence_read` tool that returns one exact visible
row/column of an input, reference export or last candidate output.

Packets now use exact channel-run profiles (`"RGB": "0*30 6 25 41 25 6 0*30"`) with decode checks.
Generated inputs are replaced by their generator spec only after the recorded PNG is verified to
decode identically. Shared target metadata appears once. Repair/route packets carry scoring policy once, failing
reasons/regions, worst pixels and exact candidateâˆ’expected deltas; passing cases are one line.
Paths, artifact lists and full per-case reports are omitted. Offline report (no model):
`.venv\Scripts\python.exe -m learning.packet_report` writes [packet sizes](evidence/packet-sizes/report.md).
Each run writes `packet-sizes.json`.

## Development resume (not a clean-start demonstration)

```powershell
.venv\Scripts\python.exe -m learning.run --resume-from evidence/learning/20261010T184129Z-78c8e934 `
  --candidate candidate-2 --workspace dev-workspaces/candidate-2 `
  --dev-evidence evidence/learning/20261010T213804Z-09ff82cb-dev-followup [--prepare-only]
```

The run verifies the source suite hash, candidate checkpoint, contract and evidence. It copies the candidate
into `dev-workspaces/<name>` (or verifies an existing copy matches exactly) and builds, gates and edits
only there. `generated-app` is hash-protected for the whole run and nothing is promoted implicitly. The selected candidate is
re-evaluated as the experimental base. Every repair starts from it, or from a later feasible
rejected candidate that strictly improves the objective on the same suite. The accepted/best-known
state is tracked separately and remains none until all gates pass. `--dev-evidence` freezes an expanded
suite, and the base and all candidates are scored on it. Provenance records `mode: development_resume` and
`clean_start_autonomous_demonstration: false`. The latest pointer is `evidence/latest-learning-dev-resume.json`.
`--prepare-only` measures and enforces the next contract/route/repair packets and never contacts a model.
Clean-start `python -m learning.run` is unchanged and still requires the genuine no-blur app.

Contract alignment: if any suite evidence is cited by no claim in the reused contract (with
`--dev-evidence`, the follow-up rows), a live resume first makes one contract update
(`contract-resume`) so the contract and builder packets describe the same knowledge. Anything still
uncited is listed in the builder packet as `unincorporated_evidence` (raw observations, not contract
knowledge), and developer rows are listed as `developer_selected_evidence`. `--prepare-only` measures
that contract update and shows the pre-update builder packet, with the label.

Developer follow-up evidence (`python -m learning.followup`, at most six, chosen by a developer):
[observations](evidence/learning/20261010T213804Z-09ff82cb-dev-followup/observations.md) and
[next-repair notes](evidence/learning/20261010T213804Z-09ff82cb-dev-followup/next-repair.md).
Interpretations there are hypotheses unless a distinguishing experiment is cited. The developer generators
(`DEVELOPER_DEFINITIONS`: uniform low alpha, adjacent alpha, hidden RGB) and the suggested next patterns
are **not selectable by the model planner**, whose schema allows only the fixed `KINDS`. Using them is
developer-assisted debugging; an autonomous run would need bounded planner support added first.

CI fixtures: `test_learning` reads only the saved files listed in `fixtures/learning-ci-files.txt`
(47 files, ~0.87 MB of the attempt-2 run and pre-change prompts). Commit those, not whole run archives.
Saved records hold absolute paths from the machine that wrote them; `learning.core.relocate` maps
`evidence/`/`fixtures/` paths onto the current checkout, and hashes are still verified.
`python -m learning.ci_fixtures` regenerates the list; `--check` runs the offline tests from a
clean copy at another path containing only code and those fixtures.

## What is autonomous and what is supplied

The model selects new diagnostic inputs and exact integer Percentage values, states
competing hypotheses and predicted distinguishing observations, summarizes exported
evidence, updates structured claims, writes an independent operation, and suggests
failure classification and the next action. These are bounded decisions through
`gpt-6.1-sol` at `medium`, using the existing ChatGPT-managed sign-in. No API key,
fallback model, unrestricted shell, browser evaluation, or delegation is provided.

Ordinary code supplies the pattern generator (center/boundary impulses, edges,
gradients, checkerboards, RGB bands and partial alpha bands), document/import/blur/
export procedures, schemas, artifact storage, deadlines, acceptance rule, fixed
build commands, regression checks and checkpoint restores. The first planner
requests four experiments, each 3..257 pixels per side. It does not merely replay
gb010/gb017: those two permitted development cases supplement actual fresh exports.
After rejection, the model can suggest a bounded repair or 1..4 new experiments.
No unbounded unattended loop is launched.

`learning.config.json` defaults to 12 fresh reference attempts, three implementation
candidates, 600 seconds total and a 100-second cleanup reserve. Hard schema ceilings
are 20 fresh attempts, five candidates and 600 seconds; per-model/worker deadlines
and zero or one reference retry are configurable. A retry consumes another fresh
attempt. The declared experimental Percentage domain is 0..10 by default, within
the visible UI range 0..50. Percentage is never assumed to equal a pixel radius.
Individual worker process trees terminate at their parent deadlines. New learning
work stops when only the reserve remains; final rebuild/regression/restore uses
the remaining total budget.

## Evidence and contracts

Each experiment records its question, hypotheses, input specification, requested
and accepted Percentage, predictions, usefulness, target/version, action screenshots,
visible-DOM failure diagnostics, original-confirmation export, output PNG and hashes.
Reset/import/export failure is infrastructure failure; it contributes no behavior
claim. Only actual miniPaint exports supply new expectations. Original development
inputs and expected outputs remain unchanged. Export sample summaries are decoded
from those user-visible PNGs, not browser canvas/hidden application state.

Claims have IDs/statements, UNKNOWN/HYPOTHESIS/OBSERVED/VERIFIED_WITHIN_SCOPE/
CONTRADICTED status, target version, setup, parameter domain, scope, supporting and
contradicting evidence IDs, alternatives, unresolved questions and verification
cases. Unknown evidence IDs and unsupported verification status are rejected.
A matching candidate verifies scoped implementation parity; it does not prove
miniPaint's hidden mechanism. Raw chain-of-thought is not stored; invocation records
retain prompts, concise returned decisions, tool audits, item types, elapsed time,
model/provider/authentication type and available token usage, without credentials.

## Frozen evaluation and promotion

Every visible-suite version freezes case paths, input/expected SHA-256 hashes, exact
baseline policy, the existing `blur-provisional-v1` policy and named regions before
candidate comparison. Each image receives the full-image gate plus a clipped center
11x11 region and the full-height left four-pixel boundary. These are supplied region
rules, chosen before candidate errors and applied consistently; they are not learned
or tuned to candidate quality. The provisional policy and evaluator stay unchanged.

The objective lexicographically minimizes the number of failed cases, then the
equal-case-weight mean of each case's worst full-image/region raw RGBA MAE
`(3*RGB_MAE + alpha_MAE)/4`. A candidate can promote only with a valid build,
independent execution, passing exact baseline regressions and every visible blur
gate. Lower loss breaks comparisons; exact ties retain the incumbent. The no-blur
incumbent is explicitly unavailable rather than assigned fake blur output.
When new experiments expand the suite, both the restored incumbent and the next
candidate rerun against that same frozen version. First acceptance is recorded
separately, and this milestone stops there; it does not invent later improvements.

The four exact baseline pixel cases remain opaque/transparent round trips,
same-document replacement, and current-state mutation/export. `--allow-blur` only
permits the planned implemented-dialog copy in the shell verifier; the empty
document must still disable Percentage/Apply. Untouched-image expectations and
all four exact pixel tolerances are unchanged.

## Builder and execution boundaries

The builder receives a compact packet of contract claims, selected visible export
samples, discrepancies and permitted app files. The same environment-disabled
runtime and `shell_read_file`/`shell_write_file` broker are used. Writable files are
`src/main.tsx`, `src/current-image.ts`, `src/gaussian-blur.ts` and app README; CSS is
read-only, dependencies/configuration/lockfile and all other roots are denied.
Traversal, alternate data streams, links/junctions, hardlinks, execution requests
and unexpected tools are rejected. File sizes and broker calls remain bounded.

Trusted build commands invoke installed TypeScript/Vite directly rather than
model-edited package scripts. A separately bundled trusted Node entry invokes
`applyGaussianBlur(raster, percentage)` using only input images and writes fresh
PNGs. The reference controller is already closed. Node's permission model limits
filesystem access, child processes and native addons; an explicit trusted preloader
denies standard network APIs and probes net/https/fetch denial before execution.
Node permissions alone do not constrain networking in the installed version.
The local production UI also applies Blur and exports, compared exactly against
the batch result, with external HTTP requests blocked and recorded.

These are application/tool/process capability restrictions, **not OS sandboxing**.
The trusted host/build/verifier is not claimed to resist a hostile concurrent
process or arbitrary malicious generated code. Protected-file manifests detect
changes to trusted code, original development files and frozen expectations;
potential evaluator faults stop promotion. The implementation runs without a
reference browser, reference output files or miniPaint network access.

## Failure records and limitations

Routing distinguishes procedure/infrastructure, missing evidence/incorrect hypothesis,
implementation defect, evaluator defect, baseline regression and ambiguity/budget
exhaustion. Model classifications are suggestions with evidence IDs; trusted code
owns promotion. Rejected candidate source snapshots, evaluations and failure records
remain after restoring only the generated workspace. Controlled invalid rollback
fixtures exist only in offline tests; real run failures are not manufactured.

Visible About version 4.14.3 does not pin the hosted build. Headed reference viewport
remains 1440x1000 at scale1, en-US and America/Los_Angeles. Optional window placement
defaults to the already validated `[1600,0]`; set it to `null` for normal placement.
Do not interact with the reference browser during the run. Headless remains
unsupported for reference equivalence. Local generated-app verification is headless.
Scoring is 8-bit single-frame raw RGBA; 16-bit blur and broader browser/dimension/
parameter compatibility remain outside the verified scope. This is one operation,
not whole-editor reconstruction.

## Actual milestone outcome

[Milestone 5 results](evidence/milestone5-results.md) reports both real attempts.
The second completed experiment/evidence/contract/implementation/evaluation path
within 508.5 seconds. No candidate passed all six blur gates; the no-blur baseline
was restored with an exact source-hash match. Final build, four exact baselines
and 38 offline tests pass. Candidate 2 executed independently and passed baselines,
but only three blur cases. First acceptance and later improvements are both none.

After the real attempt, the host was hardened for punctuation-safe Percentage
selectors, explicit procedure/UI/batch classification, unscored unavailable output,
per-write source journals, partial checkpoints, lossless run-length profile packets,
repair-routing context and future trusted-source/policy archives. These changes were
validated with deterministic tests and baseline checks; no third live run was launched.
Candidate 3â€™s missing final partial source text and other historical bookkeeping
limitations are disclosed in the report; original real records were not rewritten.

Post-attempt development (no model requests): packet limits/compaction, development resume,
an isolated candidate-2 workspace that reproduces its historical metrics exactly, and four admitted
developer follow-up exports. Two follow-ups were import limitations: low-alpha color is quantized and hidden RGB
is normalized on import. Candidate 2 fails 6 of 10 cases on the expanded suite. 60 offline tests pass after independent verification hardening.


## Bounded boundary-alpha development repair

A developer-scoped resume can use `--repair-focus boundary-alpha` with a config
containing exactly one candidate. It supplies the saved operation once, P7 exact
alpha profiles/pixels, all failing-case metrics and passing constraints. The broker
permits only `src/gaussian-blur.ts` writes and operation/type-source reads; no
additional evidence tool is supplied. This is explicitly developer-assisted work.
Build/evaluation/baselines remain trusted-host tasks. The deadline comes from the
provided config on the resume path, including `--prepare-only` packet checks.

`--aligned-contract <prior contracts/contract-resume.json>` verifies the completed
invocation, ordered visible case hashes/percentages, scoring/region rules and
citations before reusing the prior contract and copying its exact frozen suite.
A mismatch stops before a model request. This avoids another paid alignment call.

[Bounded repair report](evidence/bounded-repair/report.md) records one live attempt
with [its configuration](evidence/bounded-repair/config.json): 160-second builder,
360-second overall limit, 100-second reserve, one candidate, four calls and no
evidence reads. Builder completed in 41.256 seconds; the run took 73.443 seconds.
The same ten-case suite improved from four to five passes; all three P7 boundary
alpha gates now pass, while five RGB failures remain. Build, independent execution,
UI/batch agreement and all four exact baselines pass. Compatibility remains
rejected. The isolated workspace contains a labeled experimental improvement;
main generated-app is unchanged. No automatic retry or next milestone was started.
The offline suite and isolated CI fixture check now pass 63 tests.

## Investigation guidance input and blur closure

Planner and route packets append a code-selected section from the versioned global
[investigation guidance](learning/investigation-guidance.json) (`guidance.py`). It is labeled as strategy rather
than target evidence and has size limits that raise instead of truncating. Each run records its id/version/sha256
in provenance, and per-packet strategy IDs in `guidance-selections.json`. Lessons and evidence:
[docs/investigation-lessons.md](docs/investigation-lessons.md). miniPaint-specific observations are only in
[docs/target-findings/](docs/target-findings/minipaint-gaussian-blur.md) and never enter packets.
The final developer-selected blur test ([report](dev-workspaces/blur-final/report.md)) found no general
mechanism, so the blur investigation is closed. Compatibility remains 5/10 and 7/14. 67 offline tests pass.
