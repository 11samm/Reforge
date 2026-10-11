import type { Candidate, Decision, Tri } from '../data/normalize.ts';

export interface CandidateAt {
  c: Candidate;
  evaluated: boolean;
  decided: boolean;
  decision: Decision;
  gate: (v: Tri) => Tri | 'pending';
  baselineGate: Tri | 'pending';
  stage: string;
}

export function decisionNote(c: Candidate): string | null {
  const reason = c.reason ? c.reason.replace(/[_-]+/g, ' ') : null;
  if (c.decision === 'failed' && c.errorType) return [c.errorType === 'TimeoutError' ? 'Timeout' : c.errorType, reason].filter(Boolean).join(' · ');
  return reason;
}

/** Candidate state as it was known at replay time t. */
export function candidateAt(c: Candidate, t: number): CandidateAt {
  const evaluated = c.evaluatedAt !== null && c.evaluatedAt <= t;
  const decided = c.decidedAt !== null && c.decidedAt <= t;
  const decision: Decision = decided ? c.decision : c.decision === 'unknown' ? 'unknown' : 'pending';
  const stage = decided
    ? c.decision === 'failed' ? 'Stopped before evaluation' : 'Decided'
    : evaluated ? 'Awaiting decision' : c.decision === 'pending' && c.decidedAt === null && c.evaluatedAt === null ? 'No outcome recorded' : 'Builder turn in progress';
  const gate = (v: Tri): Tri | 'pending' => (evaluated || decided ? v : 'pending');
  const baselineGate = c.baselineAt !== null && c.baselineAt <= t ? c.gates.baseline : gate(c.gates.baseline);
  return { c, evaluated, decided, decision, gate, baselineGate, stage };
}
