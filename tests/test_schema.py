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


def test_build_star_schema_is_idempotent(
    tmp_path: pytest.TempPathFactory, settings: Settings
) -> None:
    conn = duckdb.connect()
    data_dir = _seed_csvs(tmp_path)
    _ensure_raw_tables(conn)
    load_synthea_data(data_dir, conn)
    build_star_schema(conn, settings)
    build_star_schema(conn, settings)  # second call must not raise or duplicate rows
    n = conn.execute("SELECT COUNT(*) FROM fact_encounter").fetchone()[0]
    assert n == 1
