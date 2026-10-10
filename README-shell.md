# miniPaint-like editor shell

Milestone 3, October 10, 2026. Fresh React + TypeScript + Vite source was generated
through the existing subscription-backed local Codex app-server, exact model
`gpt-6.1-sol`, reasoning `medium`. One completed generation turn (180-second
limit, 24 broker-call limit), no model repair turns. The editor runs locally and
has no miniPaint dependency, embedding, calls, code, or imported reference assets.

## Start

Use Node.js 20.19+ or 22.12+:

```powershell
Set-Location 'D:\Samuel\Downloads\Code\Reforge\generated-app'
npm.cmd ci --ignore-scripts --no-audit --no-fund
npm.cmd run dev
```

Open the URL printed by Vite (normally http://127.0.0.1:5173).
Production type-check/build: `npm.cmd run build`; serve it: `npm.cmd run preview`.
The exact installed dependencies are in generated-app/package-lock.json.
No Codex login or reference site connection is required to run the editor.

File â†’ Open image (or the canvas prompt) uploads PNG/JPEG. File â†’ Export PNG
exports. Export serializes the current unpremultiplied RGBA raster as PNG, preserving
dimensions, alpha, partial alpha and invisible RGB. PNG imports use a local PNG
codec; JPEG imports use browser decoding at natural dimensions. PNG files are
re-encoded, so file bytes and metadata/color profiles need not match the upload. Dimensions and one filename layer are shown.
Preview uses the original file object URL; display fitting changes presentation only.
Transparency uses a checkerboard. Invalid uploads show an error and keep the
previous good document. Limits: 20 MiB, 8192 pixels per side, 16 megapixels.

Effects â†’ Gaussian Blur opens the unavailable placeholder; Percentage and Apply
are disabled. Close and Escape work. Other editing tools, menus, zoom, properties,
color controls and layer operations are disabled. Unicode icons, brand ornament,
color picker, font details and behavior on smaller screens are approximate.
No blur/filter implementation or learning loop is included.

## Evidence and verification

- [Milestone results](evidence/milestone3-results.md).
- [Observed layout packet](evidence/layout-packet/observation.md),
  [reference screenshot](evidence/layout-packet/reference.png), and
  [visible DOM/accessibility](evidence/layout-packet/visible-controls.json).
- [Headless and headed results](evidence/headless-validation.json).
- [Source hashes and linked invocation/verification artifacts](evidence/shell-manifest.json).

Build/type-check passed. Original opaque gb017 and transparent gb010 uploads,
source dimensions, original preview bytes, and exact decoded export RGBA passed.
Additional invisible-RGB/partial-alpha sentinel and JPEG checks passed. JPEG
matches this browser's decoded preview; exact equality across other decoders,
metadata and color profiles is not established. Display color handling follows
the browser. Empty/error states, disabled controls and blur dialog were verified.
No browser exceptions or external requests occurred. Layout was visually inspected
at 1440x1000, device scale 1: canvas position within 1px and right panels aligned.

To rerun checks from the repository root after building:

```powershell
.venv\Scripts\python.exe -m unittest -v test_smoke test_adapter test_shell_boundary
.venv\Scripts\python.exe verify_shell.py
.venv\Scripts\python.exe -m adapter.validate --headed
```

`--headless` remains explicitly unverified for equivalence and diagnostic: all six repeat-stable headless runs failed exact
reference agreement. Fresh headed recheck passed 6/6; headed remains default.
Original fixtures and strict comparisons are unchanged.

## Coding-agent restriction

`build_shell.py` reuses CodexRuntime without changing smoke.py. Its ephemeral
thread has `environments: []`, empty selected capability roots, a read-only protocol setting,
and disabled shell, plugins, connectors, hooks, memories and web search. Only
`shell_read_file` and `shell_write_file` are supplied. The host broker exposes
eight allowlisted application files and three read-only packet files. Absolute
paths, traversal, alternate data streams, links, junctions and hard links are
rejected, as are all other server requests. Real junction/hard-link probes and
runtime-denial tests passed. The actual invocation audit shows only allowed
dynamic tool calls and no built-in execution/file tools. No unrestricted shell or browser-evaluation
capability is exposed: both are explicitly rejected by the request gate and
boundary tests. Browser evaluation used by verification belongs to the trusted
verification host, outside the builder tool surface. The builder receives
no fixtures, blur outputs, evaluation code or hidden cases.

This is a practical tool/filesystem capability restriction, **not an OS sandbox
for the trusted app-server host or build/verification processes**. Those processes
remain outside the model's tools. It assumes no concurrent hostile process changes
the roots. A working directory alone is not being claimed as isolation.

Manual bounded generation replay: `.venv\Scripts\python.exe build_shell.py`.
It overwrites allowlisted shell sources; rerun build/verification afterward. The
saved prompt, exact thread/turn parameters, model, provider, account type (no
credentials), usage, calls and file hashes are retained under evidence/shell-generation/.

## Current-state export proof

The follow-up replaces the initial original-byte PNG download with
`src/current-image.ts`: upload decodes current samples, and File → Export PNG
calls `serializeCurrentImage()` every time. There is no original-byte fallback.
[fast-png](https://github.com/image-js/fast-png) supplies local decode/encode without
canvas premultiplication of PNG samples. Preview still initially displays the
original object URL. There are no product mutation controls in this milestone.
Native sample depth is retained for 16-bit PNG state; that format and profile/
interlacing edge cases are not part of the validated set. PNG metadata is omitted.

`verify_shell.py` creates a separate bundled fixture under evidence/ that imports
production App and current-image code. A fixture-only test hook changes RGB at
(2,1) of a 4x3 synthetic RGBA image while keeping alpha 1. The normal File → Export
PNG action produces exactly the expected current raster: one changed pixel,
11 unchanged pixels, unchanged dimensions and identical alpha at every pixel.
The production build is checked for absence of this test hook. Opaque/transparent
original round trips, invisible RGB/partial alpha, JPEG, disabled controls and
empty/error checks still pass. No fixture or evaluation code is builder-accessible.

See [follow-up evidence](evidence/milestone3-solidification.md). Optional headed
placement: `.venv\Scripts\python.exe -m adapter.validate --window-position=1600,0`.
Do not interact with the reference browser during experiments.
