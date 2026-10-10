import "D:/Samuel/Downloads/Code/Reforge/generated-app/src/main.tsx";
import { currentImage } from "D:/Samuel/Downloads/Code/Reforge/generated-app/src/current-image.ts";
(window as any).milestoneTestChangePixel = (x: number,y: number,rgb: number[]) => {const r=currentImage.raster;if(!r || x<0 || y<0 || x>=r.width || y>=r.height)throw new Error('Invalid fixture pixel');const i=4*(y*r.width+x);r.data.set(rgb,i);return Array.from(r.data.slice(i,i+4));};
