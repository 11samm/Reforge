import type { Raster } from './current-image';

/**
 * Bounded observational approximation, not an exact miniPaint compatibility claim.
 * Percentage is a UI setting; the fitted sigma is not a pixel-radius contract.
 */
export function applyGaussianBlur(raster: Raster, percentage: number): Raster {
  if (!Number.isInteger(percentage) || percentage < 0 || percentage > 10) {
    throw new RangeError('Unsupported Percentage. Gaussian Blur supports integer settings 0–10 only.');
  }
  if (!raster || raster.depth !== 8) {
    throw new TypeError('Gaussian Blur supports 8-bit images only. Your unchanged 16-bit image can still be exported.');
  }
  const { width, height, data } = raster;
  if (!Number.isSafeInteger(width) || !Number.isSafeInteger(height) ||
      width < 1 || height < 1 || width > 8192 || height > 8192 ||
      width * height > 16_777_216) {
    throw new RangeError('Gaussian Blur requires integer dimensions within 8192 px per side and 16 megapixels.');
  }
  if (!(data instanceof Uint8Array) || data.length !== width * height * 4) {
    throw new TypeError('Gaussian Blur requires tightly packed 8-bit RGBA data.');
  }
  if (percentage === 0) return { width, height, depth: 8, data: new Uint8Array(data) };

  // Peak 41/255 at setting 1 fits sigma approximately 1; boundary cumulative
  // coverage at 3 fits approximately 3; setting 7 edge increments fit about 7.
  // Interpolation/extrapolation within 0–10 is a declared learning assumption.
  const sigma = percentage;
  const support = Math.ceil(3 * sigma);
  const kernel = new Float64Array(2 * support + 1);
  let total = 0;
  for (let d = -support; d <= support; d++) {
    const weight = Math.exp(-d * d / (2 * sigma * sigma));
    kernel[d + support] = weight;
    total += weight;
  }
  for (let i = 0; i < kernel.length; i++) kernel[i] /= total;

  // Keep the first pass in floating point. Premature byte quantization loses
  // tiny color contributions which become visible after unpremultiplication.
  // Transparent exterior, with no boundary renormalization, explains coverage.
  const horizontal = new Float64Array(data.length);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const out = (y * width + x) * 4;
      for (let d = Math.max(-support, -x); d <= Math.min(support, width - 1 - x); d++) {
        const source = (y * width + x + d) * 4;
        const weight = kernel[d + support];
        const alpha = data[source + 3];
        const colorWeight = weight * alpha / 255;
        horizontal[out] += data[source] * colorWeight;
        horizontal[out + 1] += data[source + 1] * colorWeight;
        horizontal[out + 2] += data[source + 2] * colorWeight;
        horizontal[out + 3] += alpha * weight;
      }
    }
  }
  const output = new Uint8Array(data.length);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let r = 0, g = 0, b = 0, a = 0;
      for (let d = Math.max(-support, -y); d <= Math.min(support, height - 1 - y); d++) {
        const source = ((y + d) * width + x) * 4;
        const weight = kernel[d + support];
        r += horizontal[source] * weight;
        g += horizontal[source + 1] * weight;
        b += horizontal[source + 2] * weight;
        a += horizontal[source + 3] * weight;
      }
      const out = (y * width + x) * 4;
      const alpha = Math.round(a);
      output[out + 3] = alpha;
      // Quantize premultiplied bytes before straight-RGBA conversion: explains
      // observed low-alpha channel variation. Zero-alpha RGB is canonical black.
      if (alpha > 0) {
        output[out] = Math.min(255, Math.round(Math.round(r) * 255 / alpha));
        output[out + 1] = Math.min(255, Math.round(Math.round(g) * 255 / alpha));
        output[out + 2] = Math.min(255, Math.round(Math.round(b) * 255 / alpha));
      }
    }
  }
  return { width, height, depth: 8, data: output };
}
