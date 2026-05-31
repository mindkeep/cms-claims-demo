import polars as pl

from cms_platform.common.config import Settings


def _make_features(n: int = 10) -> pl.DataFrame:
    """Synthetic feature DataFrame with all RISK_FEATURES columns."""
    import random
    random.seed(42)
    from cms_platform.scoring.risk_model import RISK_FEATURES
    bool_cols = RISK_FEATURES[:11]
    dec_cols = RISK_FEATURES[11:]
    data: dict[str, list[object]] = {
        **{c: [float(random.randint(0, 1)) for _ in range(n)] for c in bool_cols},
        **{c: [random.uniform(0, 5000) for _ in range(n)] for c in dec_cols},
    }
    return pl.DataFrame(data)


def _make_target(n: int = 10) -> pl.Series:
    import random
    random.seed(99)
    return pl.Series("high_cost", [random.randint(0, 1) for _ in range(n)])


def test_train_risk_model_returns_risk_model() -> None:
    from cms_platform.scoring.risk_model import RiskModel, train_risk_model
    features = _make_features(20)
    target = _make_target(20)
    model = train_risk_model(features, target, Settings())
    assert isinstance(model, RiskModel)
    assert model.training_size == 20
    assert model.feature_cols is not None


def test_predict_risk_returns_series_in_range() -> None:
    from cms_platform.scoring.risk_model import predict_risk, train_risk_model
    features = _make_features(20)
    target = _make_target(20)
    model = train_risk_model(features, target, Settings())
    scores = predict_risk(model, features)
    assert isinstance(scores, pl.Series)
    assert len(scores) == 20
    assert scores.min() >= 0.0  # type: ignore[operator]
    assert scores.max() <= 1.0  # type: ignore[operator]


def test_predict_risk_handles_null_features() -> None:
    from cms_platform.scoring.risk_model import predict_risk, train_risk_model
    features = _make_features(10)
    target = _make_target(10)
    model = train_risk_model(features, target, Settings())
    # Inject nulls — fill_null(0) should handle them
    with_nulls = features.with_columns(pl.lit(None).cast(pl.Float64).alias("medreimb_ip"))
    scores = predict_risk(model, with_nulls)
    assert len(scores) == 10


def test_explain_care_gaps_stub_fires_unreachable() -> None:
    from cms_platform.scoring.explainer import explain_care_gaps
    s = Settings(ollama_base_url="http://localhost:19999/v1")
    result = explain_care_gaps("BENE_TEST", ["Annual wellness visit"], s)
    assert result.model_used == "stub"
    assert result.beneficiary_id == "BENE_TEST"


def test_explain_care_gaps_stub_empty_gaps() -> None:
    from cms_platform.scoring.explainer import explain_care_gaps
    s = Settings(ollama_base_url="http://localhost:19999/v1")
    result = explain_care_gaps("BENE_TEST", [], s)
    assert result.model_used == "stub"
    assert "no" in result.summary.lower()
