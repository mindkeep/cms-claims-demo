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

    return pl.DataFrame({col: [_coerce(row[i]) for row in rows] for i, col in enumerate(cols)})


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
