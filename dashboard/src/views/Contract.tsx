import { useState } from 'react';
import type { ClaimStatus, Run } from '../data/normalize.ts';
import { CLAIM_LABEL, clock } from '../format.ts';
import { Card, ClaimPill, Empty, EvidenceChip, Icon } from '../ui.tsx';

const ORDER: ClaimStatus[] = ['VERIFIED_WITHIN_SCOPE', 'OBSERVED', 'HYPOTHESIS', 'UNKNOWN', 'CONTRADICTED', 'UNRECOGNIZED'];

export function Contract({ run, t, onOpenEvidence }: { run: Run; t: number; onOpenEvidence: (id: string) => void }) {
  const [filter, setFilter] = useState<ClaimStatus | 'ALL'>('ALL');
  const [selected, setSelected] = useState<string | null>(null);
  const visible = run.claims.filter((c) => c.revealedAt === null ? t >= run.duration : c.revealedAt <= t);
  const rows = visible.filter((c) => filter === 'ALL' || c.status === filter);
  const claim = rows.find((c) => c.id === selected) ?? rows[0] ?? null;
  const counts = new Map(ORDER.map((s) => [s, visible.filter((c) => c.status === s).length]));
  const known = new Set([...run.experiments.map((e) => e.id), ...run.suite.cases.map((c) => c.id)]);
  const verified = counts.get('VERIFIED_WITHIN_SCOPE') ?? 0;

  if (visible.length === 0) {
    const at = run.claims[0]?.revealedAt;
    return <Card><Empty>{run.claims.length === 0 ? 'No contract claims were recorded for this run.' : `The contract is recorded at ${clock(at ?? null)}; the replay has not reached it yet.`}</Empty></Card>;
  }

  return (
    <div className="contract">
      {run.contractDecision && (
        <div className="decision glass"><Icon name="contract" /><div><small>Recorded contract decision</small><p>{run.contractDecision}</p></div></div>
      )}
      <div className="toolbar">
        <div className="chips-row">
          <button type="button" className={`filter-chip ${filter === 'ALL' ? 'active' : ''}`} onClick={() => setFilter('ALL')}>All · {visible.length}</button>
          {ORDER.filter((s) => (counts.get(s) ?? 0) > 0 || s === 'VERIFIED_WITHIN_SCOPE').map((s) => (
            <button key={s} type="button" className={`filter-chip ${filter === s ? 'active' : ''}`} onClick={() => setFilter(s)}>
              {CLAIM_LABEL[s]} · {counts.get(s) ?? 0}
            </button>
          ))}
        </div>
        {verified === 0 && <span className="muted">No claim is verified within scope.</span>}
      </div>

      <div className="master-detail">
        <div className="master">
          <Card>
            {rows.length === 0 ? <Empty>No claims with this status.</Empty> : (
              <table className="table">
                <thead><tr><th>Claim</th><th>Status</th><th>Supporting evidence</th><th>Open</th></tr></thead>
                <tbody>
                  {rows.map((c) => (
                    <tr key={c.id} className={`clickable ${claim?.id === c.id ? 'selected' : ''}`} onClick={() => setSelected(c.id)}>
                      <td><strong className="mono nowrap">{c.id}</strong><small className="muted block clamp">{c.statement}</small></td>
                      <td><ClaimPill status={c.status} raw={c.rawStatus} /></td>
                      <td><span className="chips">{c.supporting.length ? c.supporting.map((id) => <span key={id} className="mini-chip">{id}</span>) : <span className="muted">none</span>}</span></td>
                      <td className="mono">{c.unresolved.length}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>
        <div className="detail">
          {claim && (
            <Card title={<span className="mono">{claim.id}</span>} aside={<ClaimPill status={claim.status} raw={claim.rawStatus} />}>
              <p className="statement">{claim.statement}</p>
              <dl className="facts">
                <dt>Scope</dt><dd>{claim.scope ?? <span className="muted">Not recorded</span>}</dd>
                <dt>Setup</dt><dd>{claim.setup ?? <span className="muted">Not recorded</span>}</dd>
                <dt>Parameter domain</dt><dd>{claim.domain ?? <span className="muted">Not recorded</span>}</dd>
              </dl>
              <h4>Supporting evidence</h4>
              <div className="chips">
                {claim.supporting.length === 0 ? <span className="muted">None recorded</span> : claim.supporting.map((id) =>
                  known.has(id) ? <EvidenceChip key={id} id={id} onOpen={onOpenEvidence} /> : <span key={id} className="mini-chip missing" title="Not present in this bundle">{id} · missing</span>)}
              </div>
              {claim.contradicting.length > 0 && (<><h4>Contradicting evidence</h4>
                <div className="chips">{claim.contradicting.map((id) => <EvidenceChip key={id} id={id} onOpen={onOpenEvidence} />)}</div></>)}
              <h4>Unresolved questions</h4>
              {claim.unresolved.length === 0 ? <p className="muted">None recorded</p> : <ul className="bullets">{claim.unresolved.map((u, i) => <li key={i}>{u}</li>)}</ul>}
              {claim.alternatives.length > 0 && (<><h4>Alternatives kept open</h4><ul className="bullets">{claim.alternatives.map((a, i) => <li key={i}>{a}</li>)}</ul></>)}
              {claim.verificationCases.length > 0 && <p className="muted small">Verification cases: {claim.verificationCases.join(', ')}. Being cited as a verification case does not mean the case passed.</p>}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
