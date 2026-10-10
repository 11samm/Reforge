# Deterministic RGBA evaluation

Passed 2/8 cases.

Scoring uses raw RGBA. Checkerboard compositing is display only. Differences are amplified x16.

## encoding-independent: passed (match)

Policy: exact-rgba-v1. Exact decoded 8-bit RGBA equality for baseline regressions.
Dimensions agree: True; {'reference': [2, 1], 'candidate': [2, 1]}
Reasons: All declared criteria satisfied

full_image: RGB per-channel MAE [0.0, 0.0, 0.0]; RGB mean 0.0, max 0; alpha mean 0.0, max 0; RGB fraction 1.0, alpha fraction 1.0; differing pixels 0/2.

Artifacts: reference-raw.png, candidate-raw.png, alpha-difference-x16.png, candidate-raw.png, reference-raw.png, rgb-difference-x16.png, side-by-side.png

## known-rgb-change: failed (pixel_mismatch)

Policy: exact-rgba-v1. Exact decoded 8-bit RGBA equality for baseline regressions.
Dimensions agree: True; {'reference': [2, 1], 'candidate': [2, 1]}
Reasons: full_image: 1 pixels differ in raw RGBA

full_image: RGB per-channel MAE [2.0, 1.0, 0.0]; RGB mean 1.0, max 4; alpha mean 0.0, max 0; RGB fraction 0.5, alpha fraction 1.0; differing pixels 1/2.

Artifacts: reference-raw.png, candidate-raw.png, alpha-difference-x16.png, candidate-raw.png, changed-bounds-alpha-x16.png, changed-bounds-rgb-x16.png, reference-raw.png, rgb-difference-x16.png, side-by-side.png

## alpha-only-change: failed (pixel_mismatch)

Policy: exact-rgba-v1. Exact decoded 8-bit RGBA equality for baseline regressions.
Dimensions agree: True; {'reference': [2, 1], 'candidate': [2, 1]}
Reasons: full_image: 1 pixels differ in raw RGBA

full_image: RGB per-channel MAE [0.0, 0.0, 0.0]; RGB mean 0.0, max 0; alpha mean 1.0, max 2; RGB fraction 1.0, alpha fraction 0.5; differing pixels 1/2.

Artifacts: reference-raw.png, candidate-raw.png, alpha-difference-x16.png, candidate-raw.png, changed-bounds-alpha-x16.png, changed-bounds-rgb-x16.png, reference-raw.png, rgb-difference-x16.png, side-by-side.png

## dimension-mismatch: failed (dimension_mismatch)

Policy: exact-rgba-v1. Exact decoded 8-bit RGBA equality for baseline regressions.
Dimensions agree: False; {'reference': [2, 1], 'candidate': [3, 1]}
Reasons: Reference and candidate dimensions differ; pixel metrics not computed

Artifacts: reference-raw.png, candidate-raw.png, candidate-raw.png, reference-raw.png, side-by-side.png

## invalid-png: failed (invalid_output)

Policy: exact-rgba-v1. Exact decoded 8-bit RGBA equality for baseline regressions.
Dimensions agree: None; {'reference': [2, 1]}
Reasons: candidate: invalid PNG (UnidentifiedImageError: cannot identify image file 'D:\\Samuel\\Downloads\\Code\\Reforge\\evidence\\evaluator-examples\\20261010-111957-1384f482\\invalid-png\\candidate-raw.png')

Artifacts: reference-raw.png, candidate-raw.png, candidate-raw.png, reference-raw.png

## missing-png: failed (missing_output)

Policy: exact-rgba-v1. Exact decoded 8-bit RGBA equality for baseline regressions.
Dimensions agree: None; {'reference': [2, 1]}
Reasons: candidate: missing output

Artifacts: reference-raw.png, reference-raw.png

## sparse-full-image: passed (match)

Policy: blur-provisional-v1. Provisional engineering targets, not established compatibility standards. RGB mean across all three channels <=1 and >=99% pixels with max RGB error <=3. Alpha mean <=1, maximum <=3, and 100% within 3. No blur success established.
Dimensions agree: True; {'reference': [100, 100], 'candidate': [100, 100]}
Reasons: All declared criteria satisfied

full_image: RGB per-channel MAE [0.0255, 0.0, 0.0]; RGB mean 0.0085, max 255; alpha mean 0.0, max 0; RGB fraction 0.9999, alpha fraction 1.0; differing pixels 1/10000.

Artifacts: reference-raw.png, candidate-raw.png, alpha-difference-x16.png, candidate-raw.png, changed-bounds-alpha-x16.png, changed-bounds-rgb-x16.png, reference-raw.png, rgb-difference-x16.png, side-by-side.png

## sparse-region-gate: failed (pixel_mismatch)

Policy: blur-provisional-v1. Provisional engineering targets, not established compatibility standards. RGB mean across all three channels <=1 and >=99% pixels with max RGB error <=3. Alpha mean <=1, maximum <=3, and 100% within 3. No blur success established.
Dimensions agree: True; {'reference': [100, 100], 'candidate': [100, 100]}
Reasons: informative: rgb_mae=85.0 violates rgb_mean_max=1; informative: rgb_fraction_within_tolerance=0.0 violates rgb_fraction_min=0.99

full_image: RGB per-channel MAE [0.0255, 0.0, 0.0]; RGB mean 0.0085, max 255; alpha mean 0.0, max 0; RGB fraction 0.9999, alpha fraction 1.0; differing pixels 1/10000.

informative: RGB per-channel MAE [255.0, 0.0, 0.0]; RGB mean 85.0, max 255; alpha mean 0.0, max 0; RGB fraction 0.0, alpha fraction 1.0; differing pixels 1/1.

Artifacts: reference-raw.png, candidate-raw.png, alpha-difference-x16.png, candidate-raw.png, changed-bounds-alpha-x16.png, changed-bounds-rgb-x16.png, reference-raw.png, region-informative-alpha-difference-x16.png, region-informative-changed-bounds-alpha-x16.png, region-informative-changed-bounds-rgb-x16.png, region-informative-rgb-difference-x16.png, region-informative-side-by-side.png, rgb-difference-x16.png, side-by-side.png
