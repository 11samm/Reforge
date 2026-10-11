# Bounded feature pipeline — implementation note

The feature entry point adds visible workflow discovery before the existing
investigation/reconstruction/evaluation loop. Contrast is the only accepted new
request. Its reference menu names, dialog name, control selectors, domain, defaults
and other-control settings are not supplied by developer-authored Contrast code.
The runtime must observe and return them. Test selectors describe explicitly local
mock pages, not a miniPaint Contrast procedure.

## Reuse and new boundaries (step 1)

`adapter/minipaint.py` still owns headed reset, exact original import confirmation,
single-layer/dimension checks and newly triggered PNG downloads. `adapter/brightness.py`
and the existing brightness entry point are preserved. A shared process lock now
prevents two reference adapters from controlling browsers concurrently.

`learning/core.py` and `learning/run.py` supply budgets, deadline-controlled workers,
frozen hashes, checkpoints, trusted-source guards, independent build/execution,
exact shell regressions and restoration. The evaluator and thresholds are unchanged.
`learning/model.py` uses the same environment-disabled app-server/provider; it accepts
an explicit discovery capability broker, or the narrow Contrast builder broker.
`learning/operations.py`/`worker.py` add one specification-backed operation registration.
The candidate export function and candidate UI contract are trusted host interfaces,
not discovered reference selectors.

The new abstractions are deliberately small: a v1 discovered specification, a visible
tool broker, an interpreter of role/label/labeled-row procedures, and a parameterized
numeric adjustment harness. It does not execute model-generated browser code.
`features/learning.py` reuses bounded image generators as possible probes, while the
planner chooses questions, competing hypotheses, predictions, inputs and values.
No brightness formula, neutral parameter, or brightness reference result is offered
as Contrast evidence. Existing brightness source is read-only and hash-protected;
its six original visible cases and UI/batch agreement are regression gates. Their
expected pixels stay outside the Contrast model context.

## Evidence and discovery (steps 2–4)

`features/feature-spec.schema.json` and `spec.py` define the versioned structure and
semantic validation. Facts cite observation IDs; hypotheses and unresolved questions
are separate. Null ranges/defaults remain unresolved. Grounding checks the observed
native numeric attributes for the identified visible control, and rejects omitted
numeric dialog controls. Unknown facts, nonnumeric controls, ambiguous locators,
unsupported targets and unresolved setup stop execution.

Visible tools expose rendered accessibility, a fixed visible-DOM projection, viewport
screenshots, unambiguous clicks and bounded numeric setting/readback. They cannot
accept JavaScript, selectors, shell commands, filesystem paths, navigation URLs,
source/network response requests, hidden state or canvas extraction. Page text is
explicitly untrusted. Observation evidence and concise returned decisions are stored;
raw reasoning is not retained.

Discovery: one invocation, zero retries, 90 seconds, 20 UI actions, 24 observations/
tool calls including initial inspection. An inspection is at most 16 KB; screenshots
are at most 800 KB each, with a 1.8 MB cumulative observation limit. Oversized data
stops discovery rather than silently discarding facts. Provider/tool/process deadlines
bound runtime; these are application capability restrictions, not an OS sandbox.

Only observed defaults can freeze other controls initially. A separate default-settings
diagnostic export must match the input exactly before reconstruction. This establishes
the combined default setup on that diagnostic, not an algorithmic proof of global
neutrality. Two fresh-document nondefault replays must import exactly, resolve controls,
set/read back every setting, close the dialog, export a fresh correctly sized PNG and
agree exactly. Requested/accepted settings, hashes, action screenshots and failures
remain in the private evidence archive. Discovery failure, procedure failure and
repeat/default behavior mismatch are distinct outcomes.

## Learning and acceptance (step 5)

Candidates are copied to `dev-workspaces/feature-<job-id>`; dependencies are copied
locally, without installation commands. The accepted `generated-app` is hash-protected
and is never promoted or edited. The builder may write only `src/main.tsx`,
`src/contrast.ts` and its README; the inherited file broker rejects escaping paths,
links, streams and hardlinks. It cannot read reference output files or final outputs.

The planner selects 2–4 bounded distinguishing experiments from the discovered integer
domain, including two different values. Evidence-backed claims precede building.
There are at most two candidates, 12 builder calls each and six bounded evidence reads.
Each candidate is independently executed and evaluated on the same frozen exact-RGBA
suite, checked against UI export, four existing exact editor baselines and brightness
regressions. Failures restore the prior checkpoint; partial writes remain isolated.
After visible acceptance and cleanup, two new final inputs/values are evaluated once,
after all model/repair calls end. A final failure is not repaired. Job acceptance
requires this separate final evaluation too, and means only parity on those recorded
cases. It never promotes the editor automatically.

## Local jobs and presentation (step 6)

`features/service.py` binds to 127.0.0.1 only. Its API accepts only a feature request
and cancellation, with bounded JSON, host/origin checks and explicit action headers.
It exposes no arbitrary command/path or repository-file endpoint. Service/CLI jobs
share an exclusive process lock; the reference adapter also shares a lock with legacy
brightness/blur controllers. Conflicting feature jobs return HTTP 409. Concurrent
legacy browser activity either prevents startup or produces a procedure failure.

The owner spawns a fixed child module with a validated job ID. On Windows, an OS job
object terminates descendants if the owner exits; the child waits for ownership
assignment before launching anything. Cancellation and the 600-second overall deadline
kill the process tree and cannot be converted into acceptance, even if termination
returns exit code zero. Restart recovers interrupted jobs as failed (or cancelled if
cancellation was requested), never accepted. Job state and sequenced events are written
atomically. Polling reconnects to the durable log and does not need a background model.

The dashboard uses a separate local-jobs view and labels it distinctly from recorded
playback. Existing inspector/replay screens remain available. `data/live.ts` keeps
legacy event parsing while deduplicating sequenced reconnect events; `data/jobs.ts`
requires explicit timing for jobs and only exposes evidence after its availability
event. The API serves only allowlisted scrubbed JSON presentation copies, not model
packets, reference/final expected PNGs or arbitrary files. Full action diagnostics
remain local in the archive; no general archive browser was added.

## Offline results and live limitations (steps 7–8)

No discovery, reference learning or reconstruction model invocation was run during
implementation. Local Playwright mock pages test control ambiguity, changed domains,
readback rejection, bounded inspection and the existing fresh-download exporter.
Saved brightness pairs reproduce exactly. Provider interaction and real miniPaint
Contrast discovery/procedure/behavior still need the explicitly authorized pilot.

Initial learning support is integer-valued numeric raster adjustments, exact 8-bit
single-frame PNG evaluation, one imported layer and the existing headed environment.
Fractional domains, custom nonnative widgets, ambiguous labels and unsupported setup
stop honestly. Hosted reference build is unpinned. A model can return unresolved even
if a human could find the control. The budget includes setup/dependency copying,
discovery, validation, learning, cleanup and final checks; exhaustion is a valid failed
pilot outcome. There is no hard provider token/cost ceiling: actual reported usage,
packet ceilings, tool output bounds and elapsed deadlines are recorded. Do not present
those as a guaranteed subscription-token quota.

Acceptance of a live Contrast feature has not been established. The deliverable is
offline-tested infrastructure and a bounded future pilot, not a working Contrast
implementation or an autonomous-success demonstration.
