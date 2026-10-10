# Milestone 2 validation results

October 10, 2026. Headed local Chromium; visible miniPaint About **4.14.3**.
No visible-version discrepancy; exact hosted build unknown and unpinned.

Batch `20261010-101321-32a5bc2c` passed in 23.615 seconds including controller startup and layout observation.

All six runs confirmed original input via pre-operation export; fresh output dimensions,
accepted Percentage 3, no infrastructure errors, and zero differing RGBA pixels against
the prepared development reference.

- gb017 repeat 1: **passed**, 129x97, 2.729 seconds.
- gb017 repeat 2: **passed**, 129x97, 2.887 seconds.
- gb017 repeat 3: **passed**, 129x97, 2.465 seconds.
- gb010 repeat 1: **passed**, 65x49, 2.486 seconds.
- gb010 repeat 2: **passed**, 65x49, 2.482 seconds.
- gb010 repeat 3: **passed**, 65x49, 2.484 seconds.

Each case had three identical decoded RGBA hashes and identical exported PNG hashes.
Expected reference PNGs were not modified. This validates replay for these two cases,
not blur behavior across the full parameter domain.

[Six-run details](validation-summary.json) · Full action evidence remains locally under `evidence/runs/20261010-101321-32a5bc2c/summary.json` ·
[Initial interface](layout/initial-interface.png) ·
[Visible DOM/accessibility](layout/initial-visible-dom.json)

Only gb017 (opaque poster, 129x97) and gb010 (transparent shapes, 65x49) were imported.
The alternate visible Data URL route separately passed gb010 in 2.946 seconds.
No headless equivalence, alternate browsers, exact build pin, or future coding-agent OS
sandbox has been verified. No model requests were used.

Development history: the initial six-run batch failed before export on an Information
panel size check; three bounded probes corrected panel refresh and split-text completion
selectors. One successful complete opaque-case probe preceded the final batch.
All earlier diagnostics remain under evidence/runs; no failures were discarded.
