# Synthea Pivot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the CMS DE-SynPUF data source with Synthea synthetic CSV data throughout the entire stack — ingest, schema, analytics, scoring, API, and docs.

**Architecture:** Download pre-generated Synthea CSV files (patients, encounters, conditions, medications, providers) into a DuckDB star schema with general clinical terminology. SNOMED-CT codes replace ICD-9. All V0→V2 seam annotations updated to reference FHIR/Blue Button 2.0 as the real-data migration path.

**Tech Stack:** Python 3.14, DuckDB, Polars, FastAPI, scikit-learn, httpx, Synthea CSV format

---

## File Map

**Delete entirely:**
- `src/cms_platform/ingest/download.py` — CMS-specific URL templates
- `src/cms_platform/ingest/load.py` — CMS column definitions
- `tests/test_ingest.py`, `tests/test_schema.py`, `tests/test_analytics.py`, `tests/test_scoring.py`, `tests/test_api.py`, `tests/test_compliance.py`, `tests/test_stubs.py`, `tests/test_common.py`
- `sql/schema/ddl.sql`, `sql/analytics/*.sql` (all 5)
- `notebooks/story.ipynb`
- `cms-claims-plan.md`, `check_config.py`, `test_mutable.py` (root-level scratch files)
- `docs/superpowers/plans/2026-05-30-*.md` (old WP plans)
- `COMPLIANCE.md` (rewrite from scratch)

**Rewrite:**
- `src/cms_platform/common/config.py` — swap `cms_synpuf_base_url` → `synthea_data_url`
- `src/cms_platform/common/mask.py` — update PHI field names
- `src/cms_platform/scoring/risk_model.py` — new feature set derived from Synthea
- `src/cms_platform/scoring/explainer.py` — rename `beneficiary_id` → `patient_id`
- `src/cms_platform/api/models.py` — patient-centric Pydantic models
- `src/cms_platform/api/routes/beneficiary.py` → rename file to `patient.py`
- `src/cms_platform/api/routes/benchmarks.py` — route rename `/benchmarks/providers` → `/benchmarks/encounters`
- `src/cms_platform/api/main.py` — updated router imports
- `src/cms_platform/analytics/queries.py` — column names update
- `README.md`, `ARCHITECTURE.md`, `COMPLIANCE.md`, `notebooks/story.ipynb`

**New files:**
- `src/cms_platform/ingest/download.py` — Synthea zip downloader
- `src/cms_platform/ingest/load.py` — Synthea CSV → raw tables
- `sql/schema/ddl.sql` — new star schema
- `sql/analytics/readmission_30day.sql`
- `sql/analytics/cohort_segmentation.sql`
- `sql/analytics/cost_benchmarking.sql`
- `sql/analytics/care_gap_detection.sql`
- `sql/analytics/utilization_trends.sql`
- `src/cms_platform/schema/transforms.py` — populate dim/fact tables from Synthea raws
- `tests/test_ingest.py`, `tests/test_schema.py`, `tests/test_analytics.py`, `tests/test_scoring.py`, `tests/test_api.py`, `tests/test_compliance.py`

**Keep unchanged:**
- `src/cms_platform/common/db.py`, `audit.py`, `logging.py`
- `src/cms_platform/api/deps.py`
- `tests/conftest.py` (minor update only)
- `pyproject.toml`, `Makefile`, `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`

---

## Synthea CSV Column Reference

Use these exact column names (as they appear in Synthea CSV headers) for all raw table definitions and transforms.

**patients.csv:** `ID, BIRTHDATE, DEATHDATE, SSN, DRIVERS, PASSPORT, PREFIX, FIRST, LAST, SUFFIX, MAIDEN, MARITAL, RACE, ETHNICITY, GENDER, BIRTHPLACE, ADDRESS, CITY, STATE, COUNTY, FIPS, ZIP, LAT, LON, HEALTHCARE_EXPENSES, HEALTHCARE_COVERAGE, INCOME`

**encounters.csv:** `Id, START, STOP, PATIENT, ORGANIZATION, PROVIDER, PAYER, ENCOUNTERCLASS, CODE, DESCRIPTION, BASE_ENCOUNTER_COST, TOTAL_CLAIM_COST, PAYER_COVERAGE, REASONCODE, REASONDESCRIPTION`

**conditions.csv:** `START, STOP, PATIENT, ENCOUNTER, CODE, DESCRIPTION`

**medications.csv:** `START, STOP, PATIENT, PAYER, ENCOUNTER, CODE, DESCRIPTION, BASE_COST, PAYER_COVERAGE, DISPENSES, TOTALCOST, REASONCODE, REASONDESCRIPTION`

**providers.csv:** `Id, ORGANIZATION, NAME, GENDER, SPECIALITY, ADDRESS, CITY, STATE, ZIP, LAT, LON, ENCOUNTERS, PROCEDURES`

Note: Synthea uses `Id` (mixed case) for encounters and providers, `ID` (all caps) for patients. This inconsistency is in the source data — preserve it exactly in the raw tables. Dates are ISO-8601: `YYYY-MM-DD` for patients, `YYYY-MM-DDTHH:MM:SSZ` for encounters (use `substr(col,1,10)` to extract the date part).

---

## SNOMED-CT Code Reference

Used in analytics SQL and test fixtures. These are standard SNOMED-CT codes that Synthea generates.

| Condition | SNOMED code |
|-----------|------------|
| Type 2 diabetes | `44054006` |
| Diabetes mellitus (general) | `73211009` |
| Essential hypertension | `59621000` |
| Heart failure | `84114007` |
| COPD | `13645005` |
| Asthma | `195967001` |
| Major depression | `370143000` |
| Generalized anxiety | `197480006` |

---

## Task 1: Codebase Cleanup

**Files:** Delete many, keep structure intact.

- [ ] **Step 1: Delete CMS-specific source files**

```bash
rm src/cms_platform/ingest/download.py
rm src/cms_platform/ingest/load.py
rm src/cms_platform/schema/transforms.py
```

- [ ] **Step 2: Delete all test files (will be rewritten)**

```bash
rm tests/test_ingest.py tests/test_schema.py tests/test_analytics.py
rm tests/test_scoring.py tests/test_api.py tests/test_compliance.py
rm -f tests/test_stubs.py tests/test_common.py
```

- [ ] **Step 3: Delete all SQL files (will be rewritten)**

```bash
rm sql/schema/ddl.sql
rm sql/analytics/readmission_30day.sql sql/analytics/cohort_segmentation.sql
rm sql/analytics/cost_benchmarking.sql sql/analytics/care_gap_detection.sql
rm sql/analytics/utilization_trends.sql
```

- [ ] **Step 4: Delete root-level scratch files and old notebook**

```bash
rm -f cms-claims-plan.md check_config.py test_mutable.py
rm -f notebooks/story.ipynb
rm -f docs/superpowers/plans/2026-05-30-wp1-ingest.md
rm -f docs/superpowers/plans/2026-05-30-wp2-schema.md
rm -f docs/superpowers/plans/2026-05-30-wp4-scoring.md
rm -f docs/superpowers/plans/2026-05-30-wp5-api-routes.md
rm -f docs/superpowers/plans/2026-05-30-wp7-cicd.md
```

- [ ] **Step 5: Rename beneficiary route file**

```bash
mv src/cms_platform/api/routes/beneficiary.py src/cms_platform/api/routes/patient.py
```

- [ ] **Step 6: Verify project still imports cleanly (it won't run yet — that's fine)**

```bash
python -c "import cms_platform.common.config" && echo "common ok"
```

Expected: prints "common ok". Other imports will fail until later tasks.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: remove CMS DE-SynPUF artifacts, rename beneficiary→patient"
```

---

## Task 2: Config + Common Updates

**Files:**
- Modify: `src/cms_platform/common/config.py`
- Modify: `src/cms_platform/common/mask.py`
- Modify: `src/cms_platform/scoring/explainer.py`
- Modify: `tests/conftest.py`
- Create: `tests/test_compliance.py`

- [ ] **Step 1: Write failing compliance tests**

Create `tests/test_compliance.py`:

```python
from __future__ import annotations

import hashlib

import pytest

from cms_platform.common.mask import PHI_FIELDS, mask_field, mask_record


def test_phi_fields_contains_patient_id() -> None:
    assert "patient_id" in PHI_FIELDS


def test_phi_fields_contains_dates() -> None:
    assert "birthdate" in PHI_FIELDS
    assert "deathdate" in PHI_FIELDS


def test_mask_field_phi_returns_hash_prefix() -> None:
    result = mask_field("patient_id", "abc-uuid", phi_read=False)
    assert result is not None
    assert result.startswith("****")
    expected_hash = hashlib.sha256(b"abc-uuid").hexdigest()[:8]
    assert result == f"****{expected_hash}"


def test_mask_field_phi_read_returns_plaintext() -> None:
    assert mask_field("patient_id", "abc-uuid", phi_read=True) == "abc-uuid"


def test_mask_field_non_phi_passthrough() -> None:
    assert mask_field("encounter_class", "inpatient", phi_read=False) == "inpatient"


def test_mask_record_masks_phi_fields() -> None:
    record: dict[str, object] = {
        "patient_id": "some-uuid",
        "birthdate": "1960-01-01",
        "encounter_class": "inpatient",
    }
    masked = mask_record(record)
    assert masked["patient_id"] != "some-uuid"
    assert masked["birthdate"] != "1960-01-01"
    assert masked["encounter_class"] == "inpatient"


def test_mask_record_phi_read_passthrough() -> None:
    record: dict[str, object] = {"patient_id": "some-uuid", "birthdate": "1960-01-01"}
    result = mask_record(record, phi_read=True)
    assert result["patient_id"] == "some-uuid"
    assert result["birthdate"] == "1960-01-01"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
.venv/bin/pytest tests/test_compliance.py -v
```

Expected: FAIL (PHI_FIELDS still has old field names)

- [ ] **Step 3: Update config.py**

Replace the full content of `src/cms_platform/common/config.py`:

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_path: str = Field(default="data/processed/cms.duckdb")
    raw_data_dir: str = Field(default="data/raw")
    manifests_dir: str = Field(default="data/manifests")
    ollama_base_url: str = Field(default="http://localhost:11434/v1")
    ollama_model: str = Field(default="llama3.2")
    log_level: str = Field(default="INFO")
    # Pre-generated 1 000-patient Synthea CSV dataset from MITRE.
    # TODO(future-source): swap for Blue Button 2.0 FHIR API once OAuth registration
    #   is in place — see ARCHITECTURE.md "Real Data Migration Path".
    synthea_data_url: str = Field(
        default=(
            "https://synthetichealth.github.io/synthea-sample-data"
            "/downloads/synthea_sample_data_csv_latest.zip"
        )
    )

    model_config = SettingsConfigDict(env_prefix="CMS_", env_file=".env", extra="ignore")


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Update mask.py**

Replace the full content of `src/cms_platform/common/mask.py`:

```python
from __future__ import annotations

import hashlib

# Fields treated as PHI in external API responses.
# phi_read=True bypasses masking for callers with explicit PHI_READ scope.
# TODO(future-auth): enforce phi_read via JWT claim rather than query param.
PHI_FIELDS: frozenset[str] = frozenset(
    {
        "patient_id",
        "birthdate",
        "deathdate",
        "ssn",
        "first",
        "last",
    }
)


def mask_field(field_name: str, value: str | None, *, phi_read: bool = False) -> str | None:
    """Mask a PHI field unless the caller holds PHI_READ scope.

    Returns '****' + first 8 hex chars of SHA-256(value).
    In production: replace with format-preserving encryption.
    """
    if phi_read or value is None:
        return value
    if field_name not in PHI_FIELDS:
        return value
    return "****" + hashlib.sha256(value.encode()).hexdigest()[:8]


def mask_record(
    record: dict[str, object],
    *,
    phi_read: bool = False,
) -> dict[str, object]:
    """Apply mask_field to every PHI field in a flat record dict."""
    result: dict[str, object] = {}
    for k, v in record.items():
        if k in PHI_FIELDS and isinstance(v, str):
            result[k] = mask_field(k, v, phi_read=phi_read)
        else:
            result[k] = v
    return result
```

- [ ] **Step 5: Update explainer.py — rename beneficiary_id → patient_id**

Replace `src/cms_platform/scoring/explainer.py`:

```python
from dataclasses import dataclass

from openai import OpenAI

from cms_platform.common.config import Settings


@dataclass
class CareGapExplanation:
    patient_id: str
    gaps: list[str]
    summary: str
    model_used: str


def _stub_explanation(patient_id: str, gaps: list[str]) -> CareGapExplanation:
    if not gaps:
        summary = "No open care gaps identified for this patient."
    else:
        listed = ", ".join(gaps[:3])
        tail = f" (and {len(gaps) - 3} more)" if len(gaps) > 3 else ""
        summary = (
            f"Patient has {len(gaps)} open care gap(s): {listed}{tail}. "
            "Clinical review recommended."
        )
    return CareGapExplanation(patient_id=patient_id, gaps=gaps, summary=summary, model_used="stub")


def _build_prompt(patient_id: str, gaps: list[str]) -> str:
    if not gaps:
        return f"Patient {patient_id} has no open care gaps. Confirm in one sentence."
    gap_list = "\n".join(f"- {g}" for g in gaps)
    return (
        f"You are a clinical care coordinator. Patient {patient_id} has "
        f"{len(gaps)} open care gap(s):\n{gap_list}\n\n"
        "Write 2-3 sentences summarising these gaps and recommending next steps. "
        "Be concise and clinical. Do not add invented medical details."
    )


def explain_care_gaps(
    patient_id: str,
    gaps: list[str],
    settings: Settings,
) -> CareGapExplanation:
    """Compose a natural-language care-gap summary via Ollama.

    Falls back to a deterministic stub when Ollama is unreachable — the demo
    runs fully offline without any LLM infrastructure.
    TODO(future-llm): add retry with exponential backoff for transient failures.
    """
    try:
        client = OpenAI(base_url=settings.ollama_base_url, api_key="ollama")
        response = client.chat.completions.create(
            model=settings.ollama_model,
            messages=[{"role": "user", "content": _build_prompt(patient_id, gaps)}],
            timeout=30,
        )
        content = response.choices[0].message.content or ""
        return CareGapExplanation(
            patient_id=patient_id, gaps=gaps, summary=content, model_used=settings.ollama_model
        )
    except Exception:
        return _stub_explanation(patient_id, gaps)
```

- [ ] **Step 6: Update conftest.py**

Replace `tests/conftest.py`:

```python
from pathlib import Path

import pytest

from cms_platform.common.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=str(tmp_path / "test.duckdb"),
        raw_data_dir=str(tmp_path / "raw"),
        manifests_dir=str(tmp_path / "manifests"),
    )
```

- [ ] **Step 7: Run tests — should pass**

```bash
.venv/bin/pytest tests/test_compliance.py -v
```

Expected: 7 passed

- [ ] **Step 8: Run lint**

```bash
.venv/bin/ruff check src/ tests/
.venv/bin/mypy src/
```

Expected: clean

- [ ] **Step 9: Commit**

```bash
git add src/cms_platform/common/config.py src/cms_platform/common/mask.py
git add src/cms_platform/scoring/explainer.py tests/conftest.py tests/test_compliance.py
git commit -m "feat: update config/mask/explainer for Synthea (patient_id, new PHI fields)"
```

---

## Task 3: Synthea Ingest (download + load)

**Files:**
- Create: `src/cms_platform/ingest/download.py`
- Create: `src/cms_platform/ingest/load.py`
- Create: `tests/test_ingest.py`

- [ ] **Step 1: Write failing ingest tests**

Create `tests/test_ingest.py`:

```python
from __future__ import annotations

import csv
from pathlib import Path

import duckdb
import pytest

from cms_platform.common.config import Settings
from cms_platform.ingest.load import _ensure_raw_tables, load_synthea_data


# ---------------------------------------------------------------------------
# Helpers — write minimal Synthea-format CSV fixtures
# ---------------------------------------------------------------------------

def _write_patients(path: Path) -> None:
    path.write_text(
        "ID,BIRTHDATE,DEATHDATE,SSN,DRIVERS,PASSPORT,PREFIX,FIRST,LAST,SUFFIX,"
        "MAIDEN,MARITAL,RACE,ETHNICITY,GENDER,BIRTHPLACE,ADDRESS,CITY,STATE,"
        "COUNTY,FIPS,ZIP,LAT,LON,HEALTHCARE_EXPENSES,HEALTHCARE_COVERAGE,INCOME\n"
        "aaaaaaaa-0001-0001-0001-000000000001,1960-03-15,,999-00-0001,,,"
        "Ms.,Alice,Smith,,,,white,nonhispanic,F,Springfield MA US,"
        "123 Main St,Springfield,MA,Hampden,25013,01101,42.1,-72.5,"
        "45000.00,38000.00,55000\n"
    )


def _write_encounters(path: Path) -> None:
    path.write_text(
        "Id,START,STOP,PATIENT,ORGANIZATION,PROVIDER,PAYER,ENCOUNTERCLASS,"
        "CODE,DESCRIPTION,BASE_ENCOUNTER_COST,TOTAL_CLAIM_COST,PAYER_COVERAGE,"
        "REASONCODE,REASONDESCRIPTION\n"
        "bbbbbbbb-0001-0001-0001-000000000001,"
        "2022-01-10T09:00:00Z,2022-01-12T11:00:00Z,"
        "aaaaaaaa-0001-0001-0001-000000000001,"
        "org-001,prov-001,payer-001,inpatient,"
        "32485007,Hospital admission,5000.00,7500.00,6000.00,,\n"
    )


def _write_conditions(path: Path) -> None:
    path.write_text(
        "START,STOP,PATIENT,ENCOUNTER,CODE,DESCRIPTION\n"
        "2018-06-01,,aaaaaaaa-0001-0001-0001-000000000001,"
        "bbbbbbbb-0001-0001-0001-000000000001,44054006,Diabetes mellitus type 2\n"
    )


def _write_medications(path: Path) -> None:
    path.write_text(
        "START,STOP,PATIENT,PAYER,ENCOUNTER,CODE,DESCRIPTION,BASE_COST,"
        "PAYER_COVERAGE,DISPENSES,TOTALCOST,REASONCODE,REASONDESCRIPTION\n"
        "2022-01-10,2022-04-10,aaaaaaaa-0001-0001-0001-000000000001,"
        "payer-001,bbbbbbbb-0001-0001-0001-000000000001,"
        "860975,Metformin 500 MG,5.00,4.00,3,15.00,,\n"
    )


def _write_providers(path: Path) -> None:
    path.write_text(
        "Id,ORGANIZATION,NAME,GENDER,SPECIALITY,ADDRESS,CITY,STATE,"
        "ZIP,LAT,LON,ENCOUNTERS,PROCEDURES\n"
        "prov-001,org-001,Dr. Jane Doe,F,GENERAL PRACTICE,"
        "456 Elm St,Springfield,MA,01101,42.1,-72.5,10,5\n"
    )


def _seed_csvs(tmp_path: Path) -> Path:
    data_dir = tmp_path / "synthea"
    data_dir.mkdir()
    _write_patients(data_dir / "patients.csv")
    _write_encounters(data_dir / "encounters.csv")
    _write_conditions(data_dir / "conditions.csv")
    _write_medications(data_dir / "medications.csv")
    _write_providers(data_dir / "providers.csv")
    return data_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_ensure_raw_tables_creates_all_tables(tmp_path: Path) -> None:
    conn = duckdb.connect()
    _ensure_raw_tables(conn)
    tables = {r[0] for r in conn.execute("SHOW TABLES").fetchall()}
    assert {"raw_patients", "raw_encounters", "raw_conditions",
            "raw_medications", "raw_providers"} <= tables


def test_load_synthea_data_inserts_rows(tmp_path: Path, settings: Settings) -> None:
    conn = duckdb.connect()
    data_dir = _seed_csvs(tmp_path)
    _ensure_raw_tables(conn)
    rows = load_synthea_data(data_dir, conn)
    assert rows["raw_patients"] == 1
    assert rows["raw_encounters"] == 1
    assert rows["raw_conditions"] == 1
    assert rows["raw_medications"] == 1
    assert rows["raw_providers"] == 1


def test_load_synthea_data_is_idempotent(tmp_path: Path, settings: Settings) -> None:
    conn = duckdb.connect()
    data_dir = _seed_csvs(tmp_path)
    _ensure_raw_tables(conn)
    load_synthea_data(data_dir, conn)
    rows2 = load_synthea_data(data_dir, conn)
    # Second call should insert 0 rows (already loaded)
    assert all(v == 0 for v in rows2.values())


def test_raw_patients_has_expected_columns(tmp_path: Path) -> None:
    conn = duckdb.connect()
    data_dir = _seed_csvs(tmp_path)
    _ensure_raw_tables(conn)
    load_synthea_data(data_dir, conn)
    cols = {d[0] for d in conn.execute("SELECT * FROM raw_patients LIMIT 0").description or []}
    assert "ID" in cols
    assert "BIRTHDATE" in cols
    assert "_source_file" in cols


def test_synthea_data_url_is_configured(settings: Settings) -> None:
    assert "synthea" in settings.synthea_data_url.lower()
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
.venv/bin/pytest tests/test_ingest.py -v
```

Expected: ImportError (modules don't exist yet)

- [ ] **Step 3: Create load.py**

Create `src/cms_platform/ingest/load.py`:

```python
"""Load Synthea CSV files into raw DuckDB tables.

Raw tables store every column as VARCHAR — no type coercion at ingest time.
Type casting happens in the schema transform layer (schema/transforms.py).

TODO(future-source): replace _load_csv with a FHIR bundle parser to ingest
    real Blue Button 2.0 data — the raw table contract stays identical.
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)

# Explicit column lists match Synthea CSV headers exactly (case-sensitive).
# Do not add columns that are not in the source files.
_PATIENT_COLS: list[str] = [
    "ID", "BIRTHDATE", "DEATHDATE", "SSN", "DRIVERS", "PASSPORT",
    "PREFIX", "FIRST", "LAST", "SUFFIX", "MAIDEN", "MARITAL",
    "RACE", "ETHNICITY", "GENDER", "BIRTHPLACE", "ADDRESS", "CITY",
    "STATE", "COUNTY", "FIPS", "ZIP", "LAT", "LON",
    "HEALTHCARE_EXPENSES", "HEALTHCARE_COVERAGE", "INCOME",
]

_ENCOUNTER_COLS: list[str] = [
    "Id", "START", "STOP", "PATIENT", "ORGANIZATION", "PROVIDER",
    "PAYER", "ENCOUNTERCLASS", "CODE", "DESCRIPTION",
    "BASE_ENCOUNTER_COST", "TOTAL_CLAIM_COST", "PAYER_COVERAGE",
    "REASONCODE", "REASONDESCRIPTION",
]

_CONDITION_COLS: list[str] = [
    "START", "STOP", "PATIENT", "ENCOUNTER", "CODE", "DESCRIPTION",
]

_MEDICATION_COLS: list[str] = [
    "START", "STOP", "PATIENT", "PAYER", "ENCOUNTER", "CODE",
    "DESCRIPTION", "BASE_COST", "PAYER_COVERAGE", "DISPENSES",
    "TOTALCOST", "REASONCODE", "REASONDESCRIPTION",
]

_PROVIDER_COLS: list[str] = [
    "Id", "ORGANIZATION", "NAME", "GENDER", "SPECIALITY",
    "ADDRESS", "CITY", "STATE", "ZIP", "LAT", "LON",
    "ENCOUNTERS", "PROCEDURES",
]

_TABLES: dict[str, tuple[str, list[str]]] = {
    "raw_patients":    ("patients.csv",    _PATIENT_COLS),
    "raw_encounters":  ("encounters.csv",  _ENCOUNTER_COLS),
    "raw_conditions":  ("conditions.csv",  _CONDITION_COLS),
    "raw_medications": ("medications.csv", _MEDICATION_COLS),
    "raw_providers":   ("providers.csv",   _PROVIDER_COLS),
}


def _col_ddl(cols: list[str]) -> str:
    return ",\n    ".join(f'"{c}" VARCHAR' for c in cols)


def _ensure_raw_tables(conn: duckdb.DuckDBPyConnection) -> None:
    """CREATE TABLE IF NOT EXISTS for all five raw tables."""
    for table, (_, cols) in _TABLES.items():
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                {_col_ddl(cols)},
                _source_file VARCHAR
            )
        """)


def _load_csv(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    csv_path: Path,
    cols: list[str],
) -> int:
    """Load one Synthea CSV into a raw table. Returns rows inserted (0 if already loaded)."""
    source = csv_path.name
    existing: int = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE _source_file = ?", [source]
    ).fetchone()[0]  # type: ignore[index]
    if existing > 0:
        logger.info("%s: already loaded (%d rows), skipping", source, existing)
        return 0

    col_list = ", ".join(f'"{c}"' for c in cols)
    conn.execute(f"""
        INSERT INTO {table} ({col_list}, _source_file)
        SELECT {col_list}, '{source}'
        FROM read_csv(
            '{csv_path}',
            all_varchar = true,
            ignore_errors = true,
            header = true
        )
    """)
    inserted: int = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE _source_file = ?", [source]
    ).fetchone()[0]  # type: ignore[index]
    logger.info("%s → %s: %d rows", source, table, inserted)
    return inserted


def load_synthea_data(
    data_dir: Path,
    conn: duckdb.DuckDBPyConnection,
) -> dict[str, int]:
    """Load all five Synthea CSV files from data_dir into raw tables.

    Idempotent — skips any file already present in the table.
    Returns a dict mapping table name → rows inserted this run.
    """
    results: dict[str, int] = {}
    for table, (filename, cols) in _TABLES.items():
        csv_path = data_dir / filename
        if not csv_path.exists():
            logger.warning("%s not found in %s — skipping", filename, data_dir)
            results[table] = 0
        else:
            results[table] = _load_csv(conn, table, csv_path, cols)
    return results


def main() -> None:
    from cms_platform.common.config import get_settings
    from cms_platform.common.db import get_connection
    from cms_platform.common.logging import configure_logging

    settings = get_settings()
    configure_logging(settings.log_level)
    conn = get_connection(settings)
    _ensure_raw_tables(conn)
    data_dir = Path(settings.raw_data_dir) / "synthea"
    load_synthea_data(data_dir, conn)
```

- [ ] **Step 4: Create download.py**

Create `src/cms_platform/ingest/download.py`:

```python
"""Download pre-generated Synthea CSV data from MITRE's sample data repository.

Synthea (https://synthea.mitre.org) is an open-source synthetic patient
generator by MITRE. We use their published 1 000-patient CSV dataset so the
project runs without requiring a local Java/Synthea installation.

TODO(future-source): support running Synthea locally for custom patient counts:
    java -jar synthea-with-dependencies.jar -p <N> --exporter.csv.export true
TODO(future-source): support Blue Button 2.0 FHIR API for real Medicare data.
"""
from __future__ import annotations

import json
import logging
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import httpx

from cms_platform.common.config import Settings

logger = logging.getLogger(__name__)


def download_synthea_data(settings: Settings) -> Path:
    """Download the Synthea sample CSV zip and extract to data/raw/synthea/.

    Idempotent: if patients.csv already exists in the target directory, skips
    the download and returns the directory path immediately.

    Returns the directory containing extracted CSV files.
    """
    data_dir = Path(settings.raw_data_dir) / "synthea"
    data_dir.mkdir(parents=True, exist_ok=True)

    if (data_dir / "patients.csv").exists():
        logger.info("Synthea data already present at %s — skipping download", data_dir)
        return data_dir

    logger.info("Downloading Synthea sample data from %s", settings.synthea_data_url)
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        response = client.get(settings.synthea_data_url)
        response.raise_for_status()

    with zipfile.ZipFile(BytesIO(response.content)) as zf:
        csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
        for name in csv_names:
            # Flatten: write only the basename (no subdirectory nesting)
            dest = data_dir / Path(name).name
            dest.write_bytes(zf.read(name))
            logger.info("Extracted %s → %s", name, dest)

    _write_manifest(data_dir, settings.synthea_data_url, csv_names)
    return data_dir


def _write_manifest(data_dir: Path, url: str, csv_names: list[str]) -> None:
    manifest = {
        "source_url": url,
        "downloaded_at": datetime.now(UTC).isoformat(),
        "files": [Path(n).name for n in csv_names],
    }
    manifests_dir = data_dir.parent.parent / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    (manifests_dir / "synthea.json").write_text(json.dumps(manifest, indent=2))


def main() -> None:
    from cms_platform.common.config import get_settings
    from cms_platform.common.logging import configure_logging

    settings = get_settings()
    configure_logging(settings.log_level)
    download_synthea_data(settings)
```

- [ ] **Step 5: Run the ingest tests**

```bash
.venv/bin/pytest tests/test_ingest.py -v
```

Expected: 5 passed

- [ ] **Step 6: Run lint**

```bash
.venv/bin/ruff check src/ tests/
.venv/bin/mypy src/
```

Expected: clean

- [ ] **Step 7: Commit**

```bash
git add src/cms_platform/ingest/ tests/test_ingest.py
git commit -m "feat(ingest): Synthea CSV download + raw table loader (5 tables)"
```

---

## Task 4: Star Schema DDL + Transforms

**Files:**
- Create: `sql/schema/ddl.sql`
- Create: `src/cms_platform/schema/transforms.py`
- Create: `tests/test_schema.py`

- [ ] **Step 1: Write failing schema tests**

Create `tests/test_schema.py`:

```python
from __future__ import annotations

import duckdb
import pytest

from cms_platform.common.config import Settings
from cms_platform.ingest.load import _ensure_raw_tables, load_synthea_data
from cms_platform.schema.transforms import build_star_schema
from tests.test_ingest import _seed_csvs  # reuse fixture helpers


@pytest.fixture
def star_conn(tmp_path: pytest.TempPathFactory, settings: Settings) -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect()
    data_dir = _seed_csvs(tmp_path)
    _ensure_raw_tables(conn)
    load_synthea_data(data_dir, conn)
    build_star_schema(conn, settings)
    return conn


def test_dim_date_covers_expected_range(star_conn: duckdb.DuckDBPyConnection) -> None:
    rows = star_conn.execute(
        "SELECT COUNT(*) FROM dim_date WHERE full_date BETWEEN '2000-01-01' AND '2030-12-31'"
    ).fetchone()
    assert rows is not None and rows[0] > 10_000


def test_dim_patient_loaded(star_conn: duckdb.DuckDBPyConnection) -> None:
    n = star_conn.execute("SELECT COUNT(*) FROM dim_patient").fetchone()[0]
    assert n == 1


def test_dim_provider_loaded(star_conn: duckdb.DuckDBPyConnection) -> None:
    n = star_conn.execute("SELECT COUNT(*) FROM dim_provider").fetchone()[0]
    assert n == 1


def test_dim_condition_code_loaded(star_conn: duckdb.DuckDBPyConnection) -> None:
    n = star_conn.execute("SELECT COUNT(*) FROM dim_condition_code").fetchone()[0]
    assert n >= 1


def test_fact_encounter_loaded(star_conn: duckdb.DuckDBPyConnection) -> None:
    n = star_conn.execute("SELECT COUNT(*) FROM fact_encounter").fetchone()[0]
    assert n == 1


def test_fact_encounter_has_patient_key(star_conn: duckdb.DuckDBPyConnection) -> None:
    row = star_conn.execute(
        "SELECT fe.patient_key, dp.patient_id "
        "FROM fact_encounter fe JOIN dim_patient dp ON dp.patient_key = fe.patient_key"
    ).fetchone()
    assert row is not None
    assert row[1] == "aaaaaaaa-0001-0001-0001-000000000001"


def test_fact_condition_loaded(star_conn: duckdb.DuckDBPyConnection) -> None:
    n = star_conn.execute("SELECT COUNT(*) FROM fact_condition").fetchone()[0]
    assert n == 1


def test_fact_medication_loaded(star_conn: duckdb.DuckDBPyConnection) -> None:
    n = star_conn.execute("SELECT COUNT(*) FROM fact_medication").fetchone()[0]
    assert n == 1


def test_build_star_schema_is_idempotent(tmp_path: pytest.TempPathFactory, settings: Settings) -> None:
    conn = duckdb.connect()
    data_dir = _seed_csvs(tmp_path)
    _ensure_raw_tables(conn)
    load_synthea_data(data_dir, conn)
    build_star_schema(conn, settings)
    build_star_schema(conn, settings)  # second call must not raise or duplicate rows
    n = conn.execute("SELECT COUNT(*) FROM fact_encounter").fetchone()[0]
    assert n == 1
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
.venv/bin/pytest tests/test_schema.py -v
```

Expected: ImportError or NameError

- [ ] **Step 3: Create sql/schema/ddl.sql**

```sql
-- Business question: Unified star schema for Synthea synthetic patient data
-- SQL technique:     Dimensional modelling — surrogate keys, date dimension, NOT EXISTS guards
-- Scaling note:      At V2, partition fact_encounter by (year, patient_key % N);
--                    replace DuckDB with Postgres and add a columnar extension for analytics.

-- ── Calendar dimension ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_date (
    date_key    INTEGER PRIMARY KEY,   -- YYYYMMDD integer
    full_date   DATE    NOT NULL,
    year        SMALLINT NOT NULL,
    month       SMALLINT NOT NULL,
    day         SMALLINT NOT NULL,
    quarter     SMALLINT NOT NULL,
    day_of_week SMALLINT NOT NULL      -- 0=Sunday … 6=Saturday
);

-- ── Patient dimension ────────────────────────────────────────────────────────
-- One row per Synthea patient. Patient IDs are UUIDs; treat as PHI.
CREATE TABLE IF NOT EXISTS dim_patient (
    patient_key          BIGINT  PRIMARY KEY,
    patient_id           VARCHAR NOT NULL UNIQUE,   -- Synthea UUID — PHI
    birthdate            DATE,
    deathdate            DATE,
    gender               VARCHAR,
    race                 VARCHAR,
    ethnicity            VARCHAR,
    city                 VARCHAR,
    state                VARCHAR,
    zip                  VARCHAR,
    healthcare_expenses  DECIMAL(12,2),
    healthcare_coverage  DECIMAL(12,2),
    income               INTEGER
);

-- ── Provider dimension ───────────────────────────────────────────────────────
-- Healthcare providers (individual clinicians) from providers.csv.
CREATE TABLE IF NOT EXISTS dim_provider (
    provider_key  BIGINT  PRIMARY KEY,
    provider_id   VARCHAR NOT NULL UNIQUE,   -- Synthea UUID
    name          VARCHAR,
    speciality    VARCHAR,
    city          VARCHAR,
    state         VARCHAR
);

-- ── Condition code dimension (SNOMED-CT dictionary) ──────────────────────────
-- One row per distinct SNOMED-CT code seen in the data.
-- SNOMED-CT is the international clinical terminology standard; it replaces
-- ICD-9 for clinical use. ICD-10 is still used for billing — see ARCHITECTURE.md.
CREATE TABLE IF NOT EXISTS dim_condition_code (
    code_key     BIGINT  PRIMARY KEY,
    snomed_code  VARCHAR NOT NULL UNIQUE,
    description  VARCHAR
);

-- ── Encounter fact ───────────────────────────────────────────────────────────
-- One row per clinical encounter (visit, admission, etc.).
-- encounter_class values from Synthea: inpatient, ambulatory, emergency,
--   urgentcare, wellness, outpatient.
CREATE TABLE IF NOT EXISTS fact_encounter (
    encounter_key     BIGINT  PRIMARY KEY,
    patient_key       BIGINT  REFERENCES dim_patient(patient_key),
    provider_key      BIGINT  REFERENCES dim_provider(provider_key),
    start_date_key    INTEGER REFERENCES dim_date(date_key),
    stop_date_key     INTEGER REFERENCES dim_date(date_key),
    encounter_id      VARCHAR NOT NULL UNIQUE,
    encounter_class   VARCHAR,
    description       VARCHAR,
    base_cost         DECIMAL(10,2),
    total_claim_cost  DECIMAL(10,2),
    payer_coverage    DECIMAL(10,2),
    reason_code       VARCHAR,
    reason_description VARCHAR
);

-- ── Condition fact ───────────────────────────────────────────────────────────
-- One row per condition episode (start → stop or still active if stop IS NULL).
CREATE TABLE IF NOT EXISTS fact_condition (
    condition_key   BIGINT  PRIMARY KEY,
    patient_key     BIGINT  REFERENCES dim_patient(patient_key),
    encounter_key   BIGINT  REFERENCES fact_encounter(encounter_key),
    start_date_key  INTEGER REFERENCES dim_date(date_key),
    stop_date_key   INTEGER,           -- NULL = still active
    snomed_code     VARCHAR,
    description     VARCHAR
);

-- ── Medication fact ──────────────────────────────────────────────────────────
-- One row per medication dispense event. RxNorm codes identify drugs.
-- TODO(future-coding): add a dim_drug table keyed on rxnorm_code for richer lookups.
CREATE TABLE IF NOT EXISTS fact_medication (
    medication_key  BIGINT  PRIMARY KEY,
    patient_key     BIGINT  REFERENCES dim_patient(patient_key),
    encounter_key   BIGINT  REFERENCES fact_encounter(encounter_key),
    start_date_key  INTEGER REFERENCES dim_date(date_key),
    stop_date_key   INTEGER,           -- NULL = ongoing
    rxnorm_code     VARCHAR,
    description     VARCHAR,
    base_cost       DECIMAL(10,2),
    total_cost      DECIMAL(10,2),
    dispenses       INTEGER,
    payer_coverage  DECIMAL(10,2)
);
```

- [ ] **Step 4: Create src/cms_platform/schema/transforms.py**

```python
"""Synthea raw tables → star schema transforms.

Populates dim_date, dim_patient, dim_provider, dim_condition_code,
fact_encounter, fact_condition, fact_medication. All functions are idempotent.

V2 swap point: at V2, each fact table will be hash-partitioned by
(year, patient_key % N) so intra-shard joins never cross node boundaries.
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from cms_platform.common.config import Settings

logger = logging.getLogger(__name__)

_DDL_PATH = Path(__file__).parent.parent.parent.parent / "sql" / "schema" / "ddl.sql"


def _run_ddl(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(_DDL_PATH.read_text())


def _date_key(col: str) -> str:
    """INTEGER date key from a DATE column."""
    return f"CAST(strftime({col}, '%Y%m%d') AS INTEGER)"


def _to_date(col: str) -> str:
    """DATE from an ISO-8601 string column; handles both date and datetime forms."""
    return f"TRY_CAST(substr({col}, 1, 10) AS DATE)"


def _populate_dim_date(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(f"""
        INSERT INTO dim_date (date_key, full_date, year, month, day, quarter, day_of_week)
        SELECT
            CAST(strftime(d::DATE, '%Y%m%d') AS INTEGER),
            d::DATE,
            EXTRACT(YEAR    FROM d)::SMALLINT,
            EXTRACT(MONTH   FROM d)::SMALLINT,
            EXTRACT(DAY     FROM d)::SMALLINT,
            EXTRACT(QUARTER FROM d)::SMALLINT,
            EXTRACT(DOW     FROM d)::SMALLINT
        FROM generate_series(DATE '2000-01-01', DATE '2030-12-31', INTERVAL '1 day') AS t(d)
        WHERE NOT EXISTS (
            SELECT 1 FROM dim_date
            WHERE date_key = CAST(strftime(d::DATE, '%Y%m%d') AS INTEGER)
        )
    """)


def _populate_dim_patient(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(f"""
        INSERT INTO dim_patient (
            patient_key, patient_id, birthdate, deathdate,
            gender, race, ethnicity, city, state, zip,
            healthcare_expenses, healthcare_coverage, income
        )
        SELECT
            ROW_NUMBER() OVER ()
                + COALESCE((SELECT MAX(patient_key) FROM dim_patient), 0),
            rp."ID",
            {_to_date('"BIRTHDATE"')},
            {_to_date('"DEATHDATE"')},
            rp."GENDER", rp."RACE", rp."ETHNICITY",
            rp."CITY", rp."STATE", rp."ZIP",
            TRY_CAST(rp."HEALTHCARE_EXPENSES" AS DECIMAL(12,2)),
            TRY_CAST(rp."HEALTHCARE_COVERAGE" AS DECIMAL(12,2)),
            TRY_CAST(rp."INCOME" AS INTEGER)
        FROM raw_patients rp
        WHERE NOT EXISTS (
            SELECT 1 FROM dim_patient dp WHERE dp.patient_id = rp."ID"
        )
    """)


def _populate_dim_provider(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("""
        INSERT INTO dim_provider (provider_key, provider_id, name, speciality, city, state)
        SELECT
            ROW_NUMBER() OVER ()
                + COALESCE((SELECT MAX(provider_key) FROM dim_provider), 0),
            rp."Id", rp."NAME", rp."SPECIALITY", rp."CITY", rp."STATE"
        FROM raw_providers rp
        WHERE NOT EXISTS (
            SELECT 1 FROM dim_provider dp WHERE dp.provider_id = rp."Id"
        )
    """)


def _populate_dim_condition_code(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("""
        INSERT INTO dim_condition_code (code_key, snomed_code, description)
        SELECT
            ROW_NUMBER() OVER ()
                + COALESCE((SELECT MAX(code_key) FROM dim_condition_code), 0),
            rc."CODE",
            rc."DESCRIPTION"
        FROM (
            SELECT DISTINCT "CODE", "DESCRIPTION" FROM raw_conditions
            WHERE NULLIF("CODE", '') IS NOT NULL
        ) rc
        WHERE NOT EXISTS (
            SELECT 1 FROM dim_condition_code d WHERE d.snomed_code = rc."CODE"
        )
    """)


def _populate_fact_encounter(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(f"""
        INSERT INTO fact_encounter (
            encounter_key, patient_key, provider_key,
            start_date_key, stop_date_key,
            encounter_id, encounter_class, description,
            base_cost, total_claim_cost, payer_coverage,
            reason_code, reason_description
        )
        SELECT
            ROW_NUMBER() OVER ()
                + COALESCE((SELECT MAX(encounter_key) FROM fact_encounter), 0),
            dp.patient_key,
            prov.provider_key,
            {_date_key(_to_date('re."START"'))},
            {_date_key(_to_date('re."STOP"'))},
            re."Id",
            re."ENCOUNTERCLASS",
            re."DESCRIPTION",
            TRY_CAST(re."BASE_ENCOUNTER_COST" AS DECIMAL(10,2)),
            TRY_CAST(re."TOTAL_CLAIM_COST"    AS DECIMAL(10,2)),
            TRY_CAST(re."PAYER_COVERAGE"      AS DECIMAL(10,2)),
            NULLIF(re."REASONCODE", ''),
            NULLIF(re."REASONDESCRIPTION", '')
        FROM raw_encounters re
        LEFT JOIN dim_patient  dp   ON dp.patient_id   = re."PATIENT"
        LEFT JOIN dim_provider prov ON prov.provider_id = re."PROVIDER"
        WHERE NOT EXISTS (
            SELECT 1 FROM fact_encounter fe WHERE fe.encounter_id = re."Id"
        )
    """)


def _populate_fact_condition(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(f"""
        INSERT INTO fact_condition (
            condition_key, patient_key, encounter_key,
            start_date_key, stop_date_key,
            snomed_code, description
        )
        SELECT
            ROW_NUMBER() OVER ()
                + COALESCE((SELECT MAX(condition_key) FROM fact_condition), 0),
            dp.patient_key,
            fe.encounter_key,
            {_date_key(_to_date('rc."START"'))},
            CASE WHEN NULLIF(rc."STOP", '') IS NOT NULL
                 THEN {_date_key(_to_date('rc."STOP"'))}
                 ELSE NULL END,
            rc."CODE",
            rc."DESCRIPTION"
        FROM raw_conditions rc
        LEFT JOIN dim_patient  dp ON dp.patient_id   = rc."PATIENT"
        LEFT JOIN fact_encounter fe ON fe.encounter_id = rc."ENCOUNTER"
        WHERE NOT EXISTS (
            SELECT 1 FROM fact_condition fc
            WHERE fc.patient_key = dp.patient_key
              AND fc.snomed_code  = rc."CODE"
              AND fc.start_date_key = {_date_key(_to_date('rc."START"'))}
        )
    """)


def _populate_fact_medication(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(f"""
        INSERT INTO fact_medication (
            medication_key, patient_key, encounter_key,
            start_date_key, stop_date_key,
            rxnorm_code, description,
            base_cost, total_cost, dispenses, payer_coverage
        )
        SELECT
            ROW_NUMBER() OVER ()
                + COALESCE((SELECT MAX(medication_key) FROM fact_medication), 0),
            dp.patient_key,
            fe.encounter_key,
            {_date_key(_to_date('rm."START"'))},
            CASE WHEN NULLIF(rm."STOP", '') IS NOT NULL
                 THEN {_date_key(_to_date('rm."STOP"'))}
                 ELSE NULL END,
            NULLIF(rm."CODE", ''),
            rm."DESCRIPTION",
            TRY_CAST(rm."BASE_COST"      AS DECIMAL(10,2)),
            TRY_CAST(rm."TOTALCOST"      AS DECIMAL(10,2)),
            TRY_CAST(rm."DISPENSES"      AS INTEGER),
            TRY_CAST(rm."PAYER_COVERAGE" AS DECIMAL(10,2))
        FROM raw_medications rm
        LEFT JOIN dim_patient  dp ON dp.patient_id   = rm."PATIENT"
        LEFT JOIN fact_encounter fe ON fe.encounter_id = rm."ENCOUNTER"
        WHERE NOT EXISTS (
            SELECT 1 FROM fact_medication fm
            WHERE fm.patient_key = dp.patient_key
              AND fm.rxnorm_code  = NULLIF(rm."CODE", '')
              AND fm.start_date_key = {_date_key(_to_date('rm."START"'))}
        )
    """)


def build_star_schema(conn: duckdb.DuckDBPyConnection, settings: Settings) -> None:
    """Transform Synthea raw tables into a clean star schema. Idempotent."""
    logger.info("building star schema")
    _run_ddl(conn)
    _populate_dim_date(conn)
    _populate_dim_patient(conn)
    _populate_dim_provider(conn)
    _populate_dim_condition_code(conn)
    _populate_fact_encounter(conn)
    _populate_fact_condition(conn)
    _populate_fact_medication(conn)
    logger.info("star schema build complete")
```

- [ ] **Step 5: Run schema tests**

```bash
.venv/bin/pytest tests/test_schema.py -v
```

Expected: 9 passed

- [ ] **Step 6: Run lint**

```bash
.venv/bin/ruff check src/ tests/
.venv/bin/mypy src/
```

Expected: clean

- [ ] **Step 7: Commit**

```bash
git add sql/schema/ddl.sql src/cms_platform/schema/transforms.py tests/test_schema.py
git commit -m "feat(schema): Synthea star schema — 4 dims + 3 facts, SNOMED-CT condition codes"
```

---

## Task 5: Analytics SQL + Python

**Files:**
- Create: `sql/analytics/readmission_30day.sql`
- Create: `sql/analytics/cohort_segmentation.sql`
- Create: `sql/analytics/cost_benchmarking.sql`
- Create: `sql/analytics/care_gap_detection.sql`
- Create: `sql/analytics/utilization_trends.sql`
- Modify: `src/cms_platform/analytics/queries.py`
- Create: `tests/test_analytics.py`

- [ ] **Step 1: Write failing analytics tests**

Create `tests/test_analytics.py`:

```python
from __future__ import annotations

import duckdb
import polars as pl
import pytest

from cms_platform.analytics.queries import (
    care_gap_detection,
    cohort_segmentation,
    cost_benchmarking,
    readmission_30day,
    utilization_trends,
)
from cms_platform.common.config import Settings
from cms_platform.ingest.load import _ensure_raw_tables, load_synthea_data
from cms_platform.schema.transforms import build_star_schema
from tests.test_ingest import _seed_csvs


@pytest.fixture
def analytics_conn(tmp_path: pytest.TempPathFactory, settings: Settings) -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect()
    data_dir = _seed_csvs(tmp_path)
    _ensure_raw_tables(conn)
    load_synthea_data(data_dir, conn)
    build_star_schema(conn, settings)
    return conn


def test_readmission_30day_returns_dataframe(analytics_conn: duckdb.DuckDBPyConnection) -> None:
    df = readmission_30day(analytics_conn)
    assert isinstance(df, pl.DataFrame)
    assert set(df.columns) >= {"encounter_year", "total_admissions", "readmissions", "readmission_rate_pct"}


def test_cohort_segmentation_returns_dataframe(analytics_conn: duckdb.DuckDBPyConnection) -> None:
    df = cohort_segmentation(analytics_conn)
    assert isinstance(df, pl.DataFrame)
    assert "total_patients" in df.columns
    assert "diabetes_cohort" in df.columns


def test_cost_benchmarking_returns_dataframe(analytics_conn: duckdb.DuckDBPyConnection) -> None:
    df = cost_benchmarking(analytics_conn)
    assert isinstance(df, pl.DataFrame)
    assert "avg_cost" in df.columns
    assert "p50_cost" in df.columns


def test_care_gap_detection_returns_dataframe(analytics_conn: duckdb.DuckDBPyConnection) -> None:
    df = care_gap_detection(analytics_conn)
    assert isinstance(df, pl.DataFrame)
    assert "diabetic_patients" in df.columns


def test_utilization_trends_returns_dataframe(analytics_conn: duckdb.DuckDBPyConnection) -> None:
    df = utilization_trends(analytics_conn)
    assert isinstance(df, pl.DataFrame)
    assert "encounter_class" in df.columns
    assert "encounter_count" in df.columns


def test_cohort_fixture_has_diabetes_patient(analytics_conn: duckdb.DuckDBPyConnection) -> None:
    df = cohort_segmentation(analytics_conn)
    # Our fixture has one patient with SNOMED 44054006 (Type 2 diabetes)
    assert df["diabetes_cohort"].sum() >= 1
```

- [ ] **Step 2: Create the five SQL files**

`sql/analytics/readmission_30day.sql`:
```sql
-- Business question: What percentage of inpatient encounters result in a
--                    readmission within 30 days?
-- SQL technique:     LAG window function over inpatient encounters ordered by
--                    admit date per patient; date arithmetic on full_date
-- Scaling note:      At V2, partition fact_encounter by patient_key % N;
--                    the LAG window becomes shard-local for most patients.

WITH inpatient AS (
    SELECT
        fe.patient_key,
        dd_start.full_date                            AS admit_date,
        dd_stop.full_date                             AS discharge_date,
        EXTRACT(YEAR FROM dd_start.full_date)::INTEGER AS encounter_year
    FROM fact_encounter fe
    JOIN dim_date dd_start ON dd_start.date_key = fe.start_date_key
    JOIN dim_date dd_stop  ON dd_stop.date_key  = fe.stop_date_key
    WHERE fe.encounter_class = 'inpatient'
),
with_prior AS (
    SELECT
        patient_key,
        admit_date,
        discharge_date,
        encounter_year,
        LAG(discharge_date) OVER (
            PARTITION BY patient_key ORDER BY admit_date
        ) AS prior_discharge
    FROM inpatient
)
SELECT
    encounter_year,
    COUNT(*)                                                AS total_admissions,
    COUNT(*) FILTER (
        WHERE prior_discharge IS NOT NULL
          AND admit_date - prior_discharge <= INTERVAL '30 days'
    )                                                       AS readmissions,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE prior_discharge IS NOT NULL
              AND admit_date - prior_discharge <= INTERVAL '30 days'
        ) / NULLIF(COUNT(*), 0),
    2)                                                      AS readmission_rate_pct
FROM with_prior
GROUP BY encounter_year
ORDER BY encounter_year
```

`sql/analytics/cohort_segmentation.sql`:
```sql
-- Business question: How many patients have each major chronic condition,
--                    broken down by the year of their first encounter?
-- SQL technique:     Conditional aggregation with FILTER; LEFT JOIN to derive
--                    per-patient condition flags from SNOMED-CT codes
-- Scaling note:      At V2, materialise patient_conditions as a pre-aggregated
--                    table refreshed on each ingest run.
--
-- SNOMED-CT codes used (see ARCHITECTURE.md for full reference):
--   44054006 / 73211009 = Diabetes  |  84114007 = Heart failure
--   13645005 / 195967001 = COPD/Asthma  |  59621000 = Hypertension

WITH patient_conditions AS (
    SELECT
        patient_key,
        COUNT(DISTINCT snomed_code)                                         AS condition_count,
        MAX(CASE WHEN snomed_code IN ('44054006','73211009') THEN 1 ELSE 0 END) AS has_diabetes,
        MAX(CASE WHEN snomed_code = '84114007'               THEN 1 ELSE 0 END) AS has_heart_failure,
        MAX(CASE WHEN snomed_code IN ('13645005','195967001') THEN 1 ELSE 0 END) AS has_copd_asthma,
        MAX(CASE WHEN snomed_code = '59621000'               THEN 1 ELSE 0 END) AS has_hypertension
    FROM fact_condition
    GROUP BY patient_key
),
patient_year AS (
    SELECT
        fe.patient_key,
        EXTRACT(YEAR FROM MIN(dd.full_date))::INTEGER AS first_encounter_year
    FROM fact_encounter fe
    JOIN dim_date dd ON dd.date_key = fe.start_date_key
    GROUP BY fe.patient_key
)
SELECT
    py.first_encounter_year                             AS encounter_year,
    COUNT(*)                                            AS total_patients,
    SUM(COALESCE(pc.has_diabetes,      0))              AS diabetes_cohort,
    SUM(COALESCE(pc.has_heart_failure, 0))              AS heart_failure_cohort,
    SUM(COALESCE(pc.has_copd_asthma,   0))              AS copd_asthma_cohort,
    SUM(COALESCE(pc.has_hypertension,  0))              AS hypertension_cohort,
    ROUND(AVG(COALESCE(pc.condition_count, 0)), 2)      AS avg_condition_count
FROM patient_year py
LEFT JOIN patient_conditions pc ON pc.patient_key = py.patient_key
GROUP BY py.first_encounter_year
ORDER BY py.first_encounter_year
```

`sql/analytics/cost_benchmarking.sql`:
```sql
-- Business question: How are encounter costs distributed, and which patients
--                    are in the high-cost top quartile?
-- SQL technique:     PERCENTILE_CONT for distribution stats; NTILE(4) window
--                    for quartile assignment; CTE to separate ranking from aggregation
-- Scaling note:      At V2, pre-aggregate into a cost_summary materialised view
--                    refreshed nightly; the percentile computation is expensive at scale.

WITH ranked AS (
    SELECT
        fe.patient_key,
        fe.total_claim_cost,
        EXTRACT(YEAR FROM dd.full_date)::INTEGER AS encounter_year,
        NTILE(4) OVER (
            PARTITION BY EXTRACT(YEAR FROM dd.full_date)
            ORDER BY fe.total_claim_cost
        ) AS cost_quartile
    FROM fact_encounter fe
    JOIN dim_date dd ON dd.date_key = fe.start_date_key
    WHERE fe.total_claim_cost IS NOT NULL
)
SELECT
    encounter_year,
    COUNT(DISTINCT patient_key)                                     AS patient_count,
    ROUND(AVG(total_claim_cost), 2)                                 AS avg_cost,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (
          ORDER BY total_claim_cost), 2)                            AS p50_cost,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (
          ORDER BY total_claim_cost), 2)                            AS p90_cost,
    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (
          ORDER BY total_claim_cost), 2)                            AS p99_cost,
    ROUND(MAX(total_claim_cost), 2)                                 AS max_cost,
    COUNT(*) FILTER (WHERE cost_quartile = 4)                       AS top_quartile_count
FROM ranked
GROUP BY encounter_year
ORDER BY encounter_year
```

`sql/analytics/care_gap_detection.sql`:
```sql
-- Business question: Which diabetic patients have gone ≥ 12 months without
--                    any encounter (a proxy for a care gap)?
-- SQL technique:     LEFT JOIN anti-join; CURRENT_DATE date arithmetic
-- Scaling note:      At V2, run this as a scheduled job and write results to
--                    a care_gaps table so the API can serve them without a
--                    full-scan query at request time.
--
-- SNOMED-CT: 44054006 = Type 2 diabetes mellitus; 73211009 = Diabetes mellitus

WITH diabetic_patients AS (
    SELECT DISTINCT patient_key
    FROM fact_condition
    WHERE snomed_code IN ('44054006', '73211009')
      AND stop_date_key IS NULL          -- condition still active
),
last_encounter AS (
    SELECT
        fe.patient_key,
        MAX(dd.full_date) AS last_encounter_date
    FROM fact_encounter fe
    JOIN dim_date dd ON dd.date_key = fe.start_date_key
    GROUP BY fe.patient_key
)
SELECT
    COUNT(*)                                                        AS diabetic_patients,
    COUNT(*) FILTER (
        WHERE le.last_encounter_date IS NULL
           OR CURRENT_DATE - le.last_encounter_date > INTERVAL '365 days'
    )                                                               AS patients_with_care_gap,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE le.last_encounter_date IS NULL
               OR CURRENT_DATE - le.last_encounter_date > INTERVAL '365 days'
        ) / NULLIF(COUNT(*), 0),
    2)                                                              AS care_gap_rate_pct
FROM diabetic_patients dp
LEFT JOIN last_encounter le ON le.patient_key = dp.patient_key
```

`sql/analytics/utilization_trends.sql`:
```sql
-- Business question: How have encounter volumes and costs changed year-over-year,
--                    broken down by encounter class?
-- SQL technique:     LAG window for year-over-year delta; PARTITION BY encounter_class
--                    so each class has its own prior-year reference row
-- Scaling note:      At V2, pre-aggregate into utilization_summary; the base
--                    aggregation over 500M rows is the expensive part, not the window.

WITH yearly AS (
    SELECT
        EXTRACT(YEAR FROM dd.full_date)::INTEGER AS encounter_year,
        fe.encounter_class,
        COUNT(*)                                 AS encounter_count,
        ROUND(SUM(fe.total_claim_cost), 2)       AS total_cost
    FROM fact_encounter fe
    JOIN dim_date dd ON dd.date_key = fe.start_date_key
    GROUP BY EXTRACT(YEAR FROM dd.full_date), fe.encounter_class
)
SELECT
    encounter_year,
    encounter_class,
    encounter_count,
    total_cost,
    encounter_count - LAG(encounter_count) OVER w   AS count_delta,
    ROUND(
        100.0 * (encounter_count - LAG(encounter_count) OVER w)
        / NULLIF(LAG(encounter_count) OVER w, 0),
    2)                                               AS count_growth_pct,
    total_cost - LAG(total_cost) OVER w              AS cost_delta,
    ROUND(
        100.0 * (total_cost - LAG(total_cost) OVER w)
        / NULLIF(LAG(total_cost) OVER w, 0),
    2)                                               AS cost_growth_pct
FROM yearly
WINDOW w AS (PARTITION BY encounter_class ORDER BY encounter_year)
ORDER BY encounter_year, encounter_class
```

- [ ] **Step 3: Update src/cms_platform/analytics/queries.py**

```python
"""Execute the five analytical SQL queries against the star schema.

Each function reads its SQL from sql/analytics/, executes against the provided
DuckDB connection, and returns a Polars DataFrame.

TODO(future-perf): cache results with a TTL when the underlying data is static
    (e.g., historical synthea data that won't change between API calls).
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

_SQL_DIR = Path(__file__).parent.parent.parent.parent / "sql" / "analytics"


def _to_polars(result: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Convert a DuckDB result to Polars without requiring pyarrow."""
    rows = result.fetchall()
    desc = result.description
    if not desc:
        return pl.DataFrame()
    cols = [d[0] for d in desc]
    if not rows:
        return pl.DataFrame({col: [] for col in cols})

    def _coerce(v: Any) -> Any:
        return float(v) if isinstance(v, Decimal) else v

    return pl.DataFrame(
        {col: [_coerce(row[i]) for row in rows] for i, col in enumerate(cols)}
    )


def _run(conn: duckdb.DuckDBPyConnection, sql_file: str) -> pl.DataFrame:
    return _to_polars(conn.execute((_SQL_DIR / sql_file).read_text()))


def readmission_30day(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """30-day inpatient readmission rate by year."""
    return _run(conn, "readmission_30day.sql")


def cohort_segmentation(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Chronic-condition cohort counts by year of first encounter."""
    return _run(conn, "cohort_segmentation.sql")


def cost_benchmarking(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Encounter cost distribution (avg, P50, P90, P99) by year."""
    return _run(conn, "cost_benchmarking.sql")


def care_gap_detection(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Diabetic patients without an encounter in the past 12 months."""
    return _run(conn, "care_gap_detection.sql")


def utilization_trends(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Year-over-year encounter volume and cost deltas by encounter class."""
    return _run(conn, "utilization_trends.sql")
```

- [ ] **Step 4: Run analytics tests**

```bash
.venv/bin/pytest tests/test_analytics.py -v
```

Expected: 6 passed

- [ ] **Step 5: Run lint**

```bash
.venv/bin/ruff check src/ tests/
.venv/bin/mypy src/
```

Expected: clean

- [ ] **Step 6: Commit**

```bash
git add sql/analytics/ src/cms_platform/analytics/queries.py tests/test_analytics.py
git commit -m "feat(analytics): 5 Synthea analytics queries — readmission, cohorts, cost, care-gap, trends"
```

---

## Task 6: Risk Scoring

**Files:**
- Modify: `src/cms_platform/scoring/risk_model.py`
- Create: `tests/test_scoring.py`

The new model derives features from the star schema using a SQL query rather than reading pre-computed flags from dim_patient. The training set is all patients in dim_patient; the label is top-quartile by `healthcare_expenses`.

- [ ] **Step 1: Write failing scoring tests**

Create `tests/test_scoring.py`:

```python
from __future__ import annotations

import duckdb
import polars as pl
import pytest

from cms_platform.common.config import Settings
from cms_platform.ingest.load import _ensure_raw_tables, load_synthea_data
from cms_platform.schema.transforms import build_star_schema
from cms_platform.scoring.risk_model import (
    RISK_FEATURES,
    RiskModel,
    _build_training_features,
    predict_risk,
    train_risk_model,
)
from tests.test_ingest import _seed_csvs


@pytest.fixture
def populated_conn(tmp_path: pytest.TempPathFactory, settings: Settings) -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect()
    data_dir = _seed_csvs(tmp_path)
    _ensure_raw_tables(conn)
    load_synthea_data(data_dir, conn)
    build_star_schema(conn, settings)
    return conn


def test_risk_features_list_is_non_empty() -> None:
    assert len(RISK_FEATURES) >= 5


def test_build_training_features_returns_dataframe(populated_conn: duckdb.DuckDBPyConnection) -> None:
    df = _build_training_features(populated_conn)
    assert isinstance(df, pl.DataFrame)
    for col in RISK_FEATURES:
        assert col in df.columns, f"missing feature column: {col}"


def test_train_risk_model_returns_model(populated_conn: duckdb.DuckDBPyConnection, settings: Settings) -> None:
    df = _build_training_features(populated_conn)
    # Need at least 2 patients for both label classes; seed extra rows if needed
    import random
    random.seed(42)
    n = max(20, len(df))
    rows = {col: [random.random() for _ in range(n)] for col in RISK_FEATURES}
    big_df = pl.DataFrame(rows)
    target = pl.Series("label", [i % 2 for i in range(n)])
    model = train_risk_model(big_df, target, settings)
    assert isinstance(model, RiskModel)
    assert model.training_size == n


def test_predict_risk_returns_series(populated_conn: duckdb.DuckDBPyConnection, settings: Settings) -> None:
    import random
    random.seed(0)
    n = 20
    rows = {col: [random.random() for _ in range(n)] for col in RISK_FEATURES}
    df = pl.DataFrame(rows)
    target = pl.Series("label", [i % 2 for i in range(n)])
    model = train_risk_model(df, target, settings)
    scores = predict_risk(model, df)
    assert len(scores) == n
    assert scores.min() >= 0.0  # type: ignore[operator]
    assert scores.max() <= 1.0  # type: ignore[operator]


def test_predict_risk_handles_null_features(settings: Settings) -> None:
    import random
    random.seed(1)
    n = 20
    rows: dict[str, list[object]] = {col: [random.random() for _ in range(n)] for col in RISK_FEATURES}
    rows[RISK_FEATURES[0]] = [None] * n  # type: ignore[assignment]
    df = pl.DataFrame(rows)
    target = pl.Series("label", [i % 2 for i in range(n)])
    model = train_risk_model(df, target, settings)
    scores = predict_risk(model, df)
    assert len(scores) == n
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
.venv/bin/pytest tests/test_scoring.py -v
```

Expected: ImportError (`_build_training_features` does not exist yet)

- [ ] **Step 3: Rewrite src/cms_platform/scoring/risk_model.py**

```python
"""Risk stratification model for Synthea patient data.

Trains a logistic regression pipeline to predict whether a patient will be
in the top cost quartile. Features are derived from the star schema via SQL.

Note: synthetic data caps real predictive signal. These figures demonstrate
the pipeline architecture, not clinical validity.

TODO(future-model): swap LogisticRegression for a gradient-boosted model
    (LightGBM) once the feature set and data volume justify the complexity.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import duckdb
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from cms_platform.common.config import Settings

# Features derived from the star schema (see _build_training_features for SQL).
# Boolean flags use 1/0 integers; continuous values are left as floats.
RISK_FEATURES: list[str] = [
    "age_years",
    "is_male",
    "condition_count",
    "has_diabetes",
    "has_heart_failure",
    "has_hypertension",
    "has_copd_asthma",
    "encounter_count",
    "total_encounter_cost",
    "healthcare_expenses",
]


@dataclass
class RiskModel:
    pipeline: Pipeline
    feature_cols: list[str]
    training_size: int


def _build_training_features(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Query the star schema to build a feature row per patient.

    Returns a Polars DataFrame with one row per patient and RISK_FEATURES columns.
    """
    rows = conn.execute("""
        SELECT
            dp.patient_key,
            DATE_DIFF('year', dp.birthdate, CURRENT_DATE)          AS age_years,
            CASE WHEN dp.gender = 'M' THEN 1 ELSE 0 END            AS is_male,
            COALESCE(cond.condition_count, 0)                       AS condition_count,
            COALESCE(cond.has_diabetes,      0)                     AS has_diabetes,
            COALESCE(cond.has_heart_failure, 0)                     AS has_heart_failure,
            COALESCE(cond.has_hypertension,  0)                     AS has_hypertension,
            COALESCE(cond.has_copd_asthma,   0)                     AS has_copd_asthma,
            COALESCE(enc.encounter_count, 0)                        AS encounter_count,
            COALESCE(enc.total_cost, 0.0)                           AS total_encounter_cost,
            COALESCE(dp.healthcare_expenses, 0.0)                   AS healthcare_expenses
        FROM dim_patient dp
        LEFT JOIN (
            SELECT
                patient_key,
                COUNT(DISTINCT snomed_code)                                             AS condition_count,
                MAX(CASE WHEN snomed_code IN ('44054006','73211009') THEN 1 ELSE 0 END) AS has_diabetes,
                MAX(CASE WHEN snomed_code = '84114007'               THEN 1 ELSE 0 END) AS has_heart_failure,
                MAX(CASE WHEN snomed_code = '59621000'               THEN 1 ELSE 0 END) AS has_hypertension,
                MAX(CASE WHEN snomed_code IN ('13645005','195967001') THEN 1 ELSE 0 END) AS has_copd_asthma
            FROM fact_condition
            GROUP BY patient_key
        ) cond ON cond.patient_key = dp.patient_key
        LEFT JOIN (
            SELECT patient_key,
                   COUNT(*)                   AS encounter_count,
                   SUM(total_claim_cost)       AS total_cost
            FROM fact_encounter
            GROUP BY patient_key
        ) enc ON enc.patient_key = dp.patient_key
    """).fetchall()

    desc = conn.execute("""
        SELECT age_years, is_male, condition_count, has_diabetes,
               has_heart_failure, has_hypertension, has_copd_asthma,
               encounter_count, total_encounter_cost, healthcare_expenses
        FROM dim_patient LIMIT 0
    """).description or []

    if not rows:
        return pl.DataFrame({col: [] for col in RISK_FEATURES})

    from decimal import Decimal

    def _coerce(v: Any) -> float:
        if isinstance(v, Decimal):
            return float(v)
        if v is None:
            return 0.0
        return float(v)

    # rows include patient_key as col 0; skip it
    return pl.DataFrame(
        {col: [_coerce(row[i + 1]) for row in rows] for i, col in enumerate(RISK_FEATURES)}
    )


def train_risk_model(
    features: pl.DataFrame,
    target: pl.Series,
    settings: Settings,
) -> RiskModel:
    """Train a logistic regression risk model.

    features: DataFrame with RISK_FEATURES columns
    target:   binary Series (1 = high-cost, 0 = standard)
    """
    X = features.fill_null(0).to_numpy()
    y = target.to_numpy()
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, random_state=42)),
    ])
    pipeline.fit(X, y)
    return RiskModel(pipeline=pipeline, feature_cols=list(features.columns), training_size=len(X))


def predict_risk(model: RiskModel, features: pl.DataFrame) -> pl.Series:
    """Return a risk score (0.0–1.0) for each row in features."""
    X = features.fill_null(0).to_numpy()
    probs: Any = model.pipeline.predict_proba(X)
    scores = [float(row[1]) for row in probs]
    return pl.Series("risk_score", scores)
```

- [ ] **Step 4: Run scoring tests**

```bash
.venv/bin/pytest tests/test_scoring.py -v
```

Expected: 5 passed

- [ ] **Step 5: Run lint**

```bash
.venv/bin/ruff check src/ tests/
.venv/bin/mypy src/
```

Expected: clean

- [ ] **Step 6: Commit**

```bash
git add src/cms_platform/scoring/risk_model.py tests/test_scoring.py
git commit -m "feat(scoring): Synthea risk features derived from star schema via SQL"
```

---

## Task 7: API Routes

**Files:**
- Modify: `src/cms_platform/api/routes/patient.py` (was `beneficiary.py`)
- Modify: `src/cms_platform/api/routes/benchmarks.py`
- Modify: `src/cms_platform/api/models.py`
- Modify: `src/cms_platform/api/main.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Create `tests/test_api.py`:

```python
from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from cms_platform.api.main import app
from cms_platform.api.deps import get_db_conn
from cms_platform.common.config import Settings, get_settings
from cms_platform.ingest.load import _ensure_raw_tables, load_synthea_data
from cms_platform.schema.transforms import build_star_schema
from tests.test_ingest import _seed_csvs


@pytest.fixture
def client(tmp_path: Path, settings: Settings) -> TestClient:
    conn = duckdb.connect()
    data_dir = _seed_csvs(tmp_path)
    _ensure_raw_tables(conn)
    load_synthea_data(data_dir, conn)
    build_star_schema(conn, settings)

    app.dependency_overrides[get_db_conn] = lambda: conn
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_cohorts_returns_list(client: TestClient) -> None:
    r = client.get("/cohorts")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if data:
        assert "total_patients" in data[0]


def test_benchmarks_returns_list(client: TestClient) -> None:
    r = client.get("/benchmarks/encounters")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_patient_risk_returns_score(client: TestClient) -> None:
    r = client.get("/patients/aaaaaaaa-0001-0001-0001-000000000001/risk")
    assert r.status_code == 200
    body = r.json()
    assert "risk_score" in body
    assert 0.0 <= body["risk_score"] <= 1.0


def test_patient_risk_masks_patient_id(client: TestClient) -> None:
    r = client.get("/patients/aaaaaaaa-0001-0001-0001-000000000001/risk")
    assert r.status_code == 200
    assert r.json()["patient_id"].startswith("****")


def test_patient_risk_phi_read_returns_plain(client: TestClient) -> None:
    r = client.get("/patients/aaaaaaaa-0001-0001-0001-000000000001/risk?phi_read=true")
    assert r.status_code == 200
    assert r.json()["patient_id"] == "aaaaaaaa-0001-0001-0001-000000000001"


def test_patient_care_gaps(client: TestClient) -> None:
    r = client.get("/patients/aaaaaaaa-0001-0001-0001-000000000001/care-gaps")
    assert r.status_code == 200
    body = r.json()
    assert "gaps" in body
    assert "summary" in body


def test_patient_not_found(client: TestClient) -> None:
    r = client.get("/patients/nonexistent-uuid/risk")
    assert r.status_code == 404
```

- [ ] **Step 2: Update src/cms_platform/api/models.py**

```python
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class RiskResponse(BaseModel):
    patient_id: str
    risk_score: float
    model_version: str


class CareGapResponse(BaseModel):
    patient_id: str
    gaps: list[str]
    summary: str
    model_used: str


class CohortRow(BaseModel):
    encounter_year: int | None
    total_patients: int
    diabetes_cohort: int
    heart_failure_cohort: int
    copd_asthma_cohort: int
    hypertension_cohort: int
    avg_condition_count: float | None


class BenchmarkRow(BaseModel):
    encounter_year: int | None
    patient_count: int
    avg_cost: float | None
    p50_cost: float | None
    p90_cost: float | None
    p99_cost: float | None
    max_cost: float | None
    top_quartile_count: int
```

- [ ] **Step 3: Rewrite src/cms_platform/api/routes/patient.py**

```python
"""Patient-level API routes: risk score and care-gap explanation.

Every route calls audit.log_access() before reading any patient data.
Patient IDs are masked in all responses unless phi_read=True is passed.
TODO(future-auth): replace phi_read query param with a JWT PHI_READ scope check.
"""
from __future__ import annotations

import duckdb
import polars as pl
from fastapi import APIRouter, Depends, HTTPException, Query

from cms_platform.api.deps import get_db_conn, get_settings_dep
from cms_platform.api.models import CareGapResponse, RiskResponse
from cms_platform.common.audit import log_access
from cms_platform.common.config import Settings
from cms_platform.common.mask import mask_field
from cms_platform.scoring.explainer import explain_care_gaps
from cms_platform.scoring.risk_model import (
    RISK_FEATURES,
    RiskModel,
    _build_training_features,
    predict_risk,
    train_risk_model,
)

router = APIRouter(prefix="/patients", tags=["patients"])


def _get_patient_features(
    patient_id: str,
    conn: duckdb.DuckDBPyConnection,
) -> pl.DataFrame | None:
    """Return a single-row features DataFrame for the patient, or None if not found."""
    result = conn.execute(
        "SELECT patient_key FROM dim_patient WHERE patient_id = ?", [patient_id]
    ).fetchone()
    if result is None:
        return None
    patient_key = result[0]

    row = conn.execute(f"""
        SELECT
            DATE_DIFF('year', dp.birthdate, CURRENT_DATE)          AS age_years,
            CASE WHEN dp.gender = 'M' THEN 1 ELSE 0 END            AS is_male,
            COALESCE(cond.condition_count, 0)                       AS condition_count,
            COALESCE(cond.has_diabetes,      0)                     AS has_diabetes,
            COALESCE(cond.has_heart_failure, 0)                     AS has_heart_failure,
            COALESCE(cond.has_hypertension,  0)                     AS has_hypertension,
            COALESCE(cond.has_copd_asthma,   0)                     AS has_copd_asthma,
            COALESCE(enc.encounter_count, 0)                        AS encounter_count,
            COALESCE(enc.total_cost, 0.0)                           AS total_encounter_cost,
            COALESCE(dp.healthcare_expenses, 0.0)                   AS healthcare_expenses
        FROM dim_patient dp
        LEFT JOIN (
            SELECT patient_key,
                   COUNT(DISTINCT snomed_code) AS condition_count,
                   MAX(CASE WHEN snomed_code IN ('44054006','73211009') THEN 1 ELSE 0 END) AS has_diabetes,
                   MAX(CASE WHEN snomed_code = '84114007' THEN 1 ELSE 0 END) AS has_heart_failure,
                   MAX(CASE WHEN snomed_code = '59621000' THEN 1 ELSE 0 END) AS has_hypertension,
                   MAX(CASE WHEN snomed_code IN ('13645005','195967001') THEN 1 ELSE 0 END) AS has_copd_asthma
            FROM fact_condition GROUP BY patient_key
        ) cond ON cond.patient_key = dp.patient_key
        LEFT JOIN (
            SELECT patient_key, COUNT(*) AS encounter_count,
                   SUM(total_claim_cost) AS total_cost
            FROM fact_encounter GROUP BY patient_key
        ) enc ON enc.patient_key = dp.patient_key
        WHERE dp.patient_key = {patient_key}
    """).fetchone()

    if row is None:
        return None
    return pl.DataFrame({col: [float(v) if v is not None else 0.0]
                         for col, v in zip(RISK_FEATURES, row, strict=False)})


def _train_model(conn: duckdb.DuckDBPyConnection, settings: Settings) -> RiskModel:
    features = _build_training_features(conn)
    if features.is_empty():
        raise HTTPException(status_code=503, detail="No patient data loaded")
    costs = features["healthcare_expenses"].to_list()
    sorted_costs = sorted(costs)
    threshold = sorted_costs[max(0, int(len(sorted_costs) * 0.75) - 1)]
    target = pl.Series("label", [1 if c >= threshold else 0 for c in costs])
    return train_risk_model(features, target, settings)


@router.get("/{patient_id}/risk", response_model=RiskResponse)
def get_patient_risk(
    patient_id: str,
    phi_read: bool = Query(default=False),
    conn: duckdb.DuckDBPyConnection = Depends(get_db_conn),  # noqa: B008
    settings: Settings = Depends(get_settings_dep),  # noqa: B008
) -> RiskResponse:
    log_access(patient_id, "risk_score_read", "api")
    features = _get_patient_features(patient_id, conn)
    if features is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    model = _train_model(conn, settings)
    score = predict_risk(model, features)[0]
    masked_id = mask_field("patient_id", patient_id, phi_read=phi_read) or patient_id
    return RiskResponse(patient_id=masked_id, risk_score=float(score), model_version="v0-logistic")


@router.get("/{patient_id}/care-gaps", response_model=CareGapResponse)
def get_patient_care_gaps(
    patient_id: str,
    phi_read: bool = Query(default=False),
    conn: duckdb.DuckDBPyConnection = Depends(get_db_conn),  # noqa: B008
    settings: Settings = Depends(get_settings_dep),  # noqa: B008
) -> CareGapResponse:
    log_access(patient_id, "care_gaps_read", "api")
    exists = conn.execute(
        "SELECT 1 FROM dim_patient WHERE patient_id = ?", [patient_id]
    ).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Identify active conditions with no recent encounter as care gaps
    gaps_rows = conn.execute("""
        SELECT fc.description
        FROM fact_condition fc
        JOIN dim_patient dp ON dp.patient_key = fc.patient_key
        WHERE dp.patient_id = ?
          AND fc.stop_date_key IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM fact_encounter fe
              JOIN dim_date dd ON dd.date_key = fe.start_date_key
              WHERE fe.patient_key = dp.patient_key
                AND CURRENT_DATE - dd.full_date <= INTERVAL '365 days'
          )
    """, [patient_id]).fetchall()

    gaps = [r[0] for r in gaps_rows if r[0]]
    explanation = explain_care_gaps(patient_id, gaps, settings)
    masked_id = mask_field("patient_id", patient_id, phi_read=phi_read) or patient_id
    return CareGapResponse(
        patient_id=masked_id,
        gaps=explanation.gaps,
        summary=explanation.summary,
        model_used=explanation.model_used,
    )
```

- [ ] **Step 4: Update src/cms_platform/api/routes/benchmarks.py**

```python
from __future__ import annotations

from typing import Any

import duckdb
from fastapi import APIRouter, Depends

from cms_platform.analytics.queries import cost_benchmarking
from cms_platform.api.deps import get_db_conn

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.get("/encounters")
def get_encounter_benchmarks(
    conn: duckdb.DuckDBPyConnection = Depends(get_db_conn),  # noqa: B008
) -> list[dict[str, Any]]:
    """Encounter cost distribution benchmarks by year. Aggregate data — no PHI."""
    return cost_benchmarking(conn).to_dicts()
```

- [ ] **Step 5: Update src/cms_platform/api/main.py**

```python
from __future__ import annotations

from fastapi import FastAPI

from cms_platform.api.routes import benchmarks, cohorts, patient
from cms_platform.common.config import get_settings
from cms_platform.common.logging import configure_logging

app = FastAPI(title="Synthea Claims Platform", version="0.1.0")

app.include_router(cohorts.router)
app.include_router(patient.router)
app.include_router(benchmarks.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    settings = get_settings()
    configure_logging(settings.log_level)
    uvicorn.run("cms_platform.api.main:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 6: Run API tests**

```bash
.venv/bin/pytest tests/test_api.py -v
```

Expected: 8 passed

- [ ] **Step 7: Run full test suite**

```bash
.venv/bin/pytest tests/ -q
```

Expected: all pass, ruff + mypy clean

- [ ] **Step 8: Commit**

```bash
git add src/cms_platform/api/ tests/test_api.py
git commit -m "feat(api): patient routes — /patients/{id}/risk and /patients/{id}/care-gaps"
```

---

## Task 8: Documentation + Notebook

**Files:**
- Rewrite: `README.md`
- Update: `ARCHITECTURE.md` (remove CMS references, add Synthea/FHIR)
- Create: `COMPLIANCE.md`
- Create: `notebooks/story.ipynb`

- [ ] **Step 1: Rewrite README.md**

Replace the full content of `README.md` with:

```markdown
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
```

- [ ] **Step 2: Update ARCHITECTURE.md — replace CMS-specific references**

Find and update these sections in `ARCHITECTURE.md`:
1. In "Design Philosophy", replace "CMS DE-SynPUF" references with "Synthea CSV"
2. In "V0→V1→V2 Migration Path — Ingestion", update the V2 path: "Replace `ingest/download.py` Synthea CSV fetch with a Blue Button 2.0 FHIR R4 consumer. Same raw table contract — different producer."
3. In "Kafka Streaming Design (V2)" — add a note: "Topic schemas use FHIR R4 resource types as the event envelope (`Patient`, `Encounter`, `Condition`) so the V2 Kafka pipeline is compatible with real Blue Button 2.0 data without re-mapping."
4. Remove any remaining "DE-SynPUF", "ICD-9", "DESYNPUF_ID", "CLM_ID" references.

- [ ] **Step 3: Create COMPLIANCE.md**

```markdown
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
```

- [ ] **Step 4: Create notebooks/story.ipynb**

Write a valid Jupyter notebook JSON (`nbformat` 4) with these cells:

**Cell 1 (markdown):** Title + "What is Synthea?" explanation with link

**Cell 2 (code):** Setup — `sys.path.insert`, import duckdb/polars, print versions

**Cell 3 (markdown):** "Section 1 — Ingest" — explain the 5 CSV files and the raw-table approach

**Cell 4 (code):**
```python
from cms_platform.ingest.load import _TABLES
for table, (filename, cols) in _TABLES.items():
    print(f"{filename:30s} → {table}  ({len(cols)} columns)")
```

**Cell 5 (markdown):** "Section 2 — Star Schema" — explain dims + facts, mention SNOMED-CT

**Cell 6 (code):** Build schema on in-memory DuckDB with fixture data and print row counts (use the same fixture helpers from tests/test_ingest.py — import `_seed_csvs`; call `_ensure_raw_tables`, `load_synthea_data`, `build_star_schema`)

**Cell 7 (markdown):** "Section 3 — Analytics" — explain the 5 queries

**Cell 8 (code):** Run all 5 queries and print results

**Cell 9 (markdown):** "Section 4 — Risk Stratification" + honest-metrics caveat

**Cell 10 (code):** Generate synthetic features (random.seed(42)), train model, print scores + caveat

**Cell 11 (markdown):** "Section 5 — Care-Gap Explanation (Ollama)"

**Cell 12 (code):** Call `explain_care_gaps` with stub gaps; print result

**Cell 13 (markdown):** "Section 6 — V0 → V2" — swap-point table + FHIR migration note

**Cell 14 (markdown):** Closing — repo map

Notebook JSON format (nbformat 4.5):
```json
{
  "nbformat": 4, "nbformat_minor": 5,
  "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
               "language_info": {"name": "python", "version": "3.14.0"}},
  "cells": [...]
}
```
Each cell id must be a unique 8-char hex string.

After writing: validate JSON and run all code cells as a script to confirm no errors.

- [ ] **Step 5: Run final full test suite**

```bash
.venv/bin/ruff check src/ tests/
.venv/bin/mypy src/
.venv/bin/pytest tests/ -q
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add README.md ARCHITECTURE.md COMPLIANCE.md notebooks/story.ipynb
git commit -m "docs: rewrite README/ARCHITECTURE/COMPLIANCE for Synthea; add narrative notebook"
```

---

## Self-Review

**Spec coverage check:**

1. ✅ Delete all CMS DE-SynPUF artifacts — Task 1
2. ✅ Synthea CSV download (pre-generated, no Java) — Task 3 `download.py`
3. ✅ Option A: all-VARCHAR raw tables, SNOMED-CT, general terminology — Tasks 3-4
4. ✅ `make ingest` workflow preserved — `load.py` `main()` entry point
5. ✅ Star schema with dim_patient, dim_provider, dim_condition_code, dim_date — Task 4
6. ✅ 5 analytics queries rewritten for new schema — Task 5
7. ✅ Risk features derived from schema via SQL — Task 6
8. ✅ API routes renamed (`/patients/` prefix) — Task 7
9. ✅ PHI masking updated (patient_id, birthdate, deathdate) — Task 2
10. ✅ TODO comments for future FHIR/Blue Button 2.0 integration — Tasks 2, 3, 4, 7
11. ✅ Educational README with external links — Task 8
12. ✅ COMPLIANCE.md rewritten — Task 8
13. ✅ Narrative notebook — Task 8

**No placeholders found** — every step has complete code.

**Type consistency** — `patient_id` used consistently throughout (not `beneficiary_id`). `encounter_year` used in all analytics query column names. `RISK_FEATURES` list is defined once in `risk_model.py` and imported everywhere else.
