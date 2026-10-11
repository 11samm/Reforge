# Brightness candidate

Image → Color Corrections… offers Brightness from -100 to 100 (integer steps, default 0), Apply and Close. Contrast, Saturation, Hue, Luminance and all three channel controls are visibly disabled at 0. Apply edits the current raster; repeated applications use the current pixels. Close discards the unapplied slider setting. Brightness and Apply are disabled without an image or while uploading.

## Independent observation-based implementation

No reference internals, evaluator or runtime execution were accessed. The supplied miniPaint 4.14.3 observations concern one imported layer in a fresh transparent document with all other corrections zero; the hosted build is unpinned.

- Opaque RGB candidate: min(255, floor(channel × (1 + brightness/100))). Evidence covers -100, -37, 0, 17 and 25, not every slider value or arbitrary mixed-color input.
- Translucent candidate: round(round(scaled × alpha/255) × 255/alpha). At brightness -37, scaled 255 becomes 160 for alpha 255, 159 for alpha 128 and 165 for alpha 17, consistent with the supplied observations. This quantization model is an inference, not an observed internal mechanism; other translucent colors and brightness values remain unverified.
- Brightness 0 returns an independent exact byte copy, including hidden RGB. Nonneutral fully transparent pixels retain hidden RGB as a conservative, unverified choice.
- Dimensions and every alpha sample are preserved; source samples are not mutated. No dimension-specific cases are used.
- Brightness rejects depth 16 before mutation. Existing 16-bit PNG upload and export paths remain unchanged; the dialog explains the unsupported edit.

Preview PNGs are encoded from the resulting raster before committing document state. Both previews and currentImage.raster are updated, and exports serialize those current samples. The main image retains its accessible name “Original image preview: filename”.

Original layout/CSS and the Gaussian Blur placeholder are unchanged. No dependencies or configuration were changed. Tests/builds were not run, as requested. Exact RGBA generalization beyond supplied evidence is not claimed.
