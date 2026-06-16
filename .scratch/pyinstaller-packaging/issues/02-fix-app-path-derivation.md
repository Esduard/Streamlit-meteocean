# 02 — Fix path derivation in app pages

Status: done

## Parent

`.scratch/pyinstaller-packaging/PRD.md`

## What to build

Replace all `__file__`-relative path derivations and `sys.path` hacks in the Streamlit app files with calls to `path_utils`.

Two specific changes:

1. `streamlitapp/app/Home.py` — replace `_MODELS_DIR = Path(__file__).parent.parent / "models"` with `path_utils.get_models_dir()`.

2. `streamlitapp/app/pages/1_Current_Speed.py`, `2_Wave_Height.py`, `3_Wind_Speed.py` — remove the `sys.path.insert(0, str(Path(__file__).parents[1]))` line from each. The `meteocean_forecast` package will be made importable by the PyInstaller `.spec` configuration (issue 04); these files must not patch `sys.path` at runtime.

No changes to domain logic, feature engineering, model loading, or inference.

## Acceptance criteria

- [x] `Home.py` derives the models directory via `path_utils.get_models_dir()`
- [x] No `sys.path.insert` calls remain in any page file
- [x] `streamlit run streamlitapp/app/Home.py` from the repo root loads models and all three pages correctly (verified via `streamlit.testing.v1.AppTest`, which replicates the real bootstrap's `_fix_sys_path` adding `app/` to `sys.path` before page scripts execute — no exceptions on Home or any of the 3 pages)
- [x] Existing tests (`pytest streamlitapp/tests/`) continue to pass (48 passed)

## Blocked by

- `01-path-utils-module.md`
