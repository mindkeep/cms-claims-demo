from __future__ import annotations

from collections.abc import Generator

import duckdb
from fastapi import Depends

from cms_platform.common.config import Settings, get_settings
from cms_platform.common.db import get_connection


def get_settings_dep() -> Settings:
    return get_settings()


def get_db_conn(
    settings: Settings = Depends(get_settings_dep),  # noqa: B008
) -> Generator[duckdb.DuckDBPyConnection]:
    conn = get_connection(settings)
    try:
        yield conn
    finally:
        conn.close()
