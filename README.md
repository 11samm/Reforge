# Reforge

Reforge reconstructs image-editing features by observing miniPaint, running experiments, building an isolated implementation, and independently evaluating the result. A React dashboard shows the investigation, candidate decisions, pixel comparisons, regression checks, and recorded evidence.

## Current results

- Brightness and Contrast have accepted actual-run recordings bundled with the dashboard.
- A later fresh Brightness attempt accepted in 208.604 seconds at commit `396b0870962a2be9e15ed347ddf56dfb6033984c`. Its separately exported submission recording is not bundled in this source download.
- Gaussian Blur is an unresolved historical attempt, not an accepted feature or Blur Brush.
- Fresh-run repeatability remains under development. An accepted run establishes success within its tested scope, not exhaustive compatibility or guaranteed success on another attempt.

## Try recorded playback first

Requires Node.js 24 and npm. From the extracted repository directory:

```sh
npm --prefix dashboard ci
npm --prefix dashboard run build
npm --prefix dashboard run preview
```

Open http://127.0.0.1:5181/ and select **Overview**. Choose the accepted Brightness or Contrast recording in **Run bundle**, then **Restart replay**, **20x**, and **Play**. **Jump to end → Candidates** reveals comparisons and final evidence. At time zero, later results are intentionally hidden.

Recorded playback needs no Python service, Codex login, API key, or reference website. **Replay saved run** imports a portable `.reforge.json` recording from your computer.

Replay uses Overview, Experiments, Contract, Candidates, Model usage, and Event log. It does not recreate the Implement tab's live browser layout. Archived screenshots are not continuous video. Synthetic fixtures are labeled and must not be presented as actual results.

## Live learning setup

Requires Python 3.12+, Node.js 24, Playwright Chromium, access to hosted miniPaint, and an installed Codex CLI on PATH. Run commands from the repository root, not the Python executable's directory.

```sh
python -m venv .venv
```

Activate the environment. In Windows Command Prompt:

```bat
.venv\Scripts\activate.bat
```

In PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```sh
source .venv/bin/activate
```

Then install dependencies:

```sh
python -m pip install -r requirements-adapter.txt
python -m playwright install chromium
npm --prefix generated-app ci
npm --prefix generated-app run build
npm --prefix dashboard ci
npm --prefix dashboard run build
```

### Sign in with your own account

Reforge does **not** automatically open a ChatGPT sign-in popup. Install the [Codex CLI](https://developers.openai.com/codex/cli/) separately, then check authentication and sign in if needed:

```sh
codex --version
codex login status
codex login
```

Complete the CLI's browser sign-in with your own supported ChatGPT account. This project uses managed ChatGPT authentication, not API-key authentication; inherited API-key variables are removed from the model runtime. Account access and usage limits still apply. The exact configured model must be available to your account; provider fallback is disabled.

Your download does not include the author's `.env`, Codex login credentials, or local authentication directory. Reforge does not supply access to the author's account. Keep your own credentials outside version control. Historical documentation can contain local example paths; replace them with your checkout path.

### Start the services

In one terminal:

```sh
python -m features.service --enable-pilot
```

In another terminal, from the same repository root:

```sh
npm --prefix dashboard run preview
```

Open http://127.0.0.1:5181/ and choose **Implement a feature**. The API runs at http://127.0.0.1:5190/. Starting the service without `--enable-pilot` disables new learning while retaining access to available local jobs.

1. Select Brightness or Contrast.
2. Click **Prepare fresh demo**. Preparation builds an isolated starting editor without invoking the model.
3. Click **Learn** once for that preparation. This starts a model-backed attempt and consumes your account's usage.
4. Watch progress and evidence. Reference browser activity generally begins before candidate testing. The candidate can remain idle during investigation, code generation, and build checks.
5. Final held-out evaluation deliberately hides/closes the visible browser sessions. A **Held-out evaluation** screen is expected.
6. After acceptance, open the isolated candidate exploration, upload a new image, and exercise the feature. Exploration is unscored and does not automatically promote the candidate into the main editor.

**Cancel run** appears in Feature jobs while an attempt is active. Wait for terminal cancellation before stopping the service. Browser windows are controlled by the harness; closing them can interrupt execution. Presentation failures may leave stale frames, which are explicitly labeled; consult job status and event evidence.

The service uses shared ownership locks. If it reports another pipeline owns the browser/service, locate that existing process and coordinate shutdown. Do not delete lock files or blanket-kill Python, Node, or Chrome. Only one learning attempt should own the shared resources at a time.

## Download and evidence boundaries

The source ZIP contains tracked project files. Dependencies, generated builds, local candidate workspaces, private scratch data, and untracked raw run archives are not included. Bundled replay evidence is distinct from a runnable candidate archive. Links to a particular local job's candidate preview work only while its service and preserved local artifacts are available.

## Validation

```sh
python -m unittest test_presentation_isolation
npm --prefix dashboard test
npm --prefix dashboard run build
```

These deterministic checks do not launch a new learning attempt and do not establish end-to-end repeatability. Additional numerical and editor regression procedures are documented below.

## More documentation

- [Demo launch and playback](docs/demo-launch.md)
- [Portable recording format and verification](docs/portable-replay.md)
- [Feature pipeline architecture](docs/feature-pipeline.md)
- [Brightness evaluation](README-brightness.md)
- [Independent evaluator](README-evaluator.md)
- [Editor shell](README-shell.md)
- [Original connectivity milestone and authentication details](README-connectivity.md)

Historical milestone documents describe the state at the time they were written; some contain older feature support lists or machine-specific commands.