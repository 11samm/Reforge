import { convertIndexedToRgb, decode, encode } from 'fast-png';

export type Raster = {
  width: number;
  height: number;
  depth: 8 | 16;
  data: Uint8Array | Uint16Array;
};

// Internal document state. There are no production mutation controls or global test hooks.
export const currentImage: { raster: Raster | null } = { raster: null };

export function decodePngRaster(bytes: Uint8Array): Raster {
  const png = decode(bytes, { checkCrc: true });
  const { width, height } = png;
  let samples = png.data;
  let channels = png.channels;
  let depth = png.depth;
  if (png.palette) {
    samples = convertIndexedToRgb(png);
    channels = png.palette[0].length;
    depth = 8;
  }
  const outputDepth = depth === 16 ? 16 : 8;
  const data = outputDepth === 16 ? new Uint16Array(width * height * 4) : new Uint8Array(width * height * 4);
  const max = outputDepth === 16 ? 65535 : 255;
  const rowBytes = Math.ceil(width * depth / 8);
  for (let pixel = 0; pixel < width * height; pixel++) {
    const offset = pixel * channels;
    let r: number, g: number, b: number, alpha: number;
    if (depth < 8) {
      const x = pixel % width, y = Math.floor(pixel / width);
      const raw = (samples[y * rowBytes + Math.floor(x * depth / 8)] >> (8 - depth - x * depth % 8)) & ((1 << depth) - 1);
      r = g = b = Math.round(raw * 255 / ((1 << depth) - 1));
      alpha = png.transparency?.[0] === raw ? 0 : 255;
    } else if (channels <= 2) {
      r = g = b = samples[offset];
      alpha = channels === 2 ? samples[offset + 1] : png.transparency?.[0] === r ? 0 : max;
    } else {
      r = samples[offset]; g = samples[offset + 1]; b = samples[offset + 2];
      alpha = channels === 4 ? samples[offset + 3] :
        png.transparency?.length === 3 && png.transparency[0] === r && png.transparency[1] === g && png.transparency[2] === b ? 0 : max;
    }
    data.set([r, g, b, alpha], pixel * 4);
  }
  return { width, height, depth: outputDepth, data };
}

export function serializeRaster(raster: Raster | null): Blob {
  if (!raster || raster.data.length !== raster.width * raster.height * 4) {
    throw new Error('No valid current image to export.');
  }
  // Serialize the current unpremultiplied samples, including invisible RGB, every time.
  const encoded = encode({ ...raster, channels: 4 });
  return new Blob([new Uint8Array(encoded)], { type: 'image/png' });
}

export function serializeCurrentImage(): Blob {
  return serializeRaster(currentImage.raster);
}
