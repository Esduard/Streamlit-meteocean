# Skill: solid-check

**Trigger:** When the user asks to "check SOLID", "review for SOLID principles", "audit a file for clean code", or when reviewing any diff that adds a new class, service, or module.

---

## Goal

Identify SOLID violations in the targeted file or diff and produce a ranked, actionable findings list. Apply each principle against the *specific patterns* this codebase uses — don't produce generic advice.

---

## Scope

Default to the current git diff if no file is specified:

```bash
git diff HEAD streamlitapp/src/
```

Or audit a single file when the user names one.

---

## Principle Checklist

Work through each principle in order. For each, run the checks described, then record findings.

---

### S — Single Responsibility Principle

> A module/class should have one reason to change.

**Check:**

1. Does each class have a single cohesive job name? If you need "and" to describe it, it has two responsibilities.
2. `ForecastingService` is the known risk point — it orchestrates scan + load + predict. Acceptable as an orchestrator **only if** the actual logic (feature engineering, model loading, scan logic) lives in the delegated modules. If `ForecastingService` contains non-trivial logic itself, flag it.
3. `_page_template.py` should only render UI and call `ForecastingService`. Any data transformation in page files is an SRP violation.
4. `feature_engineering.py` should only transform data — not load files, not configure models.

**Grep hints:**
```bash
grep -n "def " streamlitapp/src/meteocean_forecast/inference/forecasting_service.py
grep -n "def " streamlitapp/app/_page_template.py
```

---

### O — Open/Closed Principle

> Open for extension, closed for modification. New model families should not require changes to existing classes.

**Check:**

1. Search for `if model_family ==` or `elif model_family ==` in `src/`:
   ```bash
   grep -rn "model_family ==" streamlitapp/src/
   ```
   Any such branch means adding a new model type requires editing existing code. The correct pattern is the adapter protocol: `ProphetAdapter` is one adapter; new families get new adapter files, not new branches.

2. Search for `if model_type ==` or `elif model_type ==` chains beyond the two-branch `is_exogenous` property:
   ```bash
   grep -rn "model_type ==" streamlitapp/src/
   ```

3. Verify `scan_models()` in `model_registry.py` uses a glob pattern, not a hard-coded list of known trial names. A hard-coded list of names violates OCP.

4. Verify `FEATURE_NAME_MAPS` is the **only** place that must change when a new exogenous model is registered. If any other file must also change, flag the coupling.

**Correct extension pattern for reference:**
- New family (e.g., LSTM): add `inference/lstm_adapter.py` + update `model_loader.py` to route to it + update `FEATURE_NAME_MAPS` if exogenous. No changes to `ForecastingService`, `ForecastRequest`, or any page.

---

### L — Liskov Substitution Principle

> Subtypes must be substitutable for their base type without altering correctness.

**Check:**

1. Search for `isinstance` in `src/`:
   ```bash
   grep -rn "isinstance(" streamlitapp/src/
   ```
   An `isinstance` check that gates behaviour (`if isinstance(adapter, ProphetAdapter): …`) is a LSP smell — it means the types are not truly substitutable.

2. `ForecastRequest.for_univariate` and `ForecastRequest.for_exogenous` are factory methods — this is acceptable. The concern is whether downstream code uses `feature_df is None` as a type discriminant instead of calling a method on the request object.
   ```bash
   grep -rn "feature_df is None\|feature_df is not None" streamlitapp/src/
   ```
   If the check appears inside `ForecastingService` or an adapter, flag it — the request should carry its own dispatch logic.

3. Check that `predict_univariate` and `predict_exogenous` in `ProphetAdapter` return DataFrames with the **same column contract** (`ds`, `yhat`, `yhat_lower`, `yhat_upper`, `target_variable`). If a future adapter omits `yhat_lower`/`yhat_upper`, the page template will crash. Flag any inconsistency.

---

### I — Interface Segregation Principle

> Clients should not be forced to depend on methods they don't use.

**Check:**

1. `ForecastingService` is the main interface from `app/` to `src/`. Look at what each page actually calls:
   - Does `1_Current_Speed.py` use every method on the service? 
   - Does it use `prepare_exogenous_features` even when only a univariate model is selected?
   ```bash
   grep -n "service\." streamlitapp/app/pages/*.py streamlitapp/app/_page_template.py
   ```
   If pages import or call methods they never use, that's an ISP smell (usually resolved by splitting the service or accepting it — note the trade-off).

2. Check `ModelMetadata` fields: does a univariate model ever use `required_features` or `feature_name_map`? If those fields are always `()` / `None` for univariate, they are not a violation (they're optional by design), but document that clearly.

3. Check whether `engineer_features(raw_df, platform=None)` forces callers to pass `platform` when they don't need it. Optional params are acceptable; required params that go unused are ISP violations.

---

### D — Dependency Inversion Principle

> High-level modules should not depend on low-level modules. Both should depend on abstractions.

**Check:**

1. `ForecastingService.__init__` directly instantiates `ProphetAdapter`:
   ```python
   self._adapters[meta.model_path] = ProphetAdapter(wrapper, meta)
   ```
   This is a DIP violation if a second adapter type is ever added — the service will need an `if model_family ==` branch.
   
   **Expected pattern:** `model_loader.py` should return an object that satisfies an adapter protocol (duck-typed or `Protocol`-based). `ForecastingService` should call `load_adapter(meta)` and receive back something with `predict_univariate` / `predict_exogenous` methods, without caring whether it's a `ProphetAdapter` or `LSTMAdapter`.
   
   Check whether a `Protocol` or ABC for adapters exists:
   ```bash
   grep -rn "Protocol\|ABC\|abstractmethod" streamlitapp/src/
   ```
   If none, flag as a latent DIP issue (not blocking for V1, but should be addressed before a second model family is added).

2. `scan_models` in `config/model_registry.py` hard-codes `prophet_model.json` as the filename:
   ```python
   models_dir.glob("*/*/prophet_model.json")
   ```
   This couples the registry to a single serialisation format. Flag if a second format is planned.

3. Verify `app/Home.py` and pages only call `ForecastingService` — never `ProphetAdapter`, `load_prophet_from_json`, or `engineer_features` directly. Pages depending on concrete inference classes violates DIP.
   ```bash
   grep -rn "ProphetAdapter\|load_prophet\|engineer_features" streamlitapp/app/
   ```

---

## Findings Format

Produce a table:

| # | Principle | File | Line | Finding | Recommendation | Priority |
|---|---|---|---|---|---|---|
| 1 | D | `inference/forecasting_service.py` | 29 | `ProphetAdapter` instantiated directly in service | Extract `load_adapter(meta) → AdapterProtocol` from `model_loader.py` | Medium (pre-V2) |
| 2 | O | `config/model_registry.py` | 72 | glob hard-codes `prophet_model.json` | Parameterise or use a `MODEL_FILE_PATTERNS` constant | Low |

**Priority guide:**
- **High** — active correctness risk or will cause a crash when the next model family is added.
- **Medium** — latent design debt; address before adding a second model family.
- **Low** — stylistic or naming-only; address opportunistically.

If no violations are found, output: `✅ All five SOLID principles satisfied in the scanned scope.`

End with a 2–3 sentence assessment of the codebase's overall SOLID health and the single highest-leverage change to make next.
