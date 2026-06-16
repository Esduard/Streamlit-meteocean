# 01 — `path_utils` module + unit tests

Status: done

## Parent

`.scratch/pyinstaller-packaging/PRD.md`

## What to build

Introduce `streamlitapp/src/meteocean_forecast/path_utils.py` as the single module that knows whether the app is running from source or from a frozen PyInstaller bundle. It must expose:

- `get_base_dir()` — `Path(sys.executable).parent` when frozen; `Path(__file__).parent` relative to the project root when running from source
- `get_models_dir()` — `base_dir / "models"`
- `get_logs_dir()` — `base_dir / "logs"`
- `get_streamlit_config_dir()` — `base_dir / ".streamlit"`

Frozen detection uses `getattr(sys, 'frozen', False)` — the standard PyInstaller sentinel.

Add unit tests alongside `streamlitapp/tests/test_json_model_loader.py`. Tests must mock both the `sys.frozen` attribute and `sys.executable` and assert each function returns the expected `Path` in source mode and in frozen mode.

## Acceptance criteria

- [x] `path_utils.py` exists under `streamlitapp/src/meteocean_forecast/`
- [x] All four path functions are exported and return `Path` objects
- [x] `get_base_dir()` returns the correct value in both source and frozen mode (verified by unit tests)
- [x] Unit tests pass with `pytest` from the `streamlitapp/` directory
- [x] Running `streamlit run streamlitapp/app/Home.py` from the repo root still works normally (verified by `scan_models` resolving to the same `models/` directory pre/post change in issue 02)

## Blocked by

None — can start immediately
