import type { RunBundleV1 } from './bundle.ts';
import { normalizeRun, type Run } from './normalize.ts';
export interface PortableAsset {path:string;sha256:string;bytes:number;mime:string;data:string}
export interface PortableRecording {schema:string;schema_version:number;manifest:string;manifest_sha256:string;assets:PortableAsset[]}
export const safePath=(p:unknown):p is string=>typeof p==='string'&&/^[A-Za-z0-9][A-Za-z0-9._/-]*$/.test(p)&&p.split('/').every(x=>x!=='.'&&x!=='..'&&x!=='');
const digest=async(b:Uint8Array)=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b as BufferSource))).map(x=>x.toString(16).padStart(2,'0')).join('');
export async function validatePortable(value:unknown):Promise<{manifest:RunBundleV1;assets:Map<string,Uint8Array>}> {
 const p=value as PortableRecording;
 if(!p||p.schema!=='reforge.portable-recording'||p.schema_version!==1)throw Error('Unsupported portable recording schema');
 if(typeof p.manifest!=='string'||p.manifest.length>10_000_000||!Array.isArray(p.assets)||p.assets.length>3000)throw Error('Invalid or oversized recording');
 if(await digest(new TextEncoder().encode(p.manifest))!==p.manifest_sha256)throw Error('Corrupted manifest');
 const m=JSON.parse(p.manifest);
 if(m.schema!=='reforge.run-bundle'||m.schema_version!==2||m.provenance?.kind!=='recorded'||!m.run?.id)throw Error('Unsupported manifest schema or provenance');
 if(!Number.isFinite(m.run.elapsed_seconds)||m.run.elapsed_seconds<0||!m.recording||!Array.isArray(m.recording.evidence)||!Array.isArray(m.recording.final?.suite)||!Array.isArray(m.recording.final?.cases)||!Number.isFinite(m.recording.final.available_at)||m.recording.final.available_at<0||m.recording.evidence.some((e:{available_at:number})=>!Number.isFinite(e.available_at)||e.available_at<0))throw Error('Invalid recording sections');
 if(!Array.isArray(m.events)||m.events.some((e:{sequence:number;elapsed_seconds:number},i:number)=>!Number.isFinite(e.elapsed_seconds)||e.elapsed_seconds<0||!Number.isInteger(e.sequence)||(i>0&&(e.sequence<=m.events[i-1].sequence||e.elapsed_seconds<m.events[i-1].elapsed_seconds))))throw Error('Invalid replay ordering');
 const assets=new Map<string,Uint8Array>();let total=0;
 if(!Array.isArray(m.artifacts))throw Error('Missing integrity inventory');
 for(const a of p.assets){
  if(!safePath(a.path)||assets.has(a.path)||!['image/png','image/jpeg'].includes(a.mime)||!Number.isInteger(a.bytes)||a.bytes<0||a.bytes>20_000_000||typeof a.data!=='string'||a.data.length>28_000_000||!/^[A-Za-z0-9+/]*={0,2}$/.test(a.data))throw Error('Unsafe or invalid asset');
  total+=a.bytes;if(total>150_000_000)throw Error('Recording too large');
  const bytes=Uint8Array.from(atob(a.data),c=>c.charCodeAt(0));
  const png=bytes[0]===137&&bytes[1]===80&&bytes[2]===78&&bytes[3]===71;
  const jpg=bytes[0]===255&&bytes[1]===216&&bytes[2]===255;
  if(!(a.mime==='image/png'?png:jpg)||bytes.length!==a.bytes||await digest(bytes)!==a.sha256)throw Error(`Corrupted asset: ${a.path}`);
  const inv=m.artifacts.find((x:PortableAsset)=>x.path===a.path);
  if(!inv||inv.sha256!==a.sha256||inv.bytes!==a.bytes||inv.mime!==a.mime)throw Error('Asset inventory mismatch');
  assets.set(a.path,bytes);
 }
 if(m.artifacts.length!==assets.size||m.artifacts.some((a:PortableAsset)=>!assets.has(a.path)))throw Error('Missing asset');
 const check=(v:unknown,key='')=>{if(v&&typeof v==='object'){for(const [k,x]of Object.entries(v)){if(key==='artifacts'&&typeof x==='string'&&(!safePath(x)||!assets.has(x)))throw Error(`Missing or unsafe reference: ${x}`);if(k==='path'&&typeof x==='string'&&(!safePath(x)||!assets.has(x)))throw Error('Unsafe evidence path');check(x,k);}}};
 // Inventory uses an array; only evidence artifact maps contain references.
 check({...m,artifacts:undefined});
 return {manifest:m,assets};
}
export async function importPortable(value:unknown):Promise<{run:Run;dispose:()=>void}> {
 const {manifest,assets}=await validatePortable(value);const urls=new Map<string,string>();
 for(const [path,bytes]of assets){const mime=(value as PortableRecording).assets.find(a=>a.path===path)!.mime;urls.set(path,URL.createObjectURL(new Blob([bytes as BlobPart],{type:mime})));}
 try {
 const run=normalizeRun(manifest,'portable-assets/',manifest.run!.id!);
 const rewrite=(v:unknown):unknown=>typeof v==='string'&&v.startsWith('portable-assets/')?urls.get(v.slice(16))??null:Array.isArray(v)?v.map(rewrite):v&&typeof v==='object'?Object.fromEntries(Object.entries(v).map(([k,x])=>[k,rewrite(x)])):v;
 const resolved=rewrite(run) as Run;
 const recording=manifest.recording;
 resolved.recording=rewrite(recording) as Run['recording'];
 if(resolved.recording){
 const f=resolved.recording.final;
 resolved.recording.finalRun=rewrite(normalizeRun({schema_version:2,suite:{cases:f.suite},candidates:[{id:"once-only-final",cases:f.cases}]},"portable-assets/",run.id)) as Run;
 for(const e of resolved.recording.evidence)e.path=urls.get(e.path)??'';}
 return {run:resolved,dispose:()=>urls.forEach(u=>URL.revokeObjectURL(u))};
 } catch(error) { urls.forEach(u=>URL.revokeObjectURL(u)); throw error; }
}
