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

| Requirement | Where demonstrated |
|-------------|-------------------|
| Large multi-table SQL, window functions, CTEs | `sql/analytics/` + `src/cms_platform/analytics/` (WP3) |
| AI-driven features → scalable products | `src/cms_platform/scoring/` — risk model + Ollama explainer (WP4) |
| Sensitive / regulated data handling | `COMPLIANCE.md`, `src/cms_platform/common/audit.py` (WP6) |
| Distributed systems thinking | [`ARCHITECTURE.md`](ARCHITECTURE.md) — V2 design (WP9) |
| V0 / V1 / V2 architecture maturity | This README + repo structure throughout |
| Platform / API ecosystem | `src/cms_platform/api/` — FastAPI serving layer (WP5) |
| CI/CD pipelines | `.github/workflows/ci.yml` (WP7) |
| Staff-level engineering judgment | Design decisions documented per WP + ARCHITECTURE.md |

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
