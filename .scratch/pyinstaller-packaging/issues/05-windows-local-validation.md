# 05 — Local Windows build & manual smoke test

Status: ready-for-agent

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

- [ ] `MeteoceanForecast.exe` launches without requiring Python to be installed
- [ ] Browser opens automatically to the Home page
- [ ] If port 8501 is occupied, a different port is used and the browser still opens correctly
- [ ] Home page displays the model selector populated with pre-loaded Prophet models
- [ ] All three forecast pages (Current Speed, Wave Height, Wind Speed) load without errors
- [ ] Exogenous XLSX upload flow works end-to-end (upload file → forecast runs → chart renders)
- [ ] Missing model files produce a readable error message in the app (not a Python traceback)
- [ ] Malformed XLSX produces a readable validation error in the app
- [ ] No Streamlit telemetry or first-run setup dialog appears
- [ ] `logs/launcher.log` exists next to the executable and contains the last startup attempt
- [ ] Copying a new `prophet_model.json` + `prophet_metadata.json` into `models/` and relaunching picks up the new model without a rebuild

## Blocked by

- `04-pyinstaller-spec-and-streamlit-config.md`
