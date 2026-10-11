import type { Raster } from './current-image';

/**
 * Independent candidate based on supplied visible RGBA observations.
 * Translucent RGB uses an inferred 8-bit premultiply/unpremultiply
 * quantization; this is not a verified reference implementation mechanism.
 */
export function applyBrightness(raster: Raster, brightness: number): Raster {
  if (raster.depth !== 8 || !(raster.data instanceof Uint8Array)) {
    throw new Error('Brightness supports only 8-bit images. The original image remains available for export.');
  }
  if (!Number.isInteger(brightness) || brightness < -100 || brightness > 100) {
    throw new Error('Brightness must be an integer from -100 to 100.');
  }
  if (!Number.isInteger(raster.width) || !Number.isInteger(raster.height) ||
      raster.width <= 0 || raster.height <= 0 ||
      raster.data.length !== raster.width * raster.height * 4) {
    throw new Error('Invalid RGBA raster.');
  }
  const data = new Uint8Array(raster.data);
  // Neutral is byte-exact, including hidden RGB; never round-trip it.
  if (brightness !== 0) {
    const factor = 1 + brightness / 100;
    for (let i = 0; i < data.length; i += 4) {
      const alpha = data[i + 3];
      // Fully transparent nonneutral behavior is unobserved: retain hidden RGB.
      if (alpha === 0) continue;
      for (let channel = 0; channel < 3; channel++) {
        const scaled = Math.min(255, Math.floor(raster.data[i + channel] * factor));
        data[i + channel] = alpha === 255 ? scaled :
          Math.min(255, Math.round(Math.round(scaled * alpha / 255) * 255 / alpha));
      }
    }
  }
  return { ...raster, data };
}
