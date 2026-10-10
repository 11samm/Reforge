# Deterministic RGBA evaluation

Passed 1/1 cases.

Scoring uses raw RGBA. Checkerboard compositing is display only. Differences are amplified x16.

## sparse-full-image: passed (match)

Policy: blur-provisional-v1. Provisional engineering targets, not established compatibility standards. RGB mean across all three channels <=1 and >=99% pixels with max RGB error <=3. Alpha mean <=1, maximum <=3, and 100% within 3. No blur success established.
Dimensions agree: True; {'reference': [100, 100], 'candidate': [100, 100]}
Reasons: All declared criteria satisfied

full_image: RGB per-channel MAE [0.0255, 0.0, 0.0]; RGB mean 0.0085, max 255; alpha mean 0.0, max 0; RGB fraction 0.9999, alpha fraction 1.0; differing pixels 1/10000.

Artifacts: reference-raw.png, candidate-raw.png, alpha-difference-x16.png, candidate-raw.png, changed-bounds-alpha-x16.png, changed-bounds-rgb-x16.png, reference-raw.png, rgb-difference-x16.png, side-by-side.png
