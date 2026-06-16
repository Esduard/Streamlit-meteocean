# 03 — Launcher entry point + unit tests

Status: done

## Parent

`.scratch/pyinstaller-packaging/PRD.md`

## What to build

Create `launcher.py` at the repo root as the PyInstaller entry point (not `Home.py`). It must:

1. Configure a `RotatingFileHandler` writing to `logs/launcher.log` (obtained via `path_utils.get_logs_dir()`), retaining the last 3 log files.
2. Find a free port: try 8501 first, then scan for any available port using `socket`.
3. Spawn `streamlit run streamlitapp/app/Home.py` as a subprocess, passing `--server.port <port>` and `--server.headless true`.

   **Deviation from spec:** the installed Streamlit CLI (1.57.0) has no `--global.configDir` flag (verified via `streamlit run --help`). Streamlit instead auto-discovers `${cwd}/.streamlit/config.toml` (highest-priority project-level config, per `streamlit/file_util.py::get_project_streamlit_file_path`). The launcher spawns the subprocess with `cwd=path_utils.get_base_dir()` instead, so the bundled `.streamlit/config.toml` at `base_dir/.streamlit/` (= `path_utils.get_streamlit_config_dir()`) is picked up automatically with no extra flag needed. Verified end-to-end: launcher spawns Streamlit, `/_stcore/health` and `/` both return HTTP 200.
4. Schedule `webbrowser.open(f"http://localhost:{port}")` via `threading.Timer` after a short startup delay.
5. Wait on the subprocess and forward its exit code.

Uses the subprocess approach (not Streamlit's programmatic API) for stability across Streamlit versions.

Add `streamlitapp/tests/test_launcher.py`. Tests must mock `subprocess.Popen`, `socket.socket`, and `webbrowser.open`, and assert: correct port is selected (including fallback), correct arguments are passed to Popen, and browser open is scheduled.

## Acceptance criteria

- [x] `launcher.py` exists at the repo root
- [x] `logs/` directory is created automatically if absent; `launcher.log` is written on startup
- [x] Port 8501 is used when free; an alternative port is selected when 8501 is occupied
- [x] Browser open is scheduled (not immediate) after subprocess is spawned
- [x] `test_launcher.py` tests pass with `pytest` (7 tests)
- [x] Running `streamlit run streamlitapp/app/Home.py` directly still works (launcher is additive)

## Blocked by

- `01-path-utils-module.md`
