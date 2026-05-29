# Framework Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the full CMS Claims Analytics Platform project — uv project setup, `common/` modules with real tested behavior, typed stubs for all WP subpackages, and all documentation/config files (CLAUDE.md, README.md, ARCHITECTURE.md, Makefile, CI, pre-commit).

**Architecture:** src-layout single package `cms_platform` under `src/`. The `common/` subpackage (config, logging, db, audit) is fully implemented with tests. All WP subpackages (ingest, schema, analytics, scoring, api) are stubbed with typed interfaces — real implementations come in WP1–WP5 plans. ARCHITECTURE.md is written as a living doc that establishes V2 intent before V0 code, not as an afterthought.

**Tech Stack:** Python 3.14, uv, hatchling, DuckDB, Polars, FastAPI, Pydantic v2 + pydantic-settings, openai SDK (Ollama compat), lightgbm, scikit-learn, httpx, ruff, mypy (strict), pytest.

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Project deps, build system, ruff/mypy/pytest config |
| `.python-version` | Pin Python 3.14 for uv |
| `src/cms_platform/__init__.py` | Package version |
| `src/cms_platform/common/config.py` | Pydantic BaseSettings — single config source of truth |
| `src/cms_platform/common/logging.py` | JSON structured logger with audit field support |
| `src/cms_platform/common/db.py` | DuckDB connection factory (V2 swap point annotated) |
| `src/cms_platform/common/audit.py` | PHI access audit logger — called on every beneficiary-level read |
| `src/cms_platform/ingest/download.py` | Stub: fetch CMS CSVs (WP1) |
| `src/cms_platform/ingest/load.py` | Stub: stream CSV → DuckDB raw tables (WP1) |
| `src/cms_platform/schema/transforms.py` | Stub: star schema transforms (WP2) |
| `src/cms_platform/analytics/queries.py` | Stub: 5 analytical query wrappers (WP3) |
| `src/cms_platform/scoring/risk_model.py` | Stub: risk stratification model (WP4) |
| `src/cms_platform/scoring/explainer.py` | Ollama care-gap explainer with offline stub fallback (WP4 impl) |
| `src/cms_platform/api/main.py` | FastAPI app with /health endpoint + CLI entry point |
| `src/cms_platform/api/routes/__init__.py` | Empty — WP5 adds route files here |
| `src/cms_platform/api/models.py` | Pydantic response models stub |
| `tests/conftest.py` | Shared pytest fixtures (Settings with tmp DuckDB path) |
| `tests/test_common.py` | Tests for config, logging, db, audit |
| `tests/test_stubs.py` | Import + interface tests for all WP stub modules |
| `CLAUDE.md` | Agent instructions — conventions, commands, WP order |
| `README.md` | Human-facing narrative: architecture first, then JD mapping, then quick start |
| `ARCHITECTURE.md` | V2 design skeleton — written day one to establish design intent |
| `COMPLIANCE.md` | PHI posture placeholder (WP6 fills in) |
| `Makefile` | ingest / test / lint / format / serve / clean |
| `.pre-commit-config.yaml` | ruff check + ruff-format hooks |
| `.github/workflows/ci.yml` | CI skeleton (WP7 expands) |
| `docker-compose.yml` | Docker skeleton (WP5/WP7 expands) |
| `sql/schema/ddl.sql` | Placeholder — WP2 fills in |
| `sql/analytics/.gitkeep` | Directory placeholder for WP3 SQL files |
| `docs/data_dictionary.md` | Placeholder — WP1 generates from SynPUF_DUG.pdf |
| `docs/erd.md` | Placeholder — WP2 fills in |

---

## Task 1: Initialize uv project

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `src/cms_platform/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_common.py` (first test only)

- [ ] **Step 1: Create `pyproject.toml`**

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
]

[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
strict = true
python_version = "3.14"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 2: Create `.python-version`**

```
3.14
```

- [ ] **Step 3: Create `src/cms_platform/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 4: Create `tests/__init__.py`** (empty file)

- [ ] **Step 5: Write the failing import test in `tests/test_common.py`**

```python
import pytest


def test_package_importable() -> None:
    import cms_platform

    assert cms_platform.__version__ == "0.1.0"
```

- [ ] **Step 6: Install dependencies**

```bash
uv sync
```

Expected: dependencies resolved and installed, `.venv` created.

- [ ] **Step 7: Run the test to verify it passes**

```bash
uv run pytest tests/test_common.py::test_package_importable -v
```

Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml .python-version src/cms_platform/__init__.py tests/__init__.py tests/test_common.py
git commit -m "feat: initialize uv project with cms_platform package"
```

---

## Task 2: Update .gitignore for data/

**Files:**
- Modify: `.gitignore`
- Create: `data/raw/.gitkeep`
- Create: `data/processed/.gitkeep`
- Create: `data/manifests/.gitkeep`

- [ ] **Step 1: Append to `.gitignore`**

Add these lines at the end of the existing `.gitignore`:

```
# CMS claims data — raw CSVs, DuckDB file, download manifests
data/raw/*
data/processed/*
data/manifests/*
!data/raw/.gitkeep
!data/processed/.gitkeep
!data/manifests/.gitkeep
```

- [ ] **Step 2: Create directory structure**

```bash
mkdir -p data/raw data/processed data/manifests
touch data/raw/.gitkeep data/processed/.gitkeep data/manifests/.gitkeep
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore data/raw/.gitkeep data/processed/.gitkeep data/manifests/.gitkeep
git commit -m "chore: add data/ directory structure, gitignore raw/processed/manifests"
```

---

## Task 3: common/config.py — Settings

**Files:**
- Create: `src/cms_platform/common/__init__.py`
- Create: `src/cms_platform/common/config.py`
- Modify: `tests/test_common.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `src/cms_platform/common/__init__.py`** (empty file)

- [ ] **Step 2: Write the failing tests — replace `tests/test_common.py` with full content**

```python
from pathlib import Path

import pytest


def test_package_importable() -> None:
    import cms_platform

    assert cms_platform.__version__ == "0.1.0"


# ── config ────────────────────────────────────────────────────────────────────

def test_settings_defaults() -> None:
    from cms_platform.common.config import Settings

    s = Settings()
    assert s.subsamples == [1]
    assert "cms.duckdb" in s.db_path
    assert s.log_level == "INFO"


def test_settings_override() -> None:
    from cms_platform.common.config import Settings

    s = Settings(subsamples=[1, 2, 3], log_level="DEBUG")
    assert s.subsamples == [1, 2, 3]
    assert s.log_level == "DEBUG"


def test_get_settings_returns_settings() -> None:
    from cms_platform.common.config import Settings, get_settings

    assert isinstance(get_settings(), Settings)
```

- [ ] **Step 3: Run tests to verify the new ones fail**

```bash
uv run pytest tests/test_common.py -k "settings" -v
```

Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Create `src/cms_platform/common/config.py`**

```python
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    subsamples: list[int] = Field(default=[1])
    db_path: str = Field(default="data/processed/cms.duckdb")
    raw_data_dir: str = Field(default="data/raw")
    manifests_dir: str = Field(default="data/manifests")
    ollama_base_url: str = Field(default="http://localhost:11434/v1")
    ollama_model: str = Field(default="llama3.2")
    log_level: str = Field(default="INFO")

    model_config = {"env_prefix": "CMS_", "env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 5: Create `tests/conftest.py`**

```python
import pytest
from pathlib import Path

from cms_platform.common.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=str(tmp_path / "test.duckdb"),
        raw_data_dir=str(tmp_path / "raw"),
        manifests_dir=str(tmp_path / "manifests"),
    )
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/test_common.py -k "settings" -v
```

Expected: 3 PASS

- [ ] **Step 7: Commit**

```bash
git add src/cms_platform/common/__init__.py src/cms_platform/common/config.py tests/test_common.py tests/conftest.py
git commit -m "feat: add Settings (pydantic-settings, CMS_ env prefix)"
```

---

## Task 4: common/logging.py — JSON structured logger

**Files:**
- Create: `src/cms_platform/common/logging.py`
- Modify: `tests/test_common.py`

- [ ] **Step 1: Append failing tests to `tests/test_common.py`**

```python
# ── logging ───────────────────────────────────────────────────────────────────

def test_json_formatter_produces_valid_json() -> None:
    import json
    import logging as stdlib_logging

    from cms_platform.common.logging import JSONFormatter

    formatter = JSONFormatter()
    record = stdlib_logging.LogRecord(
        name="test",
        level=stdlib_logging.INFO,
        pathname="",
        lineno=0,
        msg="hello world",
        args=(),
        exc_info=None,
    )
    parsed = json.loads(formatter.format(record))
    assert parsed["message"] == "hello world"
    assert parsed["level"] == "INFO"
    assert "timestamp" in parsed


def test_configure_logging_does_not_raise() -> None:
    from cms_platform.common.logging import configure_logging

    configure_logging("DEBUG")
    configure_logging("INFO")
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_common.py -k "formatter or configure_logging" -v
```

Expected: FAIL with `ImportError`

- [ ] **Step 3: Create `src/cms_platform/common/logging.py`**

```python
import json
import logging
import sys
from datetime import UTC, datetime


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if getattr(record, "audit", False):
            data["audit"] = True
            data["beneficiary_id"] = getattr(record, "beneficiary_id", None)
            data["action"] = getattr(record, "action", None)
            data["accessor"] = getattr(record, "accessor", None)
            data["context"] = getattr(record, "context", {})
        return json.dumps(data)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
```

- [ ] **Step 4: Run to verify they pass**

```bash
uv run pytest tests/test_common.py -k "formatter or configure_logging" -v
```

Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add src/cms_platform/common/logging.py tests/test_common.py
git commit -m "feat: add JSON structured logger with audit field passthrough"
```

---

## Task 5: common/db.py — DuckDB connection

**Files:**
- Create: `src/cms_platform/common/db.py`
- Modify: `tests/test_common.py`

- [ ] **Step 1: Append failing tests to `tests/test_common.py`**

```python
# ── db ────────────────────────────────────────────────────────────────────────

def test_get_connection_returns_duckdb(settings: "Settings") -> None:
    import duckdb

    from cms_platform.common.db import get_connection

    conn = get_connection(settings)
    assert isinstance(conn, duckdb.DuckDBPyConnection)
    conn.close()


def test_get_connection_creates_parent_dirs(tmp_path: Path) -> None:
    from cms_platform.common.config import Settings
    from cms_platform.common.db import get_connection

    nested = Settings(db_path=str(tmp_path / "a" / "b" / "c.duckdb"))
    conn = get_connection(nested)
    conn.close()
    assert (tmp_path / "a" / "b" / "c.duckdb").exists()


def test_connection_executes_query(settings: "Settings") -> None:
    from cms_platform.common.db import get_connection

    conn = get_connection(settings)
    result = conn.execute("SELECT 42 AS answer").fetchone()
    conn.close()
    assert result is not None and result[0] == 42
```

Note: The `settings` fixture is defined in `conftest.py` and injected by pytest automatically. The `"Settings"` string annotation avoids a circular import at module level — you can also add `from cms_platform.common.config import Settings` at the top of the test file if preferred.

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_common.py -k "connection or duckdb" -v
```

Expected: FAIL with `ImportError`

- [ ] **Step 3: Create `src/cms_platform/common/db.py`**

```python
import duckdb
from pathlib import Path

from cms_platform.common.config import Settings


def get_connection(settings: Settings) -> duckdb.DuckDBPyConnection:
    # V2 swap point: replace with Postgres via psycopg2 / asyncpg when migrating off DuckDB
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path))
```

- [ ] **Step 4: Run to verify they pass**

```bash
uv run pytest tests/test_common.py -k "connection or duckdb" -v
```

Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/cms_platform/common/db.py tests/test_common.py
git commit -m "feat: add DuckDB connection factory with V2 Postgres swap-point annotation"
```

---

## Task 6: common/audit.py — PHI audit logger

**Files:**
- Create: `src/cms_platform/common/audit.py`
- Modify: `tests/test_common.py`

- [ ] **Step 1: Append failing tests to `tests/test_common.py`**

```python
# ── audit ─────────────────────────────────────────────────────────────────────

def test_log_access_returns_audit_record() -> None:
    from cms_platform.common.audit import AuditRecord, log_access

    record = log_access("BENE_001", "read", "api/beneficiary")
    assert isinstance(record, AuditRecord)
    assert record.beneficiary_id == "BENE_001"
    assert record.action == "read"
    assert record.accessor == "api/beneficiary"
    assert record.context == {}


def test_log_access_captures_context() -> None:
    from cms_platform.common.audit import log_access

    record = log_access("BENE_002", "read", "api/risk", endpoint="/risk", ip="127.0.0.1")
    assert record.context["endpoint"] == "/risk"
    assert record.context["ip"] == "127.0.0.1"


def test_log_access_emits_log_record(caplog: pytest.LogCaptureFixture) -> None:
    import logging

    from cms_platform.common.audit import log_access

    with caplog.at_level(logging.INFO, logger="cms_platform.common.audit"):
        log_access("BENE_003", "read", "test_caller")
    assert any("BENE_003" in r.message for r in caplog.records)
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_common.py -k "audit or log_access" -v
```

Expected: FAIL with `ImportError`

- [ ] **Step 3: Create `src/cms_platform/common/audit.py`**

```python
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


@dataclass
class AuditRecord:
    beneficiary_id: str
    action: str
    accessor: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    context: dict[str, object] = field(default_factory=dict)


def log_access(
    beneficiary_id: str,
    action: str,
    accessor: str,
    **context: object,
) -> AuditRecord:
    record = AuditRecord(
        beneficiary_id=beneficiary_id,
        action=action,
        accessor=accessor,
        context=dict(context),
    )
    logger.info(
        "PHI_ACCESS beneficiary=%s action=%s accessor=%s",
        record.beneficiary_id,
        record.action,
        record.accessor,
        extra={
            "audit": True,
            "beneficiary_id": record.beneficiary_id,
            "action": record.action,
            "accessor": record.accessor,
            "context": record.context,
        },
    )
    return record
```

- [ ] **Step 4: Run to verify they pass**

```bash
uv run pytest tests/test_common.py -v
```

Expected: all tests in this file PASS

- [ ] **Step 5: Commit**

```bash
git add src/cms_platform/common/audit.py tests/test_common.py
git commit -m "feat: add PHI audit logger — every beneficiary-level read must call log_access()"
```

---

## Task 7: Package stubs — all WP subpackages

**Files:**
- Create: `src/cms_platform/ingest/__init__.py`
- Create: `src/cms_platform/ingest/download.py`
- Create: `src/cms_platform/ingest/load.py`
- Create: `src/cms_platform/schema/__init__.py`
- Create: `src/cms_platform/schema/transforms.py`
- Create: `src/cms_platform/analytics/__init__.py`
- Create: `src/cms_platform/analytics/queries.py`
- Create: `src/cms_platform/scoring/__init__.py`
- Create: `src/cms_platform/scoring/risk_model.py`
- Create: `src/cms_platform/scoring/explainer.py`
- Create: `src/cms_platform/api/__init__.py`
- Create: `src/cms_platform/api/routes/__init__.py`
- Create: `src/cms_platform/api/models.py`
- Create: `src/cms_platform/api/main.py`
- Create: `tests/test_stubs.py`

- [ ] **Step 1: Write failing tests in `tests/test_stubs.py`**

```python
import pytest


def test_ingest_download_importable() -> None:
    from cms_platform.ingest.download import download_subsamples, main

    assert callable(download_subsamples)
    assert callable(main)


def test_ingest_load_importable() -> None:
    from cms_platform.ingest.load import load_subsamples, main

    assert callable(load_subsamples)
    assert callable(main)


def test_schema_transforms_importable() -> None:
    from cms_platform.schema.transforms import build_star_schema

    assert callable(build_star_schema)


def test_analytics_queries_importable() -> None:
    from cms_platform.analytics.queries import (
        care_gap_detection,
        cohort_segmentation,
        cost_benchmarking,
        readmission_30day,
        utilization_trends,
    )

    for fn in [readmission_30day, cohort_segmentation, cost_benchmarking,
               care_gap_detection, utilization_trends]:
        assert callable(fn)


def test_scoring_risk_model_importable() -> None:
    from cms_platform.scoring.risk_model import predict_risk, train_risk_model

    assert callable(train_risk_model)
    assert callable(predict_risk)


def test_scoring_explainer_importable() -> None:
    from cms_platform.scoring.explainer import CareGapExplanation, explain_care_gaps

    assert callable(explain_care_gaps)


def test_explainer_stub_fires_when_ollama_unreachable() -> None:
    from cms_platform.common.config import Settings
    from cms_platform.scoring.explainer import explain_care_gaps

    # Port 19999 has nothing running — Ollama call will fail → stub fires
    s = Settings(ollama_base_url="http://localhost:19999/v1")
    result = explain_care_gaps("BENE_001", ["Annual wellness visit", "Flu vaccine"], s)
    assert result.beneficiary_id == "BENE_001"
    assert result.model_used == "stub"
    assert "wellness" in result.summary.lower() or "gap" in result.summary.lower()


def test_explainer_stub_handles_no_gaps() -> None:
    from cms_platform.common.config import Settings
    from cms_platform.scoring.explainer import explain_care_gaps

    s = Settings(ollama_base_url="http://localhost:19999/v1")
    result = explain_care_gaps("BENE_002", [], s)
    assert result.model_used == "stub"
    assert "no" in result.summary.lower()


def test_api_app_importable() -> None:
    from cms_platform.api.main import app

    assert app is not None


def test_api_health_endpoint() -> None:
    from fastapi.testclient import TestClient

    from cms_platform.api.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_stubs.py -v
```

Expected: all FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create all `__init__.py` files** (all empty)

```bash
touch src/cms_platform/ingest/__init__.py
touch src/cms_platform/schema/__init__.py
touch src/cms_platform/analytics/__init__.py
touch src/cms_platform/scoring/__init__.py
touch src/cms_platform/api/__init__.py
touch src/cms_platform/api/routes/__init__.py
```

- [ ] **Step 4: Create `src/cms_platform/ingest/download.py`**

```python
from pathlib import Path

from cms_platform.common.config import Settings


def download_subsamples(subsamples: list[int], settings: Settings) -> list[Path]:
    """Fetch CMS DE-SynPUF CSV files for the given subsample numbers.

    Downloads to settings.raw_data_dir, verifies 8 files per subsample,
    writes provenance JSON to settings.manifests_dir. Idempotent — skips
    files already present. Implemented in WP1.
    """
    raise NotImplementedError("WP1")


def main() -> None:
    settings = Settings()
    download_subsamples(settings.subsamples, settings)
```

- [ ] **Step 5: Create `src/cms_platform/ingest/load.py`**

```python
from cms_platform.common.config import Settings


def load_subsamples(subsamples: list[int], settings: Settings) -> None:
    """Stream CMS CSV files for the given subsamples into DuckDB raw tables.

    Uses explicit typed schemas derived from the data dictionary — no type
    inference. Reads in chunks so a single file never fully loads into memory.
    # V2 swap point: replace chunked CSV reader with a Kafka consumer here
    Implemented in WP1.
    """
    raise NotImplementedError("WP1")


def main() -> None:
    settings = Settings()
    load_subsamples(settings.subsamples, settings)
```

- [ ] **Step 6: Create `src/cms_platform/schema/transforms.py`**

```python
import duckdb

from cms_platform.common.config import Settings


def build_star_schema(conn: duckdb.DuckDBPyConnection, settings: Settings) -> None:
    """Transform raw CMS tables into a clean star schema.

    Builds: dim_beneficiary (SCD-style), dim_provider, dim_diagnosis (ICD-9),
    dim_date, fact_inpatient, fact_outpatient, fact_carrier, fact_pde,
    and a unified fact_claim_line view across all claim types.
    # V2 note: facts will be partitioned by claim_year + beneficiary_id_hash
    # to keep joins shard-local at scale.
    Implemented in WP2.
    """
    raise NotImplementedError("WP2")
```

- [ ] **Step 7: Create `src/cms_platform/analytics/queries.py`**

```python
import duckdb
import polars as pl


def readmission_30day(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Detect 30-day readmissions via self-join and window functions over inpatient claims.

    SQL technique: LAG/LEAD window functions, self-join, date arithmetic.
    Implemented in WP3.
    """
    raise NotImplementedError("WP3")


def cohort_segmentation(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Stratify beneficiaries by chronic-condition flags; report cohort sizes and comorbidity.

    SQL technique: CASE/FILTER aggregation, GROUP BY ROLLUP.
    Implemented in WP3.
    """
    raise NotImplementedError("WP3")


def cost_benchmarking(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Cost-per-beneficiary and per-episode with percentile bucketing and provider ranking.

    SQL technique: PERCENTILE_CONT, NTILE, RANK window functions.
    Implemented in WP3.
    """
    raise NotImplementedError("WP3")


def care_gap_detection(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Anti-join: beneficiaries in a chronic cohort missing expected services in a period.

    SQL technique: NOT EXISTS / LEFT JOIN anti-join pattern.
    Implemented in WP3.
    """
    raise NotImplementedError("WP3")


def utilization_trends(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Year-over-year utilization trends 2008→2010 with cohort-level growth rates.

    SQL technique: window functions over year partitions, LAG for YoY deltas.
    Implemented in WP3.
    """
    raise NotImplementedError("WP3")
```

- [ ] **Step 8: Create `src/cms_platform/scoring/risk_model.py`**

```python
from typing import Any

import polars as pl

from cms_platform.common.config import Settings


def train_risk_model(
    features: pl.DataFrame,
    target: pl.Series,
    settings: Settings,
) -> Any:
    """Train a risk-stratification model predicting next-year high-cost beneficiaries.

    Uses logistic regression or LightGBM over prior-year features: chronic flags,
    prior cost, claim counts. Interpretability over raw accuracy — data is synthetic.
    Implemented in WP4.
    """
    raise NotImplementedError("WP4")


def predict_risk(model: Any, features: pl.DataFrame) -> pl.Series:
    """Score a cohort; returns float risk scores in [0.0, 1.0].

    Implemented in WP4.
    """
    raise NotImplementedError("WP4")
```

- [ ] **Step 9: Create `src/cms_platform/scoring/explainer.py`**

```python
from dataclasses import dataclass

from openai import OpenAI

from cms_platform.common.config import Settings


@dataclass
class CareGapExplanation:
    beneficiary_id: str
    gaps: list[str]
    summary: str
    model_used: str


def _stub_explanation(beneficiary_id: str, gaps: list[str]) -> CareGapExplanation:
    if not gaps:
        summary = "No open care gaps identified for this beneficiary."
    else:
        listed = ", ".join(gaps[:3])
        tail = f" (and {len(gaps) - 3} more)" if len(gaps) > 3 else ""
        summary = (
            f"Beneficiary has {len(gaps)} open care gap(s): {listed}{tail}. "
            "Clinical review recommended."
        )
    return CareGapExplanation(
        beneficiary_id=beneficiary_id,
        gaps=gaps,
        summary=summary,
        model_used="stub",
    )


def explain_care_gaps(
    beneficiary_id: str,
    gaps: list[str],
    settings: Settings,
) -> CareGapExplanation:
    """Compose a natural-language care-gap summary via Ollama.

    Uses the OpenAI-compatible API at settings.ollama_base_url.
    Falls back to a deterministic stub if Ollama is unreachable — the demo
    runs fully offline without any LLM infrastructure.

    WP4 replaces the NotImplementedError with the actual LLM call.
    """
    try:
        _client = OpenAI(base_url=settings.ollama_base_url, api_key="ollama")
        # WP4: build prompt and replace this error with:
        # response = _client.chat.completions.create(
        #     model=settings.ollama_model,
        #     messages=[{"role": "user", "content": _build_prompt(beneficiary_id, gaps)}],
        # )
        # return CareGapExplanation(
        #     beneficiary_id=beneficiary_id,
        #     gaps=gaps,
        #     summary=response.choices[0].message.content or "",
        #     model_used=settings.ollama_model,
        # )
        raise NotImplementedError("WP4")
    except NotImplementedError:
        return _stub_explanation(beneficiary_id, gaps)
    except Exception:
        return _stub_explanation(beneficiary_id, gaps)
```

- [ ] **Step 10: Create `src/cms_platform/api/models.py`**

```python
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
```

- [ ] **Step 11: Create `src/cms_platform/api/main.py`**

```python
from fastapi import FastAPI

from cms_platform.common.config import get_settings
from cms_platform.common.logging import configure_logging

app = FastAPI(title="CMS Claims Platform", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    settings = get_settings()
    configure_logging(settings.log_level)
    uvicorn.run("cms_platform.api.main:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 12: Run tests to verify they all pass**

```bash
uv run pytest tests/test_stubs.py -v
```

Expected: all PASS

- [ ] **Step 13: Commit**

```bash
git add src/cms_platform/ tests/test_stubs.py
git commit -m "feat: add typed stubs for all WP subpackages (ingest, schema, analytics, scoring, api)"
```

---

## Task 8: CLAUDE.md

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: Create `CLAUDE.md`**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add CLAUDE.md with agent conventions, WP order, and PHI rules"
```

---

## Task 9: README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create `README.md`**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with architecture-first structure and JD requirement mapping"
```

---

## Task 10: ARCHITECTURE.md skeleton

**Files:**
- Create: `ARCHITECTURE.md`

- [ ] **Step 1: Create `ARCHITECTURE.md`**

```markdown
# Architecture — CMS Claims Analytics Platform

> **Status:** Living document. Written before V0 code to establish design intent.
> Updated as each work package completes.
>
> **How to read this:** The V2 design below drove every V0 abstraction choice.
> Read this first, then read the V0 code — the V2 seam annotations in the code
> will make sense.

---

## Design Philosophy

V0 is not a prototype to be thrown away. It is a deliberately simple foundation
whose boundaries were chosen to make V1→V2 evolution non-destructive:

- **DuckDB** was selected for V0 because it requires zero infrastructure and is
  fully analytical-SQL-compatible. The `get_connection()` factory in `common/db.py`
  is the single swap point for Postgres/columnar warehouse at V2.
- **Chunked CSV ingestion** in `ingest/load.py` mirrors the consumer model of a
  Kafka topic — the swap to streaming is a replacement of one module, not a
  rewrite of the analytical layer.
- **Subsample-list config** (`Settings.subsamples`) exists because V2 shards by
  `beneficiary_id_hash % N`. The config boundary is the sharding boundary.
- **Star schema** is designed for partition pruning by `claim_year` and
  `beneficiary_id_hash` — the same partition keys used at V2.

---

## V0 → V1 → V2 Migration Path

### Storage

| Tier | Store | Reason |
|------|-------|--------|
| V0 | DuckDB (embedded) | Zero-infra, full analytical SQL, laptop-tractable |
| V1 | DuckDB + read API | FastAPI layer over the same DuckDB file |
| V2 | Postgres + columnar warehouse (e.g., Redshift, BigQuery, or Postgres + columnar extension) | Concurrent writes, replication, multi-tenancy |

**Migration path (V0→V2):** Replace `common/db.py::get_connection()` with a
Postgres connection pool (psycopg3 / asyncpg). All SQL in `sql/` is
standard ANSI SQL with window functions — no DuckDB-specific syntax. The
star schema DDL translates directly; partition keys (`claim_year`,
`beneficiary_id_hash`) become Postgres partition columns.

### Ingestion

| Tier | Mechanism | Reason |
|------|-----------|--------|
| V0 | Batch CSV download + chunked load | Reproducible, testable, no infra |
| V1 | Batch + scheduled refresh | Adds daily/weekly pipeline trigger |
| V2 | Kafka streaming topics per claim type | Near-real-time ingestion, replay, backpressure |

**Migration path (V0→V2):** The chunked reader in `ingest/load.py` is replaced
by a Kafka consumer. One topic per claim type (inpatient, outpatient, carrier,
PDE, beneficiary). Consumer groups allow parallel ingestion across subsamples.
Schema registry enforces the same explicit-typing discipline as V0.

### API / Serving

| Tier | Serving | Notes |
|------|---------|-------|
| V0 | None — CLI only | `make ingest`, notebook |
| V1 | FastAPI (single-node, Docker) | Read-only; DuckDB connection per request |
| V2 | FastAPI behind load balancer, read replicas | Connection pooling, horizontal scale |

---

## Partitioning Strategy

**Primary partition key:** `claim_year` (2008, 2009, 2010; extensible to current year)
**Secondary (hash) partition key:** `beneficiary_id_hash % N` (N = shard count)

Rationale: the dominant query patterns are (a) longitudinal — all claims for a
beneficiary across years, and (b) cohort — all beneficiaries in a year matching
a chronic-condition flag. Hash-partitioning by beneficiary keeps (a) shard-local.
Range-partitioning by year keeps (b) partition-prunable. The star schema's fact
tables carry both keys as partition columns.

Shard count N: start at 8 for a 20-subsample deployment (~2.3M beneficiaries ÷
8 ≈ 290K per shard). Scale to 32 when the analytical layer saturates a single
node.

---

## Kafka Streaming Design (V2)

**Topics:** one per CMS claim type — `cms.inpatient`, `cms.outpatient`,
`cms.carrier`, `cms.pde`, `cms.beneficiary`.

**Producers:** claim processors publish JSON events keyed by `beneficiary_id`
(ensures ordering per beneficiary within a partition).

**Consumers:** one consumer group per downstream: `analytics-loader` (writes to
fact tables), `risk-scorer` (triggers incremental re-scoring), `audit-logger`
(PHI access stream).

**Schema registry:** Avro schemas enforcing the same typed columns as the V0
data dictionary. No schema drift — any producer publishing an unknown field
is rejected.

**Replay / backfill:** The V0 batch CSV load becomes the Kafka producer for
historical data. Same schema, different producer implementation.

---

## High Availability & Resiliency (V2)

- **Database:** Postgres streaming replication (1 primary, 2 read replicas).
  Analytical queries routed to replicas; writes to primary only.
- **API:** Stateless FastAPI pods behind a load balancer. Horizontal scale via
  replica count. No session state — all state in the database.
- **Kafka:** 3-broker cluster, replication factor 3, min ISR 2. Topic retention
  72 hours for replay.
- **Failure modes:** DuckDB (V0) is single-node; a crash loses in-flight writes
  but the raw CSVs are the source of truth — re-running `make ingest` is the
  recovery path. At V2, WAL-based Postgres replication + Kafka log retention
  cover both the database and the ingestion pipeline.

---

## Security & Compliance

See [`COMPLIANCE.md`](COMPLIANCE.md) for the full PHI posture.

Key architectural controls:

- **Audit logging:** every beneficiary-level read emits a structured JSON log
  entry via `common/audit.py`. At V2, the audit stream is a dedicated Kafka
  topic consumed by a SIEM.
- **Field-level masking:** configurable redaction of PII fields at the API layer.
  Downstream consumers receive masked data unless they hold an explicit
  `PHI_READ` claim in their JWT.
- **Network:** at V2, the database and Kafka cluster are VPC-internal. The API
  is the only public-facing surface. TLS everywhere.
- **Data at rest:** disk encryption on all storage nodes. The V0 DuckDB file is
  stored in `data/processed/` which is gitignored and never committed.

---

## Cost & Complexity Tradeoffs

| Decision | V0 choice | V2 choice | What you'd defer |
|----------|-----------|-----------|-----------------|
| Storage | DuckDB | Postgres + columnar | Columnar until query latency demands it |
| Ingestion | Batch CSV | Kafka streaming | Kafka until latency SLA < 1 hour |
| API scale | Single Docker container | LB + replicas | Replicas until P99 latency degrades |
| Sharding | N/A | Hash by beneficiary | Sharding until single-node saturates |
| Schema evolution | Manual migration | Schema registry + migration tool | Registry until >2 producers exist |

The principle: defer complexity until the pain is real and measurable. V0 runs
on a laptop. V2 runs on a cluster. The migration path between them is explicit
and non-destructive.
```

- [ ] **Step 2: Commit**

```bash
git add ARCHITECTURE.md
git commit -m "docs: add ARCHITECTURE.md skeleton — V2 design driving V0 choices (DuckDB→Postgres, batch→Kafka, partitioning, HA, security)"
```

---

## Task 11: COMPLIANCE.md placeholder

**Files:**
- Create: `COMPLIANCE.md`

- [ ] **Step 1: Create `COMPLIANCE.md`**

```markdown
# Compliance & Regulated Data Posture

> **Status:** Placeholder. WP6 fills in the full posture. The core audit
> infrastructure (`common/audit.py`) is already wired; this document describes
> the policy it enforces.

## Why these controls exist

The CMS DE-SynPUF dataset is fully synthetic and safe to handle publicly.
These controls are modeled anyway — the engineering demonstration is the point.
A production Medicare claims platform handles real PHI; this project shows that
the engineering team has internalized what that means.

## Controls (WP6 expands each section)

### Beneficiary IDs as PHI
All `beneficiary_id` values are treated as PHI throughout the codebase.

### Audit Logging
Every beneficiary-level read calls `common.audit.log_access()`, which emits a
structured JSON audit record containing: beneficiary_id, action, accessor,
timestamp, and request context. See `src/cms_platform/common/audit.py`.

### Field-Level Masking
A config-driven masking helper (WP6) redacts or hashes sensitive fields before
they leave the API boundary.

### Minimum Necessary Access
API endpoints return only the fields required for the stated purpose. No bulk
beneficiary exports without explicit scope.

### Data Retention
Raw CSVs and the DuckDB file are gitignored and never committed. At V2, a
retention policy (default: 7 years, matching CMS requirements for Medicare data)
is enforced via automated deletion of raw records.

### De-identification Note
The dataset is already synthetic and de-identified. In a production context,
de-identification would follow the Safe Harbor or Expert Determination methods
under HIPAA before any data leaves the regulated boundary.
```

- [ ] **Step 2: Commit**

```bash
git add COMPLIANCE.md
git commit -m "docs: add COMPLIANCE.md placeholder with PHI posture overview"
```

---

## Task 12: Makefile

**Files:**
- Create: `Makefile`

- [ ] **Step 1: Create `Makefile`**

```makefile
.PHONY: install ingest test lint format serve clean

install:
	uv sync

ingest:
	uv run cms-ingest
	uv run cms-load

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src/ tests/
	uv run mypy src/

format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

serve:
	uv run uvicorn cms_platform.api.main:app --reload --host 0.0.0.0 --port 8000

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
```

- [ ] **Step 2: Verify `make test` works**

```bash
make test
```

Expected: all tests PASS

- [ ] **Step 3: Verify `make lint` works**

```bash
make lint
```

Expected: ruff and mypy both pass cleanly. If mypy reports errors, fix them before committing.

- [ ] **Step 4: Commit**

```bash
git add Makefile
git commit -m "chore: add Makefile with install/ingest/test/lint/format/serve/clean targets"
```

---

## Task 13: .pre-commit-config.yaml

**Files:**
- Create: `.pre-commit-config.yaml`

- [ ] **Step 1: Create `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

- [ ] **Step 2: Install pre-commit hooks**

```bash
uv run pre-commit install
```

Expected: `pre-commit installed at .git/hooks/pre-commit`

- [ ] **Step 3: Run pre-commit on all files to verify clean**

```bash
uv run pre-commit run --all-files
```

Expected: all hooks PASS (ruff may auto-fix minor style issues)

- [ ] **Step 4: Commit**

```bash
git add .pre-commit-config.yaml
git commit -m "chore: add pre-commit config (ruff check + ruff-format)"
```

---

## Task 14: CI skeleton + Docker skeleton

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create `.github/` directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Create `.github/workflows/ci.yml`**

```yaml
# CI/CD pipeline — skeleton expanded in WP7
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v3
        with:
          python-version: "3.14"

      - name: Install dependencies
        run: uv sync

      - name: Lint
        run: make lint

      - name: Test
        run: make test
```

- [ ] **Step 3: Create `docker-compose.yml`**

```yaml
# Docker Compose — skeleton expanded in WP5/WP7
# For local development without Docker, use: make serve
version: "3.9"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - CMS_DB_PATH=/data/processed/cms.duckdb
      - CMS_LOG_LEVEL=INFO
    volumes:
      - ./data:/data
    # WP7 adds: health check, restart policy, depends_on
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml docker-compose.yml
git commit -m "chore: add CI skeleton and docker-compose skeleton (expanded in WP7)"
```

---

## Task 15: SQL and docs directory structure

**Files:**
- Create: `sql/schema/ddl.sql`
- Create: `sql/analytics/.gitkeep`
- Create: `docs/data_dictionary.md`
- Create: `docs/erd.md`
- Create: `notebooks/.gitkeep`

- [ ] **Step 1: Create SQL directory and placeholder DDL**

```bash
mkdir -p sql/schema sql/analytics
```

Create `sql/schema/ddl.sql`:

```sql
-- DDL for CMS Claims star schema
-- Business question: defines the dimensional model for all analytical queries
-- SQL technique:     SCD-style dim_beneficiary, hash-partitioned facts
-- Scaling note:      partition keys (claim_year, beneficiary_id_hash) chosen for V2 shard-local joins
--
-- WP2 fills in the full DDL. This file is the authoritative schema definition.
-- Run via: schema/transforms.py::build_star_schema()

-- Placeholder: WP2 adds CREATE TABLE statements here
```

- [ ] **Step 2: Create `sql/analytics/.gitkeep`** (empty)

```bash
touch sql/analytics/.gitkeep
```

- [ ] **Step 3: Create `docs/data_dictionary.md`**

```markdown
# Data Dictionary

> **Status:** Placeholder. WP1 generates this from `SynPUF_DUG.pdf`.

## Source
CMS DE-SynPUF Data Users Guide — column definitions for all 5 record types:
Beneficiary Summary, Inpatient Claims, Outpatient Claims, Carrier Claims,
Prescription Drug Events (PDE).

## Record Types
- Beneficiary Summary (3 files: 2008, 2009, 2010)
- Inpatient Claims
- Outpatient Claims
- Carrier Claims (split into 2 files for size)
- Prescription Drug Events (PDE)

WP1 parses the PDF and generates column definitions, types, and descriptions here.
```

- [ ] **Step 4: Create `docs/erd.md`**

```markdown
# Entity-Relationship Diagram

> **Status:** Placeholder. WP2 generates the Mermaid ERD.

## Star Schema Overview

The analytical schema is a star schema centered on claim events:
- **Fact tables:** fact_inpatient, fact_outpatient, fact_carrier, fact_pde
- **Unified view:** fact_claim_line (cross-cutting analytics)
- **Dimension tables:** dim_beneficiary, dim_provider, dim_diagnosis, dim_date

WP2 fills in the full Mermaid diagram here.
```

- [ ] **Step 5: Create `notebooks/.gitkeep`** (empty)

```bash
mkdir -p notebooks
touch notebooks/.gitkeep
```

- [ ] **Step 6: Commit**

```bash
git add sql/ docs/data_dictionary.md docs/erd.md notebooks/.gitkeep
git commit -m "chore: add sql/ and docs/ structure with placeholders for WP1/WP2"
```

---

## Task 16: Final verification

- [ ] **Step 1: Run full test suite**

```bash
make test
```

Expected: all tests PASS. Count should be 18+ tests across test_common.py and test_stubs.py.

- [ ] **Step 2: Run linter and type checker**

```bash
make lint
```

Expected: ruff — no issues. mypy — no errors. If any errors, fix before proceeding.

- [ ] **Step 3: Verify package installs and entry points resolve**

```bash
uv run python -c "import cms_platform; print(cms_platform.__version__)"
uv run python -c "from cms_platform.api.main import app; print(app.title)"
```

Expected:
```
0.1.0
CMS Claims Platform
```

- [ ] **Step 4: Verify git log is clean**

```bash
git log --oneline
```

Expected: a clean linear history of ~14 commits from "Initialize uv project" through "sql/ and docs/ structure".

- [ ] **Step 5: Final commit if anything was adjusted**

If any files were modified during verification, commit them:

```bash
git add -p
git commit -m "chore: fix issues found during scaffold verification"
```

---

## What comes next

This scaffold is complete. The next plans implement WPs in order:

1. **WP1 plan** — `ingest/download.py` + `ingest/load.py`: real CMS download, DuckDB raw tables, provenance manifests
2. **WP2 plan** — `schema/transforms.py` + `sql/schema/ddl.sql`: star schema, dim/fact tables, ERD
3. **WP3 plan** — `analytics/queries.py` + `sql/analytics/`: 5 analytical queries with full SQL
4. **WP4/WP6/WP7 plans** — parallel: scoring, compliance, CI/CD
5. **WP5 plan** — `api/`: FastAPI routes, pagination, PHI hooks
6. **WP8/WP9 plans** — notebook and architecture doc completion
