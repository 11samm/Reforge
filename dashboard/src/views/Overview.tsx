import { PHASES, type Run, type Snapshot } from '../data/normalize.ts';
import { clock, humanize, PHASE_HINT, PHASE_LABEL, secs } from '../format.ts';
import { Card, DecisionPill, EvidenceChip, Gate, Icon, Pill } from '../ui.tsx';
import { candidateAt, decisionNote } from './shared.ts';

function GateChip({ label, title, value }: { label: string; title: string; value: boolean | null | 'pending' }) {
  const state = value === 'pending' ? 'pending' : value === true ? 'pass' : value === false ? 'fail' : 'none';
  const text = { pass: 'passed', fail: 'failed', none: 'not recorded', pending: 'pending' }[state];
  return <span className={`gate-chip gc-${state}`} title={`${title}: ${text}`}><Icon name={{ pass: 'check', fail: 'x', none: 'dash', pending: 'clock' }[state]} size={12} />{label}</span>;
}

const PHASE_ICON: Record<string, string> = {
  observe: 'search', experiment: 'experiments', contract: 'contract', implement: 'candidates', evaluate: 'telemetry', decide: 'check',
};

export function Overview({ run, snap, t, onOpenCandidate, onOpenEvidence }: {
  run: Run; snap: Snapshot; t: number; onOpenCandidate: (id: string) => void; onOpenEvidence: (id: string) => void;
}) {
  const runSeconds = run.budget.runSeconds;
  const deadline = runSeconds !== null && run.budget.reserveSeconds !== null ? runSeconds - run.budget.reserveSeconds : null;
  const used = runSeconds !== null && snap.remainingSeconds !== null ? runSeconds - snap.remainingSeconds : null;
  const visibleCandidates = run.candidates.filter((c) => c.revealedAt <= t);
  const runNotes = run.annotations.filter((a) => a.target === 'run');
  const ended = snap.stopped;
  const statusTone = ended ? (run.outcome.status === 'accepted' ? 'good' : 'bad') : 'info';

  return (
    <div className="overview">
      <div className="identity-strip glass">
        <div><small>Run</small><strong className="mono">{run.id}</strong></div>
        <div><small>Operation</small><strong>{run.operation}</strong></div>
        <div><small>Reference</small><strong>{run.target.name ?? 'Unknown'} {run.target.version ?? ''}</strong>{run.target.build && <em>build {run.target.build}</em>}</div>
        <div><small>Scope</small><strong>{run.suite.cases.length} visible cases · {String(run.suite.policy?.id ?? 'policy not recorded')}</strong><em>{run.scope[0] ?? 'Scope not recorded'}</em></div>
      </div>

      <Card className="pipeline-card">
        <ol className="pipeline">
          {PHASES.map((p, i) => {
            const state = snap.phase === p ? 'current' : snap.visited.has(p) ? 'done' : 'todo';
            return (
              <li key={p} className={`step step-${state}`}>
                <span className="step-icon"><Icon name={PHASE_ICON[p]} size={17} /></span>
                <span className="step-text"><small>Step {i + 1}</small><strong>{PHASE_LABEL[p]}</strong></span>
              </li>
            );
          })}
        </ol>
        <div className="phase-now">
          <Pill tone={snap.phase === 'stopped' ? 'bad' : 'info'}>Now: {PHASE_LABEL[snap.phase]}</Pill>
          <span>{PHASE_HINT[snap.phase]}</span>
        </div>
      </Card>

      <div className="stats">
        <Card className="stat">
          <small>Elapsed</small>
          <strong>{clock(snap.t)}</strong>
          <span>of {clock(run.duration)} recorded</span>
        </Card>
        <Card className="stat">
          <small>Remaining time budget</small>
          <strong>{snap.remainingSeconds === null ? 'Not recorded' : secs(snap.remainingSeconds)}</strong>
          {runSeconds !== null && used !== null ? (
            <div className="budget-bar" title={`Run budget ${runSeconds} s; learning deadline at ${deadline ?? '?'} s`}>
              <span className="budget-used" style={{ width: `${Math.min(100, (used / runSeconds) * 100)}%` }} />
              {deadline !== null && <span className="budget-deadline" style={{ left: `${(deadline / runSeconds) * 100}%` }} />}
            </div>
          ) : <span>Run budget not recorded</span>}
          {deadline !== null && <span>Deadline {deadline} s · {run.budget.reserveSeconds} s cleanup reserve</span>}
        </Card>
        <Card className="stat">
          <small>Candidate turns left</small>
          <strong>{snap.candidatesRemaining ?? '—'}<em> / {run.budget.candidates ?? '?'}</em></strong>
          <span>{visibleCandidates.length} started so far</span>
        </Card>
        <Card className="stat">
          <small>Fresh experiments left</small>
          <strong>{snap.experimentsRemaining ?? '—'}<em> / {run.budget.experiments ?? '?'}</em></strong>
          <span>{run.experiments.filter((e) => e.revealedAt !== null && e.revealedAt <= t).length} run so far</span>
        </Card>
      </div>

      <div className="two-col two-col-outcome">
        <Card className="question-card" title="Current question" aside={snap.questionAt !== null && <small className="muted">recorded at {clock(snap.questionAt)}</small>}>
          {snap.question ? <p className="question">“{snap.question}”</p> : <p className="muted">No question recorded yet at this point of the replay.</p>}
          {snap.question && snap.phase !== 'experiment' && snap.phase !== 'not_started' && <p className="muted small q-note">Last question recorded by the planner; later phases record no new question.</p>}
          <div className="activity">
            <small>Latest recorded event</small>
            {snap.activity ? (
              <div className={`activity-row tone-${snap.activity.tone}`}>
                <span className="activity-t">{clock(snap.activity.t)}</span>
                <div><strong>{snap.activity.title}</strong>{snap.activity.detail && <p>{snap.activity.detail}</p>}</div>
              </div>
            ) : <p className="muted">Replay is before the first event.</p>}
          </div>
        </Card>

        <Card title="Outcome and candidate history" aside={<Pill tone={statusTone}>
          {ended ? humanize(run.outcome.rawStatus ?? run.outcome.status) : run.outcome.status === 'incomplete' && t >= run.duration ? 'Record incomplete' : 'In progress at this point'}
        </Pill>}>
          {ended ? (
            <p className="outcome-lead">
              {run.outcome.status === 'accepted'
                ? `Accepted: ${run.outcome.firstAcceptance ?? 'candidate recorded as accepted'}`
                : <>No candidate was accepted. Stopped: <span className="bad-text">{humanize(run.outcome.stopReason)}</span>.</>}
            </p>
          ) : run.outcome.status === 'incomplete' && t >= run.duration ? (
            <p className="outcome-lead muted">The record ends without a stop event. Outcome unknown; nothing is assumed.</p>
          ) : (
            <p className="outcome-lead muted">Not stopped at this point of the replay.</p>
          )}

          {visibleCandidates.length === 0 ? <p className="muted">No builder turn has started at this point.</p> : (
            <table className="table table-dense">
              <thead><tr><th>Candidate</th><th>Started</th><th>Trusted gates</th><th>Blur cases</th><th>Decision</th></tr></thead>
              <tbody>
                {visibleCandidates.map((c) => {
                  const a = candidateAt(c, t);
                  const note = a.decided ? decisionNote(c) : null;
                  return (
                    <tr key={c.id} className="clickable" onClick={() => onOpenCandidate(c.id)} title="Open per-case evidence">
                      <td className="nowrap"><strong>{c.id}</strong></td>
                      <td>{clock(c.revealedAt)}</td>
                      <td><span className="gate-chips">
                        <GateChip label="Build" title="Production build" value={a.gate(c.gates.build)} />
                        <GateChip label="Indep." title="Independent execution" value={a.gate(c.gates.independent)} />
                        <GateChip label="Baseline" title="Exact baseline regressions" value={a.baselineGate} />
                      </span></td>
                      <td className="nowrap">{a.evaluated ? `${c.passedCount} of ${c.suiteCaseCount} passed` : a.decided ? <span className="muted">no output</span> : <span className="muted">pending</span>}</td>
                      <td><DecisionPill decision={a.decision} />{note && <small className="reason">{note}</small>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}

          {ended && (
            <div className="outcome-facts">
              <span>First acceptance <strong>{run.outcome.firstAcceptance ?? 'None'}</strong></span>
              <span>Later improvements <strong>{run.outcome.improvements === 0 ? 'None' : run.outcome.improvements}</strong></span>
              <span>Final build <strong>{run.outcome.finalBuild ? humanize(run.outcome.finalBuild) : 'Not recorded'}</strong></span>
              <span>Final exact baselines <Gate value={run.outcome.finalBaselinePass} /></span>
            </div>
          )}
          {ended && runNotes.map((n, i) => <p key={i} className="note"><Icon name="info" size={14} /><span>{n.text}{n.source && <cite> ({n.source})</cite>}</span></p>)}
        </Card>
      </div>

      <Card title="Run identity and scope">
        <div className="identity-grid">
          <dl className="facts">
            <dt>Run ID</dt><dd className="mono">{run.id}</dd>
            <dt>Reference</dt><dd>{run.target.name ?? 'Unknown'} {run.target.version ?? ''}{run.target.url && <small className="muted block">{run.target.url}</small>}</dd>
            <dt>Hosted build</dt><dd>{run.target.build ?? 'Not recorded'}</dd>
            <dt>Percentage domain</dt><dd>{run.budget.percentageRange ?? 'Not recorded'}</dd>
            <dt>Source</dt><dd className="mono small">{run.provenanceSource ?? 'Not recorded'}</dd>
          </dl>
          <div>
            <dl className="facts">
              <dt>Frozen suite</dt><dd>{run.suite.id ?? 'Not recorded'}{run.suite.sha256 && <small className="muted block mono">sha256 {run.suite.sha256.slice(0, 16)}…</small>}</dd>
              <dt>Cases</dt><dd><span className="chips">{run.suite.cases.map((c) => <EvidenceChip key={c.id} id={c.id} onOpen={onOpenEvidence} />)}</span></dd>
            </dl>
            {run.scope.length > 0 && <ul className="scope">{run.scope.map((s, i) => <li key={i}>{s}</li>)}</ul>}
          </div>
        </div>
      </Card>
    </div>
  );
}
