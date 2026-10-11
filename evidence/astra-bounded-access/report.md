# Bounded Astra diagnostic attempt

Outcome: stopped for insufficient distinguishing evidence. One completed Astra diagnostic, zero builder invocations, zero new experiments, zero implementation candidates. Compatibility remains rejected; the main no-blur app is unchanged.

Runtime verified: gpt-6-astra, medium; OpenAI provider, managed ChatGPT login, fallback disabled. The exact runtime model was checked against thread/start, and the diagnostic completed. Runtime codex-cli 0.162.0-alpha.17.2.

Execution: 49.998 seconds including isolated preparation, base evaluation, diagnosis and cleanup; preliminary catalog probe 0.604 seconds. Diagnostic 26.175 seconds. Actual cumulative usage: 23,820 input, 806 output, 0 cached input; 24,626 total tokens. Provider reported 0 reasoning output tokens.

Enforced path: isolated snapshot of the existing runtime with explicit Astra configuration; one decision-call cap and one conditional builder-call cap; existing packet ceilings; 120-second diagnostic and at most 240-second builder deadlines; 600-second overall budget and 100-second cleanup reserve. No retry or fallback. Existing host, evaluator and source policies were not edited. The runtime snapshot and executed runner are preserved.

## Evidence and hypotheses

- Parameter/kernel/support: sigma=Percentage and support=ceil(3*sigma) are assumptions, not identified rules. A width change should generally produce opposite-signed step residuals on opposite sides; the predominantly positive P7 residual instead motivates testing phase/asymmetry or precision loss alongside kernel alternatives.
- Intermediate quantization/pass order: the floating-point horizontal-then-vertical core cannot itself explain fresh-01's axis asymmetry. Quantized passes could produce orientation-dependent profiles and suppress the P7 impulse, but neither pass order nor rounding rule is established.
- Premultiplication/low-alpha conversion: alpha-weighted filtering is supported, but final rounding of premultiplied bytes and rounded-alpha division may differ from the reference conversion sequence. Small intermediate errors predict large straight-RGB errors at low alpha, including errors where exported alpha agrees.
- Boundaries: transparent exterior without renormalization is plausible; opacity-preserving padding is inconsistent with observed alpha loss. Finite support, accumulated precision loss, and rendering/export coverage remain competing explanations for boundary differences.

- Supplied source uses normalized sampled Gaussian weights, floating-point premultiplied passes, then rounded premultiplied channels divided by rounded alpha. P7 alone adds a coverage/density-based alpha lift; RGB retains the uncorrected denominator. This correction cannot repair any RGB residual.
- fresh-03 and dev-02 have identical reference central-row profiles despite different heights. Both candidate centers are 135 versus reference 130, with alpha exactly 255 and center RGB MAE 3.81818. Boundary-alpha correction cannot explain this interior discrepancy.
- fresh-01 has distance-two RGB 6 horizontally versus 5 vertically. dev-01 has red_sum=0 despite a white impulse. These constrain precision/kernel hypotheses but do not identify one shared implementation.
- fresh-04 retains red 255 into transparent black; dev-04's seam is (211,0,44,133). Both support alpha weighting rather than independent straight-RGB convolution.
- gb010 column_x32 has identical candidate/reference alpha throughout, yet blue differs by +128 at y=5 and y=43. fresh-04 at (16,5) has blue 32 versus 0 with alpha 8 in both; dev-04 at (21,0) has red 47 versus 38 with alpha 27 in both. Alpha-only repair is insufficient.
- Corners fall to alpha 125 at P1, 82 at P3, and 72–73 at P7; dev-06 reaches only 169 centrally. fresh-02 shows inward boundary spreading without opposite-midpoint RGB, supporting coverage loss but not exact support.
- All reported alpha gates already pass. gb017, fresh-01, fresh-02, dev-01 and dev-06 pass blur gates; build, independent execution, UI agreement and exact baselines also pass. Passing tolerance gates do not establish exact mechanisms.

## Evidence gap and experiment provenance

The current exports do not distinguish kernel phase/support from per-pass precision and low-alpha export conversion. Another alpha-only correction is contradicted by RGB discrepancies at identical alpha, including fully opaque P7 interiors. No supported implementation replacement was identified. The empirical alpha correction was preserved.

The coordinator chose an existing-evidence-only diagnostic path and explicitly disabled fresh experiments in its prompt, although the user allowed up to four. Thus no claim is made that the full optional experiment budget was exhausted. No reference browser was opened and no new import normalization or blur observation was collected. Existing follow-up import-normalization failures remain separate from admitted blur evidence.

The planner supports fixed pattern kinds plus dimensions and Percentage. It cannot express reversed/complementary steps, transposed steps, variable impulse amplitudes, or constant-color alpha ramps. Center-impulse dimension changes are expressible, but do not alone isolate pass precision from kernel alternatives. No developer-added pattern was created.

The diagnostic mentioned hidden reference intermediates/source as missing information. Those are outside the authorized boundary and were not accessed; they are not a proposed next step. Allowed future discrimination would require appropriately labeled visible-UI/export experiments, including generator support for the missing patterns.

## Validation and unchanged case results

The exact frozen suite SHA-256 is 970c46192c2b2227dca077e33a3f6623e3ec46727e13037d28b068b6f0d49501. All ten historical metrics reproduced exactly. Build, input-only execution, UI/batch agreement, and all four exact regressions passed. Final restored-state build and four exact regressions passed. There is no new candidate, so no after-candidate metrics or expanded suite exist.

- gb017: passed; unchanged (no new candidate).
- gb010: failed; unchanged (no new candidate). full_image: rgb_mae=1.6612244897959183 violates rgb_mean_max=1; full_image: rgb_fraction_within_tolerance=0.9416012558869702 violates rgb_fraction_min=0.99; boundary: rgb_mae=3.792517006802721 violates rgb_mean_max=1; boundary: rgb_fraction_within_tolerance=0.826530612244898 violates rgb_fraction_min=0.99
- fresh-01: passed; unchanged (no new candidate).
- fresh-02: passed; unchanged (no new candidate).
- fresh-03: failed; unchanged (no new candidate). full_image: rgb_mae=1.1513343799058084 violates rgb_mean_max=1; full_image: rgb_fraction_within_tolerance=0.8718995290423862 violates rgb_fraction_min=0.99; center: rgb_mae=3.8181818181818183 violates rgb_mean_max=1; center: rgb_fraction_within_tolerance=0.2727272727272727 violates rgb_fraction_min=0.99
- fresh-04: failed; unchanged (no new candidate). full_image: rgb_fraction_within_tolerance=0.9701726844583988 violates rgb_fraction_min=0.99
- dev-01: passed; unchanged (no new candidate).
- dev-02: failed; unchanged (no new candidate). full_image: rgb_mae=1.1382248520710059 violates rgb_mean_max=1; full_image: rgb_fraction_within_tolerance=0.8816568047337278 violates rgb_fraction_min=0.99; center: rgb_mae=3.8181818181818183 violates rgb_mean_max=1; center: rgb_fraction_within_tolerance=0.2727272727272727 violates rgb_fraction_min=0.99
- dev-04: failed; unchanged (no new candidate). full_image: rgb_fraction_within_tolerance=0.9614325068870524 violates rgb_fraction_min=0.99
- dev-06: passed; unchanged (no new candidate).

All protected hashes passed the final guard. The isolated workspace was restored to experimental-base-start. No runtime writes or partial operation patches occurred. Historical records and original expectations remain intact. No commit, push, promotion or further attempt.

[Diagnosis](../learning/20261010T225609Z-e994550d-dev-resume/diagnosis.json); [invocation](../learning/20261010T225609Z-e994550d-dev-resume/model/diagnostic/invocation.json); [full run report](../learning/20261010T225609Z-e994550d-dev-resume/report.json); [per-case results](paired-results.json); [limits](limits.json).
