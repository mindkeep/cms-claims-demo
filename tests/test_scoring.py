from __future__ import annotations

import duckdb
import polars as pl
import pytest

from cms_platform.common.config import Settings
from cms_platform.ingest.load import _ensure_raw_tables, load_synthea_data
from cms_platform.schema.transforms import build_star_schema
from cms_platform.scoring.risk_model import (
    RISK_FEATURES,
    RiskModel,
    _build_training_features,
    predict_risk,
    train_risk_model,
)
from tests.test_ingest import _seed_csvs


@pytest.fixture
def populated_conn(
    tmp_path: pytest.TempPathFactory, settings: Settings
) -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect()
    data_dir = _seed_csvs(tmp_path)
    _ensure_raw_tables(conn)
    load_synthea_data(data_dir, conn)
    build_star_schema(conn, settings)
    return conn


def test_risk_features_list_is_non_empty() -> None:
    assert len(RISK_FEATURES) >= 5


def test_build_training_features_returns_dataframe(
    populated_conn: duckdb.DuckDBPyConnection,
) -> None:
    df = _build_training_features(populated_conn)
    assert isinstance(df, pl.DataFrame)
    for col in RISK_FEATURES:
        assert col in df.columns, f"missing feature column: {col}"


def test_train_risk_model_returns_model(
    populated_conn: duckdb.DuckDBPyConnection, settings: Settings
) -> None:
    df = _build_training_features(populated_conn)
    # Need at least 2 patients for both label classes; seed extra rows if needed
    import random
    random.seed(42)
    n = max(20, len(df))
    rows = {col: [random.random() for _ in range(n)] for col in RISK_FEATURES}
    big_df = pl.DataFrame(rows)
    target = pl.Series("label", [i % 2 for i in range(n)])
    model = train_risk_model(big_df, target, settings)
    assert isinstance(model, RiskModel)
    assert model.training_size == n


def test_predict_risk_returns_series(
    populated_conn: duckdb.DuckDBPyConnection, settings: Settings
) -> None:
    import random
    random.seed(0)
    n = 20
    rows = {col: [random.random() for _ in range(n)] for col in RISK_FEATURES}
    df = pl.DataFrame(rows)
    target = pl.Series("label", [i % 2 for i in range(n)])
    model = train_risk_model(df, target, settings)
    scores = predict_risk(model, df)
    assert len(scores) == n
    assert scores.min() >= 0.0  # type: ignore[operator]
    assert scores.max() <= 1.0  # type: ignore[operator]


def test_predict_risk_handles_null_features(settings: Settings) -> None:
    import random
    random.seed(1)
    n = 20
    rows: dict[str, list[object]] = {
        col: [random.random() for _ in range(n)] for col in RISK_FEATURES
    }
    rows[RISK_FEATURES[0]] = [None] * n  # type: ignore[assignment]
    df = pl.DataFrame(rows)
    target = pl.Series("label", [i % 2 for i in range(n)])
    model = train_risk_model(df, target, settings)
    scores = predict_risk(model, df)
    assert len(scores) == n
