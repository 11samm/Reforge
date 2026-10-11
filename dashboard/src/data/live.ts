// Live-event ingestion interface. PREPARED ONLY: no harness integration exists
// and nothing in the UI connects to a live source yet. See DATA-CONTRACT.md,
// "Future live integration".
import type { BundleEvent, RunBundleV1 } from './bundle.ts';

export type SourceStatus = 'idle' | 'connecting' | 'open' | 'closed' | 'error';

export interface RunEventSource {
  readonly mode: 'recorded' | 'live';
  /** Receives every event in sequence order; returns an unsubscribe function. */
  subscribe(onEvent: (event: BundleEvent) => void, onStatus?: (status: SourceStatus, detail?: string) => void): () => void;
}

/**
 * Validates one incoming event line before it reaches the normalizer.
 * Returns null for anything that is not a plain event object with a name.
 */
export function parseEventLine(line: string): BundleEvent | null {
  try {
    const value: unknown = JSON.parse(line);
    if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
    const e = value as BundleEvent;
    return typeof e.event === 'string' && e.event.length > 0 && e.event.length <= 80
      && (e.sequence === undefined || (Number.isInteger(e.sequence) && Number(e.sequence) >= 1))
      && (e.elapsed_seconds === undefined || (typeof e.elapsed_seconds === 'number' && Number.isFinite(e.elapsed_seconds) && e.elapsed_seconds >= 0)) ? e : null;
  } catch {
    return null;
  }
}

/** Append live events to a static bundle skeleton so normalizeRun() can be reused unchanged. */
export function appendEvents(bundle: RunBundleV1, events: BundleEvent[]): RunBundleV1 {
  const seen = new Set((bundle.events ?? []).map((e) => e.sequence));
  const fresh = events.filter((e) => {
    if (e.sequence === undefined) return true; // Preserve the original legacy ingestion interface.
    if (seen.has(e.sequence)) return false;
    seen.add(e.sequence); return true;
  });
  const combined = [...(bundle.events ?? []), ...fresh];
  if (combined.every(e => e.sequence !== undefined)) combined.sort((a,b) => a.sequence! - b.sequence!);
  return { ...bundle, events: combined };
}

/**
 * Server-sent-events adapter for a future trusted-host endpoint that emits one
 * sanitized event per `message`. Same-origin URLs only. Untested against the harness.
 */
export class SseRunEventSource implements RunEventSource {
  readonly mode = 'live' as const;
  private readonly url: string;
  constructor(url: string) {
    const parsed = new URL(url, globalThis.location?.href ?? 'http://127.0.0.1/');
    if (globalThis.location && parsed.origin !== globalThis.location.origin) throw new Error('Live source must be same-origin');
    this.url = parsed.toString();
  }
  subscribe(onEvent: (event: BundleEvent) => void, onStatus?: (status: SourceStatus, detail?: string) => void): () => void {
    onStatus?.('connecting');
    const source = new EventSource(this.url);
    source.onopen = () => onStatus?.('open');
    source.onerror = () => onStatus?.('error', 'Live source unavailable');
    source.onmessage = (m) => {
      const e = parseEventLine(String(m.data));
      if (e) onEvent(e);
    };
    return () => { source.close(); onStatus?.('closed'); };
  }
}
