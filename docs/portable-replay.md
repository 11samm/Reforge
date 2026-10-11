# Portable accepted feature recordings

Branch: `feat/portable-replay-evidence`. Implementation worktree: `ReforgerData/portable-replay`. No model runs, promotions, fixture changes or evaluation-policy changes were performed.

## Open and replay

From this worktree run `npm.cmd --prefix dashboard run build`, then `npm.cmd --prefix dashboard run preview`. The feature backend can remain stopped. Select a bundled Brightness/Contrast recording in **Run bundle**, or click **Replay saved run** and choose either `.reforge.json` file copied to any directory. Imports start at time zero. **Jump to end** displays all archived evaluation evidence. **Candidates** contains the existing per-case inspector, once-only final inspector and recorded screenshot gallery. Restart hides later evidence again. These images are explicitly archival evidence and never appear in live-browser panes.

Agent 1 integration: `ImplementFeature` receives the optional `onReplaySavedRun: () => void` prop. App supplies `openSavedRun`, which opens its hidden file picker. `data/portable.ts` exports `validatePortable(value)` and `importPortable(value) -> {run, dispose}`. The importer performs no fetches; `dispose` revokes all asset URLs. The App manages imported/built-in URL lifetimes separately, ignores stale asynchronous loads, and resets candidate/case selection on run changes. Agent 1's temporary callback to Overview should be replaced by this wiring when integrating the commits. No ImplementFeature or live-job API files were edited here.

## Source and provenance

Brightness: job `82b68e6daf5e41ddb7c03c13a91ba1f9`, original archive `20261011T183641Z-73504a72-dev-resume`, retained in `ReforgerData/contrast-brightness-worktree`. The accepted third attempt was fresh discovery/experiments with target absent and no previous target evidence supplied. Two unresolved earlier attempts and developer host/prompt changes preceded it. Candidate 1 was rejected for a baseline regression; automatic repair accepted candidate 2. No harness repair occurred during this run. Internal `development_resume` identifies the harness's isolated workspace mode and does not imply `--resume-job`. Job time is 297.460 s. Original visible and two fresh final cases passed exact RGBA. Five original invocation usage totals are preserved, including discovery. This is one successful attempt, not a repeatability claim.

Contrast: job `9df7c33da7a5425db3934e2cd928c5ee`, original archive `20261011T083511Z-2d1ccba6-dev-resume`, retained in `ReforgerData/feature-discovery-worktree`. An isolated workspace began without Contrast and retained existing Brightness. Original provenance declares `development_resume` and `clean_start_autonomous_demonstration: false`; the recording does not relabel it as a clean-start autonomous benchmark. Candidate 1 was accepted. The job summary records 346.770 s; its final recorded stop event is 346.775 s. Playback spans the latter and preserves both original numbers. The later developer promotion/revalidation documented in `contrast-promotion-20261011.md` is separate from this recording. Acceptance is within the tested scope, not exhaustive compatibility.

The exporter joins the original learning events to their forwarded job events in order and fails if any original event cannot be matched. It preserves the archive-local clock as `archive_elapsed_seconds`, the authoritative job clock as `elapsed_seconds`, and job sequence numbers. It does not estimate offsets. Original accepted reports, job status and identity are checked before export. Input/reference hashes are checked against the frozen suites.

## Files and format

- `dashboard/public/runs/brightness-success.reforge.json`: 7,164,565 bytes, 47 events, 312 image assets.
- `dashboard/public/runs/contrast-success.reforge.json`: 7,137,393 bytes, 39 events, 321 image assets.
- `docs/portable-source-validation.json`: bundle hashes and independent source comparison results.

Each single portable JSON file contains a `reforge.portable-recording` v1 envelope, an exact UTF-8 serialized `reforge.run-bundle` v2 manifest plus its SHA-256, and base64 PNG/JPEG assets. The manifest uses relative asset references and contains SHA-256/size/MIME inventory entries. Imports reject unsupported schemas, invalid ordering, unsafe or undeclared references, duplicate/missing assets, mismatched bytes or hashes, image signature errors and oversized recordings. Hashes detect corruption; they do not authenticate the author's identity. No extraction to disk, network asset resolution, active service or original absolute paths are required. Legacy v1 dashboard recordings retain their existing behavior.

The exporter reads allowlisted evidence sections, not prompts, repair/model packets, reasoning, private transcripts, credentials, live CDP snapshots or candidate sources. Model invocation reads produce usage/status fields only, never answers. Once-only final evidence is a recording-only section, revealed at its original summary availability time. No model/repair packet code was changed and no final data is exported to learning input locations.

## Re-export

Use the original source checkout as `--repo`, its exact archive as `--run`, and its sibling `feature-<job-id>` learning directory as `--job`. Export to a new location outside these archives:

```powershell
node dashboard/scripts/export-feature-run.mjs --repo <retained-checkout> --run <original-learning-archive> --job <original-feature-job-archive> --out <new-output.reforge.json>
```

The original persisted `evidence/feature-jobs/<job-id>/job.json` is required for timing. The legacy Gaussian Blur exporter remains available for its existing format. Both original archives, workspaces, expected PNGs and evaluation policies remain unchanged.

## Validation and limits

Dashboard tests exercise both actual bundles, every image hash, raw metric preservation, final evidence, ordering, unsafe/synthetic mutations, unsupported schemas, corrupted/missing assets and distinct run-scoped object URLs. Synthetic cases are explicitly labeled. Production TypeScript/build checks pass. `test_portable_ui.py` copies each real recording to a temporary directory, imports through the production dashboard with all backend APIs blocked, decodes all displayed images, tests replay restart and switching, and rejects a missing asset. Existing `test_feature_ui` tests pass too. `portable-source-validation.json` records independent exact comparison of candidate and baseline metrics, regions, reasons, build/independence/regression checks, final metrics, and every job timestamp/sequence against original archives.

Independent source revalidation: `python verify_portable_source.py --repo <retained-checkout> --archive <original-learning-archive> --job <original-feature-job-archive> --bundle <portable-file>`.

Commands: `npm.cmd --prefix dashboard test`; `npm.cmd --prefix dashboard run typecheck`; `npm.cmd --prefix dashboard run build`; use the existing Reforge virtualenv Python for `-m unittest test_portable_ui test_feature_ui`.

Missing evidence: neither run archived a continuous browser/screencast video. Not every screenshot has a reliable individual capture timestamp, so it is conservatively revealed at section completion rather than assigned invented timing. Final case images, actual zero-difference images/metrics and summaries are available. Browser image provenance is recorded; these cannot be reopened as live sessions. Preserved private model transcripts and raw machine/process records are intentionally excluded. The recording is a presentation/evidence artifact, not an executable candidate/source archive.
