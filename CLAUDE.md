# CLAUDE.md — Agent Instructions

## Project
CMS Claims Analytics Platform. Portfolio/demo project for a Principal Software
Engineer interview. Built on the CMS DE-SynPUF synthetic Medicare dataset
(2008–2010). Demonstrates V0→V2 architecture maturity: large multi-table SQL,
AI-driven features, regulated-data discipline, distributed-systems thinking.

## Non-negotiable rules
1. Never exceed a WP's stated scope without flagging it first.
2. Every beneficiary-level read must call `common.audit.log_access()`.
3. No type inference on ingest — explicit schemas from the data dictionary only.
4. Treat all beneficiary IDs as PHI throughout.
5. Run `make lint && make test` before every commit. Never commit with failing tests.
6. Honest metrics: never oversell signal from synthetic data. Include the caveat:
   > "Note: synthetic data caps real predictive signal. These figures demonstrate
   > the pipeline, not clinical validity."

## Stack
- Python 3.14, uv (package manager), hatchling (build backend)
- DuckDB (V0 analytical store), Polars (bulk transforms)
- FastAPI + Pydantic v2 (V1 API)
- Ollama via OpenAI-compat SDK (`openai` package, `base_url=settings.ollama_base_url`)
- Docker + GitHub Actions (CI/CD — WP7)

## Commands
| Command         | What it does                                              |
|-----------------|-----------------------------------------------------------|
| `uv sync`       | Install all deps (run first on clean checkout)            |
| `make ingest`   | Download subsample(s) + load into DuckDB                  |
| `make test`     | `uv run pytest tests/ -v`                                 |
| `make lint`     | `ruff check src/ tests/` + `mypy src/`                    |
| `make format`   | `ruff format src/ tests/` + `ruff check --fix src/ tests/`|
| `make serve`    | Boot FastAPI dev server on :8000                          |
| `make clean`    | Remove cache dirs                                         |

## WP execution order
1. **WP1 (ingest) → WP2 (schema) → WP3 (analytics)** — sequential, foundational
2. **WP4 (scoring), WP6 (compliance), WP7 (CI/CD)** — parallel after WP3
3. **WP5 (API)** — after WP4
4. **WP8 (notebook/README), WP9 (architecture doc)** — last

`ARCHITECTURE.md` is a living doc, written alongside WP1, not at WP9.

## Data conventions
- Dev against `subsamples=[1]` by default.
- Every component must accept a list of ints and scale to all 20 subsamples without code change.
- `data/` is gitignored. Layout: `data/raw/` (CSVs), `data/processed/cms.duckdb` (DuckDB), `data/manifests/` (provenance JSON).
- Dataset is fully synthetic (safe to handle publicly) but modeled as PHI — intentional.

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
- `common.audit.log_access(beneficiary_id, action, accessor, **context)` → `AuditRecord`
- `common.logging.configure_logging(level)` — call once at process startup

## Ollama / LLM
- Client: `openai.OpenAI(base_url=settings.ollama_base_url, api_key="ollama")`
- Model: `settings.ollama_model` (default: `llama3.2`)
- The explainer always falls back to a deterministic stub when Ollama is unreachable.
  Never hard-fail on LLM unavailability.

## V2 seam annotations
V0 code carries one-liner comments at the architectural swap points:
- `common/db.py` — Postgres replacement seam
- `ingest/load.py` — Kafka streaming replacement seam
- `schema/transforms.py` — partitioning strategy note

These are the only "design" comments in V0 code. Do not add others.
