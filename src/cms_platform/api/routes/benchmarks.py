from __future__ import annotations

from typing import Any

import duckdb
from fastapi import APIRouter, Depends

from cms_platform.analytics.queries import cost_benchmarking
from cms_platform.api.deps import get_db_conn

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.get("/providers")
def get_provider_benchmarks(
    conn: duckdb.DuckDBPyConnection = Depends(get_db_conn),  # noqa: B008
) -> list[dict[str, Any]]:
    """Cost distribution benchmarks across years. Aggregate data — no PHI."""
    df = cost_benchmarking(conn)
    return df.to_dicts()
