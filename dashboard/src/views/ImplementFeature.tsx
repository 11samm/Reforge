import { useEffect, useState } from 'react';
import { normalizeJob, STAGES, type Job } from '../data/jobs.ts';
import { Icon, Pill } from '../ui.tsx';
import { clock } from '../format.ts';
import { LiveBrowsers } from './LiveBrowsers.tsx';
import { LiveEvidence } from './LiveEvidence.tsx';
import { CandidatePreview } from './CandidatePreview.tsx';
type Demo = { id: string; request: string; preview_url?: string; preview_status: string; preview_error?: string; preparation: { target_absent: boolean; model_invoked: boolean; memory: Record<string, unknown> } };

async function api(path = '', body?: unknown, signal?: AbortSignal) {
  const r = await fetch('/api/jobs' + path, body === undefined ? { signal } : {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Reforge-Request': '1' }, body: JSON.stringify(body), signal,
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.error ?? `HTTP ${r.status}`);
  return data;
}
const DONE = ['accepted', 'unresolved', 'failed', 'cancelled'];
const STAGE_COPY = ['Locate the control', 'Confirm repeatable exports', 'Collect pixel evidence', 'Build the implementation', 'Compare independently'];

export function ImplementFeature({ onReplaySavedRun }: { onReplaySavedRun?: () => void } = {}) {
  const [request, setRequest] = useState('Implement Brightness');
  const [demos, setDemos] = useState<Demo[]>([]), [demoId, setDemoId] = useState('');
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selected, setSelected] = useState('');
  const [enabled, setEnabled] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState('');
  const [connectionError, setConnectionError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let closed = false, refreshing = false;
    const controller = new AbortController();
    const refresh = async () => {
      if (refreshing) return;
      refreshing = true;
      try {
        const data = await api('', undefined, controller.signal);
        if (closed) return;
        setJobs(Array.isArray(data.jobs) ? data.jobs.map(normalizeJob) : []);
        setDemos(Array.isArray(data.prepared_demos) ? data.prepared_demos : []);
        setConnected(true); setEnabled(data.pilot_enabled === true); setConnectionError('');
      } catch (e) { if (!closed) { setConnected(false); setConnectionError((e as Error).message); } }
      finally { refreshing = false; }
    };
    void refresh(); const timer = setInterval(() => { void refresh(); }, 1000);
    return () => { closed = true; clearInterval(timer); controller.abort(); };
  }, []);
  const job = jobs.find(j => j.id === selected) ?? jobs[0] ?? null;
  const running = !!job && !DONE.includes(job.status);
  const anyRunning = jobs.some(j => !DONE.includes(j.status));
  const demo = demos.find(d => d.id === demoId);
  const selectedDemoUsed = jobs.some(j => j.id === demoId);
  const prepare = async () => {
    setBusy(true); setError('');
    try {
      const next = await api('/prepare', { request }) as Demo;
      setDemos(old => [next, ...old.filter(d => d.id !== next.id)]); setDemoId(next.id);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };
  const action = async (cancel = false) => {
    setBusy(true); setError('');
    try {
      const next = normalizeJob(await api(cancel ? `/${job!.id}/cancel` : '', cancel ? {} : { request, prepared_demo_id: demoId }));
      setJobs(old => [next, ...old.filter(j => j.id !== next.id)]); setSelected(next.id);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };
  const total = job?.usage?.reduce((n,u) => n + (u.total?.totalTokens ?? (u.total?.inputTokens ?? 0) + (u.total?.outputTokens ?? 0)), 0);
  const current = job ? STAGES.indexOf(job.stage as typeof STAGES[number]) : -1;
  const tone = job?.status === 'accepted' ? 'good' : job?.status === 'failed' ? 'bad' : job && DONE.includes(job.status) ? 'warn' : 'info';
  return <div className="feature-workspace">
    <section className="feature-hero glass">
      <div className="feature-hero-copy"><span className="feature-overline">From observation to implementation</span><h2>Discover. Rebuild. Verify.</h2><p>Ask Reforge to investigate a feature in miniPaint and build an independently tested implementation.</p></div>
      <span className="feature-orb" aria-hidden="true"><Icon name="experiments" size={42} /></span>
    </section>
    {job?.presentation_label && <p className="glass card small muted">{job.presentation_label}</p>}
    <LiveBrowsers key={job?.id ?? 'empty'} jobId={job?.id} status={job?.status} connected={connected} />
    <section className="glass card feature-compose">
      <div className="card-head"><h3>Prepare and learn</h3><Pill tone={connected ? 'good' : 'warn'}>{connected ? 'Service connected' : 'Service offline'}</Pill></div>
      <p className="small muted">Supported: Brightness and Contrast in miniPaint, on one imported 8-bit raster layer.</p>
      <form className="feature-form" onSubmit={e => { e.preventDefault(); if (connected && enabled && !anyRunning && !busy && demo && demo.request === request && !selectedDemoUsed) void action(); }}>
        <label className="feature-request">Feature request<select aria-label="Feature request" value={request} onChange={e => { setRequest(e.target.value); setDemoId(''); }}><option>Implement Brightness</option><option>Implement Contrast</option></select></label>
        <button className="play-btn" type="button" disabled={!connected || anyRunning || busy} onClick={() => void prepare()}>Prepare fresh {request.replace('Implement ', '')} demo</button>
        <button className="play-btn" type="submit" disabled={!connected || !enabled || anyRunning || busy || !demo || demo.request !== request || selectedDemoUsed}><Icon name="play" />{busy ? 'Working…' : `Learn ${request.replace('Implement ', '')}`}</button>
      </form>
      <button type="button" className="feature-cancel" onClick={onReplaySavedRun} disabled={!onReplaySavedRun}>Replay saved run</button>
      {demos.length > 0 && <label className="feature-history">Prepared demo<select aria-label="Prepared demo" value={demoId} onChange={e => setDemoId(e.target.value)}><option value="">Select a prepared editor</option>{demos.filter(d => d.request === request).map(d => <option value={d.id} key={d.id}>{d.request} · {d.id.slice(0, 8)} · {d.preview_status}</option>)}</select></label>}
      {demo && <div><h3>Prepared starting editor · {demo.id.slice(0, 8)}</h3><p>{demo.preparation.target_absent ? `${request.replace('Implement ', '')} is absent. This isolated editor contains the upload/export shell and codec; no model was invoked by preparation.` : 'Starting state does not establish target absence.'} {request === 'Implement Brightness' ? 'Prior Brightness code, contracts, experiments and procedures are excluded; shared import/export procedures, general guidance and model pretraining remain.' : 'Established Brightness remains as a regression baseline.'}</p><details><summary>Actual starting-state memory policy</summary><pre>{JSON.stringify(demo.preparation.memory, null, 2)}</pre></details>{selectedDemoUsed && <p>This demo is tied to run {demo.id}; prepare a new editor for another fresh run.</p>}{demo.preview_error && <p role="alert">Preview build failed: {demo.preview_error}</p>}{demo.preview_url === `/api/jobs/demos/${demo.id}/preview/index.html` && <CandidatePreview title="Prepared editor — target operation absent" url={demo.preview_url} />}</div>}
      <div className="feature-service-note"><Icon name="info" /><p>{!connected ? 'Start the local feature service to view jobs.' : !enabled ? 'Pilot execution is disabled by the local service configuration.' : anyRunning ? 'A job is already active. You can follow or cancel it below.' : 'Uses your signed-in model provider. Candidates stay isolated until separately promoted.'}</p></div>
      <details className="feature-budget"><summary>Execution limits and tested scope</summary><p>1200 seconds total; up to 5 harness repairs within 300 seconds; discovery: 90 seconds, 20 actions, 24 observations; default check and 2 procedure replays; 4 experiments; 2 candidates; 12 builder calls each; 2 final cases; no reference retries. Actual token usage is recorded.</p><p>Other features are not supported yet. Acceptance applies to recorded tested cases, with no automatic promotion or merge.</p></details>
      {(error || connectionError) && <div className="feature-alert" role="alert"><Icon name="alert" /><span>{error || connectionError}</span></div>}
    </section>
    <section className="glass card feature-job">
      <div className="card-head"><h3>Feature jobs</h3>{jobs.length > 0 && <label className="feature-history">Job history<select aria-label="Job history" value={job?.id ?? ''} onChange={e => setSelected(e.target.value)}>{jobs.map(j => <option key={j.id} value={j.id}>{j.request} · {j.status} · {j.id.slice(0,8)}</option>)}</select></label>}</div>
      {!job ? <div className="feature-empty"><Icon name="experiments" size={32} /><h3>No feature jobs yet</h3><p>New jobs will appear here with their progress and available evidence.</p></div> : <>
        <div className="feature-job-heading"><div><h2>{job.request}</h2><span className="mono muted">{job.id.slice(0,8)}</span></div><Pill tone={tone}>{job.status}</Pill></div>
        <p className="feature-activity" role="status">{job.activity || 'Waiting for the next job event'}</p>
        <ol className="feature-stages">{STAGES.map((s,i) => { const done = job.status === 'accepted' || i < current; return <li key={s} className={done ? 'stage-done' : s === job.stage ? 'stage-current' : ''} aria-current={s === job.stage && !DONE.includes(job.status) ? 'step' : undefined}><span className="feature-stage-number">{done ? <Icon name="check" size={14} /> : i + 1}</span><div><strong>{s}</strong><small>{STAGE_COPY[i]}</small></div></li>; })}</ol>
        <div className="feature-metrics"><div><span>Elapsed</span><strong>{clock(job.elapsed_seconds)}</strong></div><div><span>Recorded tokens</span><strong>{total === undefined ? 'Not reported yet' : total.toLocaleString()}</strong></div><div><span>Workspace</span><strong>Isolated candidate</strong></div>{running && <button className="feature-cancel" type="button" disabled={!connected || busy || job.status === 'cancelling'} onClick={() => { void action(true); }}>{job.status === 'cancelling' ? 'Cancelling…' : 'Cancel run'}</button>}</div>
        <LiveEvidence key={job.id} id={job.id} status={job.status} connected={connected} />
        {DONE.includes(job.status) && <p className={`feature-outcome outcome-${tone}`}><Icon name={job.status === 'accepted' ? 'check' : 'info'} />{job.status === 'accepted' ? 'Verified within the recorded tested scope. Candidate is ready for separate review and promotion.' : 'This job did not establish a verified feature. Inspect the evidence and event log for its outcome.'}</p>}
        <div className="feature-evidence"><h3>Available evidence</h3>{job.evidence.length ? <ul>{job.evidence.map(e => <li key={e.url}><a href={e.url} target="_blank" rel="noreferrer"><Icon name="contract" /><span>{e.name}</span><Icon name="link" size={14} /></a><small>Recorded at {clock(e.available_at)}</small></li>)}</ul> : <p className="small muted">Evidence appears as each stage records its results.</p>}</div>
        <details className="feature-log"><summary>Persisted event log <span className="muted">({job.events.length})</span></summary><ol>{job.events.map(e => <li key={e.sequence}><time className="mono">{clock(e.elapsed_seconds ?? 0)}</time><strong>{e.event}</strong><span>{String(e.activity ?? e.stage ?? '')}</span></li>)}</ol></details>
      </>}
    </section>
  </div>;
}
