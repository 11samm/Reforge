# Reforge presentation launch

Use this isolated checkout: `D:/Samuel/Downloads/Code/ReforgerData/demo-rehearsal`.
The rehearsal report in `demo-rehearsal-20261011.md` determines whether to present live or replay.

## Preflight and launch

In PowerShell, inspect listeners before starting. If either port belongs to another process, leave it alone and resolve the conflict with its owner. Vite uses a strict port; never assume a server that silently moved ports is the presentation server.

```powershell
Set-Location D:/Samuel/Downloads/Code/ReforgerData/demo-rehearsal
Get-NetTCPConnection -State Listen | Where-Object LocalPort -in 5181,5190 |
  Select-Object LocalAddress,LocalPort,OwningProcess
npm.cmd --prefix generated-app ci
npm.cmd --prefix dashboard ci
npm.cmd --prefix generated-app run build
npm.cmd --prefix dashboard run build
npm.cmd --prefix dashboard run preview
```

Keep that terminal open. Dashboard: `http://127.0.0.1:5181/`.
Offline replay needs only this terminal and no model login or reference website.

For a live presentation, use a second PowerShell terminal:

```powershell
Set-Location D:/Samuel/Downloads/Code/ReforgerData/demo-rehearsal
& D:/Samuel/Downloads/Code/Reforge/.venv/Scripts/python.exe -m features.service --enable-pilot
```

Feature API: `http://127.0.0.1:5190/api/jobs`. The installed `codex` command must be on PATH and signed into the existing managed ChatGPT account. The checked-in `smoke.config.json` selects `gpt-6.1-sol`, medium, provider `openai`, with provider fallback disabled. Keep this provider and all pipeline budgets unchanged. No API key or paid service is required. Actual reference execution needs access to hosted miniPaint and installed Playwright Chromium.

For a new machine, create a Python environment, install `requirements-adapter.txt`, and run `python -m playwright install chromium`; substitute that environment's Python path. The shared ownership locks are in the canonical repository's `.scratch/feature-service.lock`, `.scratch/feature-browser.lock` and `.scratch/reference-browser.lock`. A lock file's existence does not mean it is held. Let the service acquire these locks; never delete them or stop another owner's processes to force access.

## Presentation sequence

1. Open **Implement a feature**; confirm **Service connected**. Select **Implement Brightness**.
2. Click **Prepare fresh Brightness demo**. Show the new demo ID, no image, **Brightness unavailable until learned**, and the disclosed memory exclusions. Preparation invokes no model.
3. Click **Learn Brightness** for that selected preparation. The run ID must match the demo ID. Do not click again or reuse a used demo.
4. Show the actual miniPaint and candidate panes and backend elapsed time. Explain Discover, Validate procedure, Investigate, Reconstruct and Verify. Static panes can wait while the model works; their last-frame timestamps disclose freshness.
5. Inspect experiments, raw comparisons and original editor regressions. A candidate rejection is part of the recorded run. Final evaluation hides and closes both live owners before collecting held-out cases.
6. Only after **accepted**, open the isolated candidate exploration. Upload a new local PNG/JPEG, choose **Image → Brightness**, change the value and apply. This upload is unscored exploration and does not promote or merge source.
7. If the run fails or presentation time expires, disclose the outcome and use the fallback immediately. Cancel a still-running job before ending the live portion.

## Fast fallback

Leave the dashboard open in a second browser tab before presenting. In that tab choose **Overview → Run bundle → Brightness accepted real run (Oct 11, 2026)**. Use **Restart replay**, choose **20× speed**, then **Play**. Use **Jump to end → Candidates** for comparisons, baseline rejection/repair history and final evidence. Repeat with Contrast if useful. Labels must say **RECORDED PLAYBACK**; these are archived images, not live browser sessions. If Run bundle is hidden in a narrow window, expand the browser or use **Implement a feature → Replay saved run** to import the file.

The backend can be stopped. **Replay saved run** also imports either exact file from any directory:

- `dashboard/public/runs/brightness-success.reforge.json`
- `dashboard/public/runs/contrast-success.reforge.json`

Imports start at zero. Restart hides later outcomes; switching resets inspector selection. Recordings are evidence artifacts, not executable editor archives. The bundled Brightness success is an earlier run, with its two preceding failures and intervening developer changes disclosed in provenance.

## Clean shutdown

Click **Cancel run** for any active job and wait for terminal cancellation and both panes to close. Then press Ctrl+C in the feature service terminal; finally Ctrl+C in the dashboard terminal. Verify ports 5190 and 5181 are no longer held by the servers you launched. Preserve workspaces, job directories, logs, recordings and ownership files. Never use a blanket kill of Python, Node or Chrome.
