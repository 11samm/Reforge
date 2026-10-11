# miniPaint observational editor

React/TypeScript editor preserving the approved layout. No remote assets or new dependencies.

## Run
Use Node.js 20.19+ or 22.12+.
- `npm install`
- `npm run dev`
- `npm run build`
- `npm run preview`

File → Open image selects PNG/JPEG; File → Export PNG serializes the current raster. Unrelated controls remain disabled. Effects → Gaussian Blur opens the Percentage dialog (observed slider min 0, max 50, step 1). Slider and Apply are disabled without an image and during upload. Unsupported settings fail visibly without closing the dialog or changing the document. Successful Apply operates on the current raster, atomically replaces raster/preview/export state, releases the previous preview URL and closes the dialog. Repeated Apply is cumulative. Close/Escape does not edit.

## Gaussian Blur learning domain
`src/gaussian-blur.ts` exports synchronous, independent `applyGaussianBlur(raster, percentage)`. It validates integer Percentage 0–10, 8-bit tightly packed Uint8Array RGBA, positive integer dimensions up to 8192 per side and 16,777,216 pixels. No input mutation, DOM, network, reference files or fixture-specific outputs. Percentage 0 returns an exact independent copy. 16-bit blur is rejected; existing 16-bit upload/export is retained.

This is a bounded observational approximation, **not established exact miniPaint compatibility**:
- fresh-01 peak 41/255 and narrow neighbor profile suggest effective sigma near 1.
- fresh-02/gb017 boundary coverage at Percentage 3 suggests sigma near 3 and a transparent exterior, rather than clamping, wrapping or boundary renormalization.
- fresh-03 transition increments at 7 suggest sigma near 7. The symmetric model does not establish the observed transition's precise phase.
- fresh-04 retained red beside transparency motivates alpha-weighted filtering and straight-RGBA output.
- A normalized separable Gaussian truncated at three fitted sigmas is chosen. Percentage is not assumed to be kernel radius: support is derived separately. Sigma equal to the numeric setting is a fitted hypothesis; settings other than 1, 3 and 7 are interpolation/extrapolation inside the declared learning domain.
- Horizontal intermediate values remain floating point to avoid the rejected candidate's early low-alpha color loss. Final premultiplied color and alpha are byte-rounded before unpremultiplication; zero-alpha RGB is black. These are explicit precision choices, not recovered browser internals.

Exact kernel support, phase, rounding, hidden-color behavior, dimension scaling and target build remain unresolved. Supplied rejected-candidate metrics are historical evidence, not verification of this revision. No build, browser or evaluator was run during implementation; host verification is pending.

## Upload and export preservation
Uploads must have matching PNG/JPEG MIME and signature, be nonempty and at most 20 MiB, with the same dimension/area limits. PNG chunk boundaries and CRCs are checked before browser decoding; JPEG headers are checked before decoding. Invalid replacements retain the previous document. Rapid replacements are sequence-guarded; object URLs are released on replacement/unmount.

Untouched previews retain the original file URL and accessible name “Original image preview: filename”. After blur both previews display the encoded current raster without layout changes. Fit changes presentation only. Transparency uses the existing checkerboard.

PNG export serializes current unpremultiplied RGBA, preserving untouched samples including invisible RGB and 16-bit data; it re-encodes rather than returning original file bytes. JPEG uses browser decoding and a natural-size canvas. Metadata and color profiles are not preserved; resolution metadata is not parsed. PNG decoding/export logic is otherwise unchanged.
