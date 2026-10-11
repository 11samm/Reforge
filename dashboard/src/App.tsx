import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { RunIndexEntry } from './data/bundle.ts';
import { normalizeRun, snapshotAt, type Run } from './data/normalize.ts';
import { clock } from './format.ts';
import { Icon } from './ui.tsx';
import { Overview } from './views/Overview.tsx';
import { Experiments } from './views/Experiments.tsx';
import { Contract } from './views/Contract.tsx';
import { Candidates } from './views/Candidates.tsx';
import { Telemetry } from './views/Telemetry.tsx';
import { EventLog } from './views/EventLog.tsx';

export type View = 'overview' | 'experiments' | 'contract' | 'candidates' | 'telemetry' | 'events';

const NAV: { id: View; label: string; icon: string }[] = [
  { id: 'overview', label: 'Overview', icon: 'overview' },
  { id: 'experiments', label: 'Experiments', icon: 'experiments' },
  { id: 'contract', label: 'Contract', icon: 'contract' },
  { id: 'candidates', label: 'Candidates', icon: 'candidates' },
  { id: 'telemetry', label: 'Model usage', icon: 'telemetry' },
  { id: 'events', label: 'Event log', icon: 'events' },
];

const TITLES: Record<View, [string, string]> = {
  overview: ['Run overview', 'Observe → experiment → contract → implement → evaluate → accept / reject'],
  experiments: ['Experiments', 'Diagnostic inputs run through the real reference editor, with exact Percentage values'],
  contract: ['Behavior contract', 'Bounded claims, their status, supporting evidence and open questions'],
  candidates: ['Candidates', 'Builder attempts, trusted gates, per-case comparisons and decisions'],
  telemetry: ['Model usage', 'Recorded token telemetry per model invocation; missing records are marked'],
  events: ['Event log', 'Every recorded event in sequence; click a row to jump the replay'],
};

const SPEEDS = [1, 5, 20, 60];

export interface Selection { experiment: string | null; candidate: string | null; caseId: string | null }

export function App() {
  const [index, setIndex] = useState<RunIndexEntry[] | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<View>('overview');
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(20);
  const [sel, setSel] = useState<Selection>({ experiment: null, candidate: null, caseId: null });

  useEffect(() => {
    fetch('runs/index.json').then((r) => (r.ok ? r.json() : Promise.reject(new Error(`index.json: HTTP ${r.status}`))))
      .then((list: RunIndexEntry[]) => {
        setIndex(list);
        const wanted = new URLSearchParams(location.search).get('run');
        setRunId(list.find((e) => e.id === wanted)?.id ?? list.find((e) => e.kind === 'recorded')?.id ?? list[0]?.id ?? null);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    const entry = index?.find((e) => e.id === runId);
    if (!entry) return;
    setRun(null); setError(null); setPlaying(false);
    const base = entry.manifest.replace(/[^/]*$/, '');
    fetch(entry.manifest).then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${entry.manifest}: HTTP ${r.status}`))))
      .then((raw: unknown) => {
        const n = normalizeRun(raw, base, entry.id);
        if (entry.kind === 'synthetic' && n.provenance !== 'synthetic') n.provenance = 'synthetic';
        setRun(n);
        setT(n.duration);
        const lastEvaluated = [...n.candidates].reverse().find((c) => c.evaluatedCount > 0) ?? n.candidates[0];
        setSel({ experiment: n.experiments[0]?.id ?? null, candidate: lastEvaluated?.id ?? null, caseId: null });
      })
      .catch((e: Error) => setError(e.message));
  }, [index, runId]);

  useEffect(() => {
    if (!playing || !run) return;
    const id = window.setInterval(() => {
      setT((prev) => {
        const next = prev + 0.1 * speed;
        if (next >= run.duration) { setPlaying(false); return run.duration; }
        return next;
      });
    }, 100);
    return () => window.clearInterval(id);
  }, [playing, speed, run]);

  const snap = useMemo(() => (run ? snapshotAt(run, t) : null), [run, t]);
  const contentRef = useRef<HTMLDivElement>(null);
  useEffect(() => { contentRef.current?.scrollTo({ top: 0 }); }, [view, runId]);

  const openEvidence = useCallback((id: string) => {
    if (!run) return;
    if (run.experiments.some((e) => e.id === id)) {
      setSel((s) => ({ ...s, experiment: id }));
      setView('experiments');
      return;
    }
    if (run.suite.cases.some((c) => c.id === id)) {
      const cand = [...run.candidates].reverse().find((c) => c.evaluatedAt !== null && c.evaluatedAt <= t) ?? run.candidates[0];
      setSel((s) => ({ ...s, candidate: cand?.id ?? s.candidate, caseId: id }));
      setView('candidates');
    }
  }, [run, t]);

  const playToggle = () => {
    if (!run) return;
    if (!playing && t >= run.duration) setT(0);
    setPlaying((p) => !p);
  };

  const kind = run?.provenance ?? 'unknown';
  const atEnd = run ? t >= run.duration : true;

  return (
    <div className="backdrop">
      <div className="orb orb-a" /><div className="orb orb-b" /><div className="orb orb-c" />
      <div className="window glass-strong">
        <aside className="sidebar">
          <div className="brand">
            <span className="brand-mark">R</span>
            <div><strong>Reforge</strong><small>Run evidence</small></div>
          </div>
          <nav>
            {NAV.map((n) => (
              <button key={n.id} type="button" className={`nav-item ${view === n.id ? 'active' : ''}`} onClick={() => setView(n.id)}>
                <Icon name={n.icon} /> <span>{n.label}</span>
              </button>
            ))}
          </nav>
          <label className="run-picker">
            <span>Run bundle</span>
            <select value={runId ?? ''} onChange={(e) => setRunId(e.target.value)}>
              {index?.map((e) => <option key={e.id} value={e.id}>{e.kind === 'synthetic' ? '⚠ ' : ''}{e.title}</option>)}
            </select>
          </label>
          <div className="sidebar-spacer" />
          <div className={`identity identity-${kind}`}>
            <span className="identity-badge">{kind === 'synthetic' ? 'SYN' : kind === 'live' ? 'LIVE' : 'REC'}</span>
            <div>
              <strong title={run?.id}>{run?.id ?? 'No run loaded'}</strong>
              <small>{kind === 'recorded' ? 'Recorded playback' : kind === 'synthetic' ? 'Synthetic fixture' : kind === 'live' ? 'Live' : 'Unlabeled source'}</small>
            </div>
          </div>
        </aside>

        <main className="main">
          <header className="page-head">
            <div>
              <h1>{TITLES[view][0]}</h1>
              <p className="subtitle">{TITLES[view][1]}</p>
            </div>
            <span className={`mode-badge mode-${kind}`}>
              <span className="dot" />{kind === 'recorded' ? 'RECORDED PLAYBACK' : kind === 'synthetic' ? 'SYNTHETIC — NOT RESULTS' : kind === 'live' ? 'LIVE' : 'UNLABELED SOURCE'}
            </span>
          </header>

          {run && <ProvenanceBanner run={run} />}

          {run && snap && (
            <div className="replay glass">
              <div className="replay-buttons">
                <button type="button" className="icon-btn" onClick={() => { setT(0); setPlaying(false); }} title="Restart replay"><Icon name="restart" /></button>
                <button type="button" className="play-btn" onClick={playToggle} title={playing ? 'Pause' : 'Play replay'}>
                  <Icon name={playing ? 'pause' : 'play'} /> {playing ? 'Pause' : atEnd ? 'Replay run' : 'Play'}
                </button>
                <button type="button" className="icon-btn" onClick={() => { setT(run.duration); setPlaying(false); }} title="Jump to end"><Icon name="end" /></button>
                <select className="speed" value={speed} onChange={(e) => setSpeed(Number(e.target.value))} aria-label="Replay speed">
                  {SPEEDS.map((s) => <option key={s} value={s}>{s}× speed</option>)}
                </select>
              </div>
              <div className="scrub">
                <input type="range" min={0} max={run.duration} step={0.1} value={t} aria-label="Replay position"
                  onChange={(e) => { setT(Number(e.target.value)); setPlaying(false); }} />
                <div className="ticks" aria-hidden="true">
                  {run.timeline.map((e) => (
                    <span key={e.seq} className={`tick tick-${e.tone}`} style={{ left: `${(e.t / Math.max(run.duration, 1)) * 100}%` }} />
                  ))}
                </div>
              </div>
              <div className="replay-time">
                <strong>{clock(t)}</strong><span> / {clock(run.duration)}</span>
                <small>{snap.eventCount}/{run.timeline.length} events</small>
              </div>
            </div>
          )}

          <div className="content" ref={contentRef}>
            {error && <div className="load-error glass"><Icon name="alert" /> Could not load run data: {error}</div>}
            {!run && !error && <div className="loading">Loading run bundle…</div>}
            {run && snap && view === 'overview' && <Overview run={run} snap={snap} t={t} onOpenCandidate={(id) => { setSel((s) => ({ ...s, candidate: id, caseId: null })); setView('candidates'); }} onOpenEvidence={openEvidence} />}
            {run && view === 'experiments' && <Experiments run={run} t={t} selected={sel.experiment} onSelect={(id) => setSel((s) => ({ ...s, experiment: id }))} onOpenEvidence={openEvidence} />}
            {run && view === 'contract' && <Contract run={run} t={t} onOpenEvidence={openEvidence} />}
            {run && view === 'candidates' && <Candidates run={run} t={t} sel={sel} setSel={setSel} onOpenEvidence={openEvidence} />}
            {run && view === 'telemetry' && <Telemetry run={run} t={t} />}
            {run && view === 'events' && <EventLog run={run} t={t} onSeek={(x) => { setT(x); setPlaying(false); }} />}
          </div>
        </main>
      </div>
    </div>
  );
}

function ProvenanceBanner({ run }: { run: Run }) {
  if (run.provenance === 'synthetic') {
    return (
      <div className="banner banner-synthetic">
        <Icon name="alert" />
        <div><strong>Synthetic fixture: invented values for rendering tests</strong>
          <p>Nothing on this screen is a Reforge result. {run.provenanceNote}</p></div>
      </div>
    );
  }
  if (run.provenance === 'recorded') {
    return (
      <div className="banner banner-recorded">
        <Icon name="info" />
        <div><strong>Recorded playback of a completed run. Not live.</strong>
          <p>Replaying {run.timeline.length} events recorded by the trusted host from <code>{run.provenanceSource ?? 'unknown source'}</code>.
            Values come from the recorded run, not from the dashboard.</p></div>
      </div>
    );
  }
  return (
    <div className="banner banner-synthetic">
      <Icon name="alert" />
      <div><strong>Unlabeled data source</strong><p>This bundle does not declare whether it is recorded or synthetic. Do not treat it as project results.</p></div>
    </div>
  );
}
