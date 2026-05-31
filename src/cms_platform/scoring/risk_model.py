from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from cms_platform.common.config import Settings

# Feature columns extracted from dim_beneficiary for risk stratification
RISK_FEATURES: list[str] = [
    "sp_alzheimer", "sp_chf", "sp_chrnkidn", "sp_cncr", "sp_copd",
    "sp_depressn", "sp_diabetes", "sp_ischmcht", "sp_osteoprs", "sp_ra_oa",
    "sp_strketia", "medreimb_ip", "medreimb_op", "medreimb_car",
]


@dataclass
class RiskModel:
    pipeline: Pipeline
    feature_cols: list[str]
    training_size: int


def train_risk_model(
    features: pl.DataFrame,
    target: pl.Series,
    settings: Settings,
) -> RiskModel:
    """Train a risk-stratification model on prior-year features.

    Predicts next-year high-cost status (top quartile by total spend).
    Uses logistic regression for interpretability — LightGBM can be swapped in
    by replacing the estimator in the pipeline.

    Note: synthetic data caps real predictive signal. These figures demonstrate
    the pipeline, not clinical validity.
    """
    X = features.select(RISK_FEATURES).fill_null(0).to_numpy()
    y = target.to_numpy()

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=200, random_state=42)),
    ])
    pipe.fit(X, y)

    return RiskModel(pipeline=pipe, feature_cols=RISK_FEATURES, training_size=len(y))


def predict_risk(model: RiskModel, features: pl.DataFrame) -> pl.Series:
    """Score beneficiaries; returns float risk scores in [0.0, 1.0].

    Note: synthetic data caps real predictive signal. These figures demonstrate
    the pipeline, not clinical validity.
    """
    X = features.select(model.feature_cols).fill_null(0).to_numpy()
    probs: Any = model.pipeline.predict_proba(X)
    scores: list[float] = [float(p[1]) for p in probs]
    return pl.Series("risk_score", scores)
