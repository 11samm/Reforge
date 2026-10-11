import { useEffect, useState } from 'react';
import { normalizeJob, STAGES, type Job } from '../data/jobs.ts';

async function api(path = '', body?: unknown) {
  const r = await fetch('/api/jobs' + path, body === undefined ? undefined : {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Reforge-Request': '1' }, body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.error ?? `HTTP ${r.status}`);
  return data;
}

export function ImplementFeature() {
  const [request, setRequest] = useState('Implement Contrast');
  const [job, setJob] = useState<Job | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState('');
  const [connectionError, setConnectionError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let closed = false;
    const refresh = async () => {
      try {
        const data = await api();
        if (closed) return;
        setConnected(true); setEnabled(data.pilot_enabled === true); setConnectionError('');
        if (data.jobs?.[0]) setJob(normalizeJob(data.jobs[0]));
      } catch (e) { if (!closed) { setConnected(false); setConnectionError((e as Error).message); } }
    };
    void refresh(); const timer = setInterval(() => { void refresh(); }, 1000);
    return () => { closed = true; clearInterval(timer); };
  }, []);
  const running = job && !['accepted', 'unresolved', 'failed', 'cancelled'].includes(job.status);
  const action = async (cancel = false) => {
    setBusy(true); setError('');
    try { setJob(normalizeJob(await api(cancel ? `/${job!.id}/cancel` : '', cancel ? {} : { request }))); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };
  const total = job?.usage?.reduce((n,u) => n + (u.total?.totalTokens ?? (u.total?.inputTokens ?? 0) + (u.total?.outputTokens ?? 0)), 0);
  return <section className="glass feature-job">
    <p><strong>{connected ? 'LOCAL JOB SERVICE CONNECTED' : 'LOCAL JOB SERVICE OFFLINE'}</strong> · Live jobs are separate from recorded playback.</p>
    <p>Supported: Implement Contrast, miniPaint, one imported 8-bit raster layer, numeric adjustment controls. Other requests receive an explanation.</p>
    <label className="feature-request">Feature request <input aria-label="Feature request" value={request} onChange={e => setRequest(e.target.value)} maxLength={100} /></label>
    <p>Review budget: 600 seconds total; discovery 90 seconds / 20 actions / 24 observations; 2 procedure replays plus default check; 4 investigation experiments; 2 candidates; 12 builder calls each; 2 final cases; no reference retries.</p>
    <p>Uses the existing signed-in model provider. Actual token usage is recorded; elapsed time and tool limits bound execution. Candidates stay isolated pending separate promotion.</p>
    <button className="play-btn" type="button" onClick={() => { void action(); }} disabled={!connected || !enabled || !!running || busy}>Run</button>
    {!enabled && <p>Pilot execution is disabled by the local service configuration.</p>}
    {(error || connectionError) && <p role="alert">{error || connectionError}</p>}
    {job && <>
      <h2>{job.request}</h2><p><strong>{job.status}</strong> · {job.activity}</p>
      <ol className="feature-stages">{STAGES.map(s => <li key={s} aria-current={s === job.stage ? 'step' : undefined}><strong>{s === job.stage ? '→ ' : ''}{s}</strong></li>)}</ol>
      <p>Elapsed: {job.elapsed_seconds.toFixed(1)} seconds · Tokens: {total === undefined ? 'Not reported yet' : total.toLocaleString()}</p>
      {running && <button className="play-btn" type="button" disabled={busy || job.status === 'cancelling'} onClick={() => { void action(true); }}>Cancel job</button>}
      <p>Accepted means independently verified within the recorded tested scope. Unresolved, failed and cancelled jobs do not establish a working feature.</p>
      <h3>Available evidence</h3>
      <ul>{job.evidence.map(e => <li key={e.url}><a href={e.url} target="_blank" rel="noreferrer">{e.name}</a> · available at {e.available_at.toFixed(1)}s</li>)}</ul>
      <details><summary>Persisted event log</summary><ul>{job.events.map(e => <li key={e.sequence}>{e.elapsed_seconds}s · {e.event} · {String(e.activity ?? e.stage ?? '')}</li>)}</ul></details>
    </>}
  </section>;
}
