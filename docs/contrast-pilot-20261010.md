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
