# Adding Prophet Models

This directory holds all trained models served by the Streamlit app. The app discovers models automatically at startup — no configuration file needs to be edited to add a model. You only need to place the pkl file in the right folder and follow the naming rules below.

---

## Folder Convention

```
models/
└── <target_variable>/
    └── <trial_name>/
        └── prophet_best_model.pkl
```

| Segment | Rules |
|---|---|
| `<target_variable>` | Must be exactly `current_speed`, `wave_height`, or `wind_speed`. The app reads this name directly from the directory, so a typo creates a broken model entry. |
| `<trial_name>` | Free-form string describing the experiment. Shown as the model's display name in the UI. The **model type** (univariate vs. exogenous) is inferred from inside the pkl — not from this name. |
| `prophet_best_model.pkl` | The filename must be exactly `prophet_best_model.pkl`. The discovery glob is `*/*/prophet_best_model.pkl`. Any other filename is ignored. |

### Current layout

```
models/
└── current_speed/
    ├── prophet_multiplicative_exogenous_trials/
    │   ├── prophet_best_model.pkl
    │   └── trials_log.json
    └── prophet_multiplicative_univariate_trials/
        ├── prophet_best_model.pkl
        └── trials_log.json
```

`trials_log.json` is optional metadata from the hyperparameter search. The app does not read it.

---

## How the App Discovers Models

On startup, `scan_models()` in [streamlitapp/src/meteocean_forecast/config/model_registry.py](../streamlitapp/src/meteocean_forecast/config/model_registry.py) walks the models directory with:

```python
models_dir.glob("*/*/prophet_best_model.pkl")
```

For each file it finds:

1. `target_variable` ← name of the grandparent directory (`pkl_path.parents[1].name`)
2. `display_name` ← name of the parent directory (`pkl_path.parent.name`)
3. The pkl is loaded and inspected to determine `model_type` and `required_features`

If a pkl fails to load (corrupt file, missing class, wrong format), it is **skipped with a warning** — the rest of the models still load normally.

---

## What the Pkl Must Contain

The pkl must be a serialized `ProphetRegressor` wrapper object (defined in `pipeline/models/prophet.py`). The wrapper must expose:

| Attribute | Type | Description |
|---|---|---|
| `.model` | `Prophet` | A fitted Prophet model object |
| `.use_exogenous` | `bool` | `False` for univariate, `True` for exogenous |
| `.regressors` | `list[str]` | Prophet extra_regressors used during training. Empty list for univariate models. Generic names like `["feature_0", "feature_1", ...]` for exogenous. |

The app adds `pipeline/` to `sys.path` before unpickling so that Python can resolve the `models.prophet.ProphetRegressor` class. If you train a model outside the `pipeline/` directory structure, unpickling will fail.

---

## Univariate Models

A univariate model uses only Prophet's built-in time features (trend, seasonality). No external data is required at inference time.

**How the app identifies it:** `wrapper.use_exogenous is False`

**Inference behavior:**
- The app builds the future dataframe internally using `model.make_future_dataframe()`
- The user selects any horizon up to **8,760 hours (1 year)** from today
- No XLSX upload is required

**To add a univariate model:**

1. Train the model. Ensure `wrapper.use_exogenous = False` and `wrapper.regressors = []`.
2. Create the target variable directory if it does not exist:
   ```
   models/wave_height/
   ```
3. Create a trial subdirectory with a descriptive name:
   ```
   models/wave_height/prophet_additive_univariate_v2/
   ```
4. Copy the pkl:
   ```
   models/wave_height/prophet_additive_univariate_v2/prophet_best_model.pkl
   ```
5. Restart the app. The model appears in the model selector under `wave_height`.

---

## Exogenous Models

An exogenous model uses external meteocean features as Prophet regressors. The user must upload an XLSX file at inference time; the app runs feature engineering on it and passes the result to the model.

**How the app identifies it:** `wrapper.use_exogenous is True`

**Inference behavior:**
- The user uploads an XLSX file with hourly meteocean data
- The app validates and transforms the file through the feature engineering pipeline
- The maximum forecast horizon equals the number of processed rows in the uploaded file
- The user may select a shorter horizon

**Required XLSX columns (40 total):**

```
time, latitude, longitude, plat_id,
atm_wnd_spd_10m, atm_wnd_dir_10m,
wav_hs, wav_hmax, wav_tp, wav_tmm10, wav_tm01, wav_tm02, wav_hmaxt,
wav_dm, wav_ww_hs, wav_ww_tp, wav_ww_tmm10, wav_ww_tm01, wav_ww_tm02, wav_ww_dm,
wav_sw_hs, wav_sw_tp, wav_sw_tmm10, wav_sw_tm01, wav_sw_tm02, wav_sw_dm,
wav_pk1_hs, wav_pk1_tp, wav_pk1_tmm10, wav_pk1_tm01, wav_pk1_tm02, wav_pk1_dm,
wav_pk2_hs, wav_pk2_tp, wav_pk2_tmm10, wav_pk2_tm01, wav_pk2_tm02, wav_pk2_dm,
sw_cur_spd, sw_cur_dir
```

The feature engineering pipeline (`engineer_features()` in [streamlitapp/src/meteocean_forecast/features/feature_engineering.py](../streamlitapp/src/meteocean_forecast/features/feature_engineering.py)) converts these 40 raw columns into the engineered features that the model was trained on.

**To add an exogenous model:**

1. Train the model with `use_exogenous = True`. The regressors in the pkl must match the feature names produced by the feature engineering pipeline (e.g. `feature_0`, `feature_1`, …, `feature_N`).
2. Create the target variable directory if it does not exist.
3. Create a trial subdirectory:
   ```
   models/wind_speed/prophet_multiplicative_exogenous_v1/
   ```
4. Copy the pkl:
   ```
   models/wind_speed/prophet_multiplicative_exogenous_v1/prophet_best_model.pkl
   ```
5. **Register the feature name map** (see next section).
6. Restart the app.

---

## Feature Name Map (Exogenous Models Only)

The pkl stores regressors as generic names (`feature_0`, `feature_1`, …). The `FEATURE_NAME_MAPS` dictionary in [streamlitapp/src/meteocean_forecast/config/model_registry.py](../streamlitapp/src/meteocean_forecast/config/model_registry.py) maps each trial directory name to an ordered list of human-readable feature names. This is the single source of truth for which engineered feature corresponds to which position.

```python
FEATURE_NAME_MAPS: dict[str, list[str]] = {
    "prophet_multiplicative_exogenous_trials": [
        "wav_hmax",              # feature_0
        "wav_tp",                # feature_1
        "wav_tmm10",             # feature_2
        "wav_dm",                # feature_3
        "wav_ww_dm",             # feature_4
        "wav_pk1_tmm10",         # feature_5
        "wav_pk2_tmm10",         # feature_6
        "atm_wnd_dir_10m_u",     # feature_7
        "wav_dm_u",              # feature_8
        "wav_pk1_dm_u",          # feature_9
        "wav_pk2_dm_v",          # feature_10
        "wind_current_alignment",# feature_11
        "annual_sin",            # feature_12
        "annual_cos",            # feature_13
        "annual_phase",          # feature_14
        "is_summer",             # feature_15
        "is_autumn",             # feature_16
        "is_winter",             # feature_17
        "is_spring",             # feature_18
        "wind_align_NBC",        # feature_19
        "wave_align_NBC",        # feature_20
        "wind_prob_NBC",         # feature_21
        "wind_prob_SEC",         # feature_22
        "wind_prob_EUC",         # feature_23
        "wave_prob_NBC",         # feature_24
        "current_prob_NBC",      # feature_25
        "current_prob_SEC",      # feature_26
        "current_prob_EUC",      # feature_27
        "sw_cur_spd_fourier",    # feature_28
    ],
}
```

**For each new exogenous model**, add an entry keyed by the exact trial directory name, with the features listed in the same order they appear in `wrapper.regressors`. If no entry exists, the UI falls back to the generic `feature_0 … feature_N` labels — the model still works, but the feature names are not human-readable.

---

## Having Both Model Types for the Same Target Variable

Both a univariate and an exogenous model can exist under the same target variable directory. Place them in separate trial subdirectories:

```
models/current_speed/
├── prophet_multiplicative_exogenous_trials/   ← exogenous model
│   └── prophet_best_model.pkl
└── prophet_multiplicative_univariate_trials/  ← univariate model
    └── prophet_best_model.pkl
```

Both are discovered independently and shown as separate entries in the model selector. The user picks which one to use; the UI adapts (shows the XLSX upload only for the exogenous model).

There is no limit on the number of trial subdirectories under a target variable.

---

## Known Limitations (V1)

- **Scaler and PCA are re-fitted on uploaded data.** At inference time, the feature engineering pipeline fits a new StandardScaler and PCA on the uploaded XLSX rather than using the scalers from training. This may introduce small distribution differences for very short files. A future version will serialize and reuse the training scalers.

- **pkl uses Python pickle.** Prophet's official docs recommend JSON serialization. The pkl format depends on the `pipeline/models/prophet.py` class being importable at load time. A migration to Prophet JSON is planned but does not block the current app.

- **`FEATURE_NAME_MAPS` must be updated manually.** There is no automatic way to recover human-readable feature names from the pkl. When adding an exogenous model, always add its entry to `FEATURE_NAME_MAPS` at the same time.
