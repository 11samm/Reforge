# Reviewed Contrast promotion

This change adds the previously accepted independent Contrast implementation to
the canonical generated editor. The source run remains an isolated autonomous
run; these checks are developer integration revalidation, not a new learning run.

## Source and review

- Main starting commit: `4f37096`.
- Original job: `9df7c33da7a5425db3934e2cd928c5ee`.
- Original archive: `20261011T083511Z-2d1ccba6-dev-resume` in the retained
  `ReforgerData/feature-discovery-worktree` checkout.
- All eleven files listed in `checkpoints/candidate-1/manifest.json` were
  SHA-256 verified before copying.
- Only `src/main.tsx` and `src/contrast.ts` were promoted. Brightness, codecs,
  CSS, dependencies, configuration, and frozen expected outputs are unchanged.
- A preserved pre-Contrast starting shell is used for subsequent isolated
  discovery runs. The pipeline removes Contrast only from its newly copied
  candidate workspace; the canonical accepted editor and raw evidence remain.
- Accepted Contrast source SHA-256:
  `ec4bd70d05387e68fff449bc968b9ddc665a25cdc9e55d8b50f8d80ce72a31e4`.
- The source explicitly retains hypotheses/unknowns about unobserved behavior.
  Acceptance is within tested cases, not exhaustive compatibility.

## Revalidation

No model calls or reference observations were needed for these checks. Historical
final Contrast outputs were not used as repair/tuning context.

- TypeScript check and production build passed.
- All four original visible Contrast cases passed exact RGBA.
- Contrast UI output matched the independently executed batch implementation.
- All eleven saved Brightness visible/fresh cases passed exact RGBA, including
  UI/batch agreement.
- All four original exact editor baseline gates passed. The shell checks also
  cover JPEG, depth16 preservation, invalid input, replacement, and current-state
  serialization.

Local integration artifacts are preserved under this worktree:

- `evidence/learning/offline-feature-contrast-promotion/`
- `evidence/learning/offline-feature-contrast-baselines/`
- `evidence/learning/offline-feature-brightness-regression/`

The old `evidence/brightness/reproduce.py` intentionally checks the original
whole-source snapshot, including `main.tsx`. It therefore refuses this editor's
new UI revision. Its original source hashes and fixture outputs were not rewritten;
the independent candidate worker instead evaluated all eleven frozen cases against
the current implementation.

## Scope

Image → Contrast… applies an integer adjustment from -100 to 100 to the current
8-bit RGBA raster. Unsupported depth16 remains exportable and cannot be adjusted.
Upload/export and existing Brightness behavior remain available.

Dashboard replay export and live browser presentation are separate work.
