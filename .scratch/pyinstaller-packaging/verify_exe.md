# Manually verifying MeteoceanForecast.exe

Everything scriptable about issue `05-windows-local-validation.md` has already been verified
(see that file for the automated results). This is the short list of things that genuinely
need a human's eyes — mainly "does it actually look right when a real person double-clicks it."

## 1. Locate the build

```
dist/MeteoceanForecast/MeteoceanForecast.exe
```

This was already built in this session. If it's missing or you want a fresh build:

```
.venv\Scripts\pyinstaller MeteoceanForecast.spec --noconfirm
```

## 2. Launch it

Double-click `dist\MeteoceanForecast\MeteoceanForecast.exe` in File Explorer (or run it from a
terminal so you can see the console window).

Watch for:
- [ ] A console window appears showing the launcher starting up (no immediate crash).
- [ ] **Your default browser opens automatically** within a couple of seconds, pointed at
      `http://localhost:8501` (or a different port if 8501 was busy — see the console/log).
- [ ] The page that loads is the **Home** page ("Meteocean Forecasting App"), not a blank tab
      or a browser error page.
- [ ] No Streamlit "Welcome"/telemetry/email-signup dialog appears anywhere.

## 3. Look at the Home page

- [ ] A table titled "Available Models" is visible and lists two `current_speed` rows
      (`prophet_multiplicative_exogenous_trials` and `prophet_multiplicative_univariate_trials`).
- [ ] The page renders cleanly — no red error boxes, no raw Python traceback text.

> Note: `wave_height` and `wind_speed` have no model files in this repo yet, so this table will
> only ever show `current_speed` rows until those models are added. That's expected, not a bug.

## 4. Click through all three pages (left sidebar)

For **Current Speed**, **Wave Height**, **Wind Speed**:
- [ ] Page loads without an error box or traceback.
- [ ] Wave Height / Wind Speed should show a blue info box: *"No models are currently available
      for **wave_height/wind_speed**..."* — this is the correct empty state, not a failure.

## 5. Run a real forecast on Current Speed

- [ ] Select the **univariate** model from the dropdown, pick a horizon, click **Run Forecast**.
      A chart should render within a few seconds.
- [ ] Select the **exogenous** model instead. Upload any XLSX with the standard 40-column raw
      meteocean schema (see `docs/` or `streamlitapp/tests/conftest.py::_make_raw_df` for the
      expected columns if you need a sample). You should see "Loaded N rows...", then "Features
      ready...", then after clicking **Run Forecast**, a chart with a shaded confidence band.
- [ ] Try uploading a clearly wrong file (e.g. a `.xlsx` missing a required column, or a
      `.txt` renamed to `.xlsx`). You should get a **red error message** describing what's wrong
      — not a Python traceback dumped into the page.

## 6. Port fallback (optional, only if you want to double check)

1. Start any other program that occupies port 8501 (or just leave a previous instance of the
   exe running).
2. Launch a second instance of `MeteoceanForecast.exe`.
3. It should still open a browser tab successfully, just on a different port — check the
   console output or `logs\launcher.log` for the port it picked.

## 7. Check the log file

Open `dist\MeteoceanForecast\logs\launcher.log` in a text editor.
- [ ] It exists and contains lines like `Starting MeteoceanForecast launcher`, `Selected port
      8501`, and the spawn command — i.e. evidence of the last startup attempt.

## 8. Drop-in model update (optional)

1. Close the running exe.
2. Copy any existing trial folder, e.g.
   `dist\MeteoceanForecast\models\current_speed\prophet_multiplicative_univariate_trials`,
   to a new folder name (still containing only `prophet_model.json` and
   `prophet_metadata.json`) under the same `current_speed` directory.
3. Relaunch the exe — no rebuild. The Home page's model table should now show three
   `current_speed` rows instead of two.
4. Delete the extra folder afterwards if you don't want it kept around.

---

If anything here looks wrong (traceback shown to the user, browser doesn't open, app won't
start at all, etc.), open a new bug issue under `.scratch/pyinstaller-packaging/issues/` and
link it from `05-windows-local-validation.md`, per that issue's own instructions.
