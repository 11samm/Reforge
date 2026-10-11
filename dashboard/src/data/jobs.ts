import { appendEvents, parseEventLine } from './live.ts';
import type { BundleEvent } from './bundle.ts';

export const STAGES = ['Discover', 'Validate procedure', 'Investigate', 'Reconstruct', 'Verify'] as const;
export interface Job {
  id: string; presentation_label?: string; request: string; status: string; stage: string; activity: string; elapsed_seconds: number;
  budget: Record<string, number>; usage: { total?: { inputTokens?: number; outputTokens?: number; totalTokens?: number } }[] | null;
  events: BundleEvent[]; evidence: { name: string; url: string; available_at: number }[];
}
export function normalizeJob(raw: unknown): Job {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw new Error('Invalid job');
  const r = raw as Record<string, unknown>;
  if (typeof r.id !== 'string' || !/^[a-f0-9]{32}$/.test(r.id)) throw new Error('Invalid job ID');
  const text = (v: unknown) => typeof v === 'string' ? v.slice(0, 1500) : '';
  const events = Array.isArray(r.events) ? r.events.map(e => parseEventLine(JSON.stringify(e))).filter((e): e is BundleEvent => e !== null && e.sequence !== undefined && e.elapsed_seconds !== undefined) : [];
  const merged = appendEvents({}, events).events ?? [];
  const evidence: Job['evidence'] = [];
  for (const e of merged) {
    const url = text(e.artifact);
    if (new RegExp(`^/api/jobs/${r.id}/evidence/(spec|discovery-summary|validation|visible-report|final-summary|preparation|repair-summary)\\.json$`).test(url)) {
      evidence.push({ name: url.split('/').at(-1)!, url, available_at: e.elapsed_seconds! });
    }
  }
  const budget: Record<string, number> = {};
  if (r.budget && typeof r.budget === 'object') for (const [k,v] of Object.entries(r.budget)) if (typeof v === 'number' && Number.isFinite(v) && v >= 0) budget[k] = v;
  return { id: r.id, presentation_label: text(r.presentation_label), request: text(r.request), status: text(r.status), stage: text(r.stage), activity: text(r.activity),
    elapsed_seconds: typeof r.elapsed_seconds === 'number' && Number.isFinite(r.elapsed_seconds) ? r.elapsed_seconds : 0,
    budget, usage: Array.isArray(r.usage) ? r.usage : null, events: merged, evidence };
}
/** Replay only facts delivered by this cursor; final job fields never fill earlier snapshots. */
export function jobAt(job: Job, t: number) {
  const events = job.events.filter(e => e.elapsed_seconds! <= t);
  let stage = 'Discover', activity = 'Queued', status = 'queued';
  for (const e of events) {
    if (typeof e.stage === 'string' && STAGES.includes(e.stage as typeof STAGES[number])) stage = e.stage;
    if (typeof e.activity === 'string') activity = e.activity;
    if (e.event === 'start') status = 'running';
    if (e.event === 'stop' && typeof e.status === 'string') status = e.status;
  }
  return { stage, activity, status, events, evidence: job.evidence.filter(e => e.available_at <= t) };
}
