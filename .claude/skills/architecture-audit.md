# Skill: architecture-audit

**Trigger:** When the user asks to "audit architecture", "check layer violations", "review clean architecture", or "validate imports", or before any major refactor touching more than one layer.

---

## Goal

Verify that the `streamlitapp/src/meteocean_forecast/` package respects its layer boundaries, that each module's responsibility matches its layer, and that no hidden coupling has crept in. Produce an actionable findings list — not a rewrite plan.

---

## Layer Map

The project is divided into five layers. Dependencies may only flow **downward**:

```
app/              (Streamlit UI — entry points only)
    ↓
inference/        (ProphetAdapter, ForecastingService, model_loader)
    ↓         ↓
config/        features/   (independent; neither depends on the other)
    ↓              ↓
         domain/            (pure dataclasses + validation; no project imports)
```

**Hard rules:**

| Layer | May import from | Must NOT import from |
|---|---|---|
| `domain/` | stdlib, third-party only | everything else in this project |
| `features/` | stdlib, numpy, pandas, sklearn | domain, config, inference, app |
| `config/` | domain, stdlib, third-party | features, inference, app |
| `inference/` | domain, config, features, stdlib, third-party | app |
| `app/` | anything in src | (no restriction, but keep logic out of pages) |

---

## Step 1 — Collect all intra-project imports

Run the following to extract every import statement from `src/`:

```bash
grep -rn "^from meteocean_forecast" streamlitapp/src/ | sort
grep -rn "^import meteocean_forecast" streamlitapp/src/ | sort
```

Build a table:

```
file (layer)  →  imported module (layer)
```

---

## Step 2 — Check each import against the layer rules

For every import found, apply the rule table above. Flag any import where the importing layer is **not allowed** to depend on the imported layer.

**Common violations to look for specifically:**

- `domain/` importing from `config` or `inference` — breaks the stable-abstractions principle; domain must have zero project deps.
- `features/` importing from `domain` — features should be pure transformations; pulling in domain objects couples them to business rules.
- `config/` importing from `features` or `inference` — config should only know about domain objects, not how to compute them.
- `inference/` importing from `app` — the service layer must not know about the UI.
- Any `app/pages/*.py` containing business logic (feature engineering calls, direct model calls outside `ForecastingService`) — page files should only call `ForecastingService` and render results.

---

## Step 3 — Check responsibility alignment

For each file in `src/`, verify its responsibility matches its layer:

| File | Expected responsibility |
|---|---|
| `domain/model_metadata.py` | Immutable metadata dataclass — no I/O, no computation |
| `domain/forecast_request.py` | Value object + horizon validation — no I/O |
| `features/raw_xlsx_reader.py` | Read and validate raw XLSX schema — pandas only |
| `features/feature_engineering.py` | Pure transformations — deterministic, no state |
| `config/model_registry.py` | Scan disk for models; return `ModelMetadata` list |
| `inference/model_loader.py` | Load serialised model from path |
| `inference/prophet_adapter.py` | Thin typed wrapper around a loaded model |
| `inference/forecasting_service.py` | Orchestrate: scan → load → predict; no feature logic inline |
| `app/Home.py` | Session state + registry table; no prediction logic |
| `app/_page_template.py` | Shared UI widgets; calls only `ForecastingService` |

Flag any file that contains logic outside its expected responsibility.

---

## Step 4 — Check `ForecastingService` orchestration contract

`ForecastingService` is the single entry point from `app/` to all src logic. Verify:

1. `app/` pages only call methods on `ForecastingService` — they never call `engineer_features`, `load_prophet_from_json`, or any `inference/` internals directly.
2. `ForecastingService.forecast()` does not contain feature engineering logic — that lives in `prepare_exogenous_features()`.
3. `ForecastingService.__init__` does not silently swallow exceptions (the `try/except` in `scan_models` is acceptable; silent swallowing in `__init__` itself is not).

---

## Step 5 — Check for hard-coded target variable branches

Search for `if.*target_variable` or `elif.*target_variable` patterns in `src/`:

```bash
grep -rn "target_variable ==" streamlitapp/src/
grep -rn "if.*\"current_speed\"\|if.*\"wave_height\"\|if.*\"wind_speed\"" streamlitapp/src/
```

Any match inside `src/` is a potential OCP violation — the model registry should drive target-variable behaviour, not if-chains. Flag each occurrence.

---

## Step 6 — Check `FEATURE_NAME_MAPS` completeness

In `config/model_registry.py`, every trial directory that contains a `prophet_model.json` with extra regressors must have an entry in `FEATURE_NAME_MAPS`. Verify:

```bash
# list trial dirs on disk
ls streamlitapp/models/*/*/prophet_model.json

# compare against FEATURE_NAME_MAPS keys in model_registry.py
grep -A 2 "FEATURE_NAME_MAPS" streamlitapp/src/meteocean_forecast/config/model_registry.py
```

Flag any trial directory whose name is absent from `FEATURE_NAME_MAPS` and whose model has regressors (check `prophet_metadata.json` → `"extra_regressors"`).

---

## Step 7 — Report findings

Produce a findings table:

| # | File | Line | Violation type | Description | Severity |
|---|---|---|---|---|---|
| 1 | `features/feature_engineering.py` | 12 | Layer boundary | imports from `domain/` — features must not depend on domain | High |
| 2 | `app/pages/1_Current_Speed.py` | 88 | Responsibility leak | calls `engineer_features` directly — should call `ForecastingService.prepare_exogenous_features` | High |
| … | | | | | |

**Severity guide:**
- **High** — breaks a layer boundary or couples two layers that must remain independent.
- **Medium** — a responsibility is in the wrong place but no import boundary is crossed.
- **Low** — a naming, convention, or structural nit that doesn't affect correctness.

If no violations are found, output: `✅ No architecture violations detected.`

End with a short (2–3 sentence) summary of overall health.
