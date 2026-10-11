export interface BrowserSession {
  state: 'unavailable' | 'building' | 'launching' | 'ready' | 'disconnected' | 'hidden';
  session_id?: string; frame: string | null; action?: string; purpose?: string;
  parameters?: Record<string, unknown>; action_started?: number; action_elapsed_seconds?: number; captured_at?: number;
}
export interface LiveSessions {
  job_id: string; mode: 'live'; stage: string; elapsed_seconds: number; activity?: string;
  experiment?: { question?: string; usefulness?: string; input?: unknown; value?: number };
  sessions: { reference: BrowserSession; candidate: BrowserSession };
}
export function parseSessions(raw: unknown, jobId: string): LiveSessions {
  const r = raw as LiveSessions;
  if (!r || r.job_id !== jobId || r.mode !== 'live' || !r.sessions) throw new Error('Live session/job mismatch');
  for (const role of ['reference', 'candidate'] as const) {
    const s = r.sessions[role];
    if (!s || !['unavailable', 'building', 'launching', 'ready', 'disconnected', 'hidden'].includes(s.state)) throw new Error('Invalid browser status');
    if (s.frame !== null && (typeof s.frame !== 'string' || s.frame.length > 2500000 || !/^[A-Za-z0-9+/=]+$/.test(s.frame))) throw new Error('Invalid browser frame');
    // Never present a retained frame as a current connected session.
    if (s.state !== 'ready') s.frame = null;
  }
  return r;
}
