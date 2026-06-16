# PRD: Package MeteoceanForecast as a Local Executable

Status: ready-for-agent

## Problem Statement

The MeteoceanForecast Streamlit app currently requires the end user to have Python installed, a virtual environment configured, and knowledge of how to launch Streamlit from a terminal. This makes it impossible to hand the app to non-developer users on Windows or Linux without a complex onboarding process. There is no portable runtime — every machine requires manual environment setup before the app can be used.

## Solution

Package the existing Streamlit app using PyInstaller into a one-folder distribution that a user can unzip and run by double-clicking a single executable. The packaged app starts a local Streamlit server, opens the browser automatically, and behaves identically to the development version — same pages, same model loading, same file upload flows. No Python installation is required on the end-user machine.

The distribution ships with pre-populated model files and a bundled Streamlit config. External runtime resources (model files) remain outside the executable so they can be updated independently without a new build.

## User Stories

1. As a Windows user, I want to double-click `MeteoceanForecast.exe` and have the app open in my browser automatically, so that I do not need to install Python or run terminal commands.
2. As a Linux user, I want to run `./MeteoceanForecast` and have the app open in my browser automatically, so that I can use the forecasting app without a development environment.
3. As a user, I want the app to find a free port automatically if 8501 is taken, so that I can run it alongside other Streamlit apps without manual port configuration.
4. As a user, I want to see the familiar three-page forecasting interface (Current Speed, Wave Height, Wind Speed) after launching the executable, so that my workflow is unchanged.
5. As a user, I want to select from the pre-loaded Prophet models on the Home page, so that I can begin forecasting immediately after launching.
6. As a user, I want to upload an exogenous XLSX file from anywhere on my machine using the file uploader, so that I can run exogenous model forecasts without placing files in a specific folder.
7. As a user, I want missing model files to produce a readable error message in the app, so that I understand what is wrong without needing a developer.
8. As a user, I want malformed exogenous XLSX files to produce a readable validation error in the app, so that I can fix my data without needing support.
9. As a user, I want all existing charts, tables, download buttons, and metrics to work exactly as in the development version, so that my analytical outputs are preserved.
10. As a user, I want the app to start without displaying Streamlit telemetry prompts or first-run setup dialogs, so that the experience is clean and professional.
11. As an admin deploying the app, I want to copy a new `prophet_model.json` + `prophet_metadata.json` into the `models/` folder and have the app pick it up on next launch, so that model updates do not require a new build or redistribution.
12. As an admin deploying the app, I want to control whether a Windows executable, a Linux executable, or both are produced by CI, using `BUILD_WINDOWS` and `BUILD_LINUX` environment variables, so that I can manage build costs and target platforms independently.
13. As an admin diagnosing a startup failure, I want to find a `logs/launcher.log` file next to the executable with the last three startup attempts logged, so that I can diagnose failures without attaching a debugger.
14. As a developer, I want the app to continue running normally from source (`streamlit run Home.py`) after all packaging changes, so that the development workflow is not disrupted.
15. As a developer, I want all file paths in the app to resolve correctly whether running from source or from a frozen bundle, so that I do not need separate codepaths for development and production.

## Implementation Decisions

### Distribution layout

```
dist/
  MeteoceanForecast/
    MeteoceanForecast.exe        ← Windows
    MeteoceanForecast            ← Linux
    models/
      current_speed/
        prophet_multiplicative_exogenous_trials/
          prophet_model.json
          prophet_metadata.json
        prophet_multiplicative_univariate_trials/
          prophet_model.json
          prophet_metadata.json
      wave_height/   (same structure)
      wind_speed/    (same structure)
    logs/
      launcher.log               ← created at first run; last 3 runs retained
    .streamlit/
      config.toml                ← bundled; suppresses prompts and telemetry
    (PyInstaller internals)
```

`.pkl` files are excluded from the distribution. They are training artifacts and are not loaded by the app at runtime.

No `data/` folder is shipped. Exogenous data is supplied entirely through the Streamlit file uploader. No `config/app_config.toml` is shipped; there are no user-configurable app settings at this time.

### Path utility module

A new `path_utils.py` module must be introduced. It is the single place that knows whether the app is running from source or from a frozen bundle, and it exposes all runtime directory paths. All other modules that currently derive paths from `__file__` must import from this module instead.

The module must distinguish:
- **Source root** — the project directory during development
- **Base dir** — `Path(sys.executable).parent` in a frozen bundle; `Path(__file__).parent.parent` from source
- **Models dir** — `base_dir / "models"`
- **Logs dir** — `base_dir / "logs"`
- **Streamlit config dir** — the bundled `.streamlit/` directory

Detection uses `getattr(sys, 'frozen', False)` — the standard PyInstaller sentinel.

### Launcher entry point

A new `launcher.py` is introduced as the PyInstaller entry point (not `Home.py`). It:

1. Configures rotating file logging to `logs/launcher.log` (retain last 3 files).
2. Finds a free port: tries 8501 first, then scans for any available port.
3. Spawns `streamlit run` as a subprocess, passing `--server.port <port>`, `--server.headless true`, and `--global.configDir <bundled .streamlit path>`.
4. Opens `http://localhost:<port>` in the default browser after a short startup delay (via `threading.Timer`).
5. Waits on the subprocess; forwards its exit code.

The launcher uses the subprocess approach (not Streamlit's programmatic API) for stability across Streamlit versions.

### Bundled Streamlit config

A `.streamlit/config.toml` is bundled inside the distribution with at minimum:

```toml
[browser]
gatherUsageStats = false

[server]
headless = true
```

The launcher passes `--global.configDir` pointing at this file so Streamlit ignores any config in the user's home directory.

### CI build pipeline

A GitHub Actions workflow produces platform-specific distributions:
- A Linux runner builds when `BUILD_LINUX=1`.
- A Windows runner builds when `BUILD_WINDOWS=1`.
- Each runner runs PyInstaller with a shared `.spec` file targeting `launcher.py`.
- The `.spec` file collects: the `streamlitapp/app/` tree, the `models/` tree (excluding `.pkl` files), the `.streamlit/config.toml`, and all Streamlit static and metadata files via `collect_all("streamlit")`.
- Known hidden imports for Prophet and its Stan backend must be declared in the `.spec` file.
- The build artifact is uploaded as a CI artifact (zipped distribution folder).

### Required code changes

The following existing source changes are required before packaging will work:

- `Home.py` — replace the `__file__`-relative `_MODELS_DIR` derivation with a call to `path_utils.get_models_dir()`.
- `pages/1_Current_Speed.py`, `pages/2_Wave_Height.py`, `pages/3_Wind_Speed.py` — replace the `sys.path.insert(0, str(Path(__file__).parents[1]))` hack. The `meteocean_forecast` package and `_page_template` must be importable from the bundle without manual `sys.path` manipulation; fix via proper package configuration in the `.spec` file.
- No changes to domain logic, feature engineering, model loading, or inference are permitted.

### Model update mechanism

The `models/` folder is an external runtime resource. Its folder structure (`models/<target_variable>/<trial_name>/prophet_model.json`) must remain stable. The model registry glob pattern in `model_registry.py` must not change, as it is the stable interface for future model update tooling. See ADR-0001.

## Testing Decisions

Good tests for this feature verify observable runtime behaviour, not internal module structure. Do not test PyInstaller internals or launcher implementation details.

**What makes a good test here:**
- Tests that the path utility returns the correct path given a mocked environment state (`sys.frozen`, `sys.executable`).
- Tests that the launcher selects a free port and passes it correctly to the subprocess invocation (mock `subprocess.Popen` and `socket`).
- End-to-end CI tests that hit the actual running executable over HTTP.

**Modules to test:**

| Module | Test type | Notes |
|---|---|---|
| `path_utils` | Unit | Mock `sys.frozen` and `sys.executable`; assert each path function returns the expected value in both modes. Fits alongside `test_json_model_loader.py`. |
| `launcher` | Integration | Mock `subprocess.Popen`, `socket`, `webbrowser.open`; assert correct port is found and passed; assert browser open is scheduled. New test file. |
| Packaged executable | E2E smoke (CI only) | After `pyinstaller` runs, launch the executable, poll `http://localhost:<port>/healthz` (Streamlit health endpoint) until it responds or a timeout is reached; assert HTTP 200. Runs on the build platform's CI runner only. |

**Prior art:** `tests/test_json_model_loader.py` and `tests/test_prophet_inference_contract.py` show the existing pattern for mocking file system state and asserting on domain outputs.

## Out of Scope

- **In-app model update UX** — drag-and-drop or in-app replacement of model files is a future feature. See ADR-0001.
- **Code signing** — the executable will not be signed for this release. Users on Windows may see a SmartScreen warning; this is acceptable for an internal distribution.
- **Auto-update / version checking** — the app does not check for newer versions of itself.
- **Cloud or server deployment** — this is strictly a local desktop executable. No containerisation or web hosting.
- **One-file mode** — one-folder distribution only. One-file mode is not considered due to slower startup and harder external file handling.
- **macOS support** — deferred; not a target platform for this release.
- **Retraining models** — the executable does not train or fine-tune models.
- **Changing model behaviour** — no model semantics may be altered as part of packaging.

## Further Notes

- **Prophet and Stan hidden imports** are a known PyInstaller pain point. The `.spec` file will need explicit `hiddenimports` for `prophet`, `pystan` or `cmdstanpy`, and related numerical backends. This list should be derived by running `pyinstaller --collect-all prophet` and inspecting what is missed on a clean environment.
- **Startup time** will be slower than running from source because PyInstaller must extract bundled files and Streamlit must initialise. A console window (or a launcher splash) showing "Starting MeteoceanForecast…" is recommended to prevent users from thinking the app has frozen.
- **Validation on a clean machine** is required before the first release. The smoke test in CI covers this for the Linux build; a separate manual validation step on a clean Windows machine (or a Windows CI runner without cached Python) is required for the Windows build.
- **The development workflow must not be broken.** All changes must be tested by running `streamlit run streamlitapp/app/Home.py` from the repo root and verifying the app behaves normally.
