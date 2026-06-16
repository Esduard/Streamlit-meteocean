# Context

Glossary of domain terms for the streamlit-meteocean project.

## Packaging

**Packaged app** — the PyInstaller-produced distribution of the Streamlit meteocean forecasting app; runs locally without requiring the end user to install Python or any dependencies.

**Distribution folder** — the output directory produced by PyInstaller (`dist/`), containing the executable and all companion folders (`models/`, `data/`, `logs/`).

**Bundled internal resource** — a file required for the app itself to run (e.g. static assets, internal templates, Streamlit metadata). Embedded inside the PyInstaller bundle at build time; not meant to be replaced by the user.

**External runtime resource** — a file the user may replace or supply after packaging (e.g. model files, exogenous XLSX data). Lives outside the executable, in a known folder next to it.

**Portable runtime** — the executable behaves identically regardless of where the distribution folder is placed on the user's machine; no developer-machine absolute paths are baked in.

**Target platforms** — Windows and Linux. Controlled by `BUILD_WINDOWS` and `BUILD_LINUX` environment variables in CI. Builds are platform-specific: the Windows executable is produced on a Windows CI runner; the Linux executable on a Linux runner.

**Distribution mode** — one-folder (not one-file). PyInstaller produces a directory containing the executable and companion folders. The `models/` folder ships pre-populated with the current trained Prophet models.

**Launcher** — a `launcher.py` entry point (the PyInstaller target) that spawns `streamlit run` as a subprocess and automatically opens the browser at `http://localhost:8501`.

**Model file** — a `prophet_model.json` file produced by training; the only model format the app loads at runtime. Companion `.pkl` files in the `models/` directory are training artifacts and are not shipped in the distribution.

**Logs** — startup and runtime logs written to `logs/launcher.log` next to the executable. The launcher rotates logs across the last 3 runs.

**Port selection** — the launcher auto-finds a free port at startup, passes it to Streamlit, and opens the browser to the correct URL. Port 8501 is tried first; if taken, any available port is used.

**Exogenous data** — a user-supplied XLSX file uploaded at runtime via Streamlit's file uploader. No `data/` folder is shipped in the distribution; users browse to their file from anywhere on their machine.

**Streamlit config** — a `.streamlit/config.toml` bundled inside the distribution that disables telemetry, suppresses first-run prompts, and sets `server.headless = true`. The launcher points Streamlit at this config via `--global.configDir`. No user-editable `app_config.toml` is shipped.

**Executable name** — `MeteoceanForecast`. Distribution folder: `dist/MeteoceanForecast/`. Binary: `MeteoceanForecast.exe` (Windows) or `MeteoceanForecast` (Linux).

**Model update** — replacing a model file in the `models/` folder with a newer trained version. The underlying mechanism is drop-in (copy files into the folder; the app reloads on next launch). In-app UX for model updates is a future feature, not part of the packaging scope. See ADR-0001.
