import {useState} from 'react';
import {CasePanel} from './Candidates.tsx';
import {Card,PixelImage} from '../ui.tsx';
import {type Run} from '../data/normalize.ts';
export function RecordedEvidence({run,t}:{run:Run;t:number}){
 const [caseId,setCaseId]=useState<string|null>(null);
 const r=run.recording;if(!r)return null;
 const f=r.final;const ready=t>=f.available_at;
 const final=r.finalRun;
 // Imported final assets are resolved separately; no backend or original archive paths.
 return <><Card title="Recorded provenance">{t>=run.duration?<p>{run.provenanceNote}</p>:<p>Source: {run.provenanceSource}. Recording outcomes become available as playback advances.</p>}{r.missing_evidence.map(x=><p key={x}>{x}</p>)}</Card>
 <Card title="Once-only final evaluation"><p>Completed recording evidence only. Never a model or repair input.</p>{ready&&final?<CasePanel run={final} cases={final.candidates[0].cases} evaluated decided candidateFailed={false} errorText={null} selectedCase={caseId} onSelectCase={setCaseId} onOpenEvidence={()=>{}} policy={run.suite.policy}/>:<p>Not available at this recorded time.</p>}</Card>
 <Card title="Recorded screenshots"><p>Archived browser images; these are recorded evidence.</p>{r.evidence.filter(e=>e.available_at<=t).map(e=><figure key={e.path}><figcaption>{e.label}</figcaption><PixelImage src={e.path} alt={e.label} missing="Not recorded" maxWidth={480}/></figure>)}</Card></>;
}
