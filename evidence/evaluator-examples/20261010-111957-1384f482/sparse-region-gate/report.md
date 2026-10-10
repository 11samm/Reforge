# Deterministic RGBA evaluation

Passed 0/1 cases.

Scoring uses raw RGBA. Checkerboard compositing is display only. Differences are amplified x16.

## sparse-region-gate: failed (pixel_mismatch)

Policy: blur-provisional-v1. Provisional engineering targets, not established compatibility standards. RGB mean across all three channels <=1 and >=99% pixels with max RGB error <=3. Alpha mean <=1, maximum <=3, and 100% within 3. No blur success established.
Dimensions agree: True; {'reference': [100, 100], 'candidate': [100, 100]}
Reasons: informative: rgb_mae=85.0 violates rgb_mean_max=1; informative: rgb_fraction_within_tolerance=0.0 violates rgb_fraction_min=0.99

full_image: RGB per-channel MAE [0.0255, 0.0, 0.0]; RGB mean 0.0085, max 255; alpha mean 0.0, max 0; RGB fraction 0.9999, alpha fraction 1.0; differing pixels 1/10000.

informative: RGB per-channel MAE [255.0, 0.0, 0.0]; RGB mean 85.0, max 255; alpha mean 0.0, max 0; RGB fraction 0.0, alpha fraction 1.0; differing pixels 1/1.

Artifacts: reference-raw.png, candidate-raw.png, alpha-difference-x16.png, candidate-raw.png, changed-bounds-alpha-x16.png, changed-bounds-rgb-x16.png, reference-raw.png, region-informative-alpha-difference-x16.png, region-informative-changed-bounds-alpha-x16.png, region-informative-changed-bounds-rgb-x16.png, region-informative-rgb-difference-x16.png, region-informative-side-by-side.png, rgb-difference-x16.png, side-by-side.png
