// Input contract for dashboard run bundles. Every field is optional on read:
// the normalizer treats missing data as "not recorded", never as success.
// Human-readable description: ../../DATA-CONTRACT.md

export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };

export interface BundleProvenance {
  kind?: 'recorded' | 'synthetic' | 'live' | string;
  source?: string;
  exported_at?: string;
  exporter?: string;
  note?: string;
}

export interface BundleBudget {
  remaining_seconds?: number;
  fresh_experiments_remaining?: number;
  candidates_remaining?: number;
}

export interface BundleEvent {
  sequence?: number;
  event?: string;
  elapsed_seconds?: number;
  budget?: BundleBudget;
  [key: string]: unknown;
}

export interface BundleMetrics {
  pixel_count?: number;
  rgb_mae?: number;
  rgb_mae_per_channel?: number[];
  rgb_max?: number;
  alpha_mae?: number;
  alpha_max?: number;
  rgb_fraction_within_tolerance?: number;
  alpha_fraction_within_tolerance?: number;
  different_pixels?: number;
}

export interface BundleRegion {
  box?: number[] | null;
  passed?: boolean | null;
  metrics?: BundleMetrics | null;
  reasons?: string[];
}

export interface BundleCase {
  case_id?: string;
  status?: string | null;
  classification?: string | null;
  dimensions_equal?: boolean | null;
  dimensions?: { reference?: number[]; candidate?: number[] } | null;
  metrics?: BundleMetrics | null;
  regions?: Record<string, BundleRegion>;
  reasons?: string[];
  artifacts?: { candidate?: string | null; rgb_difference?: string | null; alpha_difference?: string | null };
}

export interface BundleCandidate {
  id?: string;
  status?: string | null;
  accepted?: boolean | null;
  reason?: string | null;
  started_seconds?: number | null;
  decided_seconds?: number | null;
  error?: { type?: string | null; message?: string | null } | null;
  build_valid?: boolean | null;
  independent?: boolean | null;
  baseline_pass?: boolean | null;
  evaluator_suspect?: boolean | null;
  ui_check?: { case_id?: string | null; rgba_equal?: boolean | null; external_requests?: number | null; browser_errors?: number | null } | null;
  execution?: { reference_browser_closed?: boolean | null; input_only_batch_cases?: number | null; node_permission_guard?: boolean | null; network_guard?: string | null } | null;
  builder_invocation?: string;
  baseline_label?: string;
  cases?: BundleCase[];
}

export interface BundleBaseline {
  label?: string;
  suite_id?: string | null;
  status?: string | null;
  classification?: string | null;
  shell_status?: string | null;
  shell_error?: string | null;
  cases?: BundleCase[];
}

export interface BundleExperiment {
  id?: string;
  plan?: {
    question?: string;
    hypotheses?: string[];
    predictions?: string[];
    usefulness?: string;
    input?: { kind?: string; width?: number; height?: number };
    percentage?: number;
  } | null;
  input_spec?: { kind?: string; width?: number; height?: number; definition?: string } | null;
  percentage_requested?: number | null;
  percentage_accepted?: number | null;
  status?: string | null;
  original_import_confirmed?: boolean | null;
  target?: Record<string, unknown> | null;
  artifacts?: { input?: string | null; reference_output?: string | null };
}

export interface BundleClaim {
  id?: string;
  statement?: string;
  status?: string;
  target_version?: string;
  setup?: string;
  parameter_domain?: { min?: number; max?: number };
  scope?: string;
  supporting_evidence?: string[];
  contradicting_evidence?: string[];
  alternatives?: string[];
  unresolved?: string[];
  verification_cases?: string[];
}

export interface BundleSuiteCase {
  id?: string;
  source?: string;
  percentage?: number | null;
  regions?: Record<string, number[]>;
  artifacts?: { input?: string | null; reference?: string | null };
}

export interface BundleTelemetry {
  available_at?: number;
  invocation?: string;
  record_present?: boolean;
  model?: string | null;
  effort?: string | null;
  status?: string | null;
  completion_status?: string | null;
  elapsed_seconds?: number | null;
  error?: { type?: string | null; message?: string | null } | null;
  usage?: {
    total_tokens?: number | null;
    input_tokens?: number | null;
    cached_input_tokens?: number | null;
    output_tokens?: number | null;
    reasoning_output_tokens?: number | null;
  } | null;
  concise_output?: string | null;
}

export interface BundleRecording {
  final: { available_at: number; summary?: Json; suite: BundleSuiteCase[]; cases: BundleCase[] };
  evidence: { label: string; available_at: number; path: string }[];
  missing_evidence: string[];
}

// Historical name retained for callers; v2 adds recording-only evidence.
export interface RunBundleV1 {
  recording?: BundleRecording;
  schema?: string;
  schema_version?: number;
  provenance?: BundleProvenance;
  run?: {
    id?: string;
    operation?: string;
    target?: { name?: string; url?: string; visible_about_version?: string; build?: string } | null;
    scope?: string[];
    config?: Record<string, unknown> | null;
    status?: string | null;
    stop_reason?: string | null;
    elapsed_seconds?: number | null;
    first_acceptance?: string | null;
    later_improvements?: unknown[];
    final_build_status?: string | null;
    final_baseline_pass?: boolean | null;
  };
  events?: BundleEvent[];
  suite?: { id?: string; sha256?: string | null; policy?: Record<string, unknown> | null; cases?: BundleSuiteCase[] } | null;
  experiments?: BundleExperiment[];
  contract?: { id?: string; decision?: string | null; claims?: BundleClaim[] } | null;
  candidates?: BundleCandidate[];
  baselines?: BundleBaseline[];
  telemetry?: BundleTelemetry[];
  annotations?: { target?: string; text?: string; source?: string }[];
}

export interface RunIndexEntry {
  id: string;
  title: string;
  kind: 'recorded' | 'synthetic' | string;
  manifest: string;
}
