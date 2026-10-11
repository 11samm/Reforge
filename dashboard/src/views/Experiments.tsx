import { useState } from 'react';
import type { Run } from '../data/normalize.ts';
import { clock, humanize } from '../format.ts';
import { Card, ClaimPill, Empty, EvidenceChip, Gate, Icon, PixelImage, Pill } from '../ui.tsx';

export function Experiments({ run, t, selected, onSelect, onOpenEvidence }: {
  run: Run; t: number; selected: string | null; onSelect: (id: string) => void; onOpenEvidence: (id: string) => void;
}) {
  const [query, setQuery] = useState('');
  const visible = run.experiments.filter((e) => e.revealedAt === null || e.revealedAt <= t);
  const rows = visible.filter((e) => !query || `${e.id} ${e.question} ${e.inputKind}`.toLowerCase().includes(query.toLowerCase()));
  const exp = visible.find((e) => e.id === selected) ?? visible[0] ?? null;
  const observed = exp ? exp.observedAt !== null && exp.observedAt <= t : false;
  const linkedClaims = exp ? run.claims.filter((c) => (c.revealedAt === null || c.revealedAt <= t) && (c.supporting.includes(exp.id) || c.contradicting.includes(exp.id))) : [];
  const fixtures = run.suite.cases.filter((c) => c.source === 'development_fixture');

  return (
    <div className="master-detail">
      <div className="master">
        <div className="toolbar">
          <label className="search glass"><Icon name="search" size={16} />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search experiments" /></label>
          <span className="muted">Showing {rows.length} of {run.experiments.length}</span>
        </div>
        <Card>
          {rows.length === 0 ? <Empty>No experiments recorded at this point of the replay.</Empty> : (
            <table className="table">
              <thead><tr><th>ID</th><th>Question</th><th>Input</th><th>Percentage</th><th>Status</th></tr></thead>
              <tbody>
                {rows.map((e) => {
                  const done = e.observedAt !== null && e.observedAt <= t;
                  return (
                    <tr key={e.id} className={`clickable ${exp?.id === e.id ? 'selected' : ''}`} onClick={() => onSelect(e.id)}>
                      <td className="nowrap"><strong>{e.id}</strong></td>
                      <td className="wrap">{e.question ?? <span className="muted">not recorded</span>}</td>
                      <td>{humanize(e.inputKind)}<small className="muted block">{e.inputSize ?? ''}</small></td>
                      <td className="mono">{e.requested ?? '?'} → {done ? e.accepted ?? '?' : '…'}</td>
                      <td>{done ? <Pill tone="info">{humanize(e.status ?? 'unknown')}</Pill> : <Pill tone="neutral">Running</Pill>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </Card>
        {fixtures.length > 0 && (
          <p className="muted footnote">The frozen suite also uses {fixtures.length} prepared development fixtures:{' '}
            {fixtures.map((f) => <EvidenceChip key={f.id} id={f.id} onOpen={onOpenEvidence} />)}</p>
        )}
      </div>

      <div className="detail">
        {!exp ? <Card><Empty>Select an experiment.</Empty></Card> : (
          <Card title={<>Experiment {exp.id}</>} aside={exp.revealedAt !== null && <small className="muted">planned at {clock(exp.revealedAt)}</small>}>
            <p className="question">“{exp.question ?? 'Question not recorded'}”</p>

            <div className="percentage-row">
              <div className="pct-box"><small>Requested Percentage</small><strong>{exp.requested ?? '—'}</strong></div>
              <div className="pct-box"><small>Accepted by reference UI</small><strong>{observed ? exp.accepted ?? '—' : '…'}</strong></div>
              <div className="pct-check">
                {!observed ? <Pill tone="neutral">Awaiting reference</Pill>
                  : exp.percentageMatches === true ? <Pill tone="good">Exact match</Pill>
                    : exp.percentageMatches === false ? <Pill tone="bad">Mismatch</Pill> : <Pill tone="neutral">Not recorded</Pill>}
                <span className="muted">Original import confirmed <Gate value={exp.originalImportConfirmed} /></span>
              </div>
            </div>

            <div className="image-pair">
              <figure><figcaption>Input</figcaption>
                <PixelImage src={exp.images.input} alt={`${exp.id} input`} missing="Input image not in bundle" maxWidth={250} /></figure>
              <figure><figcaption>Reference output (real miniPaint export)</figcaption>
                <PixelImage src={observed ? exp.images.reference : null} alt={`${exp.id} reference output`} maxWidth={250}
                  missing={observed ? 'Reference output not in bundle' : 'Not exported yet at this point'} /></figure>
            </div>
            {exp.inputDefinition && <p className="muted small">Input definition: {exp.inputDefinition}</p>}

            <h4>Purpose</h4>
            <p>{exp.purpose ?? <span className="muted">Not recorded</span>}</p>

            <h4>Competing hypotheses and predictions</h4>
            {exp.hypotheses.length === 0 ? <p className="muted">Not recorded</p> : (
              <ol className="hypotheses">
                {exp.hypotheses.map((h, i) => (
                  <li key={i}><strong>{h}</strong>{exp.predictions[i] && <span>{exp.predictions[i]}</span>}</li>
                ))}
              </ol>
            )}

            <h4>Claims citing this evidence</h4>
            {linkedClaims.length === 0 ? <p className="muted">None at this point of the replay.</p> : (
              <ul className="linked-claims">
                {linkedClaims.map((c) => <li key={c.id}><ClaimPill status={c.status} raw={c.rawStatus} /> <span className="mono">{c.id}</span></li>)}
              </ul>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}
