# First authorized Contrast pilot - October 10, 2026

Implementation commit: 37f648a. Job: e2f06be6c8d64d958d2a9d00b7e7e800.
One live pilot; no retries or second pilot. Failed at Discover after 35.834 seconds.

The model navigated Image > Color Corrections ... and observed the Contrast
slider: min -100, max 100, step 1, current value 0. A visible_set tool request
failed. The runtime rejected the completed turn because one tool call failed,
reporting "Denied model capability request". No validated specification,
procedure validation, investigation, candidate reconstruction or acceptance followed.

The original audit omitted failed tool arguments and their errors. Therefore the
numeric-setting failure's exact cause is unknown. A subsequent offline diagnostic
change records bounded failed-action arguments and errors while preserving
fail-closed behavior. It passed 25 focused Python tests. No model run was performed
to validate that change live.

Provider-reported usage: 88,731 total tokens; 87,333 input including 57,856 cached;
1,398 output including 67 reasoning tokens. Cached tokens are included in input
and total, not additional usage.

Original private artifacts remain under evidence/learning/feature-<job-id> and
evidence/feature-jobs/<job-id>. No candidate was promoted, merged or pushed.

## Second authorized pilot

Job: 48965c1eeb68400fbcb235c10e612b78, implementation da3f7b2.
Failed at Discover after 38.305 seconds. The new diagnostic captured:
visible_set, row/slider name "Contrast:", dialog "Color Corrections", value 10;
ValueError: "Ambiguous or missing visible control: Contrast:".
The row resolver appended a colon to an already colon-terminated label, searching
for "Contrast::". The resolver now accepts the label with or without its trailing
colon. Offline regression checks both forms and preserves duplicate rejection.
This establishes the second run's cause; the first run's missing arguments cannot
be retrospectively recovered. No further live run or candidate promotion occurred.
Provider usage: 88,847 total; 87,436 input including 57,984 cached; 1,411 output.

## Third authorized pilot and recovery integration

Job 7b1996eca8fa484cb4dfaaeaee5fd81b, implementation 1e22d1f.
Contrast numeric setting succeeded. Discovery stopped after 38.423 seconds because
the model returned request "Discover the visible workflow for Implement Contrast"
and a prose parameter field, violating the structured specification contract.
Usage: 93,338 total; 91,891 input including 57,984 cached; 1,447 output.
The subsequent offline implementation constrains these fields, adds bounded action
and specification correction, and persistent procedural lessons. No further live
pilot was launched in this turn; no Contrast candidate was constructed or promoted.

## Fourth authorized pilot - October 11, 2026

Job 2c0fba2006d64aaabc89833a983c3030, implementation 5392463.
Failed after 6.395 seconds. The model turn failed before any dynamic tool request;
completed items contained only userMessage. Runtime code: other; willRetry: false.
No provider usage was reported (not a claim of zero billed usage).
The original adapter discarded the server error message, so the exact cause cannot
be recovered from this archived record. Runtime notifications and failed-turn errors
now retain bounded redacted messages alongside codes. No further pilot was run.

## Fifth authorized pilot - October 11, 2026

Job 7caaaadaceb640c8b523800b8a1b873a, implementation a3b3ca5.
Failed after 8.753 seconds, before dynamic tool requests; no provider usage reported.
The captured server error was HTTP 400 invalid_json_schema: request's constant
Implement Contrast conflicted with parameter's enum Contrast / Contrast:.
Deepcopy preserves aliases to shared model.S dictionaries, so mutating the parameter
schema also mutated request and other string fields. The constrained fields now use
independent dictionaries, verified by an offline regression test. No additional live
pilot was launched after this fix; no candidate was constructed or promoted.

## Bounded host-repair implementation and subsequent pilot - October 11, 2026

Implementation d118441; budget wiring fix 7b1a85a. A pre-inference launch
2bcd9aa36be441c2a019906b6c6d5b3b stopped at 0.460 seconds because the legacy
Budget correctly refused run_seconds=1200. The job owner enforces 1200 seconds;
internal harness limits remain 600. Offline budget regression passed before retry.

Live job 945c402019f5497a8bc4347a5cd5263f failed at Discover after 19.441 seconds.
The model opened Effects. The resulting visible observation exceeded the 16 KB
output ceiling, then a visible_inspect also exceeded it. No specification, procedure
validation, reconstruction or acceptance followed. Provider usage: 39,286 total;
38,930 input including 24,448 cached; 356 output. No autonomous harness patch was
proposed because bounded observation/capability handling is outside the writable
resolve/output_schema function scope. The system retained every action and stopped
without relaxing limits. A future bounded pagination change is required for this
failure class; this implementation does not claim arbitrary autonomous host repair.

Repair infrastructure has offline tests for failed-before/passed-after schema replay,
forbidden patches, repeated-failure and repair-count stops, rejection without a failing
reproducer, rejected regressions, isolated patch retention and matching-host recall.
No live autonomous host repair or recalled-patch success has yet been demonstrated.
No editor promotion, merge or push occurred.

## Interaction-map pilot - October 11, 2026

Job 0ad03820b98845a3a3ba7ded63f37157, implementation 5c14d48.
Stopped after 79.827 seconds at Discover. Visible actions and inspections succeeded
without oversized observations. Four actions and six observations were retained.
The first specification's scope included prose and was rejected. The autonomous
correction produced the exact scope, but the final specification left other controls'
neutral settings unresolved; grounding raised "Other control neutrality unresolved".
No validated route, procedure replay, investigation or candidate reconstruction followed.
No harness patch was proposed for this specification failure.

The JSON interaction map was populated from delivered visible observations and retained
for future jobs. This establishes live map recording, not successful cross-job route reuse
or pagination of a large live menu. The model called map_route twice (no cached route
was available); it did not call map_query. The map retained 121 nodes and zero validated routes.

Two model invocations reported 165,013 total tokens; 162,137 input including 107,136
cached; 2,876 output including 283 reasoning tokens. Cached/reasoning values are included
in their parent totals. The correction loop was exercised but did not complete discovery.
Original failed decisions and diagnostics remain preserved. No further pilot, editor
promotion, merge or push occurred.
