import {createHash} from 'node:crypto';
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validatePortable,importPortable,safePath,type PortableRecording} from './portable.ts';
import {snapshotAt} from './normalize.ts';
const load=(n:string)=>JSON.parse(readFileSync(new URL(`../../public/runs/${n}-success.reforge.json`,import.meta.url),'utf8')) as PortableRecording;
for(const name of ['brightness','contrast'])test(`Real ${name} recording validates and replays with no fetch`,async()=>{
 const source=load(name);const {manifest,assets}=await validatePortable(source);
 assert.equal(assets.size,source.assets.length);assert.equal(manifest.run?.status,'accepted');
 const {run,dispose}=await importPortable(source);
 assert.equal(run.id,name==='brightness'?'82b68e6daf5e41ddb7c03c13a91ba1f9':'9df7c33da7a5425db3934e2cd928c5ee');
 assert.equal(run.duration,name==='brightness'?297.46:346.775);
 assert.equal(snapshotAt(run,0).stopped,false);assert.equal(snapshotAt(run,run.duration).stopped,true);
 for(const c of run.candidates){assert.ok(c.revealedAt>0);for(const k of c.cases){assert.ok(k.images.reference?.startsWith('blob:'));if(k.images.candidate)assert.ok(k.images.candidate.startsWith('blob:'));}}
 assert.deepEqual(run.candidates.map(c=>c.cases.map(k=>k.metrics?.differentPixels)),name==='brightness'?[[0,0,0,0],[0,0,0,0]]:[[0,0,0,0]]);
 assert.equal(run.recording?.finalRun?.candidates[0].cases.length,2);
 assert.equal(run.telemetry.reduce((sum,t)=>sum+(t.usage?.total??0),0),name==='brightness'?409928:250976);
 assert.equal(run.target.name,'miniPaint');
 assert.equal(run.target.version,'4.14.3');
 assert.ok(run.telemetry.every(t=>t.revealedAt!==null&&t.revealedAt>0));
 assert.ok(run.recording?.finalRun?.candidates[0].cases[0].images.reference?.startsWith('blob:'));
 dispose();
});
test('Real recording rejects corrupted/missing assets and unsupported schema',async()=>{
 const bad=load('brightness');bad.assets[0].data=bad.assets[0].data.slice(0,-4)+'AAAA';await assert.rejects(validatePortable(bad),/Corrupted/);
 const missing=load('brightness');missing.assets.pop();await assert.rejects(validatePortable(missing),/Missing/);
 const schema=load('brightness');schema.schema_version=99;await assert.rejects(validatePortable(schema),/Unsupported/);
 const manifest=load('brightness');manifest.manifest+=' ';await assert.rejects(validatePortable(manifest),/Corrupted manifest/);
});
test('Synthetic unsafe path fixture is explicitly rejected',()=>{for(const p of ['../secret','x/../secret','C:/private','/private','x\\secret','https://evil','x//y','x/./y','x%2fy'])assert.equal(safePath(p),false);});
test('Real run switches use isolated object URLs even for identical case IDs',async()=>{
 const a=await importPortable(load('brightness')),b=await importPortable(load('contrast'));
 assert.notEqual(a.run.candidates[0].cases[0].images.reference,b.run.candidates[0].cases[0].images.reference);
 assert.notEqual(a.run.id,b.run.id);a.dispose();assert.ok(b.run.candidates[0].cases[0].images.reference);b.dispose();
});

test('Synthetic mutations reject unsafe references, ordering and unsupported manifest',async()=>{
 const mutate=async(change:(m:any,p:PortableRecording)=>void)=>{const p=load('brightness');const m=JSON.parse(p.manifest);change(m,p);p.manifest=JSON.stringify(m);p.manifest_sha256=createHash('sha256').update(p.manifest).digest('hex');return validatePortable(p);};
 await assert.rejects(mutate(m=>{m.schema_version=99;}),/Unsupported/);
 await assert.rejects(mutate(m=>{m.events.reverse();}),/ordering/);
 await assert.rejects(mutate(m=>{m.suite.cases[0].artifacts.input='../private.png';}),/unsafe/);
 await assert.rejects(mutate((_m,p)=>{p.assets[0].path='C:/private.png';}),/Unsafe/);
});
