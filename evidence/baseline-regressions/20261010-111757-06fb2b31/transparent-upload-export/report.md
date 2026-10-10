# Deterministic RGBA evaluation

Passed 1/1 cases.

Scoring uses raw RGBA. Checkerboard compositing is display only. Differences are amplified x16.

## transparent-upload-export: passed (match)

Policy: exact-rgba-v1. Exact decoded 8-bit RGBA equality for baseline regressions.
Dimensions agree: True; {'reference': [65, 49], 'candidate': [65, 49]}
Reasons: All declared criteria satisfied

full_image: RGB per-channel MAE [0.0, 0.0, 0.0]; RGB mean 0.0, max 0; alpha mean 0.0, max 0; RGB fraction 1.0, alpha fraction 1.0; differing pixels 0/3185.

Artifacts: reference-raw.png, candidate-raw.png, alpha-difference-x16.png, candidate-raw.png, reference-raw.png, rgb-difference-x16.png, side-by-side.png
