#!/usr/bin/env node
// Trusted-host exporter: converts one recorded Reforge learning run directory
// into a sanitized dashboard bundle (reforge.run-bundle v1).
//
//   node scripts/export-run.mjs --repo <repo-root> --run <run-dir> --out <bundle-dir>
//        [--annotations <json-file>] [--bundle-id <id>]
//
// Reads only inside --run and <repo>/fixtures/development. Writes only inside
// --out. Absolute paths are never copied into the bundle; prompts, packets,
// request bodies, thread ids, account details and reasoning items are not read
// into the output. See ../DATA-CONTRACT.md.

import { createHash } from 'node:crypto';
import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { basename, dirname, isAbsolute, join, relative, resolve, sep } from 'node:path';

const FORBIDDEN_SEGMENTS = ['collector', 'holdout', 'final_holdout'];
const MAX_TEXT = 1200;

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 2) {
    if (!argv[i].startsWith('--') || argv[i + 1] === undefined) throw new Error(`Bad argument near ${argv[i]}`);
    out[argv[i].slice(2)] = argv[i + 1];
  }
  for (const key of ['repo', 'run', 'out']) if (!out[key]) throw new Error(`Missing --${key}`);
  return out;
}

const args = parseArgs(process.argv.slice(2));
const repo = resolve(args.repo);
const runDir = resolve(args.run);
const outDir = resolve(args.out);
const fixturesDir = join(repo, 'fixtures', 'development');
const readRoots = [runDir, fixturesDir];

function inside(root, p) {
  const rel = relative(root, p);
  return rel === '' || (!rel.startsWith('..') && !isAbsolute(rel));
}

function assertReadable(p) {
  const full = resolve(p);
  const lowered = full.toLowerCase().split(sep);
  if (FORBIDDEN_SEGMENTS.some((s) => lowered.includes(s))) throw new Error(`Refusing forbidden path: ${full}`);
  if (!readRoots.some((root) => inside(root, full))) throw new Error(`Refusing path outside allowed roots: ${full}`);
  return full;
}

function readJson(p) {
  const full = assertReadable(p);
  if (!existsSync(full)) return null;
  return JSON.parse(readFileSync(full, 'utf-8'));
}

function sha256(file) {
  return createHash('sha256').update(readFileSync(file)).digest('hex');
}

// Replace any absolute filesystem path inside free text with a neutral token.
function scrub(text) {
  if (typeof text !== 'string') return text;
  return text
    .replace(/[A-Za-z]:\\[^\s"'`<>|]+/g, (m) => `<${basename(m)}>`)
    .replace(/(^|[\s"'(])\/(?:Users|home|mnt|tmp|var)\/[^\s"'`<>|]+/g, (_m, pre) => `${pre}<path>`)
    .slice(0, MAX_TEXT);
}

function scrubDeep(value) {
  if (typeof value === 'string') return scrub(value);
  if (Array.isArray(value)) return value.map(scrubDeep);
  if (value && typeof value === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(value)) out[k] = scrubDeep(v);
    return out;
  }
  return value;
}

function pick(obj, keys) {
  if (!obj || typeof obj !== 'object') return null;
  const out = {};
  for (const k of keys) if (obj[k] !== undefined) out[k] = obj[k];
  return out;
}

const copied = new Map();
function copyArtifact(source, bundleRel) {
  if (!source) return null;
  const full = assertReadable(source);
  if (!existsSync(full) || !statSync(full).isFile()) return null;
  if (!/\.(png|jpe?g)$/i.test(full)) throw new Error(`Refusing non-image artifact: ${full}`);
  const dest = join(outDir, bundleRel);
  mkdirSync(dirname(dest), { recursive: true });
  copyFileSync(full, dest);
  const rel = bundleRel.split(sep).join('/');
  copied.set(rel, { path: rel, sha256: sha256(dest), bytes: statSync(dest).size });
  return rel;
}

function metricsSubset(m) {
  return pick(m, [
    'pixel_count', 'rgb_mae', 'rgb_mae_per_channel', 'rgb_max', 'alpha_mae', 'alpha_max',
    'rgb_fraction_within_tolerance', 'alpha_fraction_within_tolerance', 'different_pixels',
  ]);
}

function caseRecord(c, artifacts) {
  const regions = {};
  for (const [name, r] of Object.entries(c.regions ?? {})) {
    regions[name] = { box: r.box ?? null, passed: r.passed ?? null, metrics: metricsSubset(r.metrics), reasons: (r.reasons ?? []).map(scrub) };
  }
  return {
    case_id: c.case_id ?? c.id,
    status: c.status ?? null,
    classification: c.classification ?? null,
    dimensions_equal: c.dimensions_equal ?? null,
    dimensions: c.dimensions ?? null,
    metrics: metricsSubset(c.metrics),
    regions,
    reasons: (c.reasons ?? []).map(scrub),
    artifacts,
  };
}

// ---------------------------------------------------------------- read run
if (!existsSync(join(runDir, 'events.jsonl'))) throw new Error(`No events.jsonl in ${runDir}`);
const rawEvents = readFileSync(assertReadable(join(runDir, 'events.jsonl')), 'utf-8')
  .split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
const report = readJson(join(runDir, 'report.json'));
const config = readJson(join(runDir, 'config.json'));
const runId = report?.run_id ?? basename(runDir);
const bundleId = args['bundle-id'] ?? `recorded-${runId}`;

if (existsSync(outDir)) rmSync(outDir, { recursive: true });
mkdirSync(outDir, { recursive: true });

// Events: keep the event stream, drop packet references, scrub paths.
const events = rawEvents.map((e) => {
  const { packet: _packet, checkpoint: _checkpoint, report: _report, ...rest } = e;
  return scrubDeep(rest);
});

// Suite.
const suiteFile = readdirSync(join(runDir, 'suites')).find((f) => f.endsWith('.json'));
const suiteRaw = suiteFile ? readJson(join(runDir, 'suites', suiteFile)) : null;
const suite = suiteRaw && {
  id: suiteRaw.id,
  sha256: rawEvents.find((e) => e.event === 'suite_frozen')?.sha256 ?? null,
  policy: suiteRaw.policy ?? null,
  exact_baseline_policy: pick(suiteRaw.exact_baseline_policy, ['id', 'version', 'mode', 'description']),
  region_rule: scrub(typeof suiteRaw.region_rule === 'string' ? suiteRaw.region_rule : JSON.stringify(suiteRaw.region_rule ?? null)),
  cases: suiteRaw.cases.map((c) => ({
    id: c.id,
    source: inside(fixturesDir, resolve(c.input)) ? 'development_fixture' : 'fresh_experiment',
    percentage: c.percentage ?? null,
    regions: c.regions ?? {},
    input_sha256: c.input_sha256 ?? null,
    expected_sha256: c.expected_sha256 ?? null,
    artifacts: {
      input: copyArtifact(c.input, join('artifacts', 'suite', c.id, 'input.png')),
      reference: copyArtifact(c.expected, join('artifacts', 'suite', c.id, 'reference.png')),
    },
  })),
};

// Experiments.
const experiments = [];
const expRoot = join(runDir, 'experiments');
for (const id of existsSync(expRoot) ? readdirSync(expRoot).sort() : []) {
  const ev = readJson(join(expRoot, id, 'evidence.json'));
  const rec = readJson(join(expRoot, id, 'reference-record.json'));
  const evidenceEvent = rawEvents.find((e) => e.event === 'evidence' && e.id === id);
  experiments.push({
    id,
    plan: scrubDeep(pick(ev?.plan ?? rawEvents.find((e) => e.event === 'experiment' && e.id === id)?.plan,
      ['question', 'hypotheses', 'predictions', 'usefulness', 'input', 'percentage'])),
    input_spec: scrubDeep(ev?.accepted_input_spec ?? null),
    percentage_requested: rec?.requested_percentage ?? evidenceEvent?.requested ?? null,
    percentage_accepted: rec?.accepted_percentage ?? evidenceEvent?.accepted ?? null,
    status: evidenceEvent?.status ?? rec?.status ?? null,
    original_import_confirmed: rec?.original_confirmation?.rgba_equal ?? null,
    target: pick(ev?.target ?? rec?.target, ['name', 'url', 'visible_about_version', 'build', 'observed_at', 'chromium_version', 'headed', 'viewport', 'device_scale_factor']),
    artifacts: {
      input: copyArtifact(ev?.input ?? join(runDir, 'inputs', `${id}.png`), join('artifacts', 'experiments', id, 'input.png')),
      reference_output: copyArtifact(ev?.expected ?? join(expRoot, id, 'output.png'), join('artifacts', 'experiments', id, 'reference-output.png')),
    },
  });
}

// Contract (latest file).
const contractDir = join(runDir, 'contracts');
const contractFiles = existsSync(contractDir) ? readdirSync(contractDir).filter((f) => f.endsWith('.json')).sort() : [];
const contractRaw = contractFiles.length ? readJson(join(contractDir, contractFiles.at(-1))) : null;
const contract = contractRaw && {
  id: contractFiles.at(-1).replace(/\.json$/, ''),
  decision: scrub(contractRaw.decision ?? null),
  claims: (contractRaw.claims ?? []).map((c) => scrubDeep(pick(c, [
    'id', 'statement', 'status', 'target_version', 'setup', 'parameter_domain', 'scope', 'supporting_evidence',
    'contradicting_evidence', 'alternatives', 'unresolved', 'verification_cases',
  ]))),
};

// Baseline regressions (one directory per baseline event label).
function baselineFor(label) {
  const res = readJson(join(runDir, label, 'baseline', 'results.json'));
  if (!res) return null;
  return {
    label,
    suite_id: res.suite_id ?? null,
    status: res.status ?? null,
    classification: res.classification ?? null,
    shell_status: res.shell_status ?? null,
    shell_error: scrub(res.shell_error ?? null),
    cases: (res.cases ?? []).map((c) => caseRecord(c, {})),
  };
}
const baselines = rawEvents.filter((e) => e.event === 'baseline').map((e) => baselineFor(e.label)).filter(Boolean);

// Model telemetry. Usage numbers only; builder turns also keep their concise final message.
const telemetry = [];
const modelDir = join(runDir, 'model');
for (const role of existsSync(modelDir) ? readdirSync(modelDir).sort() : []) {
  const inv = readJson(join(modelDir, role, 'invocation.json'));
  const total = inv?.usage?.total;
  telemetry.push({
    invocation: role,
    record_present: Boolean(inv),
    model: inv?.model ?? null,
    effort: inv?.effort ?? null,
    status: inv?.status ?? null,
    completion_status: inv?.completion_status ?? null,
    elapsed_seconds: inv?.elapsed_seconds ?? null,
    error: inv?.error ? { type: inv.error.type ?? null, message: scrub(inv.error.message ?? '') } : null,
    usage: total ? {
      total_tokens: total.totalTokens ?? null,
      input_tokens: total.inputTokens ?? null,
      cached_input_tokens: total.cachedInputTokens ?? null,
      output_tokens: total.outputTokens ?? null,
      reasoning_output_tokens: total.reasoningOutputTokens ?? null,
    } : null,
    concise_output: role.startsWith('builder') && typeof inv?.answer === 'string' ? scrub(inv.answer) : null,
  });
}

// Candidates.
const candidates = [];
const candDir = join(runDir, 'candidates');
const candIds = rawEvents.filter((e) => e.event === 'candidate').map((e) => e.id);
for (const id of candIds) {
  const c = readJson(join(candDir, `${id}.json`));
  const evaluation = c?.evaluation ?? null;
  const evalEvent = rawEvents.find((e) => e.event === 'evaluation' && e.label === id);
  const sourceCases = evaluation?.cases ?? evalEvent?.cases ?? [];
  const cases = sourceCases.map((sc) => {
    const caseId = sc.case_id ?? sc.id;
    const dir = join(runDir, 'evaluations', id, 'evaluation', caseId);
    const base = join('artifacts', 'candidates', id, caseId);
    return caseRecord(sc, {
      candidate: copyArtifact(existsSync(join(dir, 'candidate-raw.png')) ? join(dir, 'candidate-raw.png') : join(runDir, 'evaluations', id, `${caseId}.png`), join(base, 'candidate.png')),
      rgb_difference: copyArtifact(join(dir, 'rgb-difference-x16.png'), join(base, 'rgb-difference-x16.png')),
      alpha_difference: copyArtifact(join(dir, 'alpha-difference-x16.png'), join(base, 'alpha-difference-x16.png')),
    });
  });
  const index = candIds.indexOf(id) + 1;
  candidates.push({
    id,
    status: c?.status ?? null,
    accepted: c?.accepted ?? null,
    reason: c?.reason ?? null,
    started_seconds: c?.started_seconds ?? null,
    error: c?.error ? { type: c.error.type ?? null, message: scrub(c.error.message ?? '') } : (evalEvent?.error ? scrubDeep(evalEvent.error) : null),
    build_valid: evaluation?.build_valid ?? evalEvent?.build_valid ?? null,
    independent: evaluation?.independent ?? evalEvent?.independent ?? null,
    baseline_pass: evaluation?.baseline_pass ?? evalEvent?.baseline_pass ?? null,
    evaluator_suspect: evaluation?.evaluator_suspect ?? null,
    ui_check: evaluation?.ui_check ? {
      case_id: evaluation.ui_check.case_id ?? null,
      rgba_equal: evaluation.ui_check.comparison?.rgba_equal ?? null,
      external_requests: Array.isArray(evaluation.ui_check.external_requests) ? evaluation.ui_check.external_requests.length : null,
      browser_errors: Array.isArray(evaluation.ui_check.browser_errors) ? evaluation.ui_check.browser_errors.length : null,
    } : null,
    execution: evaluation?.execution ? {
      reference_browser_closed: evaluation.execution.reference_browser_closed ?? null,
      input_only_batch_cases: Array.isArray(evaluation.execution.input_only_batch) ? evaluation.execution.input_only_batch.length : null,
      node_permission_guard: evaluation.execution.node_permission_guard ?? null,
      network_guard: scrub(evaluation.execution.standard_network_api_guard ?? null),
    } : null,
    builder_invocation: `builder-${index}`,
    baseline_label: `${id}-gates`,
    cases,
  });
}

const annotations = args.annotations ? JSON.parse(readFileSync(resolve(args.annotations), 'utf-8')) : [];

const bundle = {
  schema: 'reforge.run-bundle',
  schema_version: 1,
  provenance: {
    kind: 'recorded',
    source: relative(repo, runDir).split(sep).join('/'),
    exported_at: new Date().toISOString(),
    exporter: 'dashboard/scripts/export-run.mjs',
    note: 'Recorded playback of a completed historical run. Not live.',
  },
  run: {
    id: runId,
    operation: 'Gaussian Blur',
    target: experiments[0]?.target ? pick(experiments[0].target, ['name', 'url', 'visible_about_version', 'build']) : null,
    scope: report?.limitations?.map(scrub) ?? [],
    config: config ?? null,
    status: report?.status ?? null,
    stop_reason: report?.stop_reason ?? null,
    elapsed_seconds: report?.elapsed_seconds ?? null,
    first_acceptance: report?.first_acceptance ?? null,
    later_improvements: report?.later_improvements ?? [],
    final_build_status: report?.final_build?.status ?? null,
    final_baseline_pass: report?.final_baseline_pass ?? null,
  },
  events,
  suite,
  experiments,
  contract,
  candidates,
  baselines,
  telemetry,
  annotations,
  artifacts: [...copied.values()].sort((a, b) => a.path.localeCompare(b.path)),
};

writeFileSync(join(outDir, 'manifest.json'), JSON.stringify(bundle, null, 2) + '\n');
const leaked = JSON.stringify(bundle).match(/[A-Za-z]:\\\\|\\\\Users\\\\|\/Users\//);
if (leaked) throw new Error(`Absolute path leaked into bundle near: ${leaked[0]}`);
console.log(`Wrote ${bundleId}: ${events.length} events, ${experiments.length} experiments, ${candidates.length} candidates, ${copied.size} artifacts -> ${outDir}`);
