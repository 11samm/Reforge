# Target-scoped findings: miniPaint Gaussian Blur (hosted, visible About 4.14.3)

Scope: the hosted miniPaint URL (build unpinned), headed Chromium at 1440x1000 and scale 1,
single-layer transparent documents, 8-bit RGBA exports, Percentage 1–7 as tested. These are observations
about this one target and operation. They are **not** global guidance and are never placed in model
packets. Behavior claims for a run must cite exact evidence IDs.

Investigation status: **closed** (2026-10-10), unless explicitly reopened. Final report:
[blur-final](../../dev-workspaces/blur-final/report.md).

## Compatibility (measured)

- The experimental checkpoint passes 5/10 on the original frozen suite (`970c4619…`) and 7/14 on the
  expanded suite (`140d78d0…`).
- Build, independent execution, UI/batch agreement and four exact baselines pass.
- Main `generated-app` is the no-blur baseline. There has been no holdout evaluation.

## Observations (supported within the tested inputs)

| ID | Observation | Evidence |
|---|---|---|
| T1 | Fitted σ ≈ Percentage at P4 and P7 (3.98; 6.94–7.06). Percentage is not assumed to be a pixel radius in general. | FD step2, BF exp-b |
| T2 | On the identical dev-02 input, P4 gives the undisplaced σ=4 step response (≤1 level, centre 140), while P7 gives a +0.30 px colour displacement. Processing differs between these settings on this input. | BF exp-b, FD step3 |
| T3 | P7 colour transitions differ between images in ways no single translation explains. 65-wide rising edge: +0.30. 257 atlas band: rising −0.25 and falling +0.27 (band appears wider). 129 band: rising −0.11, falling 0.00. | FD step3, BF analyze |
| T4 | The P7 alpha falloff at a transparent exterior varies with axis length (first pixel 135/136/138/133 for 49/65/129/257). It is not monotonic. | BF analyze |
| T5 | Import quantizes low-alpha colour to the premultiplied-byte lattice and normalizes hidden RGB at alpha 0. These are import limitations, not blur behavior. | FU dev-03, dev-05 |
| T6 | Impulses of 64, 128 and 255 at P7 export zero RGB everywhere. | PF precision-03/04, FU dev-01 |
| T7 | An alpha-15 seam keeps alpha 15 and uses 17-level straight-RGB steps, mostly reproduced by premultiplied-byte conversion. | PF precision-01 |

## Fitted descriptions (do not implement as corrections)

- A per-image colour displacement (+0.30 at 65 wide, −0.25 at 257) fits rising edges only. It fails on the
  atlas falling edge and on exp-a.
- The Percentage-7 boundary-alpha lift in the experimental checkpoint (BR) is a fitted observational
  correction.

## Unresolved

- What sets the P7 colour and alpha deviations: axis length, distant content, a parameter-dependent
  processing path, or a combination. These remain confounded.
- Low-alpha RGB failures (gb010, fresh-04, dev-04).
- The threshold Percentage between 4 and 7, and behavior at P8–P50.

## Experiments that would separate the remaining confounds (not run)

- A dimensions-only series with fixed edge content and fixed edge-to-border distances.
- A content-only series at fixed dimensions (for example, moving a distant second edge).
- A Percentage series 5, 6 on the dev-02 input.

All three need developer-selected patterns or new bounded planner generators.
