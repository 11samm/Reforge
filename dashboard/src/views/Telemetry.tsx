import type { Run } from '../data/normalize.ts';
import { humanize, secs, tokens } from '../format.ts';
import { Card, Empty, Pill } from '../ui.tsx';

export function Telemetry({ run, t }: { run: Run; t: number }) {
  if (!run.telemetryIncluded) {
    return <Card><Empty tone="warn">Model telemetry was not included in this bundle. Token usage is unknown; no estimate is shown.</Empty></Card>;
  }
  const rows = run.telemetry
    .filter((x) => x.revealedAt === null ? t >= run.duration : x.revealedAt <= t)
    .sort((a, b) => (a.revealedAt ?? Infinity) - (b.revealedAt ?? Infinity));
  const withUsage = rows.filter((x) => x.recorded && x.usage && x.usage.total !== null);
  const sum = (f: (u: NonNullable<(typeof rows)[number]['usage']>) => number | null) => withUsage.reduce((s, x) => s + (f(x.usage!) ?? 0), 0);
  const missing = rows.length - withUsage.length;

  return (
    <div className="telemetry">
      <div className="stats">
        <Card className="stat"><small>Total tokens (recorded)</small><strong>{tokens(sum((u) => u.total))}</strong><span>{withUsage.length} of {rows.length} invocations have usage</span></Card>
        <Card className="stat"><small>Input tokens</small><strong>{tokens(sum((u) => u.input))}</strong><span>{tokens(sum((u) => u.cachedInput))} cached, included in input</span></Card>
        <Card className="stat"><small>Output tokens</small><strong>{tokens(sum((u) => u.output))}</strong><span>{tokens(sum((u) => u.reasoningOutput))} reasoning tokens (count only)</span></Card>
        <Card className="stat"><small>Missing telemetry</small><strong>{missing}</strong><span>{missing === 0 ? 'Every visible invocation has a record' : 'Shown as “Not recorded”, never estimated'}</span></Card>
      </div>
      <Card title="Invocations" aside={<small className="muted">Usage observations from the runtime, not an invoice or cost estimate</small>}>
        {rows.length === 0 ? <Empty>No model invocation is visible at this point of the replay.</Empty> : (
          <table className="table">
            <thead><tr><th>Invocation</th><th>Role</th><th>Model</th><th>Status</th><th>Time</th><th>Total</th><th>Input</th><th>Cached</th><th>Output</th><th>Reasoning</th></tr></thead>
            <tbody>
              {rows.map((x) => (
                <tr key={x.invocation}>
                  <td className="mono"><strong>{x.invocation}</strong></td>
                  <td>{humanize(x.role)}</td>
                  <td>{x.model ?? <span className="muted">—</span>}{x.effort && <small className="muted block">{x.effort}</small>}</td>
                  <td>{!x.recorded ? <Pill tone="warn">Record missing</Pill> : x.status === 'passed' ? <Pill tone="good">Completed</Pill> : <Pill tone="bad" title={x.error ?? ''}>{humanize(x.status ?? 'unknown')}</Pill>}</td>
                  <td className="mono">{secs(x.elapsedSeconds)}</td>
                  {x.usage ? (<>
                    <td className="mono"><strong>{tokens(x.usage.total)}</strong></td>
                    <td className="mono">{tokens(x.usage.input)}</td>
                    <td className="mono">{tokens(x.usage.cachedInput)}</td>
                    <td className="mono">{tokens(x.usage.output)}</td>
                    <td className="mono">{tokens(x.usage.reasoningOutput)}</td>
                  </>) : <td colSpan={5}><span className="missing-tag">Not recorded</span></td>}
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="muted small">Reasoning content is never stored; only its token count is shown. Timing for an invocation appears in replay once its outcome is recorded.</p>
      </Card>
    </div>
  );
}
