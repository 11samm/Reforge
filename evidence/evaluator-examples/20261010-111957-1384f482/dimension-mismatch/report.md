# Deterministic RGBA evaluation

Passed 0/1 cases.

Scoring uses raw RGBA. Checkerboard compositing is display only. Differences are amplified x16.

## dimension-mismatch: failed (dimension_mismatch)

Policy: exact-rgba-v1. Exact decoded 8-bit RGBA equality for baseline regressions.
Dimensions agree: False; {'reference': [2, 1], 'candidate': [3, 1]}
Reasons: Reference and candidate dimensions differ; pixel metrics not computed

Artifacts: reference-raw.png, candidate-raw.png, candidate-raw.png, reference-raw.png, side-by-side.png
