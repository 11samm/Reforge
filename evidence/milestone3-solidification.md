# Milestone 3 solidification

October 10, 2026. Focused host-authored corrections; no additional model invocation,
feature, blur/filter, learning loop, evaluator or dashboard. Nothing pushed.

Headed remains default. Headless is explicitly unverified/not supported for exact
reference equivalence: its prior 0/6 exact matches remain recorded unchanged.
Comparisons and fixtures are unchanged. New positioned headed batch
`20261010-105508-083356f7`: 6/6 exact RGBA matches, correct originals, accepted Percentage 3,
fresh dimensions and repeat agreement. [Full batch](runs/20261010-105508-083356f7/summary.json).

Optional `--window-position=X,Y` changes only the Chromium launch position, propagates
to every worker, and is recorded. Negative coordinates use the equals form. An
[OS geometry probe](window-position-observation.json) observed origin (1600,0),
outer window bounds 1600,0..3056,1088, viewport/screenshot 1440x1000 and scale 1.
No reference hidden state was read. Coordinates depend on monitor geometry and may
be clamped. Users must not interact with the reference browser during experiments.

The initial shell returned original PNG bytes. That path has been replaced by an
unpremultiplied current raster and local PNG serialization in
[the image-state module](../generated-app/src/current-image.ts). Original previews
still use uploaded object URLs, with no image transformations. JPEG imports are
browser decoded. Every export serializes current samples; no original-byte fallback.
PNG alpha and invisible RGB are retained without canvas premultiplication.
PNG file bytes, metadata and profiles are not preserved. Native 16-bit sample storage
is supported in code but 16-bit/interlaced/profile cases are not validated here.

[Verification](shell-verification/20261010-105502-3948761e/results.json) passes:
opaque 129x97 and transparent 65x49 original exact decoded round trips; sentinel
invisible RGB and partial alpha; browser-decoded JPEG; disabled controls; blur remains
unavailable; and empty/error states retaining previous good images. No browser
exceptions or external requests. A separate evidence fixture imports the real App
and state module, changes RGB at (2,1) from [16,46,96,1] to [17,231,83,1], and invokes
the normal File → Export PNG action. The decoded 4x3 output has exactly 1 changed
pixel, 11 unaffected equal pixels, and identical alpha at every pixel. It exactly
matches an independently prepared expected PNG. Production has no test hook.
[Fixture source](shell-verification/20261010-105502-3948761e/current-state-fixture/entry.tsx) ·
[Changed export](shell-verification/20261010-105502-3948761e/current-state-export.png).

Builder protection is **allowlisted tool access**, not OS sandboxing. Built-in
environment capabilities are disabled. Only checked file read/write tools are
supplied; unrestricted shell and browser-evaluation requests are rejected.
Fixture/evaluation/browser control is performed by the separate trusted verifier,
never exposed as builder tools. 16 offline tests pass, including runtime shell and
browser-evaluation denials, real junction/hardlink escapes, and position/mode checks.
The original invocation audit remains unchanged and records only allowed file calls.
No additional model calls were needed. The trust boundary assumes no concurrent
hostile root modification and does not sandbox the host process.

Fresh type-check/production build passed. Judging viewport 1440x1000,scale 1:
[reference](layout-packet/reference.png) and
[generated](shell-verification/20261010-105502-3948761e/generated-initial.png) were visually
compared. Canvas 1024x768 x126/y151 vs approximately x126/y152; right panels 198px
wide at x1236 and y76/268/536/640/881. No major panel/spacing/sizing differences;
no layout edits made. Icons, color ornament, text metrics, disabled styling and
small-screen behavior remain approximate. Original observations are unchanged.

[Current source hashes and linked evidence](shell-manifest.json) ·
[Original manifest](shell-manifest-initial.json) · [Startup](../README-shell.md).
