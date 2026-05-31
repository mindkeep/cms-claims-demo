from __future__ import annotations

from typing import Any

import duckdb
from fastapi import APIRouter, Depends

from cms_platform.analytics.queries import cohort_segmentation
from cms_platform.api.deps import get_db_conn

router = APIRouter(prefix="/cohorts", tags=["cohorts"])


@router.get("")
def get_cohorts(
    conn: duckdb.DuckDBPyConnection = Depends(get_db_conn),  # noqa: B008
) -> list[dict[str, Any]]:
    """Chronic-condition cohort sizes by year. Aggregate data — no PHI."""
    df = cohort_segmentation(conn)
    return df.to_dicts()
