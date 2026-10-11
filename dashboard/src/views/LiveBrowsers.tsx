import { useEffect, useState } from 'react';
import { parseSessions, type LiveSessions, type BrowserSession } from '../data/sessions.ts';
import { Pill } from '../ui.tsx';
import { clock } from '../format.ts';

function BrowserView({ title, session }: { title: string; session?: BrowserSession }) {
  const state = session?.state ?? 'unavailable';
  return <article className="live-browser">
    <div className="live-browser-heading"><strong>{title}</strong><Pill tone={state === 'ready' ? 'good' : 'warn'}>{state}</Pill></div>
    <div className="live-browser-viewport">
      {state === 'ready' && session?.frame ? <img alt={`${title} — live harness viewport`} src={`data:image/jpeg;base64,${session.frame}`} /> :
        <p>{state === 'building' ? 'Building and checking candidate…' : state === 'launching' ? 'Launching owned browser…' : state === 'hidden' ? 'Held-out evaluation is hidden' : state === 'disconnected' ? 'Session closed or disconnected' : 'No browser session available'}</p>}
    </div>
    <div className="live-browser-action"><strong>{session?.action ?? 'Waiting for browser execution'}</strong><span>{session?.purpose ?? 'The harness opens sessions when this job needs them.'}</span>
      {session?.parameters && Object.keys(session.parameters).length > 0 && <code>{JSON.stringify(session.parameters)}</code>}
      {state === 'ready' && session?.action_elapsed_seconds !== undefined && <small>Action elapsed (backend): {clock(session.action_elapsed_seconds)}</small>}
      {state === 'ready' && session?.captured_at && <small>Last frame {new Date(session.captured_at * 1000).toLocaleTimeString()} · fixed 1440 × 1000 viewport</small>}
    </div>
  </article>;
}

export function LiveBrowsers({ jobId, status, connected }: { jobId?: string; status?: string; connected: boolean }) {
  const [data, setData] = useState<LiveSessions | null>(null);
  const [feedConnected, setFeedConnected] = useState(false);
  const active = status === 'running' || status === 'queued';
  useEffect(() => {
    setData(null); setFeedConnected(false);
    if (!jobId || !connected || !active) return;
    let closed = false, pending = false;
    const controller = new AbortController();
    const refresh = async () => {
      if (pending) return;
      pending = true;
      try {
        const response = await fetch(`/api/jobs/${jobId}/live`, { signal: controller.signal, cache: 'no-store' });
        if (!response.ok) throw new Error('Live feed unavailable');
        const next = parseSessions(await response.json(), jobId);
        if (!closed) { setData(next); setFeedConnected(true); }
      } catch { if (!closed) { setData(null); setFeedConnected(false); } }
      finally { pending = false; }
    };
    void refresh(); const timer = setInterval(() => { void refresh(); }, 300);
    return () => { closed = true; controller.abort(); clearInterval(timer); };
  }, [jobId, connected, active]);
  // Guard at render too: effects run after paint on a job switch/cancellation.
  const current = connected && active && data?.job_id === jobId ? data : null;
  const fallback: BrowserSession = { state: jobId && (!connected || !active || !feedConnected) ? 'disconnected' : 'unavailable', frame: null };
  return <section className="glass card live-execution" aria-label="Live harness browsers">
    <div className="card-head"><h3>Live execution</h3><Pill tone={current && feedConnected ? 'good' : 'warn'}>{current && feedConnected ? 'Harness feed connected' : 'No live feed'}</Pill></div>
    <p className="small muted">Both actual browser sessions stay open during visible testing. Actions run separately; idle browsers wait for their next test. Final evaluation is hidden.</p>
    <div className="live-browser-pair"><BrowserView title="miniPaint reference" session={current?.sessions.reference ?? fallback} /><BrowserView title="Candidate editor" session={current?.sessions.candidate ?? fallback} /></div>
    <div className="live-activity" role="status"><div><span>Stage</span><strong>{current?.stage ?? 'No active execution'}</strong></div><div><span>Job elapsed (backend)</span><strong>{clock(current?.elapsed_seconds ?? 0)}</strong></div><div><span>Current activity</span><strong>{current?.activity ?? 'Waiting for backend events'}</strong></div>
      {current?.experiment && <div className="live-experiment"><span>Latest experiment purpose</span><strong>{current.experiment.question}</strong><p>{current.experiment.usefulness}</p><code>{JSON.stringify({ input: current.experiment.input, value: current.experiment.value })}</code></div>}
    </div>
  </section>;
}
