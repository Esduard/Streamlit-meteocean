# Streamlit App — Follow-up Brief

This document is for the next agent picking up where the previous session left off.

---

## What Was Built

A complete Streamlit meteocean forecasting app was created inside `streamlitapp/`.
The full file tree:

```
streamlitapp/
├── app/
│   ├── Home.py                        # entry point; loads models; shows registry
│   ├── _page_template.py              # shared UI logic for all 3 target pages
│   └── pages/
│       ├── 1_Current_Speed.py
│       ├── 2_Wave_Height.py
│       └── 3_Wind_Speed.py
├── src/
│   └── meteocean_forecast/
│       ├── domain/
│       │   ├── model_metadata.py      # frozen ModelMetadata dataclass
│       │   └── forecast_request.py    # ForecastRequest + HorizonValidationError
│       ├── config/
│       │   └── model_registry.py      # scans models/ dir; FEATURE_NAME_MAPS constant
│       ├── features/
│       │   ├── raw_xlsx_reader.py     # reads & validates raw XLSX (40-column schema)
│       │   └── feature_engineering.py # full port from feature_engineering.ipynb
│       └── inference/
│           ├── model_loader.py        # loads pkl; adds pipeline/ to sys.path
│           ├── prophet_adapter.py     # wraps ProphetRegressor; typed predict methods
│           └── forecasting_service.py # orchestrates scan + load + inference
├── tests/
│   ├── conftest.py                    # synthetic 40-col fixture (raw_df)
│   ├── test_feature_engineering_contract.py
│   ├── test_horizon_validation.py
│   └── test_prophet_inference_contract.py  # fully mocked; no pkl needed
├── pyproject.toml
└── requirements.txt
```

### Key design decisions already made

- Prophet `.pkl` files live in `models/<target_variable>/<trial_name>/prophet_best_model.pkl`.
  `scan_models()` walks this layout automatically.
- The pkl was serialised as `models.prophet.ProphetRegressor`. `model_loader.py` inserts
  `pipeline/` into `sys.path` before `joblib.load()` so unpickling resolves.
  A TODO comment marks this for future migration to Prophet JSON.
- The exogenous model has **29 regressors** named `feature_0`…`feature_28`. Their human-readable
  names are hard-coded in `config/model_registry.py` under `FEATURE_NAME_MAPS`:
  ```python
  "prophet_multiplicative_exogenous_trials": [
      "wav_hmax", "wav_tp", ..., "sw_cur_spd_fourier"   # 29 names in positional order
  ]
  ```
  `feature_0 = wav_hmax`, `feature_28 = sw_cur_spd_fourier`.
- **V1 limitations** (documented in code and UI, not bugs):
  - PCA (8 components) is re-fitted on the uploaded XLSX data.
  - StandardScaler is re-fitted on the uploaded XLSX data.
  - The Fourier feature (`sw_cur_spd_fourier`) requires `sw_cur_spd` in the uploaded file;
    it is fitted on the full uploaded dataset (inference mode, no train/test split).
- `wave_height` and `wind_speed` pages render a graceful "no models loaded" state
  because no `.pkl` files exist for those targets yet.

---

## What Has NOT Been Done Yet

### 1. Dependencies not installed — BLOCKING

The active Python is `pipeline/.venv/bin/python3`. These packages are **missing**:

```
streamlit, plotly, openpyxl, ruff, pytest
```

Already installed: `prophet`, `scikit-learn`, `joblib`, `pandas`, `numpy`.

**Fix:**
```bash
cd streamlitapp
pip install -r requirements.txt
```

Or install the package in editable mode first (already done once but env may not persist):
```bash
pip install -e .
pip install streamlit plotly openpyxl ruff pytest
```

### 2. Verification not run — BLOCKING

None of the acceptance checks from the skill specs have been executed:

```bash
cd streamlitapp
ruff format .
ruff check .
pytest -q
streamlit run app/Home.py
```

Expected issues to watch for:
- `ruff check` may flag the `from __future__ import annotations` pattern or unused imports.
- The `assert` statement in `forecasting_service.py:36` may trigger a ruff warning.
- `streamlit run app/Home.py` takes ~15–30 s on first run because it loads the two
  current_speed Prophet pkl files (15 MB each) and Prophet initialises Stan.

### 3. Manual end-to-end test not done

After `streamlit run app/Home.py`:

- [ ] Home page shows both `current_speed` models in the registry table.
- [ ] **Current Speed — univariate**: select model → set 720h horizon → Run Forecast →
  line chart renders with confidence band → CSV download works.
- [ ] **Current Speed — exogenous**: upload one of `dados/*.xlsx` → spinner runs feature
  engineering → success message shows row count → slider limited to file length →
  Run Forecast → chart renders.
- [ ] **Wave Height / Wind Speed pages**: both show the "no models loaded" info message
  without crashing.

A raw XLSX for testing is at (pick any):
```
dados/era5_wnd_wav_and_cmems_re_bra_cur2d_FZA-M-59 - PUC.xlsx
```

### 4. Known performance issue (low priority)

`ForecastingService.__init__` loads each pkl **twice**:
- Once inside `scan_models()` → `load_model_metadata()` → `load_prophet_wrapper()`
- Once directly to create the `ProphetAdapter`

Fix: refactor `scan_models` to return `(ModelMetadata, wrapper)` tuples, or cache wrappers
inside `load_model_metadata`. Not blocking for v1.

### 5. wave_height and wind_speed models do not exist

Only `current_speed` models are in `streamlitapp/models/`. When wave_height or wind_speed
models are trained and their pkl files are placed at:
```
streamlitapp/models/wave_height/<trial_name>/prophet_best_model.pkl
streamlitapp/models/wind_speed/<trial_name>/prophet_best_model.pkl
```
the app will pick them up automatically on restart. No code changes needed — but
`FEATURE_NAME_MAPS` in `config/model_registry.py` must be updated with the correct
feature name list for each new exogenous model.

### 6. Future migration task (documented, not blocking)

Replace pickle serialisation with Prophet JSON:
```python
from prophet.serialize import model_to_json, model_from_json
```
See Prophet docs: https://facebook.github.io/prophet/docs/additional_topics.html
Both `model_loader.py` and `config/model_registry.py` carry `TODO` comments for this.

---

## How to Run the App

```bash
cd /home/eduardo/Documents/exactaRepos/margem_equatorial_analise_exploratoria/streamlitapp

# 1. Install deps (once)
pip install -r requirements.txt

# 2. Install package in editable mode (once)
pip install -e .

# 3. Lint and format
ruff format .
ruff check .

# 4. Tests
pytest -q

# 5. Launch
streamlit run app/Home.py
```

---

## Critical File Locations

| Purpose | Path |
|---|---|
| App entry point | `streamlitapp/app/Home.py` |
| Shared page logic | `streamlitapp/app/_page_template.py` |
| Feature engineering | `streamlitapp/src/meteocean_forecast/features/feature_engineering.py` |
| Feature name map | `streamlitapp/src/meteocean_forecast/config/model_registry.py` → `FEATURE_NAME_MAPS` |
| Model loader | `streamlitapp/src/meteocean_forecast/inference/model_loader.py` |
| Forecasting service | `streamlitapp/src/meteocean_forecast/inference/forecasting_service.py` |
| Source notebook | `feature_engineering.ipynb` (repo root — not inside streamlitapp) |
| Test data XLSX | `dados/era5_wnd_wav_and_cmems_re_bra_cur2d_FZA-M-59 - PUC.xlsx` |
| Existing models | `streamlitapp/models/current_speed/` (2 pkl files) |
