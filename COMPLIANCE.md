# Compliance & Regulated Data Posture

> **Status:** Implemented in WP6. Audit infrastructure (`common/audit.py`) and
> field masking (`common/mask.py`) are both wired; this document describes the
> policy they enforce.

## Why these controls exist

The CMS DE-SynPUF dataset is fully synthetic and safe to handle publicly.
These controls are modeled anyway — the engineering demonstration is the point.
A production Medicare claims platform handles real PHI; this project shows that
the engineering team has internalized what that means.

---

## Beneficiary IDs as PHI

All `desynpuf_id` / `beneficiary_id` values are treated as PHI throughout the
codebase — even though the underlying data is synthetic.

**What this means in practice:**

- The canonical identifier `desynpuf_id` is stored in DuckDB but never returned
  raw from any API endpoint unless the caller holds `phi_read=true` (the V2
  scoped-token mechanism).
- Every query that touches beneficiary-level rows calls
  `common.audit.log_access()` before returning data.
- The `common/mask.py` module defines the canonical list of PHI field names
  (`PHI_FIELDS`) so that masking logic is never duplicated.

**Fields covered:**

| Field name       | Sensitivity   |
|------------------|---------------|
| `desynpuf_id`    | Direct identifier (de-identified synthetic ID, modeled as PHI) |
| `beneficiary_id` | API alias for the same identifier                              |
| `birth_dt`       | Date of birth                                                  |
| `death_dt`       | Date of death                                                  |

---

## Audit Logging

**Module:** `src/cms_platform/common/audit.py`

Every beneficiary-level read emits a structured audit record via the standard
Python `logging` infrastructure:

```python
log_access(beneficiary_id, action, accessor, **context)
```

**Fields logged per access event:**

| Field            | Example value          | Notes                          |
|------------------|------------------------|--------------------------------|
| `beneficiary_id` | `"B001"`               | Treated as PHI; scrubbed in prod logs |
| `action`         | `"risk_score"`         | Logical operation performed    |
| `accessor`       | `"api/risk"`           | System or user performing read |
| `timestamp`      | `2026-05-30T12:00:00Z` | UTC, set at record creation    |
| `context`        | `{}`                   | Arbitrary key-value pairs      |

**Where audit records go (V0):** The Python logger emits JSON-tagged log lines
at `INFO` level with `extra={"audit": True, ...}`. In V0 these flow to stdout /
stderr. In V2 they would be shipped to a SIEM (e.g., AWS CloudWatch Logs Insights
or Splunk) and retained for the Medicare-required 7-year period.

**Call sites (enforced by non-negotiable rule #2 in CLAUDE.md):**

- `api/routes/beneficiary.py → get_risk()` — calls `log_access(beneficiary_id, "risk_score", "api/risk")`
- `api/routes/beneficiary.py → get_care_gaps()` — calls `log_access(beneficiary_id, "care_gaps", "api/care-gaps")`

The call is made **before** any data is fetched or returned, ensuring an audit
trail even when downstream errors occur.

---

## Field-Level Masking

**Module:** `src/cms_platform/common/mask.py`

The masking helper provides two public functions:

```python
mask_field(field_name, value, *, phi_read=False) -> str | None
mask_record(record, *, phi_read=False) -> dict[str, object]
```

**Masking scheme (V0):** A deterministic `"****" + SHA-256(value)[:8]` prefix.
This lets integration tests verify masking without requiring a secrets manager.
In production, replace with a format-preserving encryption (FPE) scheme
(e.g., FF3-1 / AES-FFX) so masked tokens maintain referential integrity across
audit logs.

**`phi_read` query parameter pattern:**

All beneficiary endpoints accept `?phi_read=true` as a query parameter:

```
GET /beneficiary/{id}/risk           → beneficiary_id masked by default
GET /beneficiary/{id}/risk?phi_read=true → beneficiary_id returned as-is
```

This mirrors the V2 OAuth 2.0 scoped-token design where `PHI_READ` scope is
granted by a token introspection check. V0 uses a plain boolean flag for
portfolio demonstration; the parameter name and semantics are intentionally
identical to what V2 will enforce.

**Mapping to HIPAA Minimum Necessary Access:**

The minimum-necessary standard (45 CFR §164.502(b)) requires that only the PHI
required for the immediate purpose is accessed or disclosed. Field-level masking
enforces this at the API boundary:

- By default, no direct identifier leaves the API — the masked hash is sufficient
  for display and correlation within a single session.
- A caller who needs the raw identifier must explicitly assert `phi_read=true`,
  creating a named, auditable access pattern.
- In V2 this assertion is cryptographically bound to a JWT with `PHI_READ` scope,
  making it non-repudiable.

---

## Minimum Necessary Access

API endpoints return only the fields required for the stated purpose:

| Endpoint                        | Fields returned                                      |
|---------------------------------|------------------------------------------------------|
| `GET /beneficiary/{id}/risk`    | masked beneficiary_id, risk_score, claim_year, model_version |
| `GET /beneficiary/{id}/care-gaps` | masked beneficiary_id, gaps list, narrative summary, model_used |
| `GET /cohorts`                  | Aggregate counts only — no individual beneficiary data |
| `GET /benchmarks/providers`     | Provider-level aggregates — no beneficiary data      |

No bulk beneficiary export endpoint exists. Adding one would require explicit
scope and a data-use-agreement check (V2).

---

## API Access Control

**V0 (current):** The `phi_read` query parameter is a demonstration flag.
No authentication is required. This is intentional for a portfolio demo — the
parameter name and semantics preview the V2 design.

**V2 (planned):** JWT bearer token with scoped claims:

- `PHI_READ` scope: grants unmasked beneficiary identifiers
- `BULK_EXPORT` scope: grants cohort-level CSV exports (not yet implemented)
- Token introspection performed in a FastAPI dependency
  (`api/deps.py → verify_phi_scope(token)`)

The V2 seam is annotated in `api/routes/beneficiary.py` at the `phi_read`
parameter; swap the boolean flag for a `Depends(verify_phi_scope)` call.

---

## Data Retention

- `data/` is gitignored; no raw CSVs or the DuckDB file are ever committed.
- At V0, data lives only in the local `data/processed/cms.duckdb` file.
- At V2, a retention policy (default: 7 years, matching CMS requirements for
  Medicare data under 42 CFR Part 2 and CMS record-retention guidelines) is
  enforced via automated deletion jobs and immutable S3 object-lock buckets.
- Audit logs are retained separately from operational data with a longer
  retention schedule (10 years).

---

## De-identification Note

The DE-SynPUF dataset is already fully synthetic and de-identified.
No re-identification risk exists in this dataset.

In a production context, de-identification would follow one of two HIPAA-approved
methods before data leaves the regulated boundary:

1. **Safe Harbor method** (45 CFR §164.514(b)(2)): Remove all 18 enumerated
   identifiers (names, dates finer than year, geographic data smaller than
   state, etc.).
2. **Expert Determination method** (45 CFR §164.514(b)(1)): A qualified
   statistician certifies that re-identification risk is "very small".

The project models both approaches through its engineering controls: field-level
masking mirrors Safe Harbor identifier removal; audit logging supports the
access-control requirements that accompany Expert Determination certifications.

---

> Note: synthetic data caps real predictive signal. These figures demonstrate
> the pipeline, not clinical validity.
