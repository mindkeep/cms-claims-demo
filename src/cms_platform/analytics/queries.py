from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

_SQL_DIR = Path(__file__).parent.parent.parent.parent / "sql" / "analytics"


def _to_polars(result: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Convert a DuckDB result to a Polars DataFrame without requiring pyarrow."""
    rows = result.fetchall()
    desc = result.description
    if not desc:
        return pl.DataFrame()
    cols = [d[0] for d in desc]
    if not rows:
        return pl.DataFrame({col: [] for col in cols})

    def _coerce(v: Any) -> Any:
        if isinstance(v, Decimal):
            return float(v)
        return v

    data = {col: [_coerce(row[i]) for row in rows] for i, col in enumerate(cols)}
    return pl.DataFrame(data)


def _run(conn: duckdb.DuckDBPyConnection, sql_file: str) -> pl.DataFrame:
    sql = (_SQL_DIR / sql_file).read_text()
    return _to_polars(conn.execute(sql))


def readmission_30day(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """30-day readmission rate by year.

    SQL technique: LAG window function + self-join date range predicate.
    """
    return _run(conn, "readmission_30day.sql")


def cohort_segmentation(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Chronic-condition cohort sizes and comorbidity burden by year.

    SQL technique: CASE/FILTER aggregation, comorbidity count.
    """
    return _run(conn, "cohort_segmentation.sql")


def cost_benchmarking(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Per-beneficiary cost distribution with percentiles and quartile ranking.

    SQL technique: PERCENTILE_CONT, NTILE, RANK window functions.
    """
    return _run(conn, "cost_benchmarking.sql")


def care_gap_detection(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Diabetic beneficiaries with no carrier claim (care gap) by year.

    SQL technique: LEFT JOIN anti-join pattern.
    """
    return _run(conn, "care_gap_detection.sql")


def utilization_trends(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Year-over-year claim volume and cost trends with LAG-based deltas.

    SQL technique: LAG window function over year partitions.
    """
    return _run(conn, "utilization_trends.sql")
