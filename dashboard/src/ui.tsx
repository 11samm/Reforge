import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import type { CaseOutcome, ClaimStatus, Decision, Tone, Tri } from './data/normalize.ts';
import { CLAIM_LABEL, DECISION_LABEL, OUTCOME_LABEL } from './format.ts';

const PATHS: Record<string, string> = {
  overview: 'M3 13h8V3H3zm0 8h8v-6H3zm10 0h8V11h-8zm0-18v6h8V3z',
  experiments: 'M9 3v6.5L4 18a2 2 0 0 0 1.7 3h12.6a2 2 0 0 0 1.7-3l-5-8.5V3M8 3h8M7 15h10',
  contract: 'M7 3h7l5 5v13H7zM14 3v5h5M10 13h6M10 17h6',
  candidates: 'M8 6 3 12l5 6M16 6l5 6-5 6M13.5 4l-3 16',
  telemetry: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
  events: 'M12 7v5l3 2M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z',
  play: 'M7 4v16l13-8z',
  pause: 'M6 4h4v16H6zM14 4h4v16h-4z',
  restart: 'M4 4v6h6M4.5 15a8 8 0 1 0 1.9-8.3L4 10',
  end: 'M5 4l10 8-10 8zM17 4h2v16h-2z',
  info: 'M12 8h.01M11 12h1v5h1M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z',
  alert: 'M12 9v4M12 17h.01M10.3 3.9 2 18a2 2 0 0 0 1.7 3h16.6a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z',
  check: 'M5 12l5 5L20 7',
  x: 'M6 6l12 12M18 6 6 18',
  dash: 'M6 12h12',
  clock: 'M12 7v5l3 2M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z',
  link: 'M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1',
  chevron: 'M6 9l6 6 6-6',
  search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM21 21l-5-5',
};

export function Icon({ name, size = 18 }: { name: keyof typeof PATHS | string; size?: number }) {
  return (
    <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={PATHS[name] ?? PATHS.info} />
    </svg>
  );
}

export function Pill({ tone = 'neutral', children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return <span className={`pill pill-${tone}`} title={title}>{children}</span>;
}

const CLAIM_TONE: Record<ClaimStatus, Tone> = {
  VERIFIED_WITHIN_SCOPE: 'good', OBSERVED: 'info', HYPOTHESIS: 'warn', UNKNOWN: 'neutral', CONTRADICTED: 'bad', UNRECOGNIZED: 'neutral',
};
export function ClaimPill({ status, raw }: { status: ClaimStatus; raw: string | null }) {
  return (
    <Pill tone={CLAIM_TONE[status]} title={raw ?? 'no status recorded'}>
      {status === 'UNRECOGNIZED' ? `Unrecognized: ${raw ?? 'missing'}` : CLAIM_LABEL[status]}
    </Pill>
  );
}

const OUTCOME_TONE: Record<CaseOutcome, Tone> = {
  passed: 'good', pixel_mismatch: 'bad', dimension_mismatch: 'bad', missing_output: 'warn', infrastructure: 'warn',
  not_evaluated: 'neutral', failed_unclassified: 'bad', unknown: 'neutral',
};
export function OutcomePill({ outcome }: { outcome: CaseOutcome }) {
  return <Pill tone={OUTCOME_TONE[outcome]}>{OUTCOME_LABEL[outcome]}</Pill>;
}

const DECISION_TONE: Record<Decision, Tone> = { accepted: 'good', rejected: 'bad', failed: 'bad', pending: 'info', unknown: 'neutral' };
export function DecisionPill({ decision }: { decision: Decision }) {
  return <Pill tone={DECISION_TONE[decision]}>{DECISION_LABEL[decision]}</Pill>;
}

export function Gate({ value, label }: { value: Tri | 'pending'; label?: string }) {
  const state = value === 'pending' ? 'pending' : value === true ? 'pass' : value === false ? 'fail' : 'none';
  const text = { pass: 'Pass', fail: 'Fail', none: 'Not recorded', pending: 'Pending' }[state];
  const icon = { pass: 'check', fail: 'x', none: 'dash', pending: 'clock' }[state];
  return (
    <span className={`gate gate-${state}`} title={label ? `${label}: ${text}` : text}>
      <Icon name={icon} size={14} /> {text}
    </span>
  );
}

export function Card({ title, aside, children, className = '' }: { title?: ReactNode; aside?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`card glass ${className}`}>
      {(title || aside) && <header className="card-head"><h3>{title}</h3>{aside}</header>}
      {children}
    </section>
  );
}

export function Empty({ children, tone = 'neutral' }: { children: ReactNode; tone?: Tone }) {
  return <div className={`empty empty-${tone}`}><Icon name={tone === 'warn' || tone === 'bad' ? 'alert' : 'info'} size={16} /> <span>{children}</span></div>;
}

export function EvidenceChip({ id, onOpen }: { id: string; onOpen?: (id: string) => void }) {
  return (
    <button type="button" className="evidence-chip" onClick={() => onOpen?.(id)} title={`Open evidence ${id}`}>
      <Icon name="link" size={12} /> {id}
    </button>
  );
}

type Box = [number, number, number, number];

/** Pixel-exact artifact view. Distinguishes "not recorded" from "listed but failed to load". */
export function PixelImage({ src, alt, missing, regions, showRegions = false, maxWidth = 360 }: {
  src: string | null; alt: string; missing: string; regions?: Record<string, Box>; showRegions?: boolean; maxWidth?: number;
}) {
  const [failed, setFailed] = useState(false);
  const [size, setSize] = useState<{ w: number; h: number } | null>(null);
  useEffect(() => { setFailed(false); setSize(null); }, [src]);
  if (!src) return <div className="pixel-missing" style={{ maxWidth }}><Icon name="dash" /><span>{missing}</span></div>;
  if (failed) return <div className="pixel-missing pixel-broken" style={{ maxWidth }}><Icon name="alert" /><span>Artifact listed in bundle but could not be loaded</span></div>;
  return (
    <div className="pixel-frame checker" style={{ maxWidth }}>
      <img src={src} alt={alt} onError={() => setFailed(true)}
        onLoad={(e) => setSize({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })} />
      {showRegions && size && regions && Object.entries(regions).map(([name, [x0, y0, x1, y1]]) => (
        <div key={name} className={`region region-${name}`} style={{
          left: `${(x0 / size.w) * 100}%`, top: `${(y0 / size.h) * 100}%`,
          width: `${((x1 - x0) / size.w) * 100}%`, height: `${((y1 - y0) / size.h) * 100}%`,
        }}><span>{name}</span></div>
      ))}
      {size && <span className="pixel-size">{size.w}×{size.h}</span>}
    </div>
  );
}

export function Clamp({ children, lines = 3 }: { children: ReactNode; lines?: number }) {
  const [open, setOpen] = useState(false);
  const [overflows, setOverflows] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    if (el && !open) setOverflows(el.scrollHeight > el.clientHeight + 1);
  }, [children, open]);
  return (
    <span className="clamp-wrap">
      <span ref={ref} className={open ? '' : 'clamp-text'} style={{ WebkitLineClamp: lines }}>{children}</span>
      {(overflows || open) && <button type="button" className="link-btn" onClick={() => setOpen((o) => !o)}>{open ? 'Show less' : 'Show more'}</button>}
    </span>
  );
}

export function Segmented<T extends string>({ value, options, onChange, label }: {
  value: T; options: { id: T; label: string; disabled?: boolean }[]; onChange: (v: T) => void; label: string;
}) {
  return (
    <div className="segmented" role="tablist" aria-label={label}>
      {options.map((o) => (
        <button key={o.id} type="button" role="tab" aria-selected={value === o.id} disabled={o.disabled}
          className={value === o.id ? 'active' : ''} onClick={() => onChange(o.id)}>{o.label}</button>
      ))}
    </div>
  );
}
