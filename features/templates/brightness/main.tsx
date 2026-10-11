import { useEffect, useRef, useState, type ReactNode } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';
import { currentImage, decodePngRaster, serializeCurrentImage, type Raster } from './current-image';

type Document = { file: File; url: string; width: number; height: number; raster: Raster };
const LIMIT = 20 * 1024 * 1024;
function checkSize(w: number, h: number) {
  if (!w || !h || w > 8192 || h > 8192 || w * h > 16_777_216) throw new Error('Image exceeds the limit: 8192 px per side and 16 megapixels.');
}
function crc(bytes: Uint8Array, start: number, end: number) {
  let n = 0xffffffff;
  for (let i = start; i < end; i++) {
    n ^= bytes[i];
    for (let j = 0; j < 8; j++) n = (n >>> 1) ^ ((n & 1) ? 0xedb88320 : 0);
  }
  return (n ^ 0xffffffff) >>> 0;
}
function validate(bytes: Uint8Array, mime: string): [number, number] {
  const bad = () => { throw new Error('Corrupt or unsupported image. Please choose an original PNG or JPEG.'); };
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (mime === 'image/png') {
    if (bytes.length < 45 || ![137,80,78,71,13,10,26,10].every((v,i) => bytes[i] === v)) return bad();
    let p = 8, width = 0, height = 0, data = false, ended = false;
    while (p + 12 <= bytes.length) {
      const len = view.getUint32(p), end = p + 12 + len;
      if (end > bytes.length) return bad();
      const type = String.fromCharCode(...bytes.subarray(p + 4, p + 8));
      if (crc(bytes,p + 4,p + 8 + len) !== view.getUint32(p + 8 + len)) return bad();
      if (p === 8 && (type !== 'IHDR' || len !== 13)) return bad();
      if (type === 'IHDR') {
        if (p !== 8) return bad();
        width = view.getUint32(p + 8); height = view.getUint32(p + 12);
        checkSize(width,height);
      }
      if (type === 'IDAT') data = true;
      if (type === 'IEND') { if (len !== 0 || !data || end !== bytes.length) return bad(); ended = true; break; }
      p = end;
    }
    if (!ended) return bad();
    return [width,height];
  }
  if (mime !== 'image/jpeg' || bytes.length < 4 || bytes[0] !== 255 || bytes[1] !== 216 || bytes[bytes.length-2] !== 255 || bytes[bytes.length-1] !== 217) return bad();
  let p = 2;
  while (p < bytes.length) {
    if (bytes[p++] !== 255) return bad();
    while (bytes[p] === 255) p++;
    const marker = bytes[p++];
    if (marker === 218 || marker === 217) break;
    if (marker === 1 || (marker >= 208 && marker <= 215)) continue;
    if (p + 2 > bytes.length) return bad();
    const len = view.getUint16(p);
    if (len < 2 || p + len > bytes.length) return bad();
    if ([192,193,194,195,197,198,199,201,202,203,205,206,207].includes(marker)) {
      if (len < 8) return bad();
      const h = view.getUint16(p + 3), w = view.getUint16(p + 5);
      checkSize(w,h); return [w,h];
    }
    p += len;
  }
  return bad();
}
function Disabled({ children, name, className = '' }: { children: ReactNode; name?: string; className?: string }) {
  return <button disabled title="Unavailable" aria-label={name} className={className}>{children}</button>;
}
function Panel({ title, children, className = '' }: { title: string; children: ReactNode; className?: string }) {
  return <section className={'panel ' + className}><h2>{title}<span aria-hidden="true">▴</span></h2><div className="panel-body">{children}</div></section>;
}
function App() {
  const [doc,setDoc] = useState<Document | null>(null);
  const [error,setError] = useState('');
  const [busy,setBusy] = useState(false);
  const [menu,setMenu] = useState<'File' | 'Image' | 'Effects' | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const effects = useRef<HTMLButtonElement>(null);
  const sequence = useRef(0);
  const urls = useRef(new Set<string>());
  const current = useRef<Document | null>(null);
  const mounted = useRef(true);
  const menuRoot = useRef<HTMLElement>(null);
  useEffect(() => {
    mounted.current = true;
    const dismiss = (e: PointerEvent) => { if (!menuRoot.current?.contains(e.target as Node)) setMenu(null); };
    window.addEventListener('pointerdown',dismiss);
    return () => { mounted.current = false; currentImage.raster = null; sequence.current++; urls.current.forEach(URL.revokeObjectURL); urls.current.clear(); window.removeEventListener('pointerdown',dismiss); };
  },[]);
  async function upload(file: File) {
    const token = ++sequence.current;
    setError(''); setBusy(true);
    let url: string | undefined;
    try {
      if (file.size > LIMIT || !file.size) throw new Error('Choose a nonempty PNG or JPEG of at most 20 MiB.');
      if (!['image/png','image/jpeg'].includes(file.type)) throw new Error('Unsupported file type. Only PNG and JPEG are available.');
      const bytes = new Uint8Array(await file.arrayBuffer());
      validate(bytes,file.type);
      let raster = file.type === 'image/png' ? decodePngRaster(bytes) : null;
      if (token !== sequence.current || !mounted.current) return;
      url = URL.createObjectURL(file); urls.current.add(url);
      const img = new Image(); img.src = url;
      await img.decode();
      checkSize(img.naturalWidth,img.naturalHeight);
      if (token !== sequence.current || !mounted.current) return;
      if (!raster) {
        const canvas = document.createElement('canvas');
        canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
        const ctx = canvas.getContext('2d');
        if (!ctx) throw new Error('Image decoding is unavailable in this browser.');
        ctx.drawImage(img, 0, 0);
        raster = { width: canvas.width, height: canvas.height, depth: 8, data: new Uint8Array(ctx.getImageData(0, 0, canvas.width, canvas.height).data) };
      }
      if (raster.width !== img.naturalWidth || raster.height !== img.naturalHeight) throw new Error('Image dimensions disagree between decoders.');
      const next = { file, url, width: raster.width, height: raster.height, raster };
      if (current.current) { URL.revokeObjectURL(current.current.url); urls.current.delete(current.current.url); }
      currentImage.raster = raster; current.current = next; setDoc(next); url = undefined;
    } catch (e) {
      if (token === sequence.current && mounted.current) setError(e instanceof Error ? e.message : 'Unable to decode this image.');
    } finally {
      if (url) { URL.revokeObjectURL(url); urls.current.delete(url); }
      if (token === sequence.current && mounted.current) setBusy(false);
    }
  }
  async function exportPNG() {
    if (!doc) return;
    const selected = doc;
    try {
      const blob = serializeCurrentImage();
      if (!mounted.current) return;
      const url = URL.createObjectURL(blob); urls.current.add(url);
      const a = document.createElement('a'); a.href = url; a.download = selected.file.name.replace(/\.[^.]*$/,'') + '.png';
      document.body.appendChild(a); a.click(); a.remove();
      window.setTimeout(() => { URL.revokeObjectURL(url); urls.current.delete(url); },1000);
      setMenu(null);
    } catch { if (mounted.current) setError('Could not export PNG. Please try again.'); }
  }
  const w = doc?.width ?? 1024, h = doc?.height ?? 768;
  const tools = ['Pointer','Rectangle selection','Brush','Pencil','Eyedropper','Eraser','Magic wand','Paint bucket','Shapes','Picture','Text','Gradient','Stamp','Crop','Droplet','Diamond','Sponge','Inward arrows','Play'];
  const glyphs = ['➤','▧','🖌','✎','⚗','▰','⚒','♢','♧','▣','T','▥','♟','⌑','♧','◇','▨','⤢','⊙'];
  return <>
    <nav aria-label="Main Menu" ref={menuRoot} className="menu-row" onKeyDown={e => { if(e.key === 'Escape') setMenu(null); }}>
      <div role="menubar">{['File','Edit','View','Image','Layer','Effects','Tools','Help'].map(name =>
        name === 'File' || name === 'Effects' ? <button key={name} role="menuitem" ref={name === 'Effects' ? effects : undefined} aria-haspopup="menu" aria-expanded={menu === name} onClick={() => setMenu(menu === name ? null : name)}>{name}</button> : <button role="menuitem" key={name} disabled title="Unavailable">{name}</button>)}</div>
      {menu && <div className={'dropdown ' + (menu === 'Effects' ? 'effects-menu' : '')} role="menu" aria-label={menu}>
        {menu === 'File' ? <><button role="menuitem" onClick={() => { input.current?.click(); setMenu(null); }}>Open image…</button><button role="menuitem" disabled={!doc} onClick={exportPNG}>Export PNG</button></> :
        <button role="menuitem" onClick={() => { setMenu(null); dialog.current?.showModal(); }}>Gaussian Blur…</button>}
      </div>}
    </nav>
    <label className="sr-only" htmlFor="image-upload">Open image (PNG or JPEG)</label>
    <input ref={input} id="image-upload" className="sr-only" type="file" accept="image/png,image/jpeg" onChange={e => { const file=e.target.files?.[0]; e.target.value=''; if(file) void upload(file); }} />
    <header className="options"><span className="brand"><span className="brand-icon" aria-hidden="true">▨</span> miniPaint</span><div className="options-inset"><label>Size: <input type="number" value="4" disabled title="Unavailable" /></label><Disabled className="pressure">× &nbsp; Pressure</Disabled></div></header>
    <main className="editor">
      <aside className="tool-strip" aria-label="Unavailable editing tools">{tools.map((t,i) => <Disabled key={t} name={t} className={i===2 ? 'selected' : ''}><span aria-hidden="true">{glyphs[i]}</span></Disabled>)}</aside>
      <section className="workspace" aria-label="Image workspace">
        <div className={'document ' + (doc ? 'checker' : '')} style={{ aspectRatio: w + '/' + h, width: 'min(' + w + 'px, calc(100cqw - 40px), calc((100cqh - 40px) * ' + (w / h) + '))', maxWidth: 'calc(100% - 40px)', maxHeight: 'calc(100% - 40px)' }}>
          {doc ? <img src={doc.url} alt={'Original image preview: ' + doc.file.name} /> : <div className="empty-state"><span>No image loaded</span><span>Brightness unavailable until learned</span><button onClick={() => input.current?.click()}>Open image…</button></div>}
        </div>
        {busy && <div className="status" role="status">Validating original image…</div>}
        {error && <div className="error" role="alert">{error}</div>}
      </section>
      <aside className="sidebar">
        <Panel title="Preview" className="preview"><div className={'thumbnail ' + (doc ? 'checker' : '')}>{doc && <img src={doc.url} alt={'Original image thumbnail: ' + doc.file.name} />}</div><div className="zoom">{['−','100%','+','Fit'].map(x => <Disabled key={x} name={x}>{x}</Disabled>)}</div><input type="range" aria-label="Zoom" disabled title="Unavailable" value="100" min="0" max="1000" /></Panel>
        <Panel title="Colors" className="colors"><div className="color-top"><span className="swatch"/><div><Disabled name="Toggle Color Picker">◉</Disabled><Disabled name="Toggle Color Channels">▤</Disabled><Disabled name="Toggle Swatches">▦</Disabled></div></div><div className="picker" aria-label="Unavailable color picker ornament"><div className="saturation"><i/></div><div className="hue"/></div><label className="hex">Hex <input disabled title="Unavailable" value="#008000" /></label></Panel>
        <Panel title="Information" className="information"><div>Size: {w} x {h} px</div><div>Mouse: - px</div><div>Resolution: {doc ? '—' : '72'}</div></Panel>
        <Panel title="Layer details" className="details">{['X','Y','Width','Height','Rotate','Opacity','Color'].map((name,i) => <div className={'detail-row ' + (i===4 ? 'divider' : '')} key={name}><label htmlFor={'detail-'+name}>{name}{name==='X' ? '' : ':'}</label>{[0,1,4,5].includes(i) ? <Disabled name={'Reset '+name}>⟳</Disabled> : <span/>}<input id={'detail-'+name} title="Unavailable" disabled type={i===6 ? 'color' : 'number'} value={i===6 ? '#008000' : i===2 ? (doc?.width ?? '') : i===3 ? (doc?.height ?? '') : i===5 ? 100 : 0} /></div>)}</Panel>
        <Panel title="Layers" className="layers"><div className="layer-actions">{['+','D','R','↑','↓'].map((g,i) => <Disabled key={g} name={['Insert new layer','Duplicate layer','Convert layer to raster','Move layer up','Move layer down'][i]}>{g}</Disabled>)}</div><div className="layer-row">{doc ? <><Disabled name="Hide layer">◉</Disabled><Disabled className="layer-name" name={doc.file.name}>{doc.file.name}</Disabled><Disabled name="Delete layer" className="delete">×</Disabled></> : <span className="no-layer">No uploaded layer</span>}</div></Panel>
      </aside>
    </main>
    <dialog ref={dialog} aria-labelledby="blur-title" aria-describedby="blur-description" onClose={() => effects.current?.focus()}><h2 id="blur-title">Gaussian Blur</h2><p id="blur-description">Unavailable until the learning loop implements it. No image changes are performed.</p><label htmlFor="percentage">Percentage: 0</label><input id="percentage" type="range" min="0" max="50" step="1" value="0" disabled title="Unavailable" /><div className="dialog-actions"><Disabled>Apply</Disabled><button autoFocus onClick={() => dialog.current?.close()}>Close</button></div></dialog>
  </>;
}
createRoot(document.getElementById('root')!).render(<App />);
