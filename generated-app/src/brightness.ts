import type { Raster } from './current-image';

/**
 * Independent, observation-based 8-bit implementation.
 * Opaque RGB follows the observed floor-and-clamp mapping. Partial-alpha
 * quantization is a hypothesis consistent with the supplied -50 samples;
 * it is not a claim about reference internals. See README.md.
 */
export function applyBrightness(raster: Raster, brightness: number): Raster {
  if (raster.depth !== 8) {
    throw new Error('Brightness supports only 8-bit images. The original image remains available for export.');
  }
  if (!Number.isInteger(brightness) || brightness < -100 || brightness > 100) {
    throw new Error('Brightness must be an integer from -100 to 100.');
  }
  if (!(raster.data instanceof Uint8Array) ||
      !Number.isInteger(raster.width) || !Number.isInteger(raster.height) ||
      raster.width <= 0 || raster.height <= 0 ||
      raster.data.length !== raster.width * raster.height * 4) {
    throw new Error('Invalid 8-bit RGBA raster.');
  }
  const data = new Uint8Array(raster.data);
  // Bypass quantization entirely at neutral, including invisible RGB.
  if (brightness !== 0) {
    const factor = 1 + brightness / 100;
    for (let i = 0; i < data.length; i += 4) {
      const alpha = data[i + 3];
      // Invisible colors are unresolved by the evidence; preserve them.
      if (alpha === 0) continue;
      for (let channel = 0; channel < 3; channel++) {
        const value = Math.max(0, Math.min(255, Math.floor(raster.data[i + channel] * factor)));
        data[i + channel] = alpha === 255 ? value :
          Math.max(0, Math.min(255, Math.round(Math.round(value * alpha / 255) * 255 / alpha)));
      }
    }
  }
  return { ...raster, data };
}
