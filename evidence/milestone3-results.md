# Milestone 3 results

October 10, 2026. Completed the editor-shell milestone; no push.

## Headless equivalence and default

Headless batch `20261010-103335-dbb864d9`: correct original exports in all six runs, accepted
Percentage 3, fresh dimensions 129x97 (gb017) /65x49 (gb010), identical decoded
repeats for each case, but **0/6 exact prepared-reference matches**. Each gb017
repeat differed at 9,122 pixels (max channel delta 9); each gb010 repeat at 1,977
pixels (max delta 255). Diagnostics, exports and actions remain under
[runs/20261010-103335-dbb864d9/summary.json](runs/20261010-103335-dbb864d9/summary.json).

Fresh headed recheck `20261010-103724-0ce76cc5` passed **6/6 exact matches** with repeat agreement
and original-input confirmation. [Full result](runs/20261010-103724-0ce76cc5/summary.json).
Both modes reported About 4.14.3 and Chromium 153.0.8010.12. The cause of the
headless difference is unestablished. **Headed remains the supported default**;
explicit --headed is available for debugging/presentation, --headless is diagnostic.
Help, documentation, worker propagation and mode tests reflect that decision.
No comparison criteria, prepared references, adapter action behavior or fixtures
were weakened/changed. [Compact records](headless-validation.json).

## Observed layout and generation

[Packet](layout-packet/observation.md) Â· [Reference](layout-packet/reference.png) Â·
[Visible controls/accessibility](layout-packet/visible-controls.json).
Original observations remain in the headless batch layout directory. Only the
initial visible screenshot and layout packet were exposed to the builder. No
reference code, bundles, maps, network bodies, hidden state or blur output was
provided. Layout colors, icon roles without accessible labels, exact metrics,
responsive breakpoints and hosted build uncertainties are identified in the packet.

[Generation prompt](shell-generation/20261010-103640-cad88ad9/prompt.txt) Â·
[Invocation and actual tool audit](shell-generation/20261010-103640-cad88ad9/invocation.json).
Exact gpt-6.1-sol/medium through existing managed ChatGPT runtime. One generation
turn, 180-second turn bound, 24-call bound; zero repair turns. Returned provider/model
and completed item types were checked. Only checked dynamic file tools were used.
Total reported usage 163,231 tokens (155,645 input incl. 115,200 cached, 7,586 output).
Telemetry is not an invoice. smoke.py and working model integration unchanged.

Host restriction: no environment execution, allowlisted app-file reads/writes,
read-only packet, rejected traversal/absolute paths/links/junctions/hardlinks and
other requests. Four boundary/mode tests plus ten regressions passed (14 total),
including real junction and hard-link probes. The trusted host/build processes are
not OS-sandboxed, and concurrent hostile root mutation is outside the boundary.
See [startup and restriction details](../README-shell.md).

## Shell verification and visual inspection

Fresh source in [generated-app](../generated-app/README.md). Type-check and Vite
production build passed. [Verification results](shell-verification/20261010-104110-9e237630/results.json) Â·
[Generated screenshot](shell-verification/20261010-104110-9e237630/generated-initial.png) Â·
[Source hashes/links](shell-manifest.json).

Opaque gb017 129x97 and transparent gb010 65x49: unchanged original preview bytes,
natural preview dimensions, single named layer, checkerboard, newly downloaded PNG,
exact RGBA equality with each original (0 differing pixels,0 max delta). Extra sentinel
retained nonzero invisible RGB and alpha 1/128 exactly. JPEG-derived development
input exported to PNG with equal browser-decoded RGBA 129x97, alpha 255. JPEG
cross-decoder/profile/metadata preservation is not established.

Verified disabled editing menus/tools, sidebar controls, empty export, inaccessible
blur Percentage/Apply, dialog Close; unsupported text and corrupt PNG/JPEG errors
retain the previous good document, and invalid initial upload leaves export disabled.
No browser exceptions or external network requests. Verification server served only
generated-app/dist and was stopped afterward.

Visual inspection at 1440x1000: matching dark 30px menu, 40px options row, 40px left
strip; default 1024x768 canvas x126/y151 vs reference approximately x126/y152.
Right panels x1236,w198 aligned at y76/268/536/640/881. No major layout repair
was required. Icons, color gradients, disabled-control appearance, text metrics
and small viewport behavior remain approximate.

Functional: upload PNG/JPEG, original preview, dimensions, single layer, checkerboard,
PNG export, File actions, blur-dialog open/close and error states. Placeholders:
all editing tools, other menus, zoom, color/property/layer operations, blur slider
and Apply. No blur, other filter, autonomous loop, evaluator or dashboard was built.

## Solidification follow-up

The original-byte PNG download described above has been replaced by verified
current-state PNG serialization. Headed window positioning and explicit browser-
evaluation denial checks were added. Historical evidence above remains intact;
see [current follow-up results](milestone3-solidification.md).
