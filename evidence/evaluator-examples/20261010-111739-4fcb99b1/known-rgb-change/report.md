# Deterministic RGBA evaluation

Passed 0/1 cases.

Scoring uses raw RGBA. Checkerboard compositing is display only. Differences are amplified x16.

## known-rgb-change: failed (pixel_mismatch)

Policy: exact-rgba-v1. Exact decoded 8-bit RGBA equality for baseline regressions.
Dimensions agree: True; {'reference': [2, 1], 'candidate': [2, 1]}
Reasons: full_image: 1 pixels differ in raw RGBA

full_image: RGB per-channel MAE [2.0, 1.0, 0.0]; RGB mean 1.0, max 4; alpha mean 0.0, max 0; RGB fraction 0.5, alpha fraction 1.0; differing pixels 1/2.

Artifacts: reference-raw.png, candidate-raw.png, alpha-difference-x16.png, candidate-raw.png, changed-bounds-alpha-x16.png, changed-bounds-rgb-x16.png, reference-raw.png, rgb-difference-x16.png, side-by-side.png
