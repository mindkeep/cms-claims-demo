# CMS Claims Analytics Platform

A portfolio/demo project built on the
[CMS DE-SynPUF](https://www.cms.gov/data-research/statistics-trends-and-reports/medicare-claims-synthetic-public-use-files/cms-2008-2010-data-entrepreneurs-synthetic-public-use-file-de-synpuf)
synthetic Medicare claims dataset (2008–2010). Demonstrates V0→V2 architecture
maturity for a Principal Software Engineer role: large multi-table SQL, AI-driven
features, regulated-data discipline, and distributed-systems thinking built in
from day one.

---

## Architecture Overview

The repo is structured as an explicit V0→V2 maturity story. Each tier is a real,
runnable state of the codebase — not a slide.

| Tier | What it is | Status |
|------|------------|--------|
| **V0** | Batch analytics core: CSV → DuckDB star schema + SQL query library | In progress |
| **V1** | Served platform: FastAPI over analytics + AI-driven risk scoring + Ollama care-gap explainer | Planned |
| **V2** | Scale & resiliency: Postgres migration path, Kafka streaming ingestion, HA, multi-tenancy | Designed |

> **Read [`ARCHITECTURE.md`](ARCHITECTURE.md) first.** The V2 design drove every V0
> abstraction decision. DuckDB was chosen knowing the swap point. Chunked ingestion
> was built with the Kafka seam annotated. The subsample-list config exists because
> V2 sharding is by beneficiary hash. V0 is not a prototype; it is a deliberately
> simple foundation with a clear migration path.

---

## JD Requirement Mapping

| Requirement | Where demonstrated | Key evidence |
|-------------|-------------------|--------------|
| Large multi-table SQL, window functions, CTEs | `sql/analytics/` + `src/cms_platform/analytics/queries.py` | 5 query types: LAG 30-day readmissions, CASE/FILTER cohort segmentation, PERCENTILE_CONT/NTILE cost distribution, LEFT JOIN anti-join care-gap detection, YoY LAG utilization trends |
| AI-driven features → scalable products | `scoring/risk_model.py` + `scoring/explainer.py` | sklearn Pipeline (StandardScaler → LogisticRegression; LightGBM swap-in point documented); Ollama care-gap narrative via OpenAI-compat SDK with deterministic stub fallback |
| Sensitive / regulated data handling | `COMPLIANCE.md`, `common/audit.py`, `common/mask.py` | `log_access()` enforced before every beneficiary-level read; `mask_record()` applies SHA-256 prefix to PHI fields; beneficiary IDs treated as PHI throughout; COMPLIANCE.md documents the full posture |
| Distributed systems thinking | `ARCHITECTURE.md` + V2 seam annotations in source | Kafka topic-per-claim-type design; `beneficiary_id_hash % N` shard partitioning note in `transforms.py`; HA topology; schema registry strategy; seam annotations mark exact upgrade points |
| V0 / V1 / V2 architecture maturity | Entire repo + `ARCHITECTURE.md` | Each tier is a real runnable state of the codebase; V2 seam annotations in `db.py`, `load.py`, `transforms.py` mark swap points so migration is a refactor, not a rewrite |
| Platform / API ecosystem | `src/cms_platform/api/` | 4 FastAPI routes (`/cohorts`, `/beneficiary/{id}/risk`, `/beneficiary/{id}/care-gaps`, `/benchmarks/providers`); PHI masking applied at API boundary; per-request DuckDB connection lifecycle |
| CI/CD pipelines | `.github/workflows/ci.yml` | 3 jobs in sequence: quality (ruff + mypy) → test (pytest, 76+ tests) → Docker build; failures in earlier jobs block later ones |
| Staff-level engineering judgment | Design docs in `ARCHITECTURE.md`, `COMPLIANCE.md`, `CLAUDE.md` | YAGNI deferral table (what V0 deliberately omits and why); seam discipline (annotate, don't over-engineer); honest-metrics caveat enforced in code and docs |
| Data modeling at scale | `sql/schema/ddl.sql`, `schema/transforms.py` | Star schema with idempotent surrogate keys (`ROW_NUMBER() + MAX()` pattern); SCD-lite `dim_beneficiary` (one row per beneficiary per year); `NOT EXISTS` guards throughout |
| Observability / audit trails | `common/audit.py` | Structured JSON audit record emitted on every PHI access; `AuditRecord` dataclass with `beneficiary_id`, `action`, `accessor`, `timestamp`, and freeform `context`; maps to V2 Kafka-to-SIEM path |

---

## Quick Start

```bash
# Install dependencies
uv sync

# Download subsample 1 and load into DuckDB (~few hundred MB)
make ingest

# Run tests
make test

# Boot the API server at http://localhost:8000
make serve
```

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full system design, and
[`CLAUDE.md`](CLAUDE.md) for contributor/agent conventions.

---

## Work Package Map

| WP | Module | What it builds |
|----|--------|---------------|
| WP1 | `ingest/` | Download CMS CSVs, stream into DuckDB raw tables with explicit typed schemas |
| WP2 | `schema/` | Star schema transforms: dim_beneficiary, dim_provider, dim_diagnosis, fact tables |
| WP3 | `analytics/` | SQL library: 30-day readmissions, cohort segmentation, cost benchmarking, care gaps, utilization trends |
| WP4 | `scoring/` | LightGBM risk stratification + Ollama care-gap explainer (offline stub default) |
| WP5 | `api/` | FastAPI: `/cohorts`, `/beneficiary/{id}/risk`, `/beneficiary/{id}/care-gaps`, `/benchmarks/providers` |
| WP6 | `common/audit.py` | PHI audit logging, field masking, compliance posture (`COMPLIANCE.md`) |
| WP7 | `.github/workflows/` | CI: lint + typecheck + test + Docker build |
| WP8 | `notebooks/story.ipynb` | End-to-end narrative: ingest → schema → queries → scores → "how this scales" |
| WP9 | `ARCHITECTURE.md` | V2 distributed-systems design: Postgres migration, Kafka, HA, security |

---

## Dataset

**CMS DE-SynPUF 2008–2010.** Fully synthetic Medicare claims data (~2.3M
beneficiaries across 20 subsamples; default dev target is subsample 1, ~5% of 5%).
Safe to handle publicly, but the project models PHI discipline throughout —
beneficiary IDs are treated as sensitive, every access is audit-logged, and
field-level masking is configurable. This is intentional: the engineering
demonstration is the point, not the data.
