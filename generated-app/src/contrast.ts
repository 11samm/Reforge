import type { Raster } from './current-image';

/**
 * Independent candidate from adjustment-1 through adjustment-4.
 * Only opaque ramps at 0/+50/-50 and extreme colored channels at -50
 * are observed; other settings/colors and alpha quantization are hypotheses.
 */
export function applyContrast(raster: Raster, value: number): Raster {
  if (!Number.isInteger(value) || value < -100 || value > 100) {
    throw new Error('Contrast must be an integer from -100 to 100.');
  }
  if (raster.depth !== 8) {
    throw new Error('Contrast does not support depth16.');
  }
  if (!Number.isInteger(raster.width) || !Number.isInteger(raster.height) ||
      raster.width <= 0 || raster.height <= 0 ||
      !Number.isSafeInteger(raster.width * raster.height * 4) ||
      !(raster.data instanceof Uint8Array) ||
      raster.data.length !== raster.width * raster.height * 4) {
    throw new Error('Invalid 8-bit RGBA raster.');
  }
  const data = new Uint8Array(raster.data);
  const scale = 1 + value / 100;
  for (let i = 0; i < data.length; i += 4) {
    const alpha = raster.data[i + 3];
    // Fully transparent behavior is unobserved; preserve hidden RGB.
    if (alpha === 0) continue;
    for (let channel = 0; channel < 3; channel++) {
      let result = Math.max(0, Math.min(255,
        Math.floor((raster.data[i + channel] - 127.5) * scale + 127.5)));
      // Candidate premultiplication round trip fits adjustment-4:
      // 63/191 -> 64/191 at alpha128, and 60/195 at alpha17.
      // Apply at zero too: only opaque zero identity has been observed.
      if (alpha < 255) {
        result = Math.max(0, Math.min(255,
          Math.round(Math.round(result * alpha / 255) * 255 / alpha)));
      }
      data[i + channel] = result;
    }
  }
  return { ...raster, data };
}
