# Dashboard feature integration

The existing integration merge e3cc79e already brought the Aurora Glass redesign and feature-discovery branch together. This work completes the feature-job view using the documented design system: gradient hero, elevated request card, shared semantic pills, numbered stage cards, compact metrics, evidence cards and event disclosure. The existing recorded replay and side-by-side inspector remain separate from local jobs.

Job history selection survives polling. Run is disabled while any job is active, even when viewing an older job. Cancellation targets the selected job, is disabled while cancelling/offline, and uses the existing JSON service contract. Polls do not overlap and are aborted when leaving the page. Empty and disconnected service states are distinct from failed feature jobs. Execution limits and tested scope remain accessible in a disclosure; no unsupported feature claims or automatic promotion were added.

The 980px navigation now retains access to all sections rather than hiding the only navigation. At 390px the navigation scrolls horizontally, forms stack, and stages/evidence become one column. All new surfaces use design-system/tokens.css. Original backend gates and evaluator policies are unchanged.

Validation: 128 Python tests passed, including local browser fixtures; 11 dashboard tests and TypeScript/build passed. Both browser tests passed again after final styling/test refinements. Desktop, 980px and 390px screenshots were visually inspected, and the real preview proxy returned the loopback service with pilot_enabled=false. No paid learning runs were launched.

Review at http://127.0.0.1:5181/. Fixture screenshots in dashboard/docs/screenshots/integration show synthetic job states; inspector screenshot shows recorded Blur evidence. The feature-discovery autonomous Contrast proof remains in docs/contrast-pilot-20261010.md. Generated Contrast candidates remain in their original isolated workspaces and are not promoted here. Main and the source worktrees remain unchanged.
