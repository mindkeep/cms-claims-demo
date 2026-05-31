from __future__ import annotations

from pathlib import Path

import duckdb

from cms_platform.common.config import Settings
from cms_platform.ingest.load import (
    _ensure_raw_tables,
    load_synthea_data,
)

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
