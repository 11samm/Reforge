# Original image editor shell

A fresh React 19 + TypeScript 5 + Vite 7 shell based only on the observed layout packet. No remote assets, backend, editing engine, or filters.

## Run
Use Node.js 20.19+ or 22.12+.
- `npm install`
- `npm run dev` — open the local URL printed by Vite.
- `npm run build`
- `npm run preview`

File → Open image (or the small canvas action) selects an original PNG/JPEG. File → Export PNG downloads it. Other editor controls are disabled. Effects → Gaussian Blur opens the sole operation placeholder; Percentage and Apply are unavailable. Close or Escape dismisses it. Blur is never performed.

## Limits and preservation
Uploads must have matching PNG/JPEG MIME and signature, be nonempty and at most 20 MiB, have dimensions at most 8192 px per side and an area at most 16,777,216 pixels. PNG chunk boundaries and CRCs are checked before browser decoding; JPEG headers are checked before decoding. Browser decode errors are visible, and invalid replacements retain the previous document. Rapid replacements are sequence-guarded; object URLs are released on replacement/unmount.

Both previews use the original file object URL. Display fit changes only presentation, never source dimensions. Transparency is shown over a checkerboard. PNG export serializes the current unpremultiplied RGBA state with a local PNG codec, preserving dimensions, alpha and invisible RGB. It re-encodes PNG files rather than returning original bytes. JPEG import uses browser decoding and a natural-dimension canvas to populate that same current state; browser color-profile handling, metadata loss, and decoding differences mean it is not byte- or color-profile-preserving. Resolution metadata is not parsed.

The layout targets 1440×1000 with a default 1024×768 white canvas and all five right panels visible. No tests, fixtures, or reference assets are included.

Current-state export is verified by an isolated evidence fixture changing one known RGB pixel before using the normal export action. No mutation UI or test hook ships in the production app. PNG metadata/color profiles are omitted on export; 16-bit/profile/interlacing edge cases remain unvalidated.
