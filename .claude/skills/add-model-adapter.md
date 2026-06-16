# Skill: add-model-adapter

**Trigger:** When the user asks to "add a new model", "integrate a new model family", "add LSTM/ARIMA/XGBoost support", or "register a new model type". Also run this skill proactively before writing any model-loading or adapter code to confirm the correct extension points.

---

## Goal

Add a new model family (e.g., LSTM, ARIMA, XGBoost) **without modifying any existing class** — only by adding new files and updating the two designated extension points. This enforces OCP: the system is open for extension, closed for modification.

---

## The Two Designated Extension Points

Everything that must change when a new model family is added is concentrated here:

1. **`config/model_registry.py` → `FEATURE_NAME_MAPS`** — add a key for each new exogenous trial directory name.
2. **`inference/model_loader.py`** — add a branch in `load_adapter()` to route the new file format to the new adapter. (If `load_adapter` does not exist yet, create it — see Step 3.)

Everything else stays untouched.

---

## Step 1 — Confirm the new model's contract

Before writing any code, answer:

| Question | Answer needed |
|---|---|
| What is the model family name? | e.g. `lstm`, `xgboost`, `arima` |
| What file format is the serialised model? | e.g. `.h5`, `.pkl`, `.json`, `.pt` |
| What is the expected filename? | e.g. `lstm_best_model.h5` |
| Is it univariate or exogenous (or both)? | Determines whether `feature_name_map` is needed |
| What are the required feature columns (if exogenous)? | Ordered list in positional order |
| Does the model's `predict()` return a `ds`/`yhat` DataFrame? | If not, the adapter must translate the output |

If any answer is unknown, ask the user before proceeding.

---

## Step 2 — Create the adapter file

Create `streamlitapp/src/meteocean_forecast/inference/<family>_adapter.py`.

The adapter **must** implement the same two public methods as `ProphetAdapter`:

```python
def predict_univariate(self, horizon_hours: int) -> pd.DataFrame: ...
def predict_exogenous(self, feature_df: pd.DataFrame, horizon_hours: int) -> pd.DataFrame: ...
```

Both methods **must** return a DataFrame with these columns:

```
ds            datetime64[ns]   — hourly timestamp
yhat          float64          — point forecast
yhat_lower    float64 | NaN    — lower bound (fill NaN if model has no uncertainty)
yhat_upper    float64 | NaN    — upper bound (fill NaN if model has no uncertainty)
target_variable  str           — copied from metadata.target_variable
```

Do not return extra columns — the page template only reads these five.

**Template (copy and adapt):**

```python
from __future__ import annotations

import pandas as pd

from meteocean_forecast.domain.model_metadata import ModelMetadata


class <Family>Adapter:
    """Thin wrapper around a loaded <Family> model."""

    def __init__(self, model, metadata: ModelMetadata) -> None:
        self._model = model
        self._metadata = metadata

    def predict_univariate(self, horizon_hours: int) -> pd.DataFrame:
        # Build future datetime index, run model, return standard 5-column df.
        raise NotImplementedError

    def predict_exogenous(self, feature_df: pd.DataFrame, horizon_hours: int) -> pd.DataFrame:
        missing = [c for c in self._metadata.required_features if c not in feature_df.columns]
        if missing:
            raise ValueError(f"feature_df is missing required columns: {missing}")
        # Slice, run model, return standard 5-column df.
        raise NotImplementedError
```

---

## Step 3 — Create the loader function

In `streamlitapp/src/meteocean_forecast/inference/model_loader.py`, add a `load_<family>_model(path: Path)` function that deserialises the new format. Do not modify the existing `load_prophet_from_json`.

**If a generic `load_adapter(meta: ModelMetadata)` dispatcher does not yet exist, create it:**

```python
def load_adapter(meta: ModelMetadata):
    """Route model loading to the correct adapter based on model_family."""
    if meta.model_family == "prophet":
        wrapper = load_prophet_from_json(meta.model_path)
        from meteocean_forecast.inference.prophet_adapter import ProphetAdapter
        return ProphetAdapter(wrapper, meta)
    if meta.model_family == "<family>":
        model = load_<family>_model(meta.model_path)
        from meteocean_forecast.inference.<family>_adapter import <Family>Adapter
        return <Family>Adapter(model, meta)
    raise ValueError(f"Unknown model_family: {meta.model_family!r}")
```

Then update `ForecastingService.__init__` to call `load_adapter(meta)` instead of instantiating `ProphetAdapter` directly. This is the **one and only** change to existing code that is required.

---

## Step 4 — Register the new model in `scan_models`

`scan_models` in `config/model_registry.py` currently globs for `prophet_model.json`. Extend the glob to include the new filename:

```python
MODEL_FILE_NAMES = ["prophet_model.json", "<family>_best_model.<ext>"]

for model_filename in MODEL_FILE_NAMES:
    for model_path in sorted(models_dir.glob(f"*/*/{model_filename}")):
        ...
```

Alternatively, if all model families are stored in the same directory layout, change the glob to `*/*/` and detect family from `prophet_metadata.json` or a sibling `model_info.json`.

---

## Step 5 — Update `load_model_metadata`

`load_model_metadata` in `model_loader.py` reads `prophet_metadata.json` to infer `model_type`, `required_features`, etc. For new families, either:

- Follow the same `<family>_metadata.json` convention and update `load_model_metadata` to accept a `family` parameter, or
- Write a separate `load_<family>_metadata(path: Path, target_variable: str, feature_maps: dict) -> ModelMetadata` function.

The returned `ModelMetadata` must have `model_family` set to the new family string.

---

## Step 6 — Update `FEATURE_NAME_MAPS` (exogenous models only)

In `config/model_registry.py`, add the trial directory name and its ordered feature list:

```python
FEATURE_NAME_MAPS: dict[str, list[str]] = {
    "prophet_multiplicative_exogenous_trials": [...],  # existing — do not touch
    "<new_trial_dir_name>": [
        "feature_col_a",
        "feature_col_b",
        # ... in the exact positional order the model was trained with
    ],
}
```

---

## Step 7 — Add model files to disk

Place the serialised model at:

```
streamlitapp/models/<target_variable>/<trial_name>/<family>_best_model.<ext>
```

And a metadata sidecar at:

```
streamlitapp/models/<target_variable>/<trial_name>/<family>_metadata.json
```

The metadata sidecar must contain at minimum:

```json
{
  "model_type": "univariate" | "exogenous",
  "extra_regressors": ["feature_0", "feature_1", ...],
  "frequency": "H"
}
```

---

## Step 8 — Write a test

Add a test in `streamlitapp/tests/test_<family>_inference_contract.py` that:

1. Creates a mock model (do not load real .pkl/.h5 files in tests).
2. Instantiates `<Family>Adapter` with the mock model and a synthetic `ModelMetadata`.
3. Calls `predict_univariate(horizon_hours=24)` and asserts the output has the 5 required columns.
4. Calls `predict_exogenous(feature_df, horizon_hours=24)` and asserts the same.
5. Asserts that passing a `feature_df` missing a required column raises `ValueError`.

---

## Checklist before declaring the task done

- [ ] `<family>_adapter.py` created with both predict methods returning the 5-column contract.
- [ ] `load_<family>_model()` added to `model_loader.py`.
- [ ] `load_adapter()` dispatcher created or updated.
- [ ] `ForecastingService.__init__` updated to call `load_adapter()` (the only change to existing code).
- [ ] `scan_models()` glob updated to discover the new file format.
- [ ] `FEATURE_NAME_MAPS` updated (exogenous models only).
- [ ] Model + metadata files placed under `models/`.
- [ ] Tests added and passing (`pytest -q`).
- [ ] `ruff check .` passes with no new errors.
- [ ] App launched and the new model appears in the Home registry table.

---

## What must NOT change

- `domain/model_metadata.py` — `ModelMetadata` is stable; do not add model-family-specific fields.
- `domain/forecast_request.py` — horizon validation logic is model-family-agnostic.
- `app/` pages — pages should work with the new model automatically via `ForecastingService`.
- `features/feature_engineering.py` — feature engineering is model-family-agnostic.
- Any existing `prophet_*` file — never modify working code to accommodate new code.
