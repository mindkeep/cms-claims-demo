from typing import Any

import polars as pl

from cms_platform.common.config import Settings


def train_risk_model(
    features: pl.DataFrame,
    target: pl.Series,
    settings: Settings,
) -> Any:
    """Train a risk-stratification model predicting next-year high-cost beneficiaries.

    Uses logistic regression or LightGBM over prior-year features: chronic flags,
    prior cost, claim counts. Interpretability over raw accuracy — data is synthetic.
    Implemented in WP4.
    """
    raise NotImplementedError("WP4")


def predict_risk(model: Any, features: pl.DataFrame) -> pl.Series:
    """Score a cohort; returns float risk scores in [0.0, 1.0].

    Implemented in WP4.
    """
    raise NotImplementedError("WP4")
