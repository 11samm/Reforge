# Independent image evaluator and baseline regressions

Milestone 4 stops before blur implementation, candidate acceptance/revert, or a learning loop.
No model requests or reference-site calls are needed. The evaluator imports Pillow only;
it does not import generated code or the reference adapter.

## Commands

From the Reforge repository root, using the existing pinned Pillow/Playwright environment:

```powershell
.venv\Scripts\python.exe -m unittest -v test_smoke test_adapter test_shell_boundary test_evaluator
npm.cmd --prefix generated-app run build
.venv\Scripts\python.exe baseline_regressions.py
.venv\Scripts\python.exe -m evaluator.examples
```

Baseline runs the existing bounded local shell verifier, then independently evaluates four
cases: opaque upload/export, transparent upload/export, explicit opaque-to-transparent
replacement on the same document with one current filename layer, and current-state export
following a known RGB mutation. The mutation uses the existing separate evidence fixture
importing production code; no editing feature or test hook is added to the shipped app.
The reference adapter remains headed by default. Local shell verification retains its
previous headless setting; it does not compare rendered reference blur behavior.

Each command creates a fresh evidence directory. No expected PNG is overwritten. Baseline
reports are under `evidence/baseline-regressions/<run>/`; controlled examples are under
`evidence/evaluator-examples/<run>/`. Latest-pointer JSON files identify the new runs.
Historical failures and results remain intact. Baseline exit 0 requires all four exact gates
and the existing shell checks; exit 1 means failure. Inspect suite classification and
shell error before interpreting missing exports caused by a stopped browser procedure.

## Later orchestrator interface

Use the CLI as a separate trusted subprocess, after build/export has completed, with a
new output directory outside generated-app and the builder tool boundary:

```powershell
.venv\Scripts\python.exe -m evaluator.compare --case-id example-001 --reference fixtures/development/inputs/gb010.png --candidate path/to/fresh-export.png --output evidence/evaluation/example-001 --policy evaluator/policies/exact-rgba-v1.json
```

Exit 0: all declared gates pass. Exit 1: reported output, dimension, region or pixel failure.
Exit 2: configuration/infrastructure exception (including invalid policy or reused output
directory). The CLI prints a compact JSON record; read `result.json` for full raw metrics,
policy, policy fingerprint, dimensions, case ID, reasons, region gates, and artifacts.
For Python callers use `evaluate(case_id, reference_path, candidate_path, fresh_output_dir,
policy=load_policy(policy_path), regions=...)`. Invalid policy/configuration raises before
scoring. The orchestrator must distinguish these exceptions from a pixel mismatch. Policy
fingerprints identify exact settings; they do not score images and are not file equality gates.

`--regions regions.json` accepts a nonempty mapping such as
`{"informative": [50, 50, 51, 51]}`. Coordinates are integer, half-open rectangles
[left, top, right, bottom] in original image coordinates. Full-image scoring always remains;
each explicitly declared region is an additional independent pass gate using the same
policy. Invalid, empty or out-of-bounds boxes fail. Declare case regions before judging
candidates, based on fixture intent, not a candidate's errors. Nothing automatically selects
an informative scoring region or changes weights. A large empty image can legitimately
pass a whole-image tolerance while containing a large local error: use declared informative
regions when that behavior matters. Controlled examples demonstrate both outcomes.

## Frozen policy files

`exact-rgba-v1.json`: exact equality of decoded RGBA including invisible RGB, all alpha,
and dimensions. PNG encoding, compression and metadata do not affect equality.

`blur-provisional-v1.json`: RGB mean over all three channels <=1 on the 0-255 scale;
at least 99% of pixels have maximum RGB-channel error <=3. Alpha has separate gates:
mean <=1, maximum <=3, and 100% of pixels within alpha tolerance 3. These alpha targets
are a conservative initial engineering choice, not a discovered property of miniPaint.
All blur thresholds are provisional engineering targets, not established compatibility
standards. No blur success is claimed. Freeze a new policy ID/versioned file before any
future threshold revision; never tune a policy to a candidate or overwrite references.
All comparisons are inclusive at the stated boundary. Non-finite values, bools, strings,
invalid ranges, unknown fields and unsupported schema versions are rejected.

## Metrics and artifacts

Full image and each named region report dimensions, RGB per-channel mean absolute errors,
combined RGB mean, RGB maximum absolute error, alpha mean and maximum, fractions within
the declared RGB/alpha pixel tolerances, and exact count of pixels differing in any RGBA
channel. Raw metrics are retained even for a passing tolerance case.

Each decodable pair gets a side-by-side preview (reference left) composited over the same
8px checkerboard using gray 192/240. Raw original files are copied without changes.
Dimension-matched pairs get an RGB difference image and a separate grayscale alpha
difference image, each amplified x16 with saturation at 255. Difference images are opaque,
so invisible RGB changes remain visible. Display-only changed-bounds crops and the recorded
bounding rectangle expose sparse errors; they never alter scoring. Named regions get their
own previews/differences. Missing/invalid files cannot have decoded previews; the report
explains the failure and retains any available raw bytes. Dimension mismatches have a preview
but no invented pixel metrics/difference image.

`result.json` and `report.md` accompany every scored case. Suite `results.json` and `report.md`
provide concise combined evidence. Classifications distinguish match, pixel_mismatch,
dimension_mismatch, invalid_output, missing_output, invalid_region and infrastructure_error.
They do not infer a blur algorithm defect or behavioral cause.

## Independence and limitations

Evaluator code, policies, baseline host, expected outputs and reports are outside the
builder's eight application-file allowlist; boundary tests explicitly reject these paths.
This remains a tool capability restriction, not an OS sandbox. Trusted verification imports
production code only in the existing isolated fixture. No new builder capability is exposed.
Development fixtures already imported in the repository are reused read-only; original
prepared blur reference outputs are untouched. No collector or held-out data is accessed.

V1 evaluates single-frame PNGs with decoded 8-bit RGBA (lower-bit/palette PNGs normalize
through Pillow). Native 16-bit PNGs are explicitly rejected instead of silently reducing
precision; animated PNGs are rejected. Color profiles/gamma metadata do not change raw
sample scoring; this is not color-managed perceptual evaluation. Differences at transparent
pixels count. Checkerboard rendering is only for inspection. Performance on very large
images and alternate decoders/browser versions is not established. Current baseline scope
is two imported development inputs plus one controlled mutation; it is not whole-editor or
blur compatibility. No dashboard, acceptance loop, planning, model invocation, push or commit
is performed in this milestone.
