# Synthea Claims Analytics Platform

A portfolio project demonstrating a production-grade clinical analytics stack
built on [Synthea](https://synthea.mitre.org) synthetic patient data. Shows
a V0 → V2 architecture maturity story: from a local DuckDB pipeline to a
distributed, FHIR-native platform.

> **For non-experts:** Synthea is an open-source tool from MITRE that generates
> realistic synthetic (fake) patient records. No real patient data is ever used
> here — but we treat it *as if* it were real, to demonstrate regulated-data
> discipline.

---

## What this project answers

Five analytical questions every healthcare platform needs:

| Query | File | Technique |
|-------|------|-----------|
| 30-day readmission rate | `sql/analytics/readmission_30day.sql` | LAG window function |
| Chronic-condition cohort sizes | `sql/analytics/cohort_segmentation.sql` | Conditional aggregation |
| Encounter cost distribution | `sql/analytics/cost_benchmarking.sql` | PERCENTILE_CONT, NTILE |
| Care-gap detection (diabetic patients) | `sql/analytics/care_gap_detection.sql` | Anti-join |
| Utilisation year-over-year | `sql/analytics/utilization_trends.sql` | LAG + partition |

---

## Architecture overview

```
Synthea CSVs          Raw tables         Star schema           API / scoring
(patients,      →    (all VARCHAR,   →  (typed dims +    →   FastAPI +
 encounters,          no inference)      fact tables)          risk model +
 conditions, …)                                               Ollama explainer
```

Each layer has a documented swap point for V2:
- **Raw → Star**: replace DuckDB with Postgres (one function in `common/db.py`)
- **CSV ingest**: replace with Blue Button 2.0 FHIR API (one module in `ingest/`)
- **Risk model**: replace logistic regression with LightGBM (one file in `scoring/`)

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full V2 design.

---

## Data source: Synthea

> **Learn more:** [synthea.mitre.org](https://synthea.mitre.org) |
> [Synthea GitHub](https://github.com/synthetichealth/synthea) |
> [CSV data dictionary](https://github.com/synthetichealth/synthea/wiki/CSV-File-Data-Dictionary)

Synthea generates five CSV files we ingest:

| File | Contents |
|------|----------|
| `patients.csv` | Demographics — age, gender, race, cost totals |
| `encounters.csv` | Every clinical visit (inpatient, ambulatory, ED, etc.) with costs |
| `conditions.csv` | Diagnoses with **SNOMED-CT** codes |
| `medications.csv` | Prescription events with **RxNorm** codes |
| `providers.csv` | Clinician details |

**On coding systems:** Synthea uses SNOMED-CT (not ICD-9 or ICD-10) for diagnoses.
SNOMED-CT is the modern international clinical terminology standard. ICD-10 is still
used for US billing — real pipelines map SNOMED → ICD-10 at claim submission time.
> **Learn more:** [SNOMED-CT](https://www.snomed.org) | [ICD-10](https://www.who.int/standards/classifications/classification-of-diseases)

---

## Quick start

```bash
uv sync                  # install dependencies
make ingest              # download Synthea sample data + load into DuckDB
make test                # run test suite
make serve               # start API at http://localhost:8000
```

Try the API:
```bash
curl http://localhost:8000/cohorts
curl http://localhost:8000/benchmarks/encounters
curl "http://localhost:8000/patients/<patient-uuid>/risk"
```

---

## Star schema

```
dim_date ──────────────────────────────────────┐
dim_patient ──┬── fact_encounter ──── dim_provider
              ├── fact_condition
              └── fact_medication
dim_condition_code (SNOMED-CT dictionary)
```

> **What is a star schema?** A dimensional model with one central fact table per
> subject area, surrounded by denormalized dimension tables. Fast for analytics
> because most queries join one fact to a few dims without deep normalisation.
> [Learn more](https://en.wikipedia.org/wiki/Star_schema)

---

## JD Requirement Mapping

| Requirement | Where demonstrated | Key evidence |
|-------------|-------------------|-------------|
| Large multi-table SQL, window functions, CTEs | `sql/analytics/` | LAG readmissions, PERCENTILE_CONT cost, anti-join care-gap, YoY LAG trends |
| AI-driven features | `scoring/risk_model.py` + `scoring/explainer.py` | sklearn Pipeline + Ollama care-gap narrative; honest-metrics caveat |
| Regulated data handling | `COMPLIANCE.md`, `common/audit.py`, `common/mask.py` | `log_access()` before every patient read; SHA-256 field masking |
| Distributed systems thinking | `ARCHITECTURE.md` | Kafka topic design, shard partitioning, FHIR migration path |
| V0 / V1 / V2 maturity | Entire repo | Each tier is runnable; swap-point annotations mark migration boundaries |
| Platform / API | `src/cms_platform/api/` | 4 routes; PHI masking at boundary; per-request DuckDB connection |
| CI/CD | `.github/workflows/ci.yml` | 3 jobs: quality (ruff+mypy) → test → Docker |
| Data modelling | `sql/schema/ddl.sql`, `schema/transforms.py` | Star schema with idempotent surrogate keys |
| Observability / audit | `common/audit.py` | Structured JSON audit log on every patient read |

---

## Real data migration path

This project uses Synthea because it requires no credentials and no data use
agreement. To use real Medicare data:

1. **CMS Blue Button 2.0** — OAuth2 FHIR R4 API for individual Medicare
   beneficiaries. Register an app at [bluebutton.cms.gov](https://bluebutton.cms.gov).
   The `ingest/download.py` TODO comment marks the swap point.

2. **CMS Limited Data Set (LDS)** — Real claims data for research, with a
   Data Use Agreement. Apply via [ResDAC](https://resdac.org).

> **Learn more about Medicare:** [medicare.gov](https://www.medicare.gov) |
> [CMS data programs](https://www.cms.gov/data-research)
