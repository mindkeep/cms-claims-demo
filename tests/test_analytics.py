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
def analytics_conn(
    tmp_path: pytest.TempPathFactory, settings: Settings
) -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect()
    data_dir = _seed_csvs(tmp_path)
    _ensure_raw_tables(conn)
    load_synthea_data(data_dir, conn)
    build_star_schema(conn, settings)
    return conn


def test_readmission_30day_returns_dataframe(analytics_conn: duckdb.DuckDBPyConnection) -> None:
    df = readmission_30day(analytics_conn)
    assert isinstance(df, pl.DataFrame)
    assert set(df.columns) >= {
        "encounter_year",
        "total_admissions",
        "readmissions",
        "readmission_rate_pct",
    }


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
