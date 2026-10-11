import { test } from 'node:test';
import assert from 'node:assert/strict';
import { appendEvents, parseEventLine } from './live.ts';
import { normalizeJob, jobAt } from './jobs.ts';

test('live events require finite timing and positive sequence', () => {
  for (const x of ['{}','[]','{"event":"x","sequence":-1,"elapsed_seconds":0}','{"event":"x","sequence":1,"elapsed_seconds":-1}']) assert.equal(parseEventLine(x), null);
  assert.ok(parseEventLine('{"event":"stop"}')); // Existing legacy interface remains supported.
  assert.ok(parseEventLine('{"event":"stage","sequence":1,"elapsed_seconds":0}'));
});
test('reconnect deduplicates within batches and orders events', () => {
  const one = { sequence: 1, event: 'start', elapsed_seconds: 0 }, two = { sequence: 2, event: 'stop', elapsed_seconds: 10 };
  const bundle = appendEvents({}, [two, one, one]);
  assert.deepEqual(bundle.events, [one, two]);
  assert.deepEqual(appendEvents(bundle, [two]).events, [one, two]);
});
test('job replay cannot reveal future evidence, stages or terminal outcome', () => {
  const id = 'a'.repeat(32);
  const job = normalizeJob({ id, status: 'accepted', stage: 'Verify', evidence: [{name:'future',url:'/secret',available_at:0}], events: [
    {sequence:1,event:'start',elapsed_seconds:0},
    {sequence:2,event:'stage',elapsed_seconds:5,stage:'Investigate'},
    {sequence:3,event:'evidence',elapsed_seconds:10,artifact:`/api/jobs/${id}/evidence/spec.json`},
    {sequence:4,event:'evidence',elapsed_seconds:11,artifact:'../../secret'},
    {sequence:5,event:'stop',elapsed_seconds:20,status:'accepted'},
  ] });
  assert.equal(jobAt(job, 1).status, 'running');
  assert.equal(jobAt(job, 1).stage, 'Discover');
  assert.equal(jobAt(job, 9).evidence.length, 0);
  assert.equal(jobAt(job, 10).evidence.length, 1);
  assert.equal(jobAt(job, 19).status, 'running');
  assert.equal(jobAt(job, 20).status, 'accepted');
  assert.equal(job.evidence.length, 1);
});
