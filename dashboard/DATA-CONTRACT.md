# Dashboard run-data contract

The dashboard reads static JSON from `public/runs/` and nothing else. It never
reads the harness archive, the repository, or arbitrary filesystem paths. A
trusted host turns a run directory into a **run bundle**. The dashboard's
normalization layer (`src/data/normalize.ts`) turns that bundle into the
view model the UI renders.

Types: `src/data/bundle.ts` (input) and `src/data/normalize.ts` (output).
Tests: `src/data/normalize.test.ts` (`npm test`).

## Files

```
public/runs/
  index.json                      # list of selectable bundles
  <bundle-id>/
    manifest.json                 # one run bundle
    artifacts/...                 # PNG/JPG files referenced by the manifest
```

`index.json`:

```json
{ "runs": [
  { "id": "recorded-20261010T184129Z-78c8e934", "title": "…", "kind": "recorded",
    "manifest": "recorded-20261010T184129Z-78c8e934/manifest.json" }
] }
```

The first entry is the default bundle. `?run=<id>` selects another one.

## Bundle (`schema: "reforge.run-bundle"`, `schema_version: 1`)

Every field is optional. Missing data means "not recorded", never success.

| Section | Contents |
| --- | --- |
| `provenance` | `kind` (`recorded`, `synthetic`, `live`), `source`, `exported_at`, `exporter`, `note`. Drives the RECORDED PLAYBACK and SYNTHETIC labels. |
| `run` | `id`, `operation`, `target` (name, visible About version, build), `scope[]`, `config` (budgets), `status`, `stop_reason`, `elapsed_seconds`, `first_acceptance`, `final_build_status`, `final_baseline_pass`. |
| `events[]` | Harness events in order: `sequence`, `event`, `elapsed_seconds`, `budget` {`remaining_seconds`, `fresh_experiments_remaining`, `candidates_remaining`}, plus event-specific fields. The replay timeline is built from these. |
| `suite` | `id`, `sha256`, `policy`, and `cases[]` (`id`, `source`, `percentage`, `regions` {name: box}, `artifacts` {input, reference}). |
| `experiments[]` | `id`, `plan` (question, hypotheses, predictions, usefulness, input, percentage), `input_spec`, `percentage_requested`, `percentage_accepted`, `status`, `original_import_confirmed`, `target`, `artifacts` {input, reference_output}. |
| `contract` | `id`, `decision`, and `claims[]` (statement, status, scope, setup, parameter_domain, supporting/contradicting evidence IDs, alternatives, unresolved, verification_cases). |
| `candidates[]` | `id`, `status`, `accepted`, `reason`, `error` {type, message}, trusted gates (`build_valid`, `independent`, `baseline_pass`, `ui_check`, `execution`), `builder_invocation`, `baseline_label`, `cases[]` (evaluator case results with `metrics`, `regions`, `reasons`, `artifacts` {candidate, rgb_difference, alpha_difference}). |
| `baselines[]` | Exact baseline-regression results per label (`<candidate>-gates`, `restored-start`, …). |
| `telemetry[]` | One entry per model invocation: `record_present`, model, effort, status, elapsed, `usage` token counts, and an optional `concise_output` (the final answer only). |
| `annotations[]` | Human notes `{target, text, source}` that cite a committed document. They are shown as notes, never as metrics. |

Artifact paths are relative to the manifest's directory. They must match
`^[A-Za-z0-9][A-Za-z0-9._\-/]*$` and must not contain `..`. Anything else (an
absolute path, a drive letter, a URL, or a traversal) is dropped and listed in
the Event log's normalization warnings.

## Normalization rules

- **Accepted** only when an `acceptance` event exists for the candidate or the
  bundle says `accepted: true`. A run that claims acceptance with no accepted
  candidate gets outcome `unknown` and a warning.
- **Incomplete** when there is no `stop` event and no `run.status`.
- **Case outcomes** are kept separate:
  - `passed`
  - `pixel_mismatch`: the comparison ran and failed
  - `dimension_mismatch`
  - `missing_output`: the candidate produced no image, so no comparison was possible
  - `infrastructure`
  - `not_evaluated`: for example, the builder timed out before evaluation
  - `failed_unclassified`
  - `unknown`
- **Claim statuses** are `UNKNOWN`, `HYPOTHESIS`, `OBSERVED`,
  `VERIFIED_WITHIN_SCOPE`, and `CONTRADICTED`. Case is ignored. Anything else
  becomes `UNRECOGNIZED`, with the raw value shown.
- **Candidates with no case results** get `not_evaluated` rows from the
  suite. Images are never borrowed from another candidate.
- **Missing builder telemetry**, when the bundle has telemetry at all, is
  shown as "Not recorded". It is never zero.
- **Failure routing** is linked to the `failure_routing` event between the
  candidate's rejection and the next candidate. Its suggestion is labeled as
  model output, not as a trusted decision.
- **Replay** (`snapshotAt`) shows only events at or before the cursor:
  phase, budgets, counts, gates, and decisions. Budget time drifts between
  events and freezes after `stop`.
- **Other schema versions** load on a best-effort basis, with a warning.
  Unknown event types appear in the log as-is.

## Exporting a recorded run (trusted host)

```
node scripts/export-run.mjs \
  --repo <Reforge checkout> \
  --run  <repo>/evidence/learning/<run-id> \
  --out  public/runs/recorded-<run-id> \
  [--annotations scripts/annotations/<run-id>.json] [--bundle-id <id>]
```

Then add an entry to `public/runs/index.json`.

What the exporter does:

- It reads only inside the run directory and `<repo>/fixtures/development`.
  It refuses any path containing a `collector`, `holdout` or `final_holdout`
  segment.
- It copies only PNG/JPG artifacts that the manifest references, and records
  each one's `sha256` and size.
- It replaces absolute paths in text with their basename. It drops raw
  `packet`, `checkpoint` and `report` event fields. It fails if an absolute
  path would remain in the manifest.
- From model invocations, it keeps usage counts and the final concise answer.
  It never keeps reasoning content, which the harness does not store anyway.

The bundled recorded sample (`public/runs/recorded-20261010T184129Z-78c8e934`,
about 205 KB) was produced this way. It is not the full archive.

## Local feature jobs (implemented; live pilot not run)

The separate Implement a feature view polls the loopback job service via Vite's
same-origin `/api/jobs` proxy. It does not convert a recorded run into live data.
`data/jobs.ts` validates sequenced/timed job events, deduplicates reconnects through
`appendEvents`, and derives replay snapshots only from facts available at the cursor.
Evidence is served only after an availability event, from allowlisted sanitized JSON
copies. Future terminal state and evidence cannot populate earlier snapshots. Job
events and outcomes persist across refresh; interrupted hosts never imply acceptance.
See `../README-features.md` for setup, bounds, disabled-by-default execution and the
unexecuted Contrast pilot. Private observations and final expected images are not
served by this API.

## General harness SSE integration (not implemented)

`src/data/live.ts` defines `RunEventSource`, `parseEventLine`, `appendEvents`
and an untested `SseRunEventSource`. Nothing in the UI uses them yet. To
integrate:

1. Have the trusted host serve a same-origin, read-only Server-Sent Events
   endpoint. It should emit one sanitized event per message, applying the
   same scrubbing as the exporter. It must never serve repository files.
2. Serve a bundle skeleton (`provenance.kind: "live"`, `run`, `suite`) next
   to it. Add artifacts to the skeleton only after they have been copied
   into the served directory.
3. In `App.tsx`, subscribe with `SseRunEventSource`, fold events in with
   `appendEvents`, and re-run `normalizeRun`. Show a LIVE badge only while
   the source status is `open`.
4. Add tests that replay a captured event stream through this path before
   claiming that live mode works.

## Portable accepted recordings (v2)

`Replay saved run` imports a single `reforge.portable-recording` v1 JSON envelope. It contains the exact UTF-8 v2 manifest string and SHA-256 plus base64 images with relative path, size, MIME and SHA-256 inventory. The importer verifies schema, timing/order, path safety, references, image signatures, sizes and hashes before creating local object URLs. No backend or original archive access is needed. The same envelope can be selected from the static run index.

V2 retains the existing visible suite/candidate model. `recording.final` is a distinct recording-only section with once-only final cases, reference/input assets, evaluation metrics and original summary `available_at`; `recording.evidence` contains archival images with conservative section-completion reveal times. Final inputs/outputs never enter repair/model packets or learning input directories. Run provenance declares the original execution mode, tested acceptance scope, developer changes and repair history. `telemetry.available_at` and `candidates.decided_seconds` support explicit recorded reveal timing; absent values retain v1 behavior.

A successful import starts at time zero. The dashboard labels recorded mode and source job, hides future evaluation images/metrics, and keeps final summaries and outcome-bearing provenance hidden until available. The final inspector shares existing case rendering but its case IDs/assets are separate from visible candidate cases. Images are recorded evidence and never appear in live-session panes. Import replacements/run switches clear selections, reject stale loads and dispose owned URLs. See `../docs/portable-replay.md` for actual source provenance, exports and validation.
