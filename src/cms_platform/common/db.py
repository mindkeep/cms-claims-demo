from pathlib import Path

import duckdb

from cms_platform.common.config import Settings


def get_connection(settings: Settings) -> duckdb.DuckDBPyConnection:
    # V2 swap point: replace with Postgres via psycopg2 / asyncpg when migrating off DuckDB
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path))
