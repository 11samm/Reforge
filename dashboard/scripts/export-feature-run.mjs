import {readFileSync,writeFileSync,existsSync,readdirSync,realpathSync,mkdirSync} from 'node:fs';
import {resolve,join,relative,isAbsolute,basename} from 'node:path';
import {createHash} from 'node:crypto';
const args=Object.fromEntries(process.argv.slice(2).reduce((a,v,i,s)=> i%2?a:[...a,[v.slice(2),s[i+1]]],[]));
for(const k of ['repo','run','job','out']) if(!args[k]) throw Error(`Missing --${k}`);
const repo=realpathSync(args.repo), root=realpathSync(args.run), job=realpathSync(args.job);
const inside=(r,p)=>{const v=relative(r,p);return !isAbsolute(v)&&v!=='..'&&!v.startsWith('..\\')&&!v.startsWith('../');};
const read=p=> existsSync(p)?JSON.parse(readFileSync(p,'utf8')):null;
const hash=b=>createHash('sha256').update(b).digest('hex');
const state=read(join(repo,'evidence','feature-jobs',basename(job).replace(/^feature-/,''),'job.json'));
const report=read(join(root,'report.json')), outcome=read(join(job,'job-result.json'));
if(state?.status!=='accepted'||report?.status!=='accepted'||outcome?.status!=='accepted') throw Error('Original archive/job acceptance is required');
if(state.id!==basename(job).replace(/^feature-/,'')) throw Error('Job identity mismatch');
const spec=read(join(job,'spec.json')), prov=read(join(root,'provenance.json'));
if(basename(prov.app)!==`feature-${state.id}` || prov.feature_spec?.feature_id!==spec.feature_id)throw Error('Learning archive belongs to another job/feature');
if(!report.candidate_attempts.some(c=>c.id===report.first_acceptance?.candidate_id&&c.status==='accepted'))throw Error('Missing original candidate acceptance');
for(const c of report.candidate_attempts)if(c.checkpoint&&!inside(root,realpathSync(c.checkpoint)))throw Error('Candidate checkpoint belongs to another archive');
const operation=spec.feature_id==='brightness'?'Brightness':spec.feature_id==='contrast'?'Contrast':null;
if(!operation) throw Error('Unsupported feature archive');
// Allowlist structure and remove machine-local filesystem references. Never read model transcripts/packets.
const clean=v=>typeof v==='string'?v.replace(/(?:[A-Za-z]:[\\/]|\/(?:home|Users|tmp|workspace)\/)[^\s"<>]+/g,'[local evidence]'):Array.isArray(v)?v.map(clean):v&&typeof v==='object'?Object.fromEntries(Object.entries(v).filter(([k])=>!['thread_id','prompt','answer','packet','checkpoint','app','pid','cwd','env','requested_window_position','artifacts'].includes(k)).map(([k,x])=>[k,clean(x)])):v;
const pick=(o,keys)=>Object.fromEntries(keys.filter(k=>o?.[k]!==undefined).map(k=>[k,clean(o[k])]));
const assets=new Map();
function image(p,dest,expected){
 if(!p||!existsSync(p)) return null;
 const full=realpathSync(p); if(![root,job].some(r=>inside(r,full))) throw Error('Asset escapes source archive');
 if(!/\.(png|jpg|jpeg)$/i.test(full)) throw Error('Image only');
 const bytes=readFileSync(full); if(expected&&hash(bytes)!==expected) throw Error('Original asset hash mismatch');
 assets.set(dest,{path:dest,sha256:hash(bytes),bytes:bytes.length,mime:/\.png$/i.test(full)?'image/png':'image/jpeg',data:bytes.toString('base64')});return dest;
}
const original=readFileSync(join(root,'events.jsonl'),'utf8').trim().split(/\r?\n/).map(JSON.parse);
let cursor=0;
const events=state.events.map(e=>{
 const next=original[cursor];
 // JobStore forwards each learning event in original order. Preserve both clocks, never estimate an offset.
 if(next&&e.event===next.event&&!(e.event==='evidence'&&e.artifact)){
  cursor++;const merged={...clean(next),archive_elapsed_seconds:next.elapsed_seconds,elapsed_seconds:e.elapsed_seconds,sequence:e.sequence};
  if(merged.candidate_id) merged.id=merged.candidate_id;
  if(merged.result) Object.assign(merged,pick(merged.result,['cases','build_valid','independent','baseline_pass','ui_valid','error']));
  if(merged.event==='stop') merged.event='visible_stop';
  return merged;
 }
 return pick(e,['sequence','event','elapsed_seconds','stage','activity']);
});
if(cursor!==original.length) throw Error(`Unmatched original events: ${cursor}/${original.length}`);
const suiteRaw=read(join(root,'suite.json'));
function suiteCase(c,section){return {id:c.id,source:section==='final'?'once_only_final':'fresh_experiment',percentage:c.value,regions:c.regions,artifacts:{input:image(c.input,`assets/${section}/${c.id}/input.png`,c.input_sha256),reference:image(c.expected,`assets/${section}/${c.id}/reference.png`,c.expected_sha256)}};}
const suite={...pick(suiteRaw,['id','policy']),sha256:report.suite_sha256,cases:suiteRaw.cases.map(c=>suiteCase(c,'visible'))};
const experiments=suiteRaw.cases.map(c=>{
 const rec=read(join(root,'experiments',c.id,'reference-record.json'));
 const plan=original.find(e=>e.event==='experiment'&&e.id===c.id)?.plan;
 return {id:c.id,plan:{...pick(plan,['question','hypotheses','predictions','usefulness','input']),percentage:plan?.value??c.value},input_spec:read(join(root,'evidence',`${c.id}.json`))?.input_spec,percentage_requested:rec?.requested??c.value,percentage_accepted:rec?.accepted??null,status:rec?.status,original_import_confirmed:rec?.original_confirmation?.rgba_equal,target:pick(rec?.target,['name','url','visible_about_version','build']),artifacts:{input:suite.cases.find(s=>s.id===c.id).artifacts.input,reference_output:suite.cases.find(s=>s.id===c.id).artifacts.reference}};
});
function caseResult(c,base,section){const id=c.case_id??c.id;const dir=join(base,'evaluation',id);return {...pick(c,['case_id','status','classification','dimensions_equal','dimensions','metrics','regions','reasons','policy','policy_sha256']),artifacts:{candidate:image(join(dir,'candidate-raw.png'),`assets/${section}/${id}/candidate.png`),rgb_difference:image(join(dir,'rgb-difference-x16.png'),`assets/${section}/${id}/rgb.png`),alpha_difference:image(join(dir,'alpha-difference-x16.png'),`assets/${section}/${id}/alpha.png`)}};}
const candidates=report.candidate_attempts.map((c,i)=>{
 const result=original.find(e=>e.event==='evaluation'&&e.label===c.id)?.result;
 const start=events.find(e=>e.event==='packet_measured'&&e.label===`builder-${i+1}`);
 return {...pick(c,['id','status','reason']),accepted:c.status==='accepted',started_seconds:start?.elapsed_seconds,decided_seconds:c.status==='accepted'?events.find(e=>e.event==='visible_stop')?.elapsed_seconds:events.find(e=>e.event==='rejection'&&e.id===c.id)?.elapsed_seconds,build_valid:result?.build_valid,independent:result?.independent,baseline_pass:result?.baseline_pass,ui_check:result?.ui_check?{case_id:result.ui_check.case_id,rgba_equal:result.ui_check.comparison?.rgba_equal,external_requests:result.ui_check.external_requests?.length,browser_errors:result.ui_check.browser_errors?.length}:null,error:clean(result?.error??null),builder_invocation:`builder-${i+1}`,baseline_label:`${c.id}-gates`,cases:(result?.cases??[]).map(k=>caseResult(k,join(root,'evaluations',c.id),c.id))};
});
const baselines=original.filter(e=>e.event==='baseline').map(e=>({label:e.label,...pick(read(join(root,e.label,'baseline','results.json')),['suite_id','status','classification','shell_status','shell_error']),cases:(read(join(root,e.label,'baseline','results.json'))?.cases??[]).map(c=>pick(c,['case_id','status','classification','dimensions_equal','dimensions','metrics','regions','reasons']))}));
const telemetry=[];
function usageRecord(role,inv,availableAt){const t=inv?.usage?.total;return {...pick(inv,['model','effort','status','completion_status','elapsed_seconds']),invocation:role,record_present:Boolean(inv),available_at:availableAt,usage:t?{total_tokens:t.totalTokens,input_tokens:t.inputTokens,cached_input_tokens:t.cachedInputTokens,output_tokens:t.outputTokens,reasoning_output_tokens:t.reasoningOutputTokens}:null};}
for(const role of readdirSync(join(root,'model'))){
 const inv=read(join(root,'model',role,'invocation.json'));if(!inv)continue;
 const packet=events.find(e=>e.event==='packet_measured'&&e.label===role);
 const at=events.find(e=>e.event==='usage'&&e.elapsed_seconds>(packet?.elapsed_seconds??Infinity))?.elapsed_seconds;
 telemetry.push(usageRecord(role,inv,at));
}
const discoveryInvocation=read(join(job,'discovery','attempt','model','invocation.json'));
if(discoveryInvocation)telemetry.push(usageRecord('discovery',discoveryInvocation,state.events.find(e=>e.event==='usage')?.elapsed_seconds));
const finalRaw=read(join(job,'final','suite.json')), finalResult=read(join(job,'final','evaluation','result.json'));
const finalSummary=read(join(job,'final-summary.json'));
const finalAt=state.events.find(e=>e.artifact?.endsWith('/final-summary.json'))?.elapsed_seconds??state.elapsed_seconds;
const finalCases=finalRaw.cases.map(c=>suiteCase(c,'final'));
const finalResults=(finalResult?.cases??finalSummary.cases).map(c=>caseResult(c,join(job,'final','evaluation'),'final'));
const evidence=[];
// Screenshots are archival images; conservative availability at section completion. No live frames are read.
for(const [section,dir,at] of [['experiments',join(root,'experiments'),events.find(e=>e.event==='suite_frozen')?.elapsed_seconds??state.elapsed_seconds],...candidates.map(c=>[c.id,join(root,'evaluations',c.id),events.find(e=>e.event==='evaluation'&&e.label===c.id)?.elapsed_seconds??state.elapsed_seconds]),...original.filter(e=>e.event==='baseline').map(e=>[e.label,join(root,e.label),events.find(x=>x.event==='baseline'&&x.label===e.label)?.elapsed_seconds??state.elapsed_seconds]),['brightness-regression',join(root,'brightness-regression'),state.elapsed_seconds],['final-evaluation',join(job,'final'),finalAt],['discovery',join(job,'discovery'),state.events.find(e=>e.artifact?.endsWith('/spec.json'))?.elapsed_seconds??state.elapsed_seconds]]){
 function walk(p){for(const entry of readdirSync(p,{withFileTypes:true})){if(entry.isSymbolicLink())throw Error('Symlink refused');const f=join(p,entry.name);if(entry.isDirectory())walk(f);else if(/\.(png|jpe?g)$/i.test(entry.name)){const path=`assets/screenshots/${section}/${relative(dir,f).replaceAll('\\','/')}`;evidence.push({label:`Recorded ${section}: ${relative(dir,f)}`,available_at:at,path:image(f,path)});}}}if(existsSync(dir))walk(dir);
}
const historicalNotes=operation==='Brightness'?'Fresh third Brightness attempt. Two unresolved prior jobs preceded success; developer frozen-control host fix and shell-preservation prompt changes occurred between attempts. Prior target evidence was not supplied. Candidate 1 rejected for baseline regression; candidate 2 accepted after automatic repair. No harness repair during this run.':'Independent Contrast discovery in a newly isolated workspace without Contrast; existing Brightness retained. Internal harness mode development_resume is not proof of a resumed job. Later canonical promotion and developer revalidation are separate from this source run. Acceptance is within tested scope, not exhaustive compatibility.';
const notes=['82b68e6daf5e41ddb7c03c13a91ba1f9','9df7c33da7a5425db3934e2cd928c5ee'].includes(state.id)?historicalNotes:`${operation} run ${state.id}. ${prov.clean_start_autonomous_demonstration?'Fresh target-absent discovery and experiments; prior target evidence was excluded.':'Original provenance does not establish a clean-start autonomous attempt.'} Candidate decisions: ${report.candidate_attempts.map(c=>`${c.id}: ${c.status} (${c.reason??'reason not recorded'})`).join('; ')}. Harness repairs used: ${read(join(job,'repair-summary.json'))?.repairs_used??'not recorded'}. Acceptance is within the recorded tested scope; this recording does not establish repeatability.`;
const manifest={schema:'reforge.run-bundle',schema_version:2,provenance:{kind:'recorded',source:basename(root),exporter:'export-feature-run.mjs',note:notes,execution_mode:prov.mode,clean_start_autonomous_demonstration:prov.clean_start_autonomous_demonstration},run:{id:state.id,operation,target:experiments[0]?.target,config:pick(read(join(root,'config.json')),['run_seconds','reserve_seconds','candidates','fresh_experiments']),scope:[outcome.scope,report.scope],status:outcome.status,stop_reason:report.stop_reason,elapsed_seconds:state.elapsed_seconds,summary_elapsed_seconds:state.elapsed_seconds,first_acceptance:report.first_acceptance.candidate_id,final_build_status:report.final_build.status,final_baseline_pass:report.final_baseline_pass},events,suite,experiments,contract:clean(read(join(root,'contract.json'))),candidates,baselines,telemetry,recording:{final:{available_at:finalAt,summary:clean(finalSummary),suite:finalCases,cases:finalResults},evidence,discovery:clean(read(join(job,'discovery-summary.json'))),validation:clean(read(join(job,'validation.json'))),repair:clean(read(join(job,'repair-summary.json'))),usage_totals:clean(outcome.usage),missing_evidence:['No browser video/screencast recording was archived.','Screenshot capture times are not uniformly recorded; section completion is used as a conservative reveal boundary.']},artifacts:[...assets.values()].map(({data,...a})=>a)};
const output=resolve(args.out);
if([repo,root,job].some(r=>inside(r,output)))throw Error('Refusing to overwrite a source archive');
const manifestText=JSON.stringify(manifest);
const portable={schema:'reforge.portable-recording',schema_version:1,manifest:manifestText,manifest_sha256:hash(Buffer.from(manifestText)),assets:[...assets.values()]};
mkdirSync(resolve(args.out,'..'),{recursive:true});writeFileSync(args.out,JSON.stringify(portable));
console.log(JSON.stringify({job:state.id,operation,events:events.length,candidates:candidates.length,assets:assets.size,bytes:Buffer.byteLength(JSON.stringify(portable)),final_metrics:finalSummary.cases.map(c=>c.metrics)}));
