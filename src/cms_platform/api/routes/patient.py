"""Patient-level API routes: risk score and care-gap explanation.

Every route calls audit.log_access() before reading any patient data.
Patient IDs are masked in all responses unless phi_read=True is passed.
TODO(future-auth): replace phi_read query param with a JWT PHI_READ scope check.
"""

from __future__ import annotations

import duckdb
import polars as pl
from fastapi import APIRouter, Depends, HTTPException, Query

from cms_platform.api.deps import get_db_conn, get_settings_dep
from cms_platform.api.models import CareGapResponse, RiskResponse
from cms_platform.common.audit import log_access
from cms_platform.common.config import Settings
from cms_platform.common.mask import mask_field
from cms_platform.scoring.explainer import explain_care_gaps
from cms_platform.scoring.risk_model import (
    RISK_FEATURES,
    RiskModel,
    _build_training_features,
    predict_risk,
    train_risk_model,
)

router = APIRouter(prefix="/patients", tags=["patients"])


def _get_patient_features(
    patient_id: str,
    conn: duckdb.DuckDBPyConnection,
) -> pl.DataFrame | None:
    """Return a single-row features DataFrame for the patient, or None if not found."""
    result = conn.execute(
        "SELECT patient_key FROM dim_patient WHERE patient_id = ?", [patient_id]
    ).fetchone()
    if result is None:
        return None
    patient_key = result[0]

    row = conn.execute(f"""
        SELECT
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
            SELECT patient_key,
                   COUNT(DISTINCT snomed_code) AS condition_count,
                   MAX(CASE WHEN snomed_code IN ('44054006','73211009')
                       THEN 1 ELSE 0 END) AS has_diabetes,
                   MAX(CASE WHEN snomed_code = '84114007'
                       THEN 1 ELSE 0 END) AS has_heart_failure,
                   MAX(CASE WHEN snomed_code = '59621000'
                       THEN 1 ELSE 0 END) AS has_hypertension,
                   MAX(CASE WHEN snomed_code IN ('13645005','195967001')
                       THEN 1 ELSE 0 END) AS has_copd_asthma
            FROM fact_condition GROUP BY patient_key
        ) cond ON cond.patient_key = dp.patient_key
        LEFT JOIN (
            SELECT patient_key, COUNT(*) AS encounter_count,
                   SUM(total_claim_cost) AS total_cost
            FROM fact_encounter GROUP BY patient_key
        ) enc ON enc.patient_key = dp.patient_key
        WHERE dp.patient_key = {patient_key}
    """).fetchone()

    if row is None:
        return None
    return pl.DataFrame(
        {
            col: [float(v) if v is not None else 0.0]
            for col, v in zip(RISK_FEATURES, row, strict=False)
        }
    )


def _train_model(conn: duckdb.DuckDBPyConnection, settings: Settings) -> RiskModel:
    features = _build_training_features(conn)
    if features.is_empty():
        raise HTTPException(status_code=503, detail="No patient data loaded")
    costs = features["healthcare_expenses"].to_list()
    n = len(costs)
    # Rank-based label: top 25% by cost get label=1.
    # Using rank rather than a fixed threshold avoids degenerate single-class
    # targets when all patients have identical costs (common in tiny test DBs).
    sorted_indices = sorted(range(n), key=lambda i: costs[i], reverse=True)
    top_n = max(1, int(n * 0.25))
    high_cost_set = set(sorted_indices[:top_n])
    labels = [1 if i in high_cost_set else 0 for i in range(n)]
    # If still single-class (n=1), force both classes to allow model fit
    if len(set(labels)) < 2:
        labels[sorted_indices[0]] = 1
        if n > 1:
            labels[sorted_indices[-1]] = 0
        else:
            # Only one sample: duplicate it with opposite label
            features = pl.concat([features, features])
            labels = [1, 0]
    target = pl.Series("label", labels)
    return train_risk_model(features, target, settings)


@router.get("/{patient_id}/risk", response_model=RiskResponse)
def get_patient_risk(
    patient_id: str,
    phi_read: bool = Query(default=False),
    conn: duckdb.DuckDBPyConnection = Depends(get_db_conn),  # noqa: B008
    settings: Settings = Depends(get_settings_dep),  # noqa: B008
) -> RiskResponse:
    log_access(patient_id, "risk_score_read", "api")
    features = _get_patient_features(patient_id, conn)
    if features is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    model = _train_model(conn, settings)
    score = predict_risk(model, features)[0]
    masked_id = mask_field("patient_id", patient_id, phi_read=phi_read) or patient_id
    return RiskResponse(patient_id=masked_id, risk_score=float(score), model_version="v0-logistic")


@router.get("/{patient_id}/care-gaps", response_model=CareGapResponse)
def get_patient_care_gaps(
    patient_id: str,
    phi_read: bool = Query(default=False),
    conn: duckdb.DuckDBPyConnection = Depends(get_db_conn),  # noqa: B008
    settings: Settings = Depends(get_settings_dep),  # noqa: B008
) -> CareGapResponse:
    log_access(patient_id, "care_gaps_read", "api")
    exists = conn.execute("SELECT 1 FROM dim_patient WHERE patient_id = ?", [patient_id]).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Identify active conditions with no recent encounter as care gaps
    gaps_rows = conn.execute(
        """
        SELECT fc.description
        FROM fact_condition fc
        JOIN dim_patient dp ON dp.patient_key = fc.patient_key
        WHERE dp.patient_id = ?
          AND fc.stop_date_key IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM fact_encounter fe
              JOIN dim_date dd ON dd.date_key = fe.start_date_key
              WHERE fe.patient_key = dp.patient_key
                AND CURRENT_DATE - dd.full_date <= 365
          )
    """,
        [patient_id],
    ).fetchall()

    gaps = [r[0] for r in gaps_rows if r[0]]
    explanation = explain_care_gaps(patient_id, gaps, settings)
    masked_id = mask_field("patient_id", patient_id, phi_read=phi_read) or patient_id
    return CareGapResponse(
        patient_id=masked_id,
        gaps=explanation.gaps,
        summary=explanation.summary,
        model_used=explanation.model_used,
    )
