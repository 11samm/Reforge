import type { CaseOutcome, ClaimStatus, Decision, Phase } from './data/normalize.ts';

export function clock(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds)) return '—';
  const s = Math.max(0, seconds);
  const m = Math.floor(s / 60);
  return `${m}:${(s - m * 60).toFixed(1).padStart(4, '0')}`;
}

export const secs = (s: number | null) => (s === null ? '—' : `${s.toFixed(1)} s`);
export const fixed = (v: number | null | undefined, d = 3) => (v === null || v === undefined || Number.isNaN(v) ? '—' : v.toFixed(d));
export const pct = (v: number | null | undefined, d = 2) => (v === null || v === undefined ? '—' : `${(v * 100).toFixed(d)}%`);
export const tokens = (v: number | null | undefined) => (v === null || v === undefined ? '—' : v.toLocaleString('en-US'));
export const humanize = (s: string | null | undefined) => (s ? s.replace(/[_-]+/g, ' ') : '—');

export const PHASE_LABEL: Record<Phase, string> = {
  not_started: 'Not started',
  observe: 'Observe',
  experiment: 'Experiment',
  contract: 'Contract',
  implement: 'Implement',
  evaluate: 'Evaluate',
  decide: 'Accept / reject',
  stopped: 'Stopped',
};

export const PHASE_HINT: Record<Phase, string> = {
  not_started: 'Replay has not reached the first recorded event.',
  observe: 'Checkpoint the starting app and confirm exact baselines.',
  experiment: 'Run planned diagnostic inputs through the real reference.',
  contract: 'Freeze the visible suite and record bounded behavior claims.',
  implement: 'A restricted builder turn edits the generated app.',
  evaluate: 'Trusted host builds, runs and compares candidate output.',
  decide: 'Trusted gates accept or reject; failures are routed.',
  stopped: 'Run ended; best checkpoint restored and re-verified.',
};

export const CLAIM_LABEL: Record<ClaimStatus, string> = {
  VERIFIED_WITHIN_SCOPE: 'Verified in scope',
  OBSERVED: 'Observed',
  HYPOTHESIS: 'Hypothesis',
  UNKNOWN: 'Unknown',
  CONTRADICTED: 'Contradicted',
  UNRECOGNIZED: 'Unrecognized status',
};

export const OUTCOME_LABEL: Record<CaseOutcome, string> = {
  passed: 'Passed',
  pixel_mismatch: 'Pixel mismatch',
  dimension_mismatch: 'Dimension mismatch',
  missing_output: 'Missing output',
  infrastructure: 'Infrastructure error',
  not_evaluated: 'Not evaluated',
  failed_unclassified: 'Failed (unclassified)',
  unknown: 'Unknown',
};

export const DECISION_LABEL: Record<Decision, string> = {
  accepted: 'Accepted',
  rejected: 'Rejected',
  failed: 'Failed · no evaluation',
  pending: 'Pending',
  unknown: 'Unknown',
};

const METRIC_LABEL: Record<string, string> = {
  rgb_mae: 'RGB mean error',
  rgb_fraction_within_tolerance: 'Pixels within RGB tolerance',
  alpha_mae: 'Alpha mean error',
  alpha_max: 'Alpha max error',
  alpha_fraction_within_tolerance: 'Pixels within alpha tolerance',
  rgb_max: 'RGB max error',
};

export interface ParsedReason { region: string; metric: string; label: string; value: number; limit: number; comparator: string; raw: string }

/** Parses evaluator reasons such as "center: rgb_mae=3.81 violates rgb_mean_max=1". */
export function parseReason(raw: string, defaultRegion = 'full_image'): ParsedReason | null {
  const m = /^(?:([\w-]+):\s*)?([\w]+)=([-\d.e+]+)\s+violates\s+([\w]+)=([-\d.e+]+)$/.exec(raw.trim());
  if (!m) return null;
  const isMin = m[4].endsWith('_min');
  return {
    region: m[1] ?? defaultRegion,
    metric: m[2],
    label: METRIC_LABEL[m[2]] ?? humanize(m[2]),
    value: Number(m[3]),
    limit: Number(m[5]),
    comparator: isMin ? '<' : '>',
    raw,
  };
}

export function violated(reasons: string[], region: string, metric: string): boolean {
  return reasons.some((r) => {
    const p = parseReason(r);
    return p !== null && p.region === region && p.metric === metric;
  });
}
