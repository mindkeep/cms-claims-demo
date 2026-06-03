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
    "ID",
    "BIRTHDATE",
    "DEATHDATE",
    "SSN",
    "DRIVERS",
    "PASSPORT",
    "PREFIX",
    "FIRST",
    "LAST",
    "SUFFIX",
    "MAIDEN",
    "MARITAL",
    "RACE",
    "ETHNICITY",
    "GENDER",
    "BIRTHPLACE",
    "ADDRESS",
    "CITY",
    "STATE",
    "COUNTY",
    "FIPS",
    "ZIP",
    "LAT",
    "LON",
    "HEALTHCARE_EXPENSES",
    "HEALTHCARE_COVERAGE",
    "INCOME",
]

_ENCOUNTER_COLS: list[str] = [
    "Id",
    "START",
    "STOP",
    "PATIENT",
    "ORGANIZATION",
    "PROVIDER",
    "PAYER",
    "ENCOUNTERCLASS",
    "CODE",
    "DESCRIPTION",
    "BASE_ENCOUNTER_COST",
    "TOTAL_CLAIM_COST",
    "PAYER_COVERAGE",
    "REASONCODE",
    "REASONDESCRIPTION",
]

_CONDITION_COLS: list[str] = [
    "START",
    "STOP",
    "PATIENT",
    "ENCOUNTER",
    "CODE",
    "DESCRIPTION",
]

_MEDICATION_COLS: list[str] = [
    "START",
    "STOP",
    "PATIENT",
    "PAYER",
    "ENCOUNTER",
    "CODE",
    "DESCRIPTION",
    "BASE_COST",
    "PAYER_COVERAGE",
    "DISPENSES",
    "TOTALCOST",
    "REASONCODE",
    "REASONDESCRIPTION",
]

_PROVIDER_COLS: list[str] = [
    "Id",
    "ORGANIZATION",
    "NAME",
    "GENDER",
    "SPECIALITY",
    "ADDRESS",
    "CITY",
    "STATE",
    "ZIP",
    "LAT",
    "LON",
    "ENCOUNTERS",
    "PROCEDURES",
]

_TABLES: dict[str, tuple[str, list[str]]] = {
    "raw_patients": ("patients.csv", _PATIENT_COLS),
    "raw_encounters": ("encounters.csv", _ENCOUNTER_COLS),
    "raw_conditions": ("conditions.csv", _CONDITION_COLS),
    "raw_medications": ("medications.csv", _MEDICATION_COLS),
    "raw_providers": ("providers.csv", _PROVIDER_COLS),
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
    safe_path = str(csv_path).replace("'", "''")
    conn.execute(f"""
        INSERT INTO {table} ({col_list}, _source_file)
        SELECT {col_list}, '{source}'
        FROM read_csv(
            '{safe_path}',
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
