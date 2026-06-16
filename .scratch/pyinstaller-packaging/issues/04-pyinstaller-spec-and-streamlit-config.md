# 04 — PyInstaller `.spec` file + bundled Streamlit config

Status: done

## Parent

`.scratch/pyinstaller-packaging/PRD.md`

## What to build

Two deliverables in one slice because the config file is only meaningful as part of the bundle:

**`.streamlit/config.toml`** — create at the repo root with at minimum:

```toml
[browser]
gatherUsageStats = false

[server]
headless = true
```

**`MeteoceanForecast.spec`** — PyInstaller spec file targeting `launcher.py` that collects:

- The full `streamlitapp/app/` source tree (so Streamlit discovers pages and the `meteocean_forecast` package is on the bundle's `sys.path` without manual `sys.path` patching)
- The `models/` directory tree, excluding all `.pkl` files
- The `.streamlit/config.toml` created above, placed at `_internal/.streamlit/config.toml` inside the bundle (or wherever `path_utils.get_streamlit_config_dir()` resolves to in frozen mode)
- All Streamlit static and metadata files via `collect_all("streamlit")`
- Explicit `hiddenimports` for Prophet and its Stan/cmdstanpy backend (derive the list by running `pyinstaller --collect-all prophet` on a clean environment and inspecting what is missed)

The distribution layout must match:

```
dist/MeteoceanForecast/
  MeteoceanForecast          ← Linux executable
  MeteoceanForecast.exe      ← Windows executable
  models/<target>/<trial>/prophet_model.json
  models/<target>/<trial>/prophet_metadata.json
  logs/                      ← created at first run
  .streamlit/config.toml
```

`.pkl` files must not appear in `dist/`.

## Acceptance criteria

- [x] `.streamlit/config.toml` exists at the repo root
- [x] `MeteoceanForecast.spec` exists at the repo root
- [x] `pyinstaller MeteoceanForecast.spec` completes without errors on Linux
- [x] The produced executable launches, opens the browser, and serves all three pages (verified: `/_stcore/health` → 200, `/`, `/Current_Speed`, `/Wave_Height`, `/Wind_Speed` → 200, no tracebacks in `logs/launcher.log`)
- [x] No `.pkl` files appear anywhere under `dist/MeteoceanForecast/` (`find -iname "*.pkl"` → 0 results)
- [x] The `models/` folder is outside the executable (can be updated without a rebuild) — lives at `dist/MeteoceanForecast/models/`, a plain directory on disk
- [x] `streamlit run streamlitapp/app/Home.py` from the repo root still works normally (re-verified after the spec/launcher fixes below)

## Notes on bugs found and fixed while validating the build

1. **`--global.configDir` does not exist** in the installed Streamlit CLI (1.57.0; confirmed via `streamlit run --help`). Streamlit instead auto-discovers `${cwd}/.streamlit/config.toml` as the highest-priority project-level config (`file_util.get_project_streamlit_file_path`). Fixed in `launcher.py` by spawning the subprocess with `cwd=path_utils.get_base_dir()` instead of passing the flag — see the note already recorded in issue 03.
2. **`models/` was bundled at the wrong path.** First spec draft placed the models tree at `streamlitapp/models` inside the bundle (mirroring the source layout), but `path_utils.get_models_dir()` resolves to `<exe_parent>/models` in frozen mode. Fixed the spec's `_tree_datas` destination for the models tree to `Path("models")` so it lands directly at `dist/MeteoceanForecast/models/`.
3. **`RuntimeError: server.port does not work when global.developmentMode is true`** at actual runtime. Streamlit infers `global.developmentMode` from whether its own `__file__` contains `"site-packages"` (`streamlit/config.py::_global_development_mode`) — true when installed normally, false inside a PyInstaller bundle, which then conflicts with passing `--server.port` explicitly. Fixed by adding `--global.developmentMode false` to the frozen-mode Streamlit invocation in `launcher.py::_build_streamlit_command`.
4. **PyInstaller can't see `Home.py`'s imports.** Home.py/pages are loaded dynamically by Streamlit at runtime (via the `--run-streamlit-worker` re-exec described in issue 03), not imported by `launcher.py`, so PyInstaller's static analysis — which only follows imports from the one entry script it's given — would miss `meteocean_forecast` and `plotly`. Fixed by adding explicit top-level imports of those modules in `launcher.py` (commented with the why) so PyInstaller's modulegraph picks them up transitively.
5. Used `contents_directory="."` on the `EXE`/`COLLECT` in the spec (re-enabling the pre-6.0 onedir layout) so bundled data and the executable sit in the same flat directory — matching `path_utils`' frozen-mode contract that `models/`, `logs/`, and `.streamlit/` all live directly beside the executable, with no `_internal/` subfolder in between.
6. `collect_all("prophet")` pulls in the full `prophet/stan_model/` directory (~37 MB, includes a bundled `cmdstan` toolchain) even though the app only calls `.predict()` on pre-fitted JSON models and never invokes the Stan backend at runtime. Left as-is per the issue's explicit instruction to use `collect_all`/hiddenimports for Prophet's Stan backend; trimming this is a possible follow-up if distribution size becomes a concern.

## Blocked by

- `02-fix-app-path-derivation.md`
- `03-launcher-entry-point.md`
