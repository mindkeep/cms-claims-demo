# CLAUDE.md — Agent Instructions

## Project
Synthea Claims Analytics Platform. Portfolio/demo project for a Principal Software
Engineer interview. Built on [Synthea](https://synthea.mitre.org) synthetic patient
data (MITRE open-source generator). Demonstrates V0→V2 architecture maturity: large
multi-table SQL, AI-driven features, regulated-data discipline, distributed-systems
thinking.

## Non-negotiable rules
1. Never exceed a stated scope without flagging it first.
2. Every patient-level read must call `common.audit.log_access()`.
3. No type inference on ingest — explicit column lists from the source schema only.
4. Treat all patient IDs as PHI throughout.
5. Run `make lint && make test` before every commit. Never commit with failing tests.
6. Honest metrics: never oversell signal from synthetic data. Include the caveat:
   > "Note: synthetic data caps real predictive signal. These figures demonstrate
   > the pipeline, not clinical validity."

## Stack
- Python 3.14, uv (package manager), hatchling (build backend)
- DuckDB (V0 analytical store), Polars (bulk transforms)
- FastAPI + Pydantic v2 (V1 API)
- Ollama via OpenAI-compat SDK (`openai` package, `base_url=settings.ollama_base_url`)
- Docker + GitHub Actions (CI/CD)

## Commands
| Command         | What it does                                              |
|-----------------|-----------------------------------------------------------|
| `uv sync`       | Install all deps (run first on clean checkout)            |
| `make ingest`   | Download Synthea sample CSVs + load into DuckDB           |
| `make test`     | `uv run pytest tests/ -v`                                 |
| `make lint`     | `ruff check src/ tests/` + `mypy src/`                    |
| `make format`   | `ruff format src/ tests/` + `ruff check --fix src/ tests/`|
| `make serve`    | Boot FastAPI dev server on :8000                          |
| `make clean`    | Remove cache dirs                                         |

## Data conventions
- `data/` is gitignored. Layout: `data/raw/synthea/` (CSVs), `data/processed/cms.duckdb` (DuckDB), `data/manifests/` (provenance JSON).
- Synthea exports: `patients.csv`, `encounters.csv`, `conditions.csv`, `medications.csv`, `providers.csv`.
- All raw tables store columns as VARCHAR — no type coercion at ingest time.
- Dataset is fully synthetic (safe to handle publicly) but modelled as PHI — intentional.
- TODO(future-source): swap `ingest/download.py` for Blue Button 2.0 FHIR API — see ARCHITECTURE.md.

## SQL conventions
Every `.sql` file in `sql/` must carry this header block:
```sql
-- Business question: <what this query answers>
-- SQL technique:     <e.g., window functions, anti-join, CTEs>
-- Scaling note:      <how this would be indexed/partitioned at V2>
```

## Key module interfaces
- `common.config.get_settings()` → `Settings` — single source of truth for all config
- `common.db.get_connection(settings)` → `duckdb.DuckDBPyConnection`
- `common.audit.log_access(patient_id, action, accessor, **context)` → `AuditRecord`
- `common.logging.configure_logging(level)` — call once at process startup

## Ollama / LLM
- Client: `openai.OpenAI(base_url=settings.ollama_base_url, api_key="ollama")`
- Model: `settings.ollama_model` (default: `llama3.2`)
- The explainer always falls back to a deterministic stub when Ollama is unreachable.
  Never hard-fail on LLM unavailability.

## V2 seam annotations
V0 code carries one-liner comments at the architectural swap points:
- `common/db.py` — Postgres replacement seam
- `ingest/download.py` — Blue Button 2.0 FHIR API replacement seam
- `schema/transforms.py` — partitioning strategy note

These are the only "design" comments in V0 code. Do not add others.
