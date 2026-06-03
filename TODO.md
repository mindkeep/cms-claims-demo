# TODO — Known Issues and Improvements

Items surfaced during design review. Each entry notes whether it is a bug,
a performance issue, a design smell, or a code-hygiene fix.

---

## High Priority

### Model re-trained on every request
**File:** `src/cms_platform/api/routes/patient.py` — `_train_model()`  
**Type:** Performance bug  
`_train_model()` is called inside every `GET /patients/{id}/risk` request.
It runs a full multi-table SQL aggregation, builds a feature matrix over all
patients, and fits a sklearn pipeline — cold — on every call. At any meaningful
request rate this will be the dominant latency source.

**Fix:** Train once at application startup (FastAPI `lifespan` context) and
store the model on `app.state`. If the data changes between requests, add an
explicit invalidation hook rather than re-training blindly.

---

### SQL interpolation inconsistency in `_get_patient_features`
**File:** `src/cms_platform/api/routes/patient.py:73`  
**Type:** Code smell / latent security risk  
`patient_key` is fetched from the DB (an integer), so it is not directly
user-controlled today. But the f-string pattern sits three lines below a
correct parameterized query (`WHERE patient_id = ?`), creating a readable
pattern that will be copied with a user-supplied value.

**Fix:** Replace `WHERE dp.patient_key = {patient_key}` with a parameterized
bind (`WHERE dp.patient_key = ?`, `[patient_key]`).

---

## Medium Priority

### `fact_condition` is denormalized against `dim_condition_code`
**File:** `sql/schema/ddl.sql`, `src/cms_platform/schema/transforms.py`  
**Type:** Schema design gap  
`dim_condition_code` exists to normalize `(snomed_code, description)` pairs,
but `fact_condition` stores `snomed_code VARCHAR` and `description VARCHAR`
directly. Queries in `risk_model.py` and `patient.py` join on the raw string.
`dim_condition_code` is populated but never queried.

**Fix:** Add a `code_key BIGINT REFERENCES dim_condition_code(code_key)` FK
to `fact_condition` and drop the `description` column from the fact table.
Update the risk model and patient route queries to join via `dim_condition_code`.

---

### `except Exception` without logging in `explainer.py`
**File:** `src/cms_platform/scoring/explainer.py:63`  
**Type:** Observability gap  
The graceful fallback to the stub explanation is correct behaviour. However,
the exception is swallowed with no log output. When Ollama is unreachable in
a deployed environment, there is nothing in the logs to explain why summaries
look deterministic.

**Fix:** Add `logger.warning("Ollama unavailable, using stub: %s", e)` before
returning `_stub_explanation(...)`.

---

### `get_settings()` is not cached
**File:** `src/cms_platform/common/config.py`  
**Type:** Performance / correctness  
Every call to `get_settings()` constructs a new `Settings` instance, which
reads env variables and the `.env` file. `pydantic-settings` is designed to be
used with `@lru_cache`.

**Fix:**
```python
from functools import lru_cache

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

---

## Low Priority

### Test helper `_seed_csvs` belongs in `conftest.py`
**File:** `tests/test_ingest.py`, imported by `tests/test_api.py` and
`tests/test_scoring.py`  
**Type:** Code hygiene  
`_seed_csvs` has a leading underscore (marking it module-private by convention)
but is used as shared test infrastructure across three test modules. Coupling
test modules together makes refactoring fragile.

**Fix:** Move `_seed_csvs` to `tests/conftest.py` as a plain function (no
underscore). Remove the cross-module imports.

---

### Care-gap query is population-wide, not patient-scoped
**File:** `src/cms_platform/api/routes/patient.py:140`  
**Type:** Possible logic error  
The `NOT EXISTS` subquery checks whether the patient has *any* encounter in
the past year, not whether they have an encounter *specifically for* the active
condition. A patient with a recent wellness visit would have all their chronic
conditions suppressed from the gap list even if the conditions were never
directly addressed. Whether this is intentional depends on the clinical
definition in use.

**Fix or document:** Either tighten the query to require a condition-specific
encounter code, or add a comment explaining the intentional definition.

---

## Already Tracked in Code (no separate action needed)

The following issues are acknowledged with `TODO(future-*)` annotations in the
source and are deferred to a later work package:

| Location | Deferred item |
|----------|--------------|
| `api/routes/patient.py` | Replace `phi_read` query param with JWT `PHI_READ` scope |
| `scoring/risk_model.py` | Swap LogisticRegression for LightGBM once feature set justifies it |
| `scoring/explainer.py` | Add retry + exponential backoff for transient Ollama failures |
| `common/config.py` | Swap Synthea data source for Blue Button 2.0 FHIR API |
| `ingest/load.py` | Replace CSV loader with FHIR bundle parser |
