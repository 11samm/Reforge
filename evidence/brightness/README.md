# Minimal brightness evidence

Run from the repository root after installing the documented Python dependencies
and running `npm ci` in generated-app:

```powershell
.venv\Scripts\python.exe evidence/brightness/reproduce.py
```

This runs the unchanged transformation in Node against six visible and five fresh
saved input/expected PNG pairs and verifies exact RGBA and SHA256. It makes no model
or reference requests. Suite paths are relative to the repository root.

Reports are publication snapshots of the original autonomous stop and subsequent
trusted validation, with absolute artifact paths labeled `local-only:`. Those full
archives, diagnostic images, prompts, and checkpoints are intentionally omitted.
The original local records were not rewritten. Snapshot suite paths differ from
historical suite bytes; original suite hashes in reports identify the original
freeze, while per-PNG hashes verify the copied fixtures. Source hashes pin the app with CRLF normalized to LF for cross-platform checkouts.
Canonical contract and correction/freeze records preserve the host correction
provenance. UI/build/baseline results are historical checks, not rerun by this script.
Brightness compatibility is limited to the measured single-layer 8-bit scope.
