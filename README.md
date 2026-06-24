# Streamlit Meteocean Forecasting App

A Streamlit application for hourly meteocean forecasting using Prophet models trained on ERA5 / CMEMS data.

---

## I. Features

### Target variables

The app forecasts three oceanographic variables, each backed by its own family of Prophet models:

| Target | Unit | Available models |
|---|---|---|
| Current Speed | m/s | Univariate, Exogenous |
| Wave Height | m | _(no models yet)_ |
| Wind Speed | m/s | _(no models yet)_ |

Wave Height and Wind Speed pages render a graceful "no models loaded" state until trained models are placed in the `models/` directory.

### Model types

**Univariate**
- No feature file needed.
- The app builds the future datetime index internally from the model's last training timestamp.
- Forecast horizon is adjustable up to **8760 hours (1 year)** via a slider.

**Exogenous**
- Requires an uploaded XLSX file containing raw hourly meteocean data (40-column schema).
- The uploaded file is run through the full feature engineering pipeline (see below) and the result feeds Prophet as external regressors.
- The maximum forecast horizon equals the number of rows in the processed file; the slider is clamped to that limit.

### Feature engineering pipeline (exogenous models)

Ported from `references/feature_engineering.ipynb` into deterministic, testable Python modules:

1. **U/V decomposition** — converts wind/wave/current directional columns to U and V components (14 new columns).
2. **Wave energy** — computes spectral wave energy from height and period.
3. **Fourier current feature** (`sw_cur_spd_fourier`) — requires `sw_cur_spd` in the uploaded file.
4. **Southern-hemisphere seasonal dummies** — `is_summer`, `is_autumn`, `is_winter`, `is_spring` (December = summer).
5. **Annual Fourier harmonics** — `annual_sin`, `annual_cos`, `annual_phase`.
6. **PCA** — reduces the expanded feature set to 8 components.
7. **StandardScaler** — scales the PCA output.
8. **Column renaming** — final columns are named `feature_0 … feature_N` to match Prophet regressor names from training.

> **V1 limitation:** PCA and StandardScaler are re-fitted on each uploaded file, not serialised from training time. Accuracy may differ from training benchmarks if the uploaded distribution diverges significantly from the training set.

### Forecast output

Every forecast returns a dataframe with columns:

| Column | Description |
|---|---|
| `ds` | Hourly timestamp |
| `yhat` | Point forecast |
| `yhat_lower` | Lower bound of uncertainty interval |
| `yhat_upper` | Upper bound of uncertainty interval |
| `target_variable` | One of `current_speed`, `wave_height`, `wind_speed` |

Results are displayed as an interactive Plotly chart (line + shaded 95% interval) and can be downloaded as CSV.

---

## II. Architectural Overview

```
streamlit-meteocean/
├── models/                              # source model files (not deployed directly)
│   └── current_speed/
│       ├── prophet_multiplicative_exogenous_trials/
│       │   ├── prophet_model.json
│       │   └── prophet_metadata.json
│       └── prophet_multiplicative_univariate_trials/
│           ├── prophet_model.json
│           └── prophet_metadata.json
├── streamlitapp/                        # deployable app package
│   ├── app/
│   │   ├── Home.py                      # entry point — loads models, renders registry table
│   │   ├── _page_template.py            # shared UI logic reused by all three target pages
│   │   └── pages/
│   │       ├── 1_Current_Speed.py       # calls render_forecast_page("current_speed")
│   │       ├── 2_Wave_Height.py         # calls render_forecast_page("wave_height")
│   │       └── 3_Wind_Speed.py          # calls render_forecast_page("wind_speed")
│   ├── models/                          # model files served by the app at runtime
│   │   └── current_speed/
│   │       ├── prophet_multiplicative_exogenous_trials/
│   │       │   ├── prophet_model.json
│   │       │   └── prophet_metadata.json
│   │       └── prophet_multiplicative_univariate_trials/
│   │           ├── prophet_model.json
│   │           └── prophet_metadata.json
│   ├── src/
│   │   └── meteocean_forecast/
│   │       ├── domain/
│   │       │   ├── model_metadata.py    # frozen ModelMetadata dataclass
│   │       │   └── forecast_request.py  # ForecastRequest + HorizonValidationError
│   │       ├── config/
│   │       │   └── model_registry.py    # scans models/ dir; defines FEATURE_NAME_MAPS
│   │       ├── features/
│   │       │   ├── raw_xlsx_reader.py   # reads and validates raw 40-column XLSX
│   │       │   └── feature_engineering.py  # full pipeline (U/V, PCA, Fourier, scaler)
│   │       └── inference/
│   │           ├── model_loader.py      # loads Prophet models from JSON; reads metadata JSON
│   │           ├── prophet_adapter.py   # typed predict_univariate / predict_exogenous methods
│   │           └── forecasting_service.py  # orchestrates scan → load → inference
│   ├── tests/
│   │   ├── conftest.py                  # synthetic 40-column raw_df fixture
│   │   ├── test_feature_engineering_contract.py
│   │   ├── test_horizon_validation.py
│   │   ├── test_prophet_inference_contract.py  # ProphetAdapter + ForecastingService (mocked)
│   │   └── test_json_model_loader.py    # load_metadata_json, load_model_metadata, scan_models
│   ├── pyproject.toml
│   └── requirements.txt
└── references/
    └── feature_engineering.ipynb        # source notebook for the feature pipeline
```

### Module responsibilities

| Module | Responsibility |
|---|---|
| `Home.py` | Loads `ForecastingService` once via `@st.cache_resource`; stores it in `st.session_state`; shows the model registry table. |
| `_page_template.py` | `render_forecast_page(target)` — handles model selection, XLSX upload, feature engineering spinner, horizon slider, forecast button, Plotly chart, and CSV download. |
| `domain/model_metadata.py` | Immutable `ModelMetadata` dataclass: target variable, model type, path to `prophet_model.json`, required feature columns, frequency, max horizon, display name. |
| `domain/forecast_request.py` | `ForecastRequest` factory methods (`for_univariate`, `for_exogenous`) that validate horizon bounds and raise `HorizonValidationError` on invalid input. |
| `config/model_registry.py` | `scan_models(models_dir)` globs `*/*/prophet_model.json`, loads metadata for each, returns a sorted list of `ModelMetadata`. `FEATURE_NAME_MAPS` maps each trial directory name to its ordered list of human-readable feature names (`feature_0 = wav_hmax`, …). |
| `features/raw_xlsx_reader.py` | Reads an XLSX file upload and validates it against the expected 40-column meteocean schema. |
| `features/feature_engineering.py` | `engineer_features(raw_df)` runs the full transformation pipeline. `select_and_scale_features(df, names)` renames selected columns to `feature_0 … feature_N`. |
| `inference/model_loader.py` | `load_prophet_from_json(path)` — deserialises a Prophet model via `prophet.serialize.model_from_json`. `load_metadata_json(path)` — reads `prophet_metadata.json` for `use_exogenous`, `regressors`, and `freq`. `load_model_metadata(path, target, maps)` — constructs a `ModelMetadata` from the JSON files. |
| `inference/prophet_adapter.py` | `ProphetAdapter` wraps a raw `Prophet` instance. `predict_univariate(hours)` builds the future dataframe internally. `predict_exogenous(feature_df, hours)` validates columns and passes the feature dataframe directly to Prophet. Both return a standardised output dataframe. |
| `inference/forecasting_service.py` | `ForecastingService.__init__` scans for models and constructs one `ProphetAdapter` per model. `forecast(request)` routes to the correct adapter method. `prepare_exogenous_features(raw_df, meta)` runs the feature pipeline for a given model. |

### Data flow

```
User uploads XLSX
       │
       ▼
raw_xlsx_reader.read_raw_xlsx()
       │
       ▼
feature_engineering.engineer_features()
       │
       ▼
feature_engineering.select_and_scale_features()   ← renames to feature_0…N
       │
       ▼
ForecastRequest.for_exogenous(meta, feature_df, horizon)
       │
       ▼
ForecastingService.forecast(request)
       │
       ▼
ProphetAdapter.predict_exogenous(feature_df, horizon)
       │
       ▼
Prophet.predict(future_df)  →  yhat, yhat_lower, yhat_upper
```

For univariate models the upload and feature engineering steps are skipped; `ProphetAdapter.predict_univariate(horizon)` calls `Prophet.make_future_dataframe` internally.

### Adding a new model

1. Train the model and export `prophet_model.json` + `prophet_metadata.json` with the pipeline.
2. Place both files at `streamlitapp/models/<target_variable>/<trial_name>/`.
3. If the model is exogenous, add the ordered feature name list to `FEATURE_NAME_MAPS` in `config/model_registry.py`.
4. Restart the app — `scan_models` picks it up automatically.

---

## III. Installation and Running

### Prerequisites

- Python 3.10 or higher

### 1. Clone the repository

```bash
git clone <repo-url>
cd streamlit-meteocean
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\Activate.ps1    # Windows PowerShell
```

### 3. Install the package and dependencies

```bash
cd streamlitapp
pip install -e .
pip install -r requirements.txt
```

The `-e .` step installs `meteocean_forecast` (from `src/`) so Streamlit pages can import it without any path hacks.

### 4. Run the app

```bash
streamlit run app/Home.py
```

Streamlit prints a local URL (usually `http://localhost:8501`). The first load takes 15–30 seconds while Prophet initialises Stan and deserialises the model files.

To use a different port:

```bash
streamlit run app/Home.py --server.port 8502
```

### 5. Run the tests

```bash
pytest -q
```

All tests are fully mocked — no model files or network access required.

### Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: meteocean_forecast` | Run `pip install -e .` from inside `streamlitapp/` |
| `prophet` install fails on Ubuntu | `sudo apt install python3-dev` then retry, or use `conda install -c conda-forge prophet` |
| Port already in use | `streamlit run app/Home.py --server.port 8502` |
| Wave Height / Wind Speed pages show "no models" | Expected — no trained models exist for those targets yet |