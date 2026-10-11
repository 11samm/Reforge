# miniPaint brightness

Image → Color Corrections… provides Brightness (-100 to 100, integer steps,
default 0) and Apply/Close. Contrast, Saturation, Hue, Luminance, Red channel,
Green channel and Blue channel are visibly disabled at 0. Brightness and Apply
are disabled without an image; Apply is also disabled for depth16 images.
The existing layout, stylesheet and Gaussian Blur placeholder are unchanged.

## Independent implementation

`src/brightness.ts` exports
`applyBrightness(raster: Raster, brightness: number): Raster`.
It uses only the supplied visible observations, not reference internals.

- Opaque channels use `clamp(floor(c * (1 + brightness / 100)), 0, 255)`.
  This agrees with the supplied samples at -50, -37, 0, 1, 17 and 50.
  Extension to other parameters and opaque rasters is a hypothesis.
- For nonzero brightness and alpha 1–254, the transformed channel is quantized
  as `round(round(value * alpha / 255) * 255 / alpha)`, then clamped.
  This independent hypothesis agrees with the observed active-channel results
  at -50: 127 for alpha255, 128 for alpha128, and 120 for alpha17.
  Other partial-alpha colors and parameters remain unverified; no universal
  exact-match claim is made.
- Fully transparent RGB is preserved as a conservative choice because the
  supplied evidence does not establish its nonneutral behavior.
- Neutral brightness bypasses all RGB processing and returns an exact copy.
  All supported results preserve dimensions and alpha, with a newly allocated
  data buffer; the source is never modified.
- Depth16 is explicitly rejected, including at neutral, without modifying the
  source. Its existing upload and original PNG export remain available.
  Noninteger/out-of-range brightness and malformed 8-bit rasters are rejected.

Apply uses current document pixels, so successive applications accumulate.
The preview is built before committing the new raster to both document state
and `currentImage.raster`. PNG export serializes the current raster directly;
preview canvas conversion does not replace the export samples. The main
preview retains the accessible name `Original image preview: filename`.

No execution, evaluator access, reference-internal access, dependency changes
or configuration changes were used. This describes the original builder boundary. Subsequent trusted host validation passed six visible and five fresh exact RGBA cases, independent execution, UI agreement and four baselines, without transformation repairs or new model calls. See [milestone report](../evidence/brightness-results.md) for measured scope and limits.

Use Node.js 20.19+ or 22.12+, `npm ci`, then `npm run dev` or `npm run build`.
