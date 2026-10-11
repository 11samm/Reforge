import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { appendEvents, parseEventLine } from './live.ts';
import { caseOutcome, claimStatus, normalizeRun, resolveArtifact, snapshotAt } from './normalize.ts';

const load = (p: string): unknown => JSON.parse(readFileSync(new URL(p, import.meta.url), 'utf-8'));
const recorded = load('../../public/runs/recorded-20261010T184129Z-78c8e934/manifest.json');
const synthetic = load('../../public/runs/synthetic-render-check/manifest.json');
const BASE = 'runs/x/';

test('recorded run keeps the historical unresolved outcome', () => {
  const run = normalizeRun(recorded, BASE);
  assert.equal(run.provenance, 'recorded');
  assert.equal(run.outcome.status, 'unresolved');
  assert.equal(run.outcome.stopReason, 'budget_exhausted');
  assert.equal(run.outcome.firstAcceptance, null);
  assert.equal(run.outcome.improvements, 0);
  assert.equal(run.candidates.some((c) => c.decision === 'accepted'), false);
  assert.deepEqual(run.candidates.map((c) => c.decision), ['rejected', 'rejected', 'failed']);
});

test('candidate 3 timeout is a missing evaluation, not a pixel failure', () => {
  const c3 = normalizeRun(recorded, BASE).candidates[2];
  assert.equal(c3.id, 'candidate-3');
  assert.equal(c3.errorType, 'TimeoutError');
  assert.equal(c3.reason, 'ambiguous_budget_exhausted');
  assert.equal(c3.evaluatedCount, 0);
  assert.ok(c3.cases.length === 6 && c3.cases.every((c) => c.outcome === 'not_evaluated' && c.images.candidate === null));
  assert.equal(c3.passedCount, 0);
});

test('candidate pixel failures and baseline missing outputs are distinguished', () => {
  const [c1, c2] = normalizeRun(recorded, BASE).candidates;
  assert.equal(c2.passedCount, 3);
  assert.deepEqual(c2.cases.filter((c) => c.outcome === 'pixel_mismatch').map((c) => c.id), ['gb010', 'fresh-03', 'fresh-04']);
  assert.equal(c2.gates.baseline, true);
  assert.equal(c1.gates.baseline, false);
  assert.ok(c1.baseline && c1.baseline.cases.every((c) => c.outcome === 'missing_output'));
  const fresh03 = c2.cases.find((c) => c.id === 'fresh-03')!;
  assert.equal(fresh03.regions.find((r) => r.name === 'center')?.passed, false);
  assert.ok(fresh03.images.reference && fresh03.images.candidate && fresh03.images.rgbDifference);
});

test('replay snapshot at end shows stop, exhausted candidates and no live drift', () => {
  const run = normalizeRun(recorded, BASE);
  const end = snapshotAt(run, run.duration + 50);
  assert.equal(end.phase, 'stopped');
  assert.equal(end.stopped, true);
  assert.equal(end.candidatesRemaining, 0);
  assert.ok(Math.abs(end.remainingSeconds! - 91.473) < 1e-6);
  const mid = snapshotAt(run, 300);
  assert.equal(mid.phase, 'implement');
  assert.equal(mid.question, 'Are RGB and alpha blurred independently, with alpha weighting, or with alpha preserved?');
  assert.equal(snapshotAt(run, 0).phase, 'not_started');
});

test('model telemetry is the recorded usage, with nothing invented', () => {
  const run = normalizeRun(recorded, BASE);
  const total = run.telemetry.reduce((s, t) => s + (t.usage?.total ?? 0), 0);
  assert.equal(total, 1257517);
  assert.equal(run.candidates[2].builder?.usage?.total, 178876);
});

test('synthetic fixture: unknown statuses, unsafe paths, newer schema, incomplete run', () => {
  const run = normalizeRun({ ...(synthetic as Record<string, unknown>), schema_version: 99 }, BASE);
  assert.equal(run.provenance, 'synthetic');
  assert.equal(run.outcome.status, 'incomplete');
  assert.deepEqual(run.claims.map((c) => c.status), ['UNRECOGNIZED', 'UNRECOGNIZED', 'HYPOTHESIS']);
  const unsafe = run.suite.cases.find((c) => c.id === 'syn-unsafe')!;
  assert.equal(unsafe.images.input, null);
  assert.equal(unsafe.images.reference, null);
  assert.ok(run.warnings.some((w) => w.includes('newer')));
  assert.ok(run.warnings.some((w) => w.includes('unsafe artifact')));
  assert.equal(run.experiments[0].percentageMatches, false);
  assert.equal(run.candidates[0].decision, 'rejected');
  assert.equal(run.candidates[0].decidedAt, 40);
  assert.equal(run.candidates[1].decision, 'pending');
  assert.equal(run.candidates[1].decidedAt, null);
  assert.equal(run.candidates[0].cases[1].outcome, 'missing_output');
  assert.equal(run.telemetry.find((t) => t.invocation === 'builder-1')?.recorded, false);
});

test('legacy events-only and empty inputs never become successes', () => {
  const legacy = normalizeRun({ events: [
    { event: 'candidate', id: 'c1', elapsed_seconds: 1 },
    { event: 'stop', elapsed_seconds: 2, reason: 'done', status: 'accepted' },
  ] }, BASE);
  assert.equal(legacy.provenance, 'unknown');
  assert.equal(legacy.outcome.status, 'unknown');
  assert.equal(legacy.candidates[0].decision, 'pending');
  assert.ok(legacy.warnings.some((w) => w.includes('no candidate acceptance')));
  const empty = normalizeRun(null, BASE);
  assert.equal(empty.outcome.status, 'incomplete');
  assert.equal(empty.candidates.length, 0);
});

test('primitive classifiers', () => {
  assert.equal(caseOutcome('failed', 'missing_output', false), 'missing_output');
  assert.equal(caseOutcome('failed', null, true), 'pixel_mismatch');
  assert.equal(caseOutcome('failed', null, false), 'failed_unclassified');
  assert.equal(caseOutcome(null, null, false), 'unknown');
  assert.equal(claimStatus('verified_within_scope'), 'VERIFIED_WITHIN_SCOPE');
  assert.equal(claimStatus(undefined), 'UNRECOGNIZED');
  assert.equal(resolveArtifact('runs/a', 'artifacts/x.png'), 'runs/a/artifacts/x.png');
  for (const bad of ['/etc/passwd', '../x.png', 'a/../../x.png', 'https://evil/x.png', 'C:\\x.png', 'file:x']) assert.equal(resolveArtifact('runs/a', bad), null);
  assert.equal(parseEventLine('{"event":"stop"}')?.event, 'stop');
  assert.equal(parseEventLine('[1]'), null);
  assert.equal(appendEvents({ events: [{ sequence: 1, event: 'a' }] }, [{ sequence: 1, event: 'a' }, { sequence: 2, event: 'b' }]).events?.length, 2);
});
