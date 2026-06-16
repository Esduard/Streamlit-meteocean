# Migration: Prophet models from `.pkl` to `.json`

## Context

Prophet's official docs recommend JSON serialization over pickle. The top-level `models/` directory already exports both `prophet_model.json` and `prophet_metadata.json` alongside the pkl. The `streamlitapp/models/` directory currently only contains `prophet_best_model.pkl` files.

The current pkl loading has two known fragilities:
- Requires adding `pipeline/` to `sys.path` at runtime so the pickled `models.prophet.ProphetRegressor` class resolves.
- `joblib.load` on a pkl executes arbitrary code — a security hazard if the path is ever wrong.

JSON loading via Prophet's `model_from_json` eliminates both.

---

## Scope

Files affected by the implementation:

| File | Change |
|---|---|
| `streamlitapp/src/meteocean_forecast/inference/model_loader.py` | Replace `load_prophet_wrapper` (pkl) with `load_prophet_from_json`. Remove `_ensure_pipeline_importable`. Add helper to read `prophet_metadata.json`. |
| `streamlitapp/src/meteocean_forecast/config/model_registry.py` | Change glob from `*/*/prophet_best_model.pkl` to `*/*/prophet_model.json`. Read metadata from `prophet_metadata.json` instead of unpickling. |
| `streamlitapp/models/<target>/<trial>/` | Add `prophet_model.json` and `prophet_metadata.json` to each trial directory (copy from top-level `models/` or re-export from pipeline). Do NOT delete the existing `.pkl` files until the migration is validated end-to-end. |
| `streamlitapp/src/meteocean_forecast/domain/model_metadata.py` | `model_path` semantics shift from pointing to the pkl to pointing to the `prophet_model.json`. No field rename needed, but update docstring. |
| `streamlitapp/src/meteocean_forecast/inference/forecasting_service.py` | Update any calls to `load_prophet_wrapper` to use the new JSON loader. |
| `streamlitapp/tests/test_prophet_inference_contract.py` | Update mocks and fixtures — see Testing section. |
| `streamlitapp/tests/conftest.py` | Add JSON-based fixtures if needed. |

---

## Implementation plan

### Step 1 — Populate JSON files in `streamlitapp/models/`

The top-level `models/<target>/<trial>/` already has `prophet_model.json` and `prophet_metadata.json`. Copy them into the corresponding `streamlitapp/models/<target>/<trial>/` directories. Confirm the directory names match exactly.

Do not overwrite existing `.pkl` files.

### Step 2 — Rewrite `model_loader.py`

Replace the entire pkl-based loading path:

```python
# OLD (remove)
def _ensure_pipeline_importable(pkl_path: Path) -> None: ...
def load_prophet_wrapper(pkl_path: Path): ...   # uses joblib.load

# NEW
def load_prophet_from_json(json_path: Path):
    """Load a Prophet model from a JSON file using prophet_model_from_json."""
    from prophet.serialize import model_from_json
    with open(json_path) as f:
        return model_from_json(f.read())

def load_metadata_json(json_path: Path) -> dict:
    """Read prophet_metadata.json sitting next to prophet_model.json."""
    import json
    meta_path = json_path.parent / "prophet_metadata.json"
    with open(meta_path) as f:
        return json.load(f)

def load_model_metadata(json_path: Path, target_variable: str, feature_name_maps: dict) -> ModelMetadata:
    meta = load_metadata_json(json_path)
    model_type = "exogenous" if meta.get("use_exogenous") else "univariate"
    required_features = tuple(meta.get("regressors", []))
    dir_name = json_path.parent.name
    raw_map = feature_name_maps.get(dir_name)
    feature_name_map = tuple(raw_map) if raw_map is not None else None
    return ModelMetadata(
        target_variable=target_variable,
        model_family="prophet",
        model_type=model_type,
        model_path=json_path,
        required_features=required_features,
        feature_name_map=feature_name_map,
        frequency=meta.get("freq", "H"),
        max_univariate_horizon_hours=8760,
        display_name=dir_name,
    )
```

### Step 3 — Rewrite `model_registry.py`

Change the glob and the loader call:

```python
# OLD
for pkl_path in sorted(models_dir.glob("*/*/prophet_best_model.pkl")):
    metadata = load_model_metadata(pkl_path, target_variable, FEATURE_NAME_MAPS)

# NEW
for json_path in sorted(models_dir.glob("*/*/prophet_model.json")):
    metadata = load_model_metadata(json_path, target_variable, FEATURE_NAME_MAPS)
```

### Step 4 — Update `forecasting_service.py`

Replace `load_prophet_wrapper(meta.model_path)` with `load_prophet_from_json(meta.model_path)`.

The returned object is a raw `Prophet` instance (not a `ProphetRegressor` wrapper), so update `ProphetAdapter` if it currently accesses `wrapper.model` — after this change `wrapper` IS the model. Verify the adapter's `.model.make_future_dataframe` and `.model.predict` call sites.

### Step 5 — Validation gate before removing pkl files

Run the full test suite and do a manual smoke-test through the Streamlit UI for both univariate and exogenous models. Only after both pass, mark the `.pkl` files as safe to remove (do not delete them in this PR).

---

## Testing

> **Agent separation rule**: the agent that writes the tests must NOT be the same agent that implements Steps 1–4. Hand off the spec at this section boundary.

### What the testing agent receives

- The updated `model_loader.py`, `model_registry.py`, and `forecasting_service.py`.
- This spec (so it understands intent).
- Access to the existing test files.

### Tests to update

**`test_prophet_inference_contract.py`**

- `_make_meta()`: change `model_path=Path("/fake/prophet_best_model.pkl")` to `model_path=Path("/fake/prophet_model.json")`.
- `test_service_routes_univariate` and `test_service_routes_exogenous`: the patch target changes from `load_prophet_wrapper` to `load_prophet_from_json`. The mock's interface also changes: the old mock had `wrapper.model.predict(...)` and `wrapper.model.make_future_dataframe(...)`; the new mock is the Prophet model directly, so calls become `mock.predict(...)` and `mock.make_future_dataframe(...)`. Update `_make_wrapper()` accordingly.

### New tests to add

Add a new file `streamlitapp/tests/test_json_model_loader.py`:

1. **`test_load_metadata_json_reads_use_exogenous`**: given a tmp directory with a synthetic `prophet_metadata.json` that sets `use_exogenous: true`, assert `load_metadata_json` returns the correct dict.
2. **`test_load_model_metadata_exogenous`**: same synthetic metadata, assert the returned `ModelMetadata` has `model_type == "exogenous"` and `required_features == tuple(regressors_in_file)`.
3. **`test_load_model_metadata_univariate`**: synthetic metadata with `use_exogenous: false` and empty `regressors`, assert `model_type == "univariate"` and `required_features == ()`.
4. **`test_scan_models_finds_json`**: create a tmp directory tree `target_var/trial_name/prophet_model.json` + `prophet_metadata.json`, mock `load_prophet_from_json` (or use `prophet.serialize` if available in test env), call `scan_models`, assert one `ModelMetadata` is returned with correct `target_variable` and `display_name`.
5. **`test_scan_models_skips_malformed_metadata`**: create a trial dir with `prophet_model.json` but a malformed (empty) `prophet_metadata.json`, assert `scan_models` returns an empty list and emits a warning (not an exception).

### Regression tests to keep green

All existing tests in `test_horizon_validation.py` and `test_feature_engineering_contract.py` must continue to pass unchanged — they do not touch the loader.

---

## Constraints

- Do not delete `.pkl` files as part of this migration PR.
- `prophet_metadata.json` is the single source of truth for `use_exogenous` and `regressors`. Do not re-derive these from the model object.
- `FEATURE_NAME_MAPS` in `model_registry.py` stays as the source of truth for human-readable feature names; this migration does not remove it.
- `model_path` on `ModelMetadata` will point to `prophet_model.json` after migration; any downstream code that constructs paths relative to `model_path` must be updated.
- Do not introduce a compatibility shim that tries pkl first and JSON second — commit to JSON only.
