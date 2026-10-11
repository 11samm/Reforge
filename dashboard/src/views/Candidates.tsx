import { useState } from 'react';
import type { CaseResult, Run } from '../data/normalize.ts';
import type { Selection } from '../App.tsx';
import { clock, fixed, humanize, parseReason, pct, secs, tokens, violated } from '../format.ts';
import { Card, Clamp, DecisionPill, Empty, EvidenceChip, Gate, Icon, OutcomePill, PixelImage, Pill, Segmented } from '../ui.tsx';
import { candidateAt, decisionNote } from './shared.ts';

type Tab = 'cases' | 'baselines' | 'builder';
type ImageMode = 'side' | 'reference' | 'candidate' | 'rgb' | 'alpha' | 'input';

export function Candidates({ run, t, sel, setSel, onOpenEvidence }: {
  run: Run; t: number; sel: Selection; setSel: (f: (s: Selection) => Selection) => void; onOpenEvidence: (id: string) => void;
}) {
  const [tab, setTab] = useState<Tab>('cases');
  const visible = run.candidates.filter((c) => c.revealedAt <= t);
  const cand = visible.find((c) => c.id === sel.candidate) ?? visible.at(-1) ?? null;

  if (run.candidates.length === 0) return <Card><Empty>No candidates were recorded for this run.</Empty></Card>;
  if (!cand) return <Card><Empty>No builder turn has started at this point of the replay (first at {clock(run.candidates[0].revealedAt)}).</Empty></Card>;

  const a = candidateAt(cand, t);
  const policy = run.suite.policy;

  return (
    <div className="candidates">
      <Card>
        <table className="table">
          <thead><tr><th>Candidate</th><th>Started</th><th>Build</th><th>Independent</th><th>UI export</th><th>Baselines</th><th>Blur cases</th><th>Decision</th></tr></thead>
          <tbody>
            {visible.map((c) => {
              const x = candidateAt(c, t);
              return (
                <tr key={c.id} className={`clickable ${c.id === cand.id ? 'selected' : ''}`} onClick={() => setSel((s) => ({ ...s, candidate: c.id }))}>
                  <td><strong>{c.id}</strong></td>
                  <td>{clock(c.revealedAt)}</td>
                  <td><Gate value={x.gate(c.gates.build)} /></td>
                  <td><Gate value={x.gate(c.gates.independent)} /></td>
                  <td><Gate value={x.gate(c.gates.ui)} /></td>
                  <td><Gate value={x.baselineGate} /></td>
                  <td>{x.evaluated ? <span className="case-dots">{c.cases.map((k) => <span key={k.id} className={`case-dot o-${k.outcome}`} title={`${k.id}: ${k.outcome}`} />)} <span>{c.passedCount}/{c.suiteCaseCount}</span></span>
                    : x.decided ? <span className="muted">no output</span> : <span className="muted">pending</span>}</td>
                  <td><DecisionPill decision={x.decision} />{x.decided && decisionNote(c) && <small className="reason">{decisionNote(c)}</small>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>

      <div className="cand-head">
        <div>
          <h2>{cand.id}</h2>
          <span className="muted">{a.stage}{cand.decidedAt !== null && a.decided ? ` at ${clock(cand.decidedAt)}` : ''}</span>
        </div>
        <DecisionPill decision={a.decision} />
        {a.decided && cand.reason && <Pill tone="neutral">Route label: {humanize(cand.reason)}</Pill>}
        <div className="grow" />
        <Segmented<Tab> label="Candidate evidence" value={tab} onChange={setTab} options={[
          { id: 'cases', label: `Blur cases · ${cand.suiteCaseCount}` },
          { id: 'baselines', label: `Baseline regressions${cand.baseline ? ` · ${cand.baseline.cases.length}` : ''}` },
          { id: 'builder', label: 'Builder turn' },
        ]} />
      </div>

      {(a.evaluated || a.decided) && (cand.error || cand.notes.length > 0 || (cand.routing && cand.routing.t <= t)) && (
        <div className="cand-notes">
          {cand.error && (
            <div className={`callout ${cand.decision === 'failed' ? 'callout-bad' : 'callout-warn'}`}>
              <Icon name="alert" /><div><strong>{cand.errorType ?? 'Error'}{cand.decision === 'failed' ? ' · candidate stopped, no evaluation' : ' · recorded during evaluation'}</strong><p className="mono small">{cand.error}</p></div>
            </div>
          )}
          {cand.routing && cand.routing.t <= t && (
            <div className="callout callout-info">
              <Icon name="info" /><div>
                <strong>Failure routing → {humanize(cand.routing.nextAction)} · {humanize(cand.routing.classification)}</strong>
                <p><Clamp>{cand.routing.explanation}</Clamp></p>
                <small className="muted">Model's concise route suggestion. Trusted acceptance: {cand.routing.trustedAcceptance === false ? 'not granted' : String(cand.routing.trustedAcceptance)}.</small>
              </div>
            </div>
          )}
          {cand.notes.map((n, i) => (
            <div key={i} className="callout callout-neutral"><Icon name="contract" /><div><strong>Historical note</strong><p><Clamp>{n.text}</Clamp></p>{n.source && <small className="muted">Source: {n.source}</small>}</div></div>
          ))}
        </div>
      )}

      {tab === 'cases' && <CasePanel run={run} cases={cand.cases} evaluated={a.evaluated} decided={a.decided} candidateFailed={cand.decision === 'failed'}
        errorText={cand.errorType ? `${cand.errorType}: ${cand.error ?? ''}` : null} selectedCase={sel.caseId}
        onSelectCase={(id) => setSel((s) => ({ ...s, caseId: id }))} onOpenEvidence={onOpenEvidence} policy={policy} />}

      {tab === 'baselines' && (
        <Card title="Exact baseline regressions" aside={cand.baseline && a.evaluated ? <Pill tone={cand.baseline.status === 'passed' ? 'good' : 'bad'}>{humanize(cand.baseline.status)} · {humanize(cand.baseline.classification)}</Pill> : undefined}>
          {!a.evaluated && !a.decided ? <Empty>Baselines run after the builder turn; pending at this point.</Empty>
            : !cand.baseline ? <Empty tone="warn">No baseline run was recorded for this candidate{cand.decision === 'failed' ? ' (it stopped before evaluation)' : ''}.</Empty> : (
              <>
                <p className="muted small">Exact 8-bit RGBA equality against the pre-existing editor behavior. <strong>Missing output</strong> means the verifier never produced a candidate image to compare; it is not a pixel regression.</p>
                {cand.baseline.cases.length === 0 ? <Empty>Only the summary status was recorded.</Empty> : (
                  <table className="table">
                    <thead><tr><th>Baseline case</th><th>Result</th><th>Different pixels</th><th>Reasons</th></tr></thead>
                    <tbody>{cand.baseline.cases.map((c) => (
                      <tr key={c.id}><td className="mono">{c.id}</td><td><OutcomePill outcome={c.outcome} /></td>
                        <td className="mono">{c.metrics ? tokens(c.metrics.differentPixels) : <span className="muted">no comparison</span>}</td>
                        <td className="wrap small">{c.reasons.length ? c.reasons.join('; ') : <span className="muted">—</span>}</td></tr>
                    ))}</tbody>
                  </table>
                )}
              </>
            )}
        </Card>
      )}

      {tab === 'builder' && (
        <Card title={`Builder turn · ${cand.builder?.invocation ?? 'not recorded'}`}>
          {!cand.builder ? <Empty tone="warn">Model telemetry for this builder turn is not included in the bundle.</Empty>
            : !cand.builder.recorded ? <Empty tone="warn">Invocation record missing: no usage telemetry was recorded for this turn.</Empty> : (
              <>
                <dl className="facts facts-inline">
                  <dt>Status</dt><dd>{humanize(cand.builder.status)}{cand.builder.completion ? ` · ${humanize(cand.builder.completion)}` : ''}</dd>
                  <dt>Model</dt><dd>{cand.builder.model ?? 'Not recorded'} {cand.builder.effort && `· ${cand.builder.effort}`}</dd>
                  <dt>Turn time</dt><dd>{secs(cand.builder.elapsedSeconds)}</dd>
                  <dt>Total tokens</dt><dd>{cand.builder.usage ? tokens(cand.builder.usage.total) : 'Not recorded'}</dd>
                </dl>
                {cand.builder.error && <p className="mono small bad-text">{cand.builder.error}</p>}
                <h4>Builder's concise final message</h4>
                {cand.builder.conciseOutput ? <blockquote>{cand.builder.conciseOutput}</blockquote> : <p className="muted">No final message recorded{cand.decision === 'failed' ? ' (turn did not complete)' : ''}.</p>}
                <p className="muted small">Raw reasoning is never stored or shown; only the reasoning token count is recorded (see Model usage).</p>
              </>
            )}
        </Card>
      )}
    </div>
  );
}

function CasePanel({ run, cases, evaluated, decided, candidateFailed, errorText, selectedCase, onSelectCase, onOpenEvidence, policy }: {
  run: Run; cases: CaseResult[]; evaluated: boolean; decided: boolean; candidateFailed: boolean; errorText: string | null;
  selectedCase: string | null; onSelectCase: (id: string) => void; onOpenEvidence: (id: string) => void; policy: Record<string, unknown> | null;
}) {
  const k = cases.find((c) => c.id === selectedCase) ?? cases.find((c) => evaluated && c.outcome !== 'passed') ?? cases[0] ?? null;
  const [mode, setMode] = useState<ImageMode>('side');
  const [regions, setRegions] = useState(true);
  if (!k) return <Card><Empty>No suite cases recorded.</Empty></Card>;
  const showResults = evaluated;
  const suiteCase = run.suite.cases.find((c) => c.id === k.id);
  const regionBoxes = suiteCase?.regions ?? Object.fromEntries(k.regions.filter((r) => r.box).map((r) => [r.name, r.box!]));

  const missingCandidate = !showResults ? (decided && candidateFailed ? `No candidate output: candidate stopped before evaluation${errorText ? ` (${errorText})` : ''}` : 'Not evaluated yet at this point')
    : k.outcome === 'missing_output' ? 'Evaluator recorded missing candidate output' : 'Candidate image not in bundle';
  const imgs = { reference: k.images.reference, candidate: showResults ? k.images.candidate : null, rgb: showResults ? k.images.rgbDifference : null, alpha: showResults ? k.images.alphaDifference : null, input: k.images.input };
  const missings = { reference: 'Reference output not in bundle', input: 'Input not in bundle', candidate: missingCandidate,
    rgb: showResults ? 'RGB difference image not in bundle' : missingCandidate, alpha: showResults ? 'Alpha difference image not in bundle' : missingCandidate };
  const parsed = k.reasons.map((r) => parseReason(r) ?? { raw: r, region: '', metric: '', label: r, value: NaN, limit: NaN, comparator: '' });
  const P = (key: string) => (typeof policy?.[key] === 'number' ? (policy[key] as number) : null);

  return (
    <div className="case-panel">
      <Card title="Per-case results" aside={policy && <small className="muted">Gates ({String(policy.id ?? 'policy')}): RGB mean ≤ {P('rgb_mean_max') ?? '?'}, ≥ {pct(P('rgb_fraction_min'), 0)} within ±{P('rgb_pixel_tolerance') ?? '?'}; alpha mean ≤ {P('alpha_mean_max') ?? '?'}, max ≤ {P('alpha_max') ?? '?'}</small>}>
        <table className="table table-dense">
          <thead><tr><th>Case</th><th title="Percentage">%</th><th>Result</th><th>RGB mean</th><th>RGB ±tol</th><th>α mean</th><th>α max</th><th>Regions</th></tr></thead>
          <tbody>
            {cases.map((c) => {
              const m = showResults ? c.metrics : null;
              const bad = (metric: string) => (violated(c.reasons, 'full_image', metric) ? 'bad-cell' : '');
              return (
                <tr key={c.id} className={`clickable ${c.id === k.id ? 'selected' : ''}`} onClick={() => onSelectCase(c.id)}>
                  <td><strong className="mono">{c.id}</strong><small className="muted block">{c.source === 'development_fixture' ? 'fixture' : c.source === 'fresh_experiment' ? 'fresh' : ''}</small></td>
                  <td className="mono">{c.percentage ?? '—'}</td>
                  <td>{showResults ? <OutcomePill outcome={c.outcome} /> : <Pill tone="neutral">{decided ? 'No output' : 'Pending'}</Pill>}</td>
                  <td className={`mono ${bad('rgb_mae')}`}>{m ? fixed(m.rgbMae, 4) : '—'}</td>
                  <td className={`mono ${bad('rgb_fraction_within_tolerance')}`}>{m ? pct(m.rgbWithinTolerance) : '—'}</td>
                  <td className={`mono ${bad('alpha_mae')}`}>{m ? fixed(m.alphaMae, 4) : '—'}</td>
                  <td className={`mono ${bad('alpha_max')}`}>{m ? m.alphaMax ?? '—' : '—'}</td>
                  <td>{showResults && c.regions.length ? (
                    <span className="region-gates">{c.regions.map((r) => (
                      <span key={r.name} className={`rg rg-${r.passed === true ? 'pass' : r.passed === false ? 'fail' : 'none'}`} title={`${r.name}: ${r.passed === true ? 'passed' : r.passed === false ? 'failed' : 'not recorded'}`}>
                        {r.name[0].toUpperCase()}
                      </span>
                    ))}</span>
                  ) : <span className="muted">—</span>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>

      <Card className="inspector" title={<>Inspect <span className="mono">{k.id}</span></>} aside={<EvidenceChip id={k.id} onOpen={onOpenEvidence} />}>
        <div className="inspector-controls">
          <Segmented<ImageMode> label="Image view" value={mode} onChange={setMode} options={[
            { id: 'side', label: 'Side by side' },
            { id: 'reference', label: 'Reference' },
            { id: 'candidate', label: 'Candidate' },
            { id: 'rgb', label: 'RGB ×16' },
            { id: 'alpha', label: 'Alpha ×16' },
            { id: 'input', label: 'Input' },
          ]} />
          <label className="toggle"><input type="checkbox" checked={regions} onChange={(e) => setRegions(e.target.checked)} /> Regions</label>
        </div>
        {mode === 'side' ? (
          <div className="side-by-side">
            <figure>
              <figcaption>Reference <small className="muted">miniPaint output</small></figcaption>
              <PixelImage src={imgs.reference} alt={`${k.id} reference`} missing={missings.reference} regions={regionBoxes} showRegions={regions} maxWidth={240} />
            </figure>
            <figure>
              <figcaption>Candidate <small className="muted">generated app output</small></figcaption>
              <PixelImage src={imgs.candidate} alt={`${k.id} candidate`} missing={missings.candidate} regions={regionBoxes} showRegions={regions} maxWidth={240} />
            </figure>
          </div>
        ) : (
          <PixelImage src={imgs[mode]} alt={`${k.id} ${mode}`} missing={missings[mode]} regions={regionBoxes} showRegions={regions} maxWidth={420} />
        )}
        <p className="muted small">Scored on raw unpremultiplied RGBA; checkerboard is display only. Difference images come from the trusted evaluator.</p>

        <h4>{showResults && k.outcome === 'passed' ? 'Why it passed' : 'Why it failed'}</h4>
        {!showResults ? <Empty tone={decided ? 'warn' : 'neutral'}>{missingCandidate}. No pixel comparison exists, so this is not a pixel failure.</Empty>
          : k.outcome === 'passed' ? <p className="good-text">All full-image and region gates passed on this case.</p>
            : k.outcome === 'missing_output' ? <Empty tone="warn">The evaluator found no candidate output to compare. This is a missing output, not a failed pixel comparison.</Empty>
              : parsed.length === 0 ? <Empty>Failed, but no reasons were recorded.</Empty> : (
                <ul className="reasons">
                  {parsed.map((p, i) => (
                    <li key={i}>
                      {p.metric ? (<><span className="reason-region">{humanize(p.region)}</span>
                        <span>{p.label}</span>
                        <strong className="mono">{p.metric.includes('fraction') ? pct(p.value) : fixed(p.value, 4)}</strong>
                        <span className="muted">{p.comparator === '<' ? 'needs ≥' : 'limit ≤'} {p.metric.includes('fraction') ? pct(p.limit, 0) : p.limit}</span></>)
                        : <span className="mono small">{p.raw}</span>}
                    </li>
                  ))}
                </ul>
              )}
        {showResults && k.regions.length > 0 && (
          <table className="table table-dense region-table">
            <thead><tr><th>Region</th><th>RGB mean</th><th>RGB ±tol</th><th>α mean</th><th>Gate</th></tr></thead>
            <tbody>{k.regions.map((r) => (
              <tr key={r.name}><td title={r.box ? `box x0,y0,x1,y1 = ${r.box.join(',')}` : 'box not recorded'}>{r.name}</td>
                <td className={`mono ${violated(k.reasons, r.name, 'rgb_mae') ? 'bad-cell' : ''}`}>{fixed(r.metrics?.rgbMae, 4)}</td>
                <td className={`mono ${violated(k.reasons, r.name, 'rgb_fraction_within_tolerance') ? 'bad-cell' : ''}`}>{pct(r.metrics?.rgbWithinTolerance)}</td>
                <td className={`mono ${violated(k.reasons, r.name, 'alpha_mae') ? 'bad-cell' : ''}`}>{fixed(r.metrics?.alphaMae, 4)}</td>
                <td><Gate value={r.passed} /></td></tr>
            ))}</tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
