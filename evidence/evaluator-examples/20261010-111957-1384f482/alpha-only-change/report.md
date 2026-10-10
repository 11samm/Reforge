# Deterministic RGBA evaluation

Passed 0/1 cases.

Scoring uses raw RGBA. Checkerboard compositing is display only. Differences are amplified x16.

## alpha-only-change: failed (pixel_mismatch)

Policy: exact-rgba-v1. Exact decoded 8-bit RGBA equality for baseline regressions.
Dimensions agree: True; {'reference': [2, 1], 'candidate': [2, 1]}
Reasons: full_image: 1 pixels differ in raw RGBA

full_image: RGB per-channel MAE [0.0, 0.0, 0.0]; RGB mean 0.0, max 0; alpha mean 1.0, max 2; RGB fraction 1.0, alpha fraction 0.5; differing pixels 1/2.

Artifacts: reference-raw.png, candidate-raw.png, alpha-difference-x16.png, candidate-raw.png, changed-bounds-alpha-x16.png, changed-bounds-rgb-x16.png, reference-raw.png, rgb-difference-x16.png, side-by-side.png
