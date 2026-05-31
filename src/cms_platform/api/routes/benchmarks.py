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
