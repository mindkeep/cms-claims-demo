"""Risk stratification model for Synthea patient data.

Trains a logistic regression pipeline to predict whether a patient will be
in the top cost quartile. Features are derived from the star schema via SQL.

Note: synthetic data caps real predictive signal. These figures demonstrate
the pipeline architecture, not clinical validity.

TODO(future-model): swap LogisticRegression for a gradient-boosted model
    (LightGBM) once the feature set and data volume justify the complexity.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import duckdb
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from cms_platform.common.config import Settings

# Features derived from the star schema (see _build_training_features for SQL).
# Boolean flags use 1/0 integers; continuous values are left as floats.
RISK_FEATURES: list[str] = [
    "age_years",
    "is_male",
    "condition_count",
    "has_diabetes",
    "has_heart_failure",
    "has_hypertension",
    "has_copd_asthma",
    "encounter_count",
    "total_encounter_cost",
    "healthcare_expenses",
]


@dataclass
class RiskModel:
    pipeline: Pipeline
    feature_cols: list[str]
    training_size: int


def _build_training_features(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Query the star schema to build a feature row per patient.

    Returns a Polars DataFrame with one row per patient and RISK_FEATURES columns.
    """
    rows = conn.execute("""
        SELECT
            dp.patient_key,
            DATE_DIFF('year', dp.birthdate, CURRENT_DATE)          AS age_years,
            CASE WHEN dp.gender = 'M' THEN 1 ELSE 0 END            AS is_male,
            COALESCE(cond.condition_count, 0)                       AS condition_count,
            COALESCE(cond.has_diabetes,      0)                     AS has_diabetes,
            COALESCE(cond.has_heart_failure, 0)                     AS has_heart_failure,
            COALESCE(cond.has_hypertension,  0)                     AS has_hypertension,
            COALESCE(cond.has_copd_asthma,   0)                     AS has_copd_asthma,
            COALESCE(enc.encounter_count, 0)                        AS encounter_count,
            COALESCE(enc.total_cost, 0.0)                           AS total_encounter_cost,
            COALESCE(dp.healthcare_expenses, 0.0)                   AS healthcare_expenses
        FROM dim_patient dp
        LEFT JOIN (
            SELECT
                patient_key,
                COUNT(DISTINCT snomed_code) AS condition_count,
                MAX(CASE WHEN snomed_code IN ('44054006','73211009')
                    THEN 1 ELSE 0 END) AS has_diabetes,
                MAX(CASE WHEN snomed_code = '84114007'
                    THEN 1 ELSE 0 END) AS has_heart_failure,
                MAX(CASE WHEN snomed_code = '59621000'
                    THEN 1 ELSE 0 END) AS has_hypertension,
                MAX(CASE WHEN snomed_code IN ('13645005','195967001')
                    THEN 1 ELSE 0 END) AS has_copd_asthma
            FROM fact_condition
            GROUP BY patient_key
        ) cond ON cond.patient_key = dp.patient_key
        LEFT JOIN (
            SELECT patient_key,
                   COUNT(*)                   AS encounter_count,
                   SUM(total_claim_cost)       AS total_cost
            FROM fact_encounter
            GROUP BY patient_key
        ) enc ON enc.patient_key = dp.patient_key
    """).fetchall()

    if not rows:
        return pl.DataFrame({col: [] for col in RISK_FEATURES})

    from decimal import Decimal

    def _coerce(v: Any) -> float:
        if isinstance(v, Decimal):
            return float(v)
        if v is None:
            return 0.0
        return float(v)

    # rows include patient_key as col 0; skip it
    return pl.DataFrame(
        {col: [_coerce(row[i + 1]) for row in rows] for i, col in enumerate(RISK_FEATURES)}
    )


def train_risk_model(
    features: pl.DataFrame,
    target: pl.Series,
    settings: Settings,
) -> RiskModel:
    """Train a logistic regression risk model.

    features: DataFrame with RISK_FEATURES columns
    target:   binary Series (1 = high-cost, 0 = standard)
    """
    X = features.fill_null(0).to_numpy()
    y = target.to_numpy()
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, random_state=42)),
    ])
    pipeline.fit(X, y)
    return RiskModel(pipeline=pipeline, feature_cols=list(features.columns), training_size=len(X))


def predict_risk(model: RiskModel, features: pl.DataFrame) -> pl.Series:
    """Return a risk score (0.0–1.0) for each row in features."""
    X = features.fill_null(0).to_numpy()
    probs: Any = model.pipeline.predict_proba(X)
    scores = [float(row[1]) for row in probs]
    return pl.Series("risk_score", scores)
