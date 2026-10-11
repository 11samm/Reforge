import { useEffect, useState } from 'react';
import { CandidatePreview } from './CandidatePreview.tsx';

type Artifact = { label: string; status: string; url?: string; reason?: string };
type Row = { case_id?: string; status?: string; classification?: string; reasons?: string[]; metrics?: unknown; artifacts?: Artifact[] };
type Results = { job_id: string; experiments: { id: string; plan: unknown; artifacts: Artifact[] }[]; candidates: { id: string; result: Record<string, unknown>; cases: Row[]; logs: Record<string, string>; baseline?: unknown; brightness_regression?: unknown }[]; report?: unknown; final?: unknown; events?: unknown[] };
const recorded = (value: unknown) => JSON.stringify(value, null, 2) ?? 'Not recorded';
function EvidenceImage({ url, label }: { url: string; label: string }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [url]);
  return failed ? <p role="status">Recorded artifact could not be loaded.</p> : <a href={url} target="_blank" rel="noreferrer"><img src={url} alt={label} loading="lazy" onError={() => setFailed(true)} /></a>;
}
function Artifacts({ items, id }: { items: Artifact[]; id: string }) {
  return <div className="evidence-images">{items.map((a, i) => {
    const available = a.status === 'available' && new RegExp(`^/api/jobs/${id}/artifacts/[a-f0-9]{64}\\.png$`).test(a.url ?? '');
    return <figure key={i}><figcaption>{a.label}</figcaption>{available ? <EvidenceImage url={a.url!} label={a.label} /> : <p className="small muted">{a.reason || 'Not yet produced or not recorded'}</p>}</figure>;
  })}</div>;
}
export function LiveEvidence({ id, status, connected }: { id: string; status: string; connected: boolean }) {
  const [data, setData] = useState<Results | null>(null), [error, setError] = useState('');
  const [preview, setPreview] = useState<{ url?: string; reason?: string } | null>(null);
  useEffect(() => {
    setData(null); setPreview(null); setError('');
    if (!connected) return;
    const controller = new AbortController(); let pending = false;
    const refresh = async () => {
      if (pending) return; pending = true;
      try {
        const response = await fetch(`/api/jobs/${id}/results`, { signal: controller.signal });
        if (!response.ok) throw new Error('Recorded evidence feed unavailable');
        const next = await response.json() as Results;
        if (next.job_id !== id || !Array.isArray(next.experiments) || !Array.isArray(next.candidates)) throw new Error('Incorrect evidence job');
        if (!controller.signal.aborted) { setData(next); setError(''); }
      } catch (e) { if (!controller.signal.aborted) { setData(null); setError((e as Error).message); } }
      finally { pending = false; }
    };
    void refresh(); const timer = setInterval(() => void refresh(), 1000);
    return () => { controller.abort(); clearInterval(timer); };
  }, [id, connected, status]);
  const review = async () => {
    try {
      const response = await fetch(`/api/jobs/${id}/preview`); const next = await response.json();
      if (!response.ok || next.job_id !== id) throw new Error(next.error || 'Candidate preview unavailable');
      if (next.url && next.url !== `/api/jobs/${id}/preview/index.html`) throw new Error('Incorrect preview job');
      setPreview(next);
    } catch (e) { setPreview({ reason: (e as Error).message }); }
  };
  return <section className="feature-evidence"><h3>Experiment and candidate results</h3><p className="small muted">Recorded backend evidence. Image differences are amplified ×16 for display; scoring uses raw RGBA.</p>
    {error && <p role="alert">{error}</p>}
    {!data?.experiments.length && <p>Experiment inputs and reference outputs: not yet produced or not recorded.</p>}
    {data?.experiments.map(e => <details key={e.id} open><summary>Experiment {e.id}</summary><pre>{recorded(e.plan)}</pre><Artifacts id={id} items={e.artifacts} />{!data.candidates.length ? <p>Candidate output, difference images and metrics: not yet produced.</p> : <ul>{data.candidates.map(c => <li key={c.id}>{c.cases.some(row => row.case_id === e.id) ? <a href={`#live-case-${id}-${c.id}-${e.id}`}>{c.id}: candidate output, differences and recorded metrics</a> : <span>{c.id}: candidate output, differences and metrics not produced or not recorded for this experiment</span>}</li>)}</ul>}</details>)}
    {!data?.candidates.length && <p>Build, UI/batch, regression and acceptance results: not yet produced or not recorded.</p>}
    {data?.candidates.map(c => <details key={c.id} open><summary>Candidate {c.id}</summary><div className="feature-metrics">{['build_valid', 'independent', 'ui_valid', 'baseline_pass'].map(k => <div key={k}><span>{({ build_valid: 'Build', independent: 'Independent batch', ui_valid: 'UI/batch agreement', baseline_pass: 'Regressions' } as Record<string, string>)[k]}</span><strong>{c.result[k] === true ? 'Passed' : c.result[k] === false ? 'Failed' : 'Not recorded'}</strong></div>)}</div><pre>{recorded(c.result)}</pre><details><summary>Build and batch logs</summary>{Object.entries(c.logs).map(([name, log]) => <div key={name}><h4>{name}</h4><pre>{log || 'Recorded empty log'}</pre></div>)}</details><details><summary>Original editor regression results</summary><pre>{recorded(c.baseline)}</pre></details>{!!c.brightness_regression && <details><summary>Established Brightness regression</summary><pre>{recorded(c.brightness_regression)}</pre></details>}
      {c.cases.map((row, i) => <div key={row.case_id ?? i} id={`live-case-${id}-${c.id}-${row.case_id}`}><h4>{row.case_id}: {row.status} · {row.classification}</h4>{row.reasons?.map((reason, j) => <p key={j}>{reason}</p>)}<pre>{row.metrics == null ? 'Metrics not produced or not recorded' : recorded(row.metrics)}</pre><Artifacts id={id} items={row.artifacts ?? []} /></div>)}
    </details>)}
    <details><summary>Recorded rejection, repair and acceptance history</summary><pre>{recorded(data?.events)}</pre></details>
    <details><summary>Acceptance and final evaluation</summary><pre>{recorded(data?.report)}</pre><pre>{recorded(data?.final)}</pre></details>
    {status === 'accepted' && <div><button type="button" className="play-btn" onClick={() => void review()}>Review accepted candidate</button><p>Interactive exploration: upload a new image using the editor’s Open image control and try Brightness. These uploads are not scored acceptance evidence. Candidate code remains isolated; no automatic promotion or merge.</p>{preview?.reason && <p role="status">{preview.reason}</p>}{preview?.url && <CandidatePreview title="Accepted isolated candidate — interactive exploration" url={preview.url} />}</div>}
  </section>;
}
