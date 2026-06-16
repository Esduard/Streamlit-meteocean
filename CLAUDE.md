# CLAUDE.md

## Project goal

Build a Streamlit application for hourly meteocean forecasting.

The app predicts three target variables:

1. current speed
2. wave height
3. wind speed

Each target variable has its own family of models. The first page must allow the user to load available models from disk into application memory. The user then uploads XLSX files containing raw meteocean data for inference when the selected model requires exogenous features.

## Model types

The app supports two model types:

- Univariate models:
  - Do not require an uploaded feature file.
  - Forecast horizon can be selected up to 1 year from today.
  - Must create the future dataframe internally.

- Exogenous models:
  - Require an uploaded XLSX file with raw hourly meteocean data.
  - The raw XLSX must be transformed using the feature engineering logic ported from `references/feature_engineering.ipynb`.
  - The maximum forecast horizon is the last timestamp available after processing the uploaded file.
  - The user may select a shorter forecast horizon.

All models operate at hourly granularity.

## Current model format

The existing Prophet models are saved as `prophet_model.json` inside the `models` folder.

Do not delete or overwrite existing `.json` model files. Load them only from trusted local paths.

## Required model metadata

Every loaded model must be represented by metadata:

- target_variable: one of `current_speed`, `wave_height`, `wind_speed`
- model_family: initially `prophet`
- model_type: `univariate` or `exogenous`
- model_path
- required_features: list of required feature columns for exogenous models
- datetime_column:
- prediction_column:
- frequency: `H`, or hourly
- max_univariate_horizon_hours: 8760

If metadata is missing, create a clear TODO and a safe temporary fallback, but do not hardcode hidden assumptions in the UI.

## Prophet inference contract

Prophet prediction input must contain a `ds` datetime column.

For exogenous Prophet models, the future dataframe must also contain all regressors used during training.

Prediction output must include:

- ds
- yhat
- yhat_lower, if available
- yhat_upper, if available
- target_variable
- model_name
- model_type

## Feature engineering contract

Port the logic from `references/feature_engineering.ipynb` into reusable Python modules.

Do not call notebook cells from the app.

Feature engineering must be deterministic and testable.

The feature engineering pipeline should expose a function like:

```python
engineer_features(raw_df: pd.DataFrame, platform: str | None = None) -> pd.DataFrame
```

## Agent skills

### Issue tracker

Issues live as local markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default canonical strings (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: one `CONTEXT.md` + `docs/adr/` at the repo root (neither exists yet — skills will proceed silently until created). See `docs/agents/domain.md`.