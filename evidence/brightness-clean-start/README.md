# One corrected-harness brightness clean-start verification

Run `20261011T012950Z-0ee26b62` accepted candidate 1 without human intervention. Six visible cases passed exact RGBA; four NEW final cases passed once after freezing the candidate, contract, suite and exact policy. Production build, independent input-only execution, UI/batch agreement and all four original exact baselines passed. No host, selector, evaluator, policy or manual implementation fixes occurred during the trajectory. No retry, escalation or second learning run occurred.

The recorded pre-brightness checkpoint was `evidence/learning/20261011T010106Z-25785e7a/checkpoints/no-blur-start` in the original local checkout. Its nine files matched the recorded manifest. Brightness source and applyBrightness binding were absent, and the isolated start passed production build and four exact baselines. `start-manifest.json` and `setup.json` record exact hashes and provenance; `executed-command.ps1` records the actual command. The corrected host came from main `380484c08e23e14444bc2061c3b39fc0f57a99d0`.

Clean start means brightness was unavailable in the candidate and restricted runtime context. The development agent had read prior results and the model may have prior knowledge. The runtime received only the isolated candidate, two approved visible developer scope observations, supplied procedures/strategy and its four fresh selected reference exports. It received no accepted main implementation, prior candidate checkpoint or prior fresh outputs. The original failed autonomous run remains a separate historical failure.

The runtime selected channel ramps at -37, clipping/rounding patches at +25, partial alpha at -37 and a grayscale ramp at -100. All original-confirmation exports were exact. Numerical hypotheses/predictions are in `experiments/`. Candidate 1 passed all six gates; candidate 2 was unused. About 4.14.3 and actual target metadata were supplied. No rejection occurred, so corrected rejection/repair routing was prechecked but not exercised live.

First acceptance: 156.418 s. Learning including cleanup: 165.748 s. New final verification: 21.177 s. Wall time from clean-start launch through final: approximately 200.836 s, including the handoff gap. Limits: 600 s total with 100 s cleanup reserve, four learning experiments plus four new final references (eight total), two candidates, zero retries, existing packet/tool deadlines. Actual packets passed limits. Three subscription-backed gpt-6.1-sol/medium invocations used 120,827 tokens: 115,384 input (62,208 cached) and 5,443 output (989 reasoning output included). Usage is provider telemetry, not an invoice.

Final parameters were -61, +26, +79 and 0 on new coordinate-generated RGB geometries and saturated partial-alpha blocks. Expected outputs were created only after the repair loop closed, were not exposed to a model, and were evaluated once. No repairs followed final results. Final frozen hashes remain unchanged. The final suite remains final evaluation evidence; using it for repair would convert it to development evidence.

31 offline precheck tests passed, alongside the build, four baselines, broker denial checks, operation-specific menu/selectors, named full regions, reference metadata, routing ID validation, packet/deadline budgets and subscription auth/catalog checks. No inference occurred during prechecks. Ordinary host process permissions were needed before the run to launch the browser. Runtime file/tool restrictions and independent execution guards are capability restrictions, not an OS sandbox for the trusted host.

Main app source/dist/configuration and declared experimental sources were hash-preserved (25 files); 604 dependency hashes matched the pre-run independent copy. Full Git status remained unchanged. No main app promotion or dashboard worktree change occurred. Unrelated artifact contents were not broadly inspected. Collector, blur holdout and final_holdout were not accessed; no reference source, bundles, hidden state or network bodies were inspected.

## Offline reproduction

From the repository root with documented Python dependencies and generated-app npm dependencies installed:

```powershell
.venv\Scripts\python.exe evidence/brightness-clean-start/reproduce.py
```

This checks the archived NEW candidate operation against the six visible and four final saved PNG pairs. It makes no model or browser requests and does not edit the accepted main app. It reproduces pixel equality; production build/UI/baseline records are historical gates rather than rerun by this script. Candidate-source is an archival snapshot, not a replacement for generated-app.

`integration.json` is the dashboard-ready handoff. `run-report.json`, `final-report.json`, contracts, prechecks, boundary audits and freeze records are publication snapshots. Absolute artifact paths are labeled `local-only:`; full local logs and checkpoint archives remain outside this bundle. Suite paths are relocated, preserving per-PNG hashes; original frozen suite hashes remain explicit. Candidate source hash checks normalize CRLF to LF for cross-platform checkouts; historical raw checkpoint hashes remain in the manifests. The command retains its exact original machine paths.

Limits: one run; discrete single-layer 8-bit PNG inputs/parameters; headed fixed browser/viewport; About 4.14.3 with unpinned hosted build. No all-input, multilayer, 16-bit or whole-editor claim.
