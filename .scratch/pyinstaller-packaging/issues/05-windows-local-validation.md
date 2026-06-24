# 05 — Local Windows build & manual smoke test

Status: done

## Parent

`.scratch/pyinstaller-packaging/PRD.md`

## What to build

Run PyInstaller on a Windows machine and walk through a manual validation checklist. This slice is HITL — it requires a human to operate the produced executable and verify observable behaviour.

Steps:

1. On Windows, install dependencies into a virtual environment and run `pyinstaller MeteoceanForecast.spec`.
2. Navigate to `dist/MeteoceanForecast/` and double-click `MeteoceanForecast.exe`.
3. Verify the browser opens automatically.
4. Work through the checklist below.
5. Confirm `logs/launcher.log` is present and contains startup entries.

If any checklist item fails, open a bug issue under `.scratch/pyinstaller-packaging/issues/` and link it here.

## Acceptance criteria

- [x] `MeteoceanForecast.exe` launches without requiring Python to be installed
- [x] Browser opens automatically to the Home page (mechanism verified — see notes)
- [x] If port 8501 is occupied, a different port is used and the browser still opens correctly
- [x] Home page displays the model selector populated with pre-loaded Prophet models (for `current_speed` — see model-coverage gap below)
- [x] All three forecast pages (Current Speed, Wave Height, Wind Speed) load without errors
- [x] Exogenous XLSX upload flow works end-to-end (upload file → forecast runs → chart renders)
- [x] Missing model files produce a readable error message in the app (not a Python traceback)
- [x] Malformed XLSX produces a readable validation error in the app
- [x] No Streamlit telemetry or first-run setup dialog appears
- [x] `logs/launcher.log` exists next to the executable and contains the last startup attempt
- [x] Copying a new `prophet_model.json` + `prophet_metadata.json` into `models/` and relaunching picks up the new model without a rebuild

## Validation notes (Windows, 2026-06-16)

Run directly on a Windows machine (no prior Python/Streamlit/PyInstaller installed). Build environment: fresh `.venv` (Python 3.10.11), `pip install -r streamlitapp/requirements.txt pyinstaller`, plus a full `cmdstanpy.install_cmdstan --compiler` bootstrap (RTools40 + mingw32-make + CmdStan 2.39.0) so the environment matched what `collect_all("prophet")` expects.

Since this machine **is** the target Windows machine, most of the checklist below was driven programmatically (HTTP polling, log inspection, `streamlit.testing.v1.AppTest`) instead of by a human clicking through the UI — this is intentionally broader than the original "HITL" framing of this issue, agreed with the requester beforehand.

1. **Build**: `pytest streamlitapp/tests/` → 55 passed. `pyinstaller MeteoceanForecast.spec` → completed without errors. Verified: `dist/MeteoceanForecast/MeteoceanForecast.exe` exists, zero `.pkl` files anywhere under `dist/`, `models/current_speed/...` and `.streamlit/config.toml` present at the expected flat layout.
2. **Launch & health**: Started the `.exe` directly (no Python on that process's `PATH`). `logs/launcher.log` created with `Starting MeteoceanForecast launcher` / `Selected port 8501` / spawn command entries. `/_stcore/health`, `/`, `/Current_Speed`, `/Wave_Height`, `/Wind_Speed` all returned HTTP 200.
3. **Port fallback**: Pre-occupied port 8501 with a dummy listener, relaunched — `launcher.log` recorded `Selected port 58122`, and `/_stcore/health` on that port returned 200.
4. **Browser auto-open**: `webbrowser.open()` fires after the scheduled delay and the URL is reachable (confirmed above); this exact call path is also covered by the existing `test_main_spawns_subprocess_and_schedules_browser` unit test. Programmatically proving a *visible new browser window* appeared isn't reliable on this machine (dozens of pre-existing Chrome/Edge processes; Chrome hands new URLs to its existing process via IPC with no trace in any process's command line) — **this one sub-item stays a manual eyeball check** for whoever next runs the executable interactively.
5. **Content-level checks (`AppTest`, 17/17 passed)**: Home page model table shows both `current_speed` trials; Wave Height / Wind Speed pages render the "No models are currently available" info state with no exception; the `current_speed` exogenous flow (select model → upload valid XLSX → feature engineering → Run Forecast → plotly chart) completed end-to-end with a chart rendered; a malformed XLSX (missing `wav_hs`) produced the readable `st.error` "Failed to process uploaded file: Uploaded file is missing required columns: ['wav_hs']" with no uncaught exception; pointing the service at an empty models directory produced the readable empty-state message on both Home and the Current Speed page, no traceback.
6. **No telemetry / first-run dialog**: bundled `dist/MeteoceanForecast/.streamlit/config.toml` contains `gatherUsageStats = false` and `headless = true`; launcher spawns Streamlit with `cwd` set to the dist folder so this config is picked up automatically (per the fix already recorded in issue 04).
7. **Drop-in model update**: Copied a duplicate trial folder into `dist/MeteoceanForecast/models/current_speed/` while the exe was stopped. `scan_models()` against the dist folder went from 2 → 3 models immediately. Relaunched the actual `.exe` with the new folder present — clean startup, `/_stcore/health` → 200, no rebuild involved.
8. **Regression**: `streamlit run streamlitapp/app/Home.py` from source still works (separate port, health check 200) — packaging changes did not break the dev workflow.

**Known gap (not a bug):** only `streamlit/models/current_speed/` has real Prophet model files in this repo; `wave_height` and `wind_speed` have none. Their pages were verified to load cleanly and show the correct empty-state message, but the "model selector populated with pre-loaded models" criterion could only be exercised against `current_speed`. Full three-target coverage needs real `wave_height`/`wind_speed` model files added to the repo first.

No real bugs were found during this pass — no new bug issue was opened.

## Blocked by

- `04-pyinstaller-spec-and-streamlit-config.md`
