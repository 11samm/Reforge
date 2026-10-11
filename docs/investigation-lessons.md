# Investigation lessons for feature-learning runs

These are target-independent lessons from the Gaussian Blur investigation (2026-10-10). Each one says
when it applies, what to do, what evidence is required, where it falls short, and which runs or
experiments support it. Target-specific numbers are kept separately in
[target-findings/minipaint-gaussian-blur.md](target-findings/minipaint-gaussian-blur.md). That file
describes one target and operation and must not be read as advice for any other feature.

The harness gives future runs a compact, code-selected subset of these lessons through
[learning/investigation-guidance.json](../learning/investigation-guidance.json) (`G1`–`G9` map to `L1`–`L9`).
See [How runs receive this guidance](#how-runs-receive-this-guidance).

Abbreviations for evidence locations (all under `evidence/`):
- **A1**: `learning/20261010T183813Z-8b39a334` (attempt 1)
- **A2**: `learning/20261010T184129Z-78c8e934` (attempt 2)
- **FU**: `learning/20261010T213804Z-09ff82cb-dev-followup` (developer follow-up)
- **BR**: `bounded-repair/` and `learning/20261010T224627Z-c87f41fb-dev-resume`
- **PF**: `learning/precision-followup-20261010` and run `learning/20261010T230409Z-414ee17c-dev-resume`
- **FD**: `dev-workspaces/fable-diagnostic`
- **BF**: `dev-workspaces/blur-final` with exports in `evidence/learning/blur-final-20261010`

---

## L1. Verify import/reset/export before attributing a difference to the feature

- **Trigger:** any new reference experiment, or any discrepancy that could come from how input reached
  the target rather than from the operation.
- **Action:** reset to a fresh document, import, and export *before* the operation, then compare that
  export byte-for-byte (RGBA) with the supplied input. If it differs, record a collection limitation and
  make no behavior claim.
- **Required evidence:** an original-confirmation export with `rgba_equal: true`, `different_pixels: 0`,
  and accepted parameter equal to the requested parameter.
- **Limitations:** this proves only that the round trip is lossless for *that* input. Low-alpha colour and
  hidden RGB were altered by import, so those properties cannot be observed through this procedure at all.
- **Support:** FU dev-03 (low-alpha colour quantized on import) and dev-05 (hidden RGB normalized to black)
  in [observations](../evidence/learning/20261010T213804Z-09ff82cb-dev-followup/observations.md); PF all four
  confirmations exact ([stop decision](../evidence/learning/precision-followup-20261010/stop-decision.json));
  BF exp-a/exp-b exact ([report](../dev-workspaces/blur-final/report.md)).

## L2. Separate automation, model/specification, implementation, evaluator and regression failures

- **Trigger:** any rejected candidate or stopped run.
- **Action:** classify each failure on its own:
  - procedure/automation (reset, import, export, timeouts);
  - model/specification output (invalid schema, sentences in ID fields, a plan that doesn't match the
    generator);
  - missing evidence or a wrong hypothesis;
  - implementation defect;
  - evaluator defect;
  - baseline regression.

  Give each class its own next action. Do not change feature behavior to fix a procedure, evaluator or
  regression failure.
- **Required evidence:** gate results (build, independent execution, UI/batch agreement, baselines), the
  per-case failure reasons, and the evidence IDs behind each classification. Classifications suggested by
  the model are advisory; trusted code owns them.
- **Limitations:** some failures can't be attributed from the records. The bounded-repair builder
  timeout had no per-round timestamps, so "too broad an assignment" is plausible but not established.
- **Support:** A1, where the contract was rejected for sentences in evidence-ID fields and plan
  descriptions didn't match generators ([milestone 5](../evidence/milestone5-results.md));
  BR [diagnosis](../evidence/bounded-repair/diagnosis.md) (timeout treated as procedure/scope, not behavior).

## L3. Design matched experiments that vary one relevant factor

- **Trigger:** two or more hypotheses explain the current evidence equally well.
- **Action:** change one factor (size, position, parameter, contrast direction, distant content) and hold
  the rest fixed. Preregister each hypothesis's numerical prediction before export. Name the confounds the
  design cannot separate.
- **Required evidence:** a preregistration file timestamped before the exports, and the actual result
  placed next to each prediction.
- **Limitations:** a single matched pair rarely separates more than two hypotheses. Atlas-style inputs
  that combine several panels add confounds from shared remote content. Some designs need input patterns
  the model planner cannot express (see [Limitations](#limitations-requiring-developer-selected-patterns)).
- **Support:** FU dev-01/dev-02 (matched impulse/edge); PF precision-01/02 (exact transpose);
  BF exp-b (same input, P4 vs P7) separated parameter dependence; BF exp-a showed that "same local
  geometry" does not reproduce dev-02.

## L4. Use deterministic hypothesis calculations and numerical profiles

- **Trigger:** gate metrics say a case fails but not why.
- **Action:** compute each hypothesis's exact predicted profile with a small script, compare it with
  exact exported profiles, and keep the script with its output. Measure *every* instance of a feature,
  including mirrored or opposite-direction instances, before generalizing.
- **Required evidence:** a reproducible script, its saved output, and per-instance values (not only an
  aggregate).
- **Limitations:** a scanner bug can silently drop a whole class of instances. Fable's edge scanner
  returned nothing for falling edges, so a "per-image displacement" was inferred from rising edges only.
  Profile fits describe data; they do not identify mechanisms.
- **Support:** FD `step1`–`step4` scripts and JSON; BF [analyze.py](../dev-workspaces/blur-final/analyze.py)
  ([results](../dev-workspaces/blur-final/results.json)), where the atlas falling edge at x=128 contradicted
  the rising-edge interpretation.

## L5. Distinguish usable, experimental and verified feature states

- **Trigger:** reporting progress, or deciding whether to promote a candidate.
- **Action:** use exactly three labels:
  - **usable**: every visible gate and baseline passes on the frozen suite, and the candidate is promoted;
  - **experimental**: improved but failing, kept in an isolated checkpoint, never promoted;
  - **verified within scope**: parity on stated inputs, parameters and version.

  Always quote pass counts on a named suite hash.
- **Required evidence:** the frozen suite SHA-256, per-case pass/fail, baseline results, and the
  checkpoint manifest.
- **Limitations:** "verified within scope" means implementation parity on visible cases. It says nothing
  about the hidden mechanism or about held-out cases.
- **Support:** BR (4/10 to 5/10, experimental checkpoint, main app unchanged,
  [report](../evidence/bounded-repair/report.md)); PF (7/14 expanded suite,
  [report](../evidence/learning/precision-followup-20261010/report.md)).

## L6. Avoid fitted special cases without validation on fresh development cases

- **Trigger:** a correction reduces error but its parameters were estimated from the failing cases.
- **Action:** state the general rule before coding it. Reject corrections keyed to dimensions, case IDs or
  fitted constants. Validate on development cases that were not used to fit it.
- **Required evidence:** a prediction made by the rule on at least one fresh case, checked against a new
  export.
- **Limitations:** a fitted correction can still be the best available engineering choice. Label it
  experimental and keep it out of promotion.
- **Support:** BR's Percentage-7 alpha lift was a fitted observational correction (it passes three alpha
  gates, but its generalization is unverified). FD's per-image displacement fitted four failing cases but
  did not predict the falling edge in the same image or the new geometry in BF exp-a.

## L7. Keep prompts compact, retrieve bounded evidence, and repair narrowly

- **Trigger:** builder timeouts, or packets near their limits.
- **Action:** supply source once, provide only the exact profiles relevant to one failure class, keep
  passing-case constraints, cap tool calls and evidence reads, and never silently truncate evidence (stop
  instead).
- **Required evidence:** per-role packet measurements against hard limits, plus provider-reported token
  usage next to the estimates.
- **Limitations:** packet limits cover initial context, not cumulative tool rounds. A narrow repair can
  improve one gate while leaving others unchanged.
- **Support:** [packet sizes](../evidence/packet-sizes/report.md); BR packet 43,364 to 20,866 bytes, with
  the builder completing in 41 s where the broad assignment had timed out at 160 s.

## L8. Resume from reproducible candidate/evidence checkpoints

- **Trigger:** continuing after a rejected candidate, or after adding evidence.
- **Action:** resume from a hash-verified checkpoint in an isolated workspace. Re-evaluate the restored
  base on the same frozen suite first, and compare old and new candidates on the same suite and policy.
  Never promote implicitly.
- **Required evidence:** the checkpoint manifest, the suite hash, and an exact reproduction of the base
  metrics before any new candidate is scored.
- **Limitations:** saved records contain absolute paths (relocation is needed), and some historical
  bookkeeping gaps can't be repaired retroactively.
- **Support:** README "Development resume"; the candidate-2 workspace reproduced its historical metrics
  exactly; PF reproduced all original ten-case metrics exactly before scoring the expanded suite.

## L9. Stop when uncertainty or budgets prevent a supported next action

- **Trigger:** no hypothesis is supported strongly enough to implement, or the remaining budget can't buy
  a distinguishing experiment.
- **Action:** stop. Record what is unknown and what experiment would separate it. Do not escalate model,
  budget or scope inside the same task.
- **Required evidence:** a stop decision listing the basis, the remaining confounds, and the reason for not
  repairing.
- **Limitations:** stopping leaves compatibility unresolved. That is an honest outcome, not a failure of
  the harness.
- **Support:** PF [stop decision](../evidence/learning/precision-followup-20261010/stop-decision.json)
  (builder call deliberately unused); FD "Proposed implementation change: none yet"; BF closed at the
  timebox with no exploratory implementation.

---

## How runs receive this guidance

- **What is sent:** `learning/investigation-guidance.json` (schema `reforge-investigation-guidance/1`,
  version `1.0.0`) holds nine one-sentence strategies. `learning/guidance.py` loads and validates it and
  selects strategies with ordinary code:
  - the planner always gets `planning` strategies (G1, G3, G4);
  - the route packet gets strategies whose triggers match signals computed from the trusted result
    (`any_failure`, `behavior_mismatch`, `partial_progress`, `infrastructure`, `baseline_regression`,
    `evaluator_suspect`).
- **Labeling:** the section is labeled as global strategy, not target evidence and not contract claims.
  The model cannot choose, edit or extend it.
- **Provenance:** each run records guidance `id`, `version`, `source` and `sha256` in `provenance.json`
  and `report.json`. Per-packet signals and strategy IDs go to `guidance-selections.json`. The JSON file
  is a protected host file, archived in `executed-host-source/`.
- **Separation from target claims:**
  - loading rejects strategy text containing target/operation vocabulary (miniPaint, Gaussian, blur,
    Percentage, sigma, kernel, premultiplied) or evidence-ID shapes (`dev-02`, `precision-01`, ...);
  - scope must be `global`;
  - the target findings file is never placed in packets;
  - behavior claims still come only from exact evidence IDs.
- **Size limits:** at most 260 characters per strategy, 2,600 bytes per packet section and 8,000 bytes
  per file. Exceeding any of them raises an error; nothing is truncated. Measured with guidance:
  - planner: 3,431 bytes and 8,515 estimated tokens, against limits of 8,000 and 11,000;
  - route (attempt-2 fixture): 12,114 bytes and 11,940 estimated tokens, against 32,000 and 22,000.
- **Not wired yet:** builder, repair and contract packets do not receive guidance.

## Limitations requiring developer-selected patterns

The model planner may only choose the fixed generators in `learning/diagnostics.py` (`KINDS`) with
dimensions and an integer parameter. Several designs recommended by L3/L4 cannot be expressed that way.
Those include a band whose two edges sit at chosen positions (exp-a), any edge whose position is held
fixed while the dimensions change (the `edge` generator always places it at `floor(width/2)`), and
fixed-content/varied-dimension series. This task did not expand the planner's generators. Until bounded
planner support exists, such experiments are developer-selected and must be labeled that way, as in
FU, PF and BF.
