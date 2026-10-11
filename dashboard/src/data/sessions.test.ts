import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseSessions } from './sessions.ts';
const id = 'a'.repeat(32);
const fixture = () => ({ job_id: id, mode: 'live', sessions: { reference: { state: 'ready', frame: 'YWJj' }, candidate: { state: 'building', frame: 'YWJj' } } });
test('synthetic session fixture rejects another job and recorded playback', () => {
  assert.throws(() => parseSessions(fixture(), 'b'.repeat(32)));
  assert.throws(() => parseSessions({ ...fixture(), mode: 'recorded' }, id));
});
test('synthetic session fixture clears unavailable frames and rejects arbitrary image URLs', () => {
  assert.equal(parseSessions(fixture(), id).sessions.candidate.frame, null);
  const r = fixture(); r.sessions.reference.frame = 'https://another-host/frame.jpg';
  assert.throws(() => parseSessions(r, id));
});
