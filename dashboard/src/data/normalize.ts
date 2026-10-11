import type {
  BundleBaseline, BundleCandidate, BundleCase, BundleClaim, BundleEvent, BundleExperiment, BundleMetrics,
  BundleTelemetry, RunBundleV1,
} from './bundle.ts';

export const PHASES = ['observe', 'experiment', 'contract', 'implement', 'evaluate', 'decide'] as const;
export type Phase = (typeof PHASES)[number] | 'stopped' | 'not_started';

export type ProvenanceKind = 'recorded' | 'synthetic' | 'live' | 'unknown';
export type ClaimStatus = 'VERIFIED_WITHIN_SCOPE' | 'OBSERVED' | 'HYPOTHESIS' | 'UNKNOWN' | 'CONTRADICTED' | 'UNRECOGNIZED';
export type CaseOutcome =
  | 'passed' | 'pixel_mismatch' | 'dimension_mismatch' | 'missing_output' | 'infrastructure'
  | 'not_evaluated' | 'failed_unclassified' | 'unknown';
export type Decision = 'accepted' | 'rejected' | 'failed' | 'pending' | 'unknown';
export type Tri = boolean | null;
export type Tone = 'neutral' | 'good' | 'bad' | 'warn' | 'info';

const KNOWN_CLAIM_STATUSES: ClaimStatus[] = ['VERIFIED_WITHIN_SCOPE', 'OBSERVED', 'HYPOTHESIS', 'UNKNOWN', 'CONTRADICTED'];

export interface Metrics {
  pixelCount: number | null;
  rgbMae: number | null;
  rgbMaePerChannel: number[] | null;
  rgbMax: number | null;
  alphaMae: number | null;
  alphaMax: number | null;
  rgbWithinTolerance: number | null;
  alphaWithinTolerance: number | null;
  differentPixels: number | null;
}

export interface Region {
  name: string;
  box: [number, number, number, number] | null;
  passed: Tri;
  metrics: Metrics | null;
  reasons: string[];
}

export interface CaseImages {
  input: string | null;
  reference: string | null;
  candidate: string | null;
  rgbDifference: string | null;
  alphaDifference: string | null;
}

export interface CaseResult {
  id: string;
  outcome: CaseOutcome;
  rawStatus: string | null;
  rawClassification: string | null;
  percentage: number | null;
  source: string | null;
  dimensionsEqual: Tri;
  metrics: Metrics | null;
  regions: Region[];
  reasons: string[];
  images: CaseImages;
}

export interface Baseline {
  label: string;
  status: string | null;
  classification: string | null;
  shellError: string | null;
  cases: CaseResult[];
}

export interface Invocation {
  invocation: string;
  role: 'planner' | 'contract' | 'route' | 'builder' | 'other';
  recorded: boolean;
  model: string | null;
  effort: string | null;
  status: string | null;
  completion: string | null;
  elapsedSeconds: number | null;
  error: string | null;
  usage: {
    total: number | null; input: number | null; cachedInput: number | null; output: number | null; reasoningOutput: number | null;
  } | null;
  conciseOutput: string | null;
  revealedAt: number | null;
}

export interface Routing {
  t: number;
  classification: string | null;
  nextAction: string | null;
  explanation: string | null;
  evidenceIds: string[];
  trustedAcceptance: Tri;
}

export interface Candidate {
  id: string;
  index: number;
  revealedAt: number;
  evaluatedAt: number | null;
  /** Time of this candidate's baseline-regression event, which precedes its evaluation event. */
  baselineAt: number | null;
  decidedAt: number | null;
  decision: Decision;
  reason: string | null;
  error: string | null;
  errorType: string | null;
  gates: { build: Tri; independent: Tri; ui: Tri; baseline: Tri };
  cases: CaseResult[];
  passedCount: number;
  evaluatedCount: number;
  suiteCaseCount: number;
  baseline: Baseline | null;
  builder: Invocation | null;
  routing: Routing | null;
  notes: Annotation[];
}

export interface Experiment {
  id: string;
  question: string | null;
  hypotheses: string[];
  predictions: string[];
  purpose: string | null;
  inputKind: string | null;
  inputSize: string | null;
  inputDefinition: string | null;
  requested: number | null;
  accepted: number | null;
  percentageMatches: Tri;
  status: string | null;
  originalImportConfirmed: Tri;
  images: { input: string | null; reference: string | null };
  revealedAt: number | null;
  observedAt: number | null;
}

export interface Claim {
  id: string;
  statement: string;
  status: ClaimStatus;
  rawStatus: string | null;
  scope: string | null;
  setup: string | null;
  domain: string | null;
  supporting: string[];
  contradicting: string[];
  alternatives: string[];
  unresolved: string[];
  verificationCases: string[];
  revealedAt: number | null;
}

export interface TimelineEvent {
  seq: number;
  t: number;
  kind: string;
  phase: Phase | null;
  title: string;
  detail: string | null;
  refId: string | null;
  tone: Tone;
  budget: { remainingSeconds: number | null; experimentsRemaining: number | null; candidatesRemaining: number | null };
  currentQuestion: string | null;
}

export interface Annotation { target: string; text: string; source: string | null }

export interface SuiteCase {
  id: string;
  source: string | null;
  percentage: number | null;
  regions: Record<string, [number, number, number, number]>;
  images: { input: string | null; reference: string | null };
}

export interface Run {
  bundleId: string;
  provenance: ProvenanceKind;
  provenanceSource: string | null;
  provenanceNote: string | null;
  exportedAt: string | null;
  schemaVersion: number | null;
  warnings: string[];
  id: string;
  operation: string;
  target: { name: string | null; version: string | null; build: string | null; url: string | null };
  scope: string[];
  budget: { runSeconds: number | null; reserveSeconds: number | null; candidates: number | null; experiments: number | null; percentageRange: string | null };
  outcome: {
    status: 'accepted' | 'unresolved' | 'incomplete' | 'failed' | 'unknown';
    rawStatus: string | null;
    stopReason: string | null;
    finalBaselinePass: Tri;
    finalBuild: string | null;
    firstAcceptance: string | null;
    improvements: number;
    stopped: boolean;
  };
  duration: number;
  timeline: TimelineEvent[];
  experiments: Experiment[];
  suite: { id: string | null; sha256: string | null; policy: Record<string, unknown> | null; cases: SuiteCase[] };
  contractDecision: string | null;
  claims: Claim[];
  candidates: Candidate[];
  baselines: Baseline[];
  telemetry: Invocation[];
  telemetryIncluded: boolean;
  annotations: Annotation[];
}

// ------------------------------------------------------------------ helpers
const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);
const str = (v: unknown): string | null => (typeof v === 'string' && v.trim() !== '' ? v : null);
const bool = (v: unknown): Tri => (typeof v === 'boolean' ? v : null);
const strs = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : []);
const obj = (v: unknown): Record<string, unknown> | null =>
  v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : null;

const SAFE_ARTIFACT = /^[A-Za-z0-9][A-Za-z0-9._\-/]*$/;

/** Resolve a bundle-relative artifact path; rejects absolute, parent-relative or scheme paths. */
export function resolveArtifact(baseUrl: string, path: unknown, warnings?: string[]): string | null {
  if (typeof path !== 'string' || path === '') return null;
  if (!SAFE_ARTIFACT.test(path) || path.split('/').includes('..')) {
    warnings?.push(`Rejected unsafe artifact path "${path.slice(0, 80)}"`);
    return null;
  }
  return `${baseUrl.replace(/\/?$/, '/')}${path}`;
}

function metrics(m: BundleMetrics | null | undefined): Metrics | null {
  if (!m || typeof m !== 'object') return null;
  return {
    pixelCount: num(m.pixel_count),
    rgbMae: num(m.rgb_mae),
    rgbMaePerChannel: Array.isArray(m.rgb_mae_per_channel) ? m.rgb_mae_per_channel.map((x) => num(x) ?? NaN) : null,
    rgbMax: num(m.rgb_max),
    alphaMae: num(m.alpha_mae),
    alphaMax: num(m.alpha_max),
    rgbWithinTolerance: num(m.rgb_fraction_within_tolerance),
    alphaWithinTolerance: num(m.alpha_fraction_within_tolerance),
    differentPixels: num(m.different_pixels),
  };
}

function box(v: unknown): [number, number, number, number] | null {
  return Array.isArray(v) && v.length === 4 && v.every((x) => typeof x === 'number') ? (v as [number, number, number, number]) : null;
}

/** Classify a case so that "no output" is never confused with "output compared and failed". */
export function caseOutcome(status: string | null, classification: string | null, hasMetrics: boolean): CaseOutcome {
  const c = classification?.toLowerCase() ?? '';
  const s = status?.toLowerCase() ?? '';
  if (s === 'passed' || s === 'pass') return 'passed';
  if (c.includes('missing')) return 'missing_output';
  if (c.includes('dimension')) return 'dimension_mismatch';
  if (c.includes('infrastructure') || c.includes('procedure')) return 'infrastructure';
  if (c.includes('pixel') || c.includes('mismatch')) return 'pixel_mismatch';
  if (s === 'failed' || s === 'fail') return hasMetrics ? 'pixel_mismatch' : 'failed_unclassified';
  if (s === 'not_evaluated' || s === 'skipped') return 'not_evaluated';
  return 'unknown';
}

export function claimStatus(raw: unknown): ClaimStatus {
  const s = typeof raw === 'string' ? raw.trim().toUpperCase() : '';
  return (KNOWN_CLAIM_STATUSES as string[]).includes(s) ? (s as ClaimStatus) : 'UNRECOGNIZED';
}

function invocationRole(name: string): Invocation['role'] {
  if (name.startsWith('builder')) return 'builder';
  if (name.startsWith('contract')) return 'contract';
  if (name.startsWith('route')) return 'route';
  if (name.startsWith('planner')) return 'planner';
  return 'other';
}

export function eventPhase(e: BundleEvent): Phase | null {
  switch (e.event) {
    case 'checkpoint': return 'observe';
    case 'baseline':
      if (e.label === 'initial') return 'observe';
      if (e.label === 'final') return 'stopped';
      return 'evaluate';
    case 'experiment': case 'evidence': return 'experiment';
    case 'suite_frozen': case 'suite_adopted': case 'suite_expanded': case 'claim_update': case 'contract_alignment': return 'contract';
    case 'candidate': return 'implement';
    case 'evaluation': case 'resume_base_evaluated': return 'evaluate';
    case 'acceptance': case 'rejection': case 'failure_routing': case 'experimental_base_updated': return 'decide';
    case 'failure': return typeof e.id === 'string' ? 'decide' : 'stopped';
    case 'restore': case 'stop': return 'stopped';
    default: return null;
  }
}

function fmtCases(cases: unknown): string {
  if (!Array.isArray(cases)) return 'no case results';
  if (cases.length === 0) return 'no blur output (unscored)';
  const passed = cases.filter((c) => obj(c)?.status === 'passed').length;
  return `${passed}/${cases.length} cases passed`;
}

function describe(e: BundleEvent): { title: string; detail: string | null; tone: Tone; refId: string | null } {
  const id = str(e.id) ?? str(e.label);
  const err = obj(e.error);
  switch (e.event) {
    case 'checkpoint': return { title: `Checkpoint saved · ${str(e.state) ?? 'unnamed'}`, detail: null, tone: 'neutral', refId: null };
    case 'baseline': {
      const ok = e.status === 'passed';
      return { title: `Baseline ${str(e.label) ?? ''} ${ok ? 'passed' : str(e.status) ?? 'unknown'}`, detail: str(e.classification), tone: ok ? 'good' : 'bad', refId: str(e.label) };
    }
    case 'experiment': {
      const plan = obj(e.plan);
      return { title: `Experiment ${id ?? '?'} planned · Percentage ${num(plan?.percentage) ?? '?'}`, detail: str(e.current_question) ?? str(plan?.question), tone: 'info', refId: id };
    }
    case 'evidence':
      return { title: `Reference output observed · ${id ?? '?'}`, detail: `Requested ${num(e.requested) ?? '?'} · accepted ${num(e.accepted) ?? '?'}`, tone: 'neutral', refId: id };
    case 'suite_frozen':
      return { title: `Suite frozen · ${id ?? '?'}`, detail: `${strs(e.case_ids).length || '?'} cases, policy ${str(obj(e.policy)?.id) ?? 'unknown'}`, tone: 'neutral', refId: id };
    case 'claim_update':
      return { title: `Contract updated · ${Array.isArray(e.claims) ? e.claims.length : '?'} claims`, detail: str(e.decision), tone: 'info', refId: null };
    case 'candidate': return { title: `Builder turn started · ${id ?? '?'}`, detail: null, tone: 'info', refId: id };
    case 'evaluation':
      return { title: `Evaluated ${id ?? '?'} · ${fmtCases(e.cases)}`, detail: err ? `${str(err.type) ?? 'Error'}: ${str(err.message) ?? ''}` : null, tone: err ? 'warn' : 'neutral', refId: id };
    case 'rejection': return { title: `Rejected ${id ?? '?'}`, detail: str(e.reason), tone: 'bad', refId: id };
    case 'acceptance': return { title: `Accepted ${id ?? '?'}`, detail: str(e.reason), tone: 'good', refId: id };
    case 'failure_routing': {
      const s = obj(e.suggestion);
      return { title: `Failure routed → ${str(s?.next_action) ?? '?'}`, detail: str(s?.classification), tone: 'warn', refId: null };
    }
    case 'failure':
      return { title: `Failure${id ? ` · ${id}` : ''} · ${str(e.classification) ?? 'unclassified'}`, detail: err ? `${str(err.type) ?? 'Error'}: ${str(err.message) ?? ''}` : null, tone: 'bad', refId: id };
    case 'restore': return { title: 'Restored best checkpoint', detail: e.preserved_failure_records ? 'Failure records preserved' : null, tone: 'neutral', refId: null };
    case 'stop': return { title: `Stopped · ${str(e.reason) ?? 'unknown reason'}`, detail: `Status: ${str(e.status) ?? 'unknown'}`, tone: e.status === 'accepted' ? 'good' : 'bad', refId: null };
    default: return { title: `Event: ${str(e.event) ?? 'unnamed'}`, detail: 'Not interpreted by this dashboard version', tone: 'neutral', refId: id };
  }
}

function caseFrom(c: BundleCase, base: string, warnings: string[], suite: Map<string, SuiteCase>): CaseResult {
  const id = str(c.case_id) ?? 'unknown-case';
  const sc = suite.get(id);
  const m = metrics(c.metrics);
  const regions: Region[] = Object.entries(c.regions ?? {}).map(([name, r]) => ({
    name,
    box: box(r?.box),
    passed: bool(r?.passed),
    metrics: metrics(r?.metrics),
    reasons: strs(r?.reasons),
  }));
  return {
    id,
    outcome: caseOutcome(str(c.status), str(c.classification), m !== null),
    rawStatus: str(c.status),
    rawClassification: str(c.classification),
    percentage: sc?.percentage ?? null,
    source: sc?.source ?? null,
    dimensionsEqual: bool(c.dimensions_equal),
    metrics: m,
    regions,
    reasons: strs(c.reasons),
    images: {
      input: sc?.images.input ?? null,
      reference: sc?.images.reference ?? null,
      candidate: resolveArtifact(base, c.artifacts?.candidate, warnings),
      rgbDifference: resolveArtifact(base, c.artifacts?.rgb_difference, warnings),
      alphaDifference: resolveArtifact(base, c.artifacts?.alpha_difference, warnings),
    },
  };
}

function baselineFrom(b: BundleBaseline, base: string, warnings: string[]): Baseline {
  return {
    label: str(b.label) ?? 'unlabeled',
    status: str(b.status),
    classification: str(b.classification),
    shellError: str(b.shell_error),
    cases: (b.cases ?? []).map((c) => caseFrom(c, base, warnings, new Map())),
  };
}

function telemetryFrom(t: BundleTelemetry): Invocation {
  const name = str(t.invocation) ?? 'unknown';
  const u = t.usage;
  return {
    invocation: name,
    role: invocationRole(name),
    recorded: t.record_present !== false,
    model: str(t.model),
    effort: str(t.effort),
    status: str(t.status),
    completion: str(t.completion_status),
    elapsedSeconds: num(t.elapsed_seconds),
    error: t.error ? [str(t.error.type), str(t.error.message)].filter(Boolean).join(': ') || null : null,
    usage: u ? {
      total: num(u.total_tokens), input: num(u.input_tokens), cachedInput: num(u.cached_input_tokens),
      output: num(u.output_tokens), reasoningOutput: num(u.reasoning_output_tokens),
    } : null,
    conciseOutput: str(t.concise_output),
    revealedAt: null,
  };
}

// ------------------------------------------------------------------ main
export function normalizeRun(input: unknown, baseUrl: string, bundleId = 'run'): Run {
  const warnings: string[] = [];
  const raw = (obj(input) ?? {}) as RunBundleV1;
  if (!obj(input)) warnings.push('Bundle is not a JSON object; nothing could be read.');

  const schemaVersion = num(raw.schema_version);
  if (raw.schema !== undefined && raw.schema !== 'reforge.run-bundle') warnings.push(`Unrecognized schema "${String(raw.schema)}"; reading known fields only.`);
  if (schemaVersion === null) warnings.push('No schema_version; treated as legacy events-only bundle.');
  else if (schemaVersion > 1) warnings.push(`schema_version ${schemaVersion} is newer than this dashboard (1); unknown fields ignored.`);

  const kindRaw = str(raw.provenance?.kind);
  const provenance: ProvenanceKind = kindRaw === 'recorded' || kindRaw === 'synthetic' || kindRaw === 'live' ? kindRaw : 'unknown';
  if (provenance === 'unknown') warnings.push('Provenance not declared; results must not be presented as project results.');

  // Events, sorted and de-duplicated by sequence when present.
  const events: BundleEvent[] = (Array.isArray(raw.events) ? raw.events : [])
    .filter((e): e is BundleEvent => obj(e) !== null)
    .map((e, i) => ({ ...e, sequence: num(e.sequence) ?? i + 1, elapsed_seconds: num(e.elapsed_seconds) ?? 0 }))
    .sort((a, b) => (a.elapsed_seconds! - b.elapsed_seconds!) || (a.sequence! - b.sequence!));
  if (events.length === 0) warnings.push('No events recorded.');
  const lastEventAt = events.length ? events[events.length - 1].elapsed_seconds! : 0;
  const firstAt = (pred: (e: BundleEvent) => boolean) => events.find(pred)?.elapsed_seconds ?? null;

  const timeline: TimelineEvent[] = events.map((e) => {
    const d = describe(e);
    const b = obj(e.budget);
    return {
      seq: e.sequence!, t: e.elapsed_seconds!, kind: str(e.event) ?? 'unknown', phase: eventPhase(e), ...d,
      budget: {
        remainingSeconds: num(b?.remaining_seconds),
        experimentsRemaining: num(b?.fresh_experiments_remaining),
        candidatesRemaining: num(b?.candidates_remaining),
      },
      currentQuestion: str(e.current_question),
    };
  });

  // Suite cases (reference + input images shared by every candidate).
  const suiteCases: SuiteCase[] = (raw.suite?.cases ?? []).map((c) => ({
    id: str(c.id) ?? 'unknown-case',
    source: str(c.source),
    percentage: num(c.percentage),
    regions: Object.fromEntries(Object.entries(c.regions ?? {}).map(([k, v]) => [k, box(v)]).filter((x) => x[1])) as Record<string, [number, number, number, number]>,
    images: { input: resolveArtifact(baseUrl, c.artifacts?.input, warnings), reference: resolveArtifact(baseUrl, c.artifacts?.reference, warnings) },
  }));
  const frozen = events.find((e) => e.event === 'suite_frozen');
  if (suiteCases.length === 0 && frozen) {
    for (const id of strs(frozen.case_ids)) suiteCases.push({ id, source: null, percentage: null, regions: {}, images: { input: null, reference: null } });
  }
  const suiteMap = new Map(suiteCases.map((c) => [c.id, c]));

  // Experiments: bundle section first, events as fallback.
  const expSource: BundleExperiment[] = Array.isArray(raw.experiments) && raw.experiments.length
    ? raw.experiments
    : events.filter((e) => e.event === 'experiment').map((e) => ({ id: str(e.id) ?? undefined, plan: obj(e.plan) as BundleExperiment['plan'] }));
  const experiments: Experiment[] = expSource.map((x) => {
    const id = str(x.id) ?? 'unknown-experiment';
    const ev = events.find((e) => e.event === 'evidence' && e.id === id);
    const requested = num(x.percentage_requested) ?? num(ev?.requested) ?? num(x.plan?.percentage);
    const accepted = num(x.percentage_accepted) ?? num(ev?.accepted);
    const spec = x.input_spec ?? x.plan?.input ?? null;
    return {
      id,
      question: str(x.plan?.question),
      hypotheses: strs(x.plan?.hypotheses),
      predictions: strs(x.plan?.predictions),
      purpose: str(x.plan?.usefulness),
      inputKind: str(spec?.kind),
      inputSize: num(spec?.width) !== null && num(spec?.height) !== null ? `${spec!.width}×${spec!.height}` : null,
      inputDefinition: str((x.input_spec ?? {}).definition),
      requested,
      accepted,
      percentageMatches: requested !== null && accepted !== null ? requested === accepted : null,
      status: str(x.status) ?? str(ev?.status),
      originalImportConfirmed: bool(x.original_import_confirmed),
      images: {
        input: resolveArtifact(baseUrl, x.artifacts?.input, warnings) ?? suiteMap.get(id)?.images.input ?? null,
        reference: resolveArtifact(baseUrl, x.artifacts?.reference_output, warnings) ?? suiteMap.get(id)?.images.reference ?? null,
      },
      revealedAt: firstAt((e) => e.event === 'experiment' && e.id === id),
      observedAt: ev ? ev.elapsed_seconds! : null,
    };
  });

  // Claims: full contract preferred; claim_update events otherwise.
  const claimUpdate = [...events].reverse().find((e) => e.event === 'claim_update');
  const claimAt = firstAt((e) => e.event === 'claim_update');
  const claimSource: BundleClaim[] = raw.contract?.claims?.length ? raw.contract.claims : (Array.isArray(claimUpdate?.claims) ? claimUpdate!.claims as BundleClaim[] : []);
  const claims: Claim[] = claimSource.map((c) => {
    const d = c.parameter_domain;
    return {
      id: str(c.id) ?? 'unnamed-claim',
      statement: str(c.statement) ?? '(no statement recorded)',
      status: claimStatus(c.status),
      rawStatus: str(c.status),
      scope: str(c.scope),
      setup: str(c.setup),
      domain: d && (num(d.min) !== null || num(d.max) !== null)
        ? (d.min === d.max ? `Percentage ${d.min}` : `Percentage ${d.min ?? '?'}–${d.max ?? '?'}`) : null,
      supporting: strs(c.supporting_evidence),
      contradicting: strs(c.contradicting_evidence),
      alternatives: strs(c.alternatives),
      unresolved: strs(c.unresolved),
      verificationCases: strs(c.verification_cases),
      revealedAt: claimAt,
    };
  });
  for (const c of claims) if (c.status === 'UNRECOGNIZED') warnings.push(`Claim ${c.id} has unrecognized status "${c.rawStatus ?? 'missing'}".`);

  // Telemetry.
  const telemetryIncluded = Array.isArray(raw.telemetry);
  const telemetry: Invocation[] = (raw.telemetry ?? []).map(telemetryFrom);
  const routingEvents = events.filter((e) => e.event === 'failure_routing');
  for (const t of telemetry) {
    const n = Number(/(\d+)$/.exec(t.invocation)?.[1] ?? NaN);
    if (t.role === 'planner') t.revealedAt = firstAt((e) => e.event === 'experiment');
    else if (t.role === 'contract') t.revealedAt = claimAt;
    else if (t.role === 'route' && Number.isFinite(n)) t.revealedAt = routingEvents[n - 1]?.elapsed_seconds ?? null;
  }

  const baselines = (raw.baselines ?? []).map((b) => baselineFrom(b, baseUrl, warnings));
  const annotations: Annotation[] = (raw.annotations ?? [])
    .filter((a) => str(a?.target) && str(a?.text))
    .map((a) => ({ target: a.target!, text: a.text!, source: str(a.source) }));

  // Candidates: one per candidate event, enriched by the candidates section.
  const candIds = [...new Set([
    ...events.filter((e) => e.event === 'candidate').map((e) => str(e.id)).filter((x): x is string => !!x),
    ...(raw.candidates ?? []).map((c) => str(c.id)).filter((x): x is string => !!x),
  ])];
  const candidates: Candidate[] = candIds.map((id, i) => {
    const bc: BundleCandidate = (raw.candidates ?? []).find((c) => c.id === id) ?? {};
    const startEv = events.find((e) => e.event === 'candidate' && e.id === id);
    const evalEv = events.find((e) => e.event === 'evaluation' && e.label === id);
    const acceptEv = events.find((e) => e.event === 'acceptance' && e.id === id);
    const rejectEv = events.find((e) => e.event === 'rejection' && e.id === id);
    const failEv = events.find((e) => e.event === 'failure' && e.id === id);
    const nextStart = events.find((e) => e.event === 'candidate' && (e.elapsed_seconds ?? 0) > (startEv?.elapsed_seconds ?? 0));
    const routeEv = routingEvents.find((e) => (e.elapsed_seconds ?? 0) >= (rejectEv?.elapsed_seconds ?? evalEv?.elapsed_seconds ?? Infinity)
      && (!nextStart || (e.elapsed_seconds ?? 0) <= (nextStart.elapsed_seconds ?? 0)));

    let decision: Decision = 'pending';
    if (acceptEv || bc.accepted === true) decision = 'accepted';
    else if (rejectEv || bc.status === 'rejected') decision = 'rejected';
    else if (failEv || bc.status === 'failed') decision = 'failed';
    else if (bc.status && !['running', 'pending'].includes(bc.status)) decision = 'unknown';

    const rawCases: BundleCase[] = bc.cases?.length ? bc.cases : (Array.isArray(evalEv?.cases) ? evalEv!.cases as BundleCase[] : []);
    let cases = rawCases.map((c) => caseFrom(c, baseUrl, warnings, suiteMap));
    if (cases.length === 0) {
      cases = suiteCases.map((sc) => ({
        id: sc.id, outcome: 'not_evaluated' as CaseOutcome, rawStatus: null, rawClassification: null,
        percentage: sc.percentage, source: sc.source, dimensionsEqual: null, metrics: null, regions: [], reasons: [],
        images: { input: sc.images.input, reference: sc.images.reference, candidate: null, rgbDifference: null, alphaDifference: null },
      }));
    }
    const baselineLabel = bc.baseline_label ?? `${id}-gates`;
    const baselineEv = events.find((e) => e.event === 'baseline' && e.label === baselineLabel);
    const err = bc.error ?? obj(failEv?.error) ?? obj(evalEv?.error);
    const builderName = bc.builder_invocation ?? `builder-${i + 1}`;
    let builder = telemetry.find((t) => t.invocation === builderName) ?? null;
    if (!builder && telemetryIncluded) {
      builder = { ...telemetryFrom({ invocation: builderName, record_present: false }) };
      telemetry.push(builder);
    }
    const decidedAt = (acceptEv ?? rejectEv ?? failEv)?.elapsed_seconds
      ?? (decision !== 'pending' ? evalEv?.elapsed_seconds ?? lastEventAt : null);
    if (builder) builder.revealedAt = decidedAt ?? evalEv?.elapsed_seconds ?? null;
    const evaluated = cases.filter((c) => c.outcome !== 'not_evaluated');
    const routeSuggestion = obj(routeEv?.suggestion);
    return {
      id,
      index: i + 1,
      revealedAt: startEv?.elapsed_seconds ?? num(bc.started_seconds) ?? 0,
      evaluatedAt: evalEv?.elapsed_seconds ?? null,
      baselineAt: baselineEv?.elapsed_seconds ?? null,
      decidedAt,
      decision,
      reason: str(acceptEv?.reason) ?? str(rejectEv?.reason) ?? str(failEv?.classification) ?? str(bc.reason),
      error: err ? str((err as Record<string, unknown>).message) : null,
      errorType: err ? str((err as Record<string, unknown>).type) : null,
      gates: {
        build: bool(bc.build_valid ?? evalEv?.build_valid),
        independent: bool(bc.independent ?? evalEv?.independent),
        ui: bc.ui_check ? bool(bc.ui_check.rgba_equal) : null,
        baseline: bool(bc.baseline_pass ?? evalEv?.baseline_pass ?? (baselineEv ? baselineEv.status === 'passed' : undefined)),
      },
      cases,
      passedCount: cases.filter((c) => c.outcome === 'passed').length,
      evaluatedCount: evaluated.length,
      suiteCaseCount: suiteCases.length || cases.length,
      baseline: baselines.find((b) => b.label === baselineLabel)
        ?? (baselineEv ? { label: baselineLabel, status: str(baselineEv.status), classification: str(baselineEv.classification), shellError: null, cases: [] } : null),
      builder,
      routing: routeEv ? {
        t: routeEv.elapsed_seconds!,
        classification: str(routeSuggestion?.classification),
        nextAction: str(routeSuggestion?.next_action),
        explanation: str(routeSuggestion?.explanation),
        evidenceIds: strs(routeSuggestion?.evidence_ids),
        trustedAcceptance: bool(routeEv.trusted_acceptance),
      } : null,
      notes: annotations.filter((a) => a.target === id),
    };
  });

  // Outcome.
  const stopEv = [...events].reverse().find((e) => e.event === 'stop');
  const rawStatus = str(raw.run?.status) ?? str(stopEv?.status);
  const anyAccepted = candidates.some((c) => c.decision === 'accepted');
  let status: Run['outcome']['status'];
  if (!stopEv && !raw.run?.status) status = 'incomplete';
  else if (rawStatus === 'accepted' || rawStatus === 'improved') status = anyAccepted ? 'accepted' : 'unknown';
  else if (rawStatus === 'unresolved') status = 'unresolved';
  else if (rawStatus === 'failed' || rawStatus === 'error') status = 'failed';
  else status = 'unknown';
  if ((rawStatus === 'accepted' || rawStatus === 'improved') && !anyAccepted) warnings.push('Run claims acceptance but no candidate acceptance is recorded; shown as unknown.');

  const cfg = obj(raw.run?.config);
  const pMin = num(cfg?.percentage_min); const pMax = num(cfg?.percentage_max);

  return {
    bundleId,
    provenance,
    provenanceSource: str(raw.provenance?.source),
    provenanceNote: str(raw.provenance?.note),
    exportedAt: str(raw.provenance?.exported_at),
    schemaVersion,
    warnings,
    id: str(raw.run?.id) ?? bundleId,
    operation: str(raw.run?.operation) ?? 'Unknown operation',
    target: {
      name: str(raw.run?.target?.name), version: str(raw.run?.target?.visible_about_version),
      build: str(raw.run?.target?.build), url: str(raw.run?.target?.url),
    },
    scope: strs(raw.run?.scope),
    budget: {
      runSeconds: num(cfg?.run_seconds), reserveSeconds: num(cfg?.reserve_seconds),
      candidates: num(cfg?.candidates), experiments: num(cfg?.fresh_experiments),
      percentageRange: pMin !== null && pMax !== null ? `${pMin}–${pMax}` : null,
    },
    outcome: {
      status,
      rawStatus,
      stopReason: str(raw.run?.stop_reason) ?? str(stopEv?.reason),
      finalBaselinePass: bool(raw.run?.final_baseline_pass),
      finalBuild: str(raw.run?.final_build_status),
      firstAcceptance: str(raw.run?.first_acceptance),
      improvements: Array.isArray(raw.run?.later_improvements) ? raw.run!.later_improvements!.length : 0,
      stopped: Boolean(stopEv),
    },
    duration: Math.max(num(raw.run?.elapsed_seconds) ?? 0, lastEventAt),
    timeline,
    experiments,
    suite: { id: str(raw.suite?.id) ?? str(frozen?.id), sha256: str(raw.suite?.sha256) ?? str(frozen?.sha256), policy: obj(raw.suite?.policy) ?? obj(frozen?.policy), cases: suiteCases },
    contractDecision: str(raw.contract?.decision) ?? str(claimUpdate?.decision),
    claims,
    candidates,
    baselines,
    telemetry,
    telemetryIncluded,
    annotations,
  };
}

// ------------------------------------------------------------------ replay
export interface Snapshot {
  t: number;
  phase: Phase;
  visited: Set<Phase>;
  remainingSeconds: number | null;
  experimentsRemaining: number | null;
  candidatesRemaining: number | null;
  question: string | null;
  questionAt: number | null;
  activity: TimelineEvent | null;
  stopped: boolean;
  eventCount: number;
}

/** State of the run as known at elapsed time `t` (seconds), derived only from recorded events. */
export function snapshotAt(run: Run, t: number): Snapshot {
  const seen = run.timeline.filter((e) => e.t <= t);
  let phase: Phase = 'not_started';
  const visited = new Set<Phase>();
  let question: string | null = null; let questionAt: number | null = null;
  for (const e of seen) {
    if (e.phase) { phase = e.phase; visited.add(e.phase); }
    if (e.currentQuestion) { question = e.currentQuestion; questionAt = e.t; }
  }
  const last = seen.at(-1) ?? null;
  const stopped = seen.some((e) => e.kind === 'stop');
  const withBudget = [...seen].reverse().find((e) => e.budget.remainingSeconds !== null);
  let remaining: number | null = null;
  if (withBudget) {
    const drift = stopped ? 0 : Math.max(0, t - withBudget.t);
    remaining = Math.max(0, withBudget.budget.remainingSeconds! - drift);
  } else if (run.budget.runSeconds !== null && seen.length === 0) {
    remaining = run.budget.runSeconds;
  }
  const lastCounts = [...seen].reverse().find((e) => e.budget.candidatesRemaining !== null);
  return {
    t,
    phase,
    visited,
    remainingSeconds: remaining,
    experimentsRemaining: lastCounts?.budget.experimentsRemaining ?? run.budget.experiments,
    candidatesRemaining: lastCounts?.budget.candidatesRemaining ?? run.budget.candidates,
    question,
    questionAt,
    activity: last,
    stopped,
    eventCount: seen.length,
  };
}

export function isVisible(revealedAt: number | null, t: number, duration: number): boolean {
  return revealedAt === null ? t >= duration : revealedAt <= t;
}
