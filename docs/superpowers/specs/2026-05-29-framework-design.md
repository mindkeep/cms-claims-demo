---
name: framework-design
description: Initial project framework design for the CMS Claims Analytics Platform — directory layout, tooling, CLAUDE.md, README structure, and WP9 architecture-first approach.
metadata:
  type: project
---

# CMS Claims Analytics Platform — Framework Design

**Date:** 2026-05-29
**Status:** Approved

---

## 1. Context

Portfolio/demo project for a Principal Software Engineer interview. Built on CMS DE-SynPUF synthetic Medicare claims (2008–2010). Demonstrates V0→V2 architecture maturity across: large multi-table SQL, AI-driven features, regulated-data discipline, and distributed-systems thinking.

Stack: Python 3.14, uv, DuckDB (V0), Polars, FastAPI + Pydantic v2 (V1), Ollama via OpenAI-compat SDK (agentic explainer), Docker, GitHub Actions.

---

## 2. Directory Layout

```
cms-claims-demo/
  README.md
  CLAUDE.md
  ARCHITECTURE.md              # Skeleton written day one — drives V0 design decisions
  COMPLIANCE.md                # WP6
  Makefile
  pyproject.toml               # uv project + ruff + mypy + pytest config
  uv.lock
  .python-version              # 3.14
  .pre-commit-config.yaml
  docker-compose.yml           # WP5/WP7
  .github/workflows/ci.yml     # WP7
  data/                        # gitignored
    raw/
    processed/
    manifests/
  src/cms_platform/
    __init__.py
    ingest/                    # WP1
      download.py
      load.py
    schema/                    # WP2
      transforms.py
    analytics/                 # WP3
      queries.py
    scoring/                   # WP4
      risk_model.py
      explainer.py             # Ollama/OpenAI-compat care-gap explainer
    api/                       # WP5
      main.py
      routes/
      models.py
    common/
      config.py                # Pydantic BaseSettings
      db.py
      logging.py
      audit.py                 # PHI access audit logger (WP6)
  sql/
    schema/ddl.sql
    analytics/                 # one .sql per WP3 query
  notebooks/story.ipynb        # WP8
  tests/
  docs/
    data_dictionary.md
    erd.md
```

---

## 3. pyproject.toml

```toml
[project]
name = "cms-claims-platform"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = [
    "duckdb>=1.2",
    "polars>=1.0",
    "fastapi>=0.115",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "uvicorn[standard]>=0.30",
    "openai>=1.0",
    "scikit-learn>=1.5",
    "lightgbm>=4.0",
    "httpx>=0.27",
]

[project.scripts]
cms-ingest = "cms_platform.ingest.download:main"
cms-load   = "cms_platform.ingest.load:main"
cms-serve  = "cms_platform.api.main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "mypy>=1.10",
    "ruff>=0.6",
    "pre-commit>=3.7",
    "types-requests",
]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
strict = true
python_version = "3.14"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

---

## 4. CLAUDE.md

Agent-facing instructions covering: project purpose, stack, WP execution order, Makefile commands, global conventions (no type inference, PHI treatment, SQL headers, honest metrics), data layout, and Ollama config.

Key conventions:
- Subsample list is config-driven; default `[1]`, must scale to all 20 without code change
- Every beneficiary-level read calls `common.audit.log_access()`
- Every `.sql` file carries: business question, SQL technique, scaling note
- Stub explainer is the default when Ollama is unreachable

---

## 5. README.md Structure

Sections in reading order:
1. One-paragraph project purpose
2. **Architecture overview** (V0→V2 story — placed high, before quick start)
3. **JD requirement mapping table** (near top; distributed-systems row prominent)
4. Quick start (`uv sync` → `make ingest` → `make test` → `make serve`)
5. Work package map
6. Dataset notes (synthetic, PHI discipline modeled)

---

## 6. ARCHITECTURE.md — Written Day One

Skeleton committed alongside WP1. Framed as "the design that drives V0 choices" — establishes:
- DuckDB chosen knowing it will be replaced by Postgres/columnar warehouse at V2
- Chunked ingestion designed with the Kafka streaming seam explicit
- Subsample-list config exists because V2 sharding is by beneficiary hash
- Star schema designed for partition pruning by claim year

Fills in progressively as WPs complete; sections: DuckDB→Postgres migration path, partitioning/sharding, Kafka streaming ingestion, HA, security, multi-tenancy, cost/complexity tradeoffs.

---

## 7. V2 Seam Annotations in V0 Code

Short one-liner comments at the abstraction points in V0 code:
- `common/db.py`: note the swap point for Postgres
- `ingest/load.py`: note the Kafka replacement seam for chunked reads
- `common/config.py`: note that subsample list is the sharding boundary

These are the only comments added — purpose is to signal architectural intent to the interviewer reading the code.

---

## 8. WP Execution Order

1. **Sequential:** WP1 → WP2 → WP3 (foundational; nothing downstream is real until these work)
2. **Parallel once WP3 lands:** WP4, WP6, WP7
3. **After WP4:** WP5
4. **Last:** WP8, WP9 (describes the finished whole)

ARCHITECTURE.md skeleton is written alongside WP1, not at WP9.
