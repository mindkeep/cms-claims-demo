# Compliance Posture

This project uses **fully synthetic** Synthea data — no real patients.
We model it as PHI to demonstrate regulated-data discipline.

## PHI fields

| Field | Source | Masking |
|-------|--------|---------|
| `patient_id` | `patients.csv ID` | `****` + SHA-256[:8] |
| `birthdate` | `patients.csv BIRTHDATE` | `****` + SHA-256[:8] |
| `deathdate` | `patients.csv DEATHDATE` | `****` + SHA-256[:8] |
| `ssn` | `patients.csv SSN` | `****` + SHA-256[:8] |
| `first` / `last` | `patients.csv FIRST/LAST` | `****` + SHA-256[:8] |

## Audit logging

Every patient-level API read calls `common.audit.log_access()` before
any data is fetched. The audit record includes: `patient_id`, `action`,
`accessor`, `timestamp`, and freeform `context`.

```python
log_access(patient_id, "risk_score_read", "api")
```

At V2: the audit log stream becomes a dedicated Kafka topic (`cms.audit`)
consumed by a SIEM for real-time alerting.

## PHI bypass

Routes accept `?phi_read=true` to return unmasked data. In V0 this is an
honour system. At V2: replace with a JWT `PHI_READ` scope claim.
See `TODO(future-auth)` comments in `api/routes/patient.py`.

## Data retention

Raw Synthea CSVs: kept indefinitely (no retention obligation — synthetic data).
Audit logs: retain 7 years (mirrors HIPAA §164.530(j) for production posture).
DuckDB file: re-generatable from raw CSVs at any time via `make ingest`.

## Safe Harbour note

Synthea data is not de-identified real data — it is fully generated. The PHI
modelling here is for architectural demonstration only.
