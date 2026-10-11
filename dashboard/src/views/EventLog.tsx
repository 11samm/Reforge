import type { Run } from '../data/normalize.ts';
import { clock, PHASE_LABEL } from '../format.ts';
import { Card, Empty } from '../ui.tsx';

export function EventLog({ run, t, onSeek }: { run: Run; t: number; onSeek: (t: number) => void }) {
  return (
    <div className="eventlog">
      {run.warnings.length > 0 && (
        <Card title="Normalization warnings">
          <ul className="bullets">{run.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </Card>
      )}
      <Card title={`${run.timeline.length} recorded events`} aside={<small className="muted">schema v{run.schemaVersion ?? '0 (legacy)'} · exported {run.exportedAt ? new Date(run.exportedAt).toLocaleString() : 'unknown'}</small>}>
        {run.timeline.length === 0 ? <Empty>No events recorded.</Empty> : (
          <ol className="events">
            {run.timeline.map((e) => (
              <li key={e.seq} className={`event tone-${e.t <= t ? e.tone : 'neutral'} ${e.t <= t ? 'past' : 'future'}`}>
                <button type="button" onClick={() => onSeek(e.t)} title="Jump replay here">
                  <span className="event-t mono">{clock(e.t)}</span>
                  <span className="event-phase">{e.t <= t && e.phase ? PHASE_LABEL[e.phase] : '—'}</span>
                  <span className="event-body"><strong>{e.t <= t ? e.title : `Recorded event ${e.seq} · not available yet`}</strong>{e.t <= t && e.detail && <small>{e.detail}</small>}</span>
                  <span className="event-budget mono">{e.t <= t && e.budget.remainingSeconds !== null ? `${e.budget.remainingSeconds.toFixed(0)} s left` : ''}</span>
                </button>
              </li>
            ))}
          </ol>
        )}
      </Card>
    </div>
  );
}
