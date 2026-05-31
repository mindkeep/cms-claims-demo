from __future__ import annotations

import duckdb
import polars as pl
from fastapi import APIRouter, Depends, HTTPException, Query

from cms_platform.api.deps import get_db_conn, get_settings_dep
from cms_platform.common.audit import log_access
from cms_platform.common.config import Settings
from cms_platform.common.mask import mask_record
from cms_platform.scoring.explainer import explain_care_gaps
from cms_platform.scoring.risk_model import RISK_FEATURES, RiskModel, predict_risk, train_risk_model

router = APIRouter(prefix="/beneficiary", tags=["beneficiary"])


def _get_bene_features(
    beneficiary_id: str,
    conn: duckdb.DuckDBPyConnection,
) -> tuple[pl.DataFrame, int] | None:
    """Return (features_df, claim_year) for the beneficiary's latest year, or None."""
    cols = ", ".join(RISK_FEATURES)
    result = conn.execute(
        f"SELECT {cols}, claim_year FROM dim_beneficiary "
        "WHERE desynpuf_id = ? ORDER BY claim_year DESC LIMIT 1",
        [beneficiary_id],
    ).fetchone()
    if result is None:
        return None
    values = list(result)
    claim_year = int(values[-1]) if values[-1] is not None else 0
    feature_values = [float(v) if v is not None else 0.0 for v in values[:-1]]
    df = pl.DataFrame({col: [val] for col, val in zip(RISK_FEATURES, feature_values, strict=False)})
    return df, claim_year


def _train_model_on_all(
    conn: duckdb.DuckDBPyConnection,
    settings: Settings,
) -> RiskModel:
    """Train a risk model on all beneficiaries in dim_beneficiary."""
    cols = ", ".join(RISK_FEATURES)
    rows = conn.execute(
        f"SELECT {cols}, medreimb_ip + medreimb_op + medreimb_car AS total_cost "
        "FROM dim_beneficiary"
    ).fetchall()
    if not rows:
        raise HTTPException(status_code=503, detail="No beneficiary data loaded")

    all_data = pl.DataFrame(
        {
            col: [float(r[i]) if r[i] is not None else 0.0 for r in rows]
            for i, col in enumerate(RISK_FEATURES)
        }
    )
    costs = [float(r[-1]) if r[-1] is not None else 0.0 for r in rows]
    n = len(costs)
    # Rank-based label: top 25% by cost get label=1 (at least 1 sample).
    # Using rank rather than a threshold value avoids degenerate single-class
    # targets when all beneficiaries have identical costs (common in tiny test DBs).
    sorted_indices = sorted(range(n), key=lambda i: costs[i], reverse=True)
    top_n = max(1, int(n * 0.25))
    high_cost_set = set(sorted_indices[:top_n])
    target = pl.Series("high_cost", [1 if i in high_cost_set else 0 for i in range(n)])
    # If still single-class (all n=1), force both classes to allow model fit
    if len(set(target.to_list())) < 2:
        labels = [0] * n
        labels[sorted_indices[0]] = 1
        target = pl.Series("high_cost", labels)
    return train_risk_model(all_data, target, settings)


@router.get("/{beneficiary_id}/risk")
def get_risk(
    beneficiary_id: str,
    phi_read: bool = Query(default=False),  # noqa: B008
    conn: duckdb.DuckDBPyConnection = Depends(get_db_conn),  # noqa: B008
    settings: Settings = Depends(get_settings_dep),  # noqa: B008
) -> dict[str, object]:
    """Risk score for a specific beneficiary. Logs PHI access."""
    log_access(beneficiary_id, "risk_score", "api/risk")
    features_result = _get_bene_features(beneficiary_id, conn)
    if features_result is None:
        raise HTTPException(status_code=404, detail=f"Beneficiary {beneficiary_id!r} not found")
    features, claim_year = features_result
    model = _train_model_on_all(conn, settings)
    scores = predict_risk(model, features)
    response: dict[str, object] = {
        "beneficiary_id": beneficiary_id,
        "risk_score": float(scores[0]),
        "claim_year": claim_year,
        "model_version": "logistic_regression_v1",
    }
    return mask_record(response, phi_read=phi_read)


@router.get("/{beneficiary_id}/care-gaps")
def get_care_gaps(
    beneficiary_id: str,
    phi_read: bool = Query(default=False),  # noqa: B008
    conn: duckdb.DuckDBPyConnection = Depends(get_db_conn),  # noqa: B008
    settings: Settings = Depends(get_settings_dep),  # noqa: B008
) -> dict[str, object]:
    """Care gap explanation for a beneficiary. Logs PHI access."""
    log_access(beneficiary_id, "care_gaps", "api/care-gaps")

    result = conn.execute(
        "SELECT sp_diabetes FROM dim_beneficiary WHERE desynpuf_id = ? LIMIT 1",
        [beneficiary_id],
    ).fetchone()
    if result is None:
        raise HTTPException(status_code=404, detail=f"Beneficiary {beneficiary_id!r} not found")

    is_diabetic = bool(result[0])
    gaps: list[str] = []
    if is_diabetic:
        carrier_row = conn.execute(
            "SELECT COUNT(*) FROM fact_carrier WHERE desynpuf_id = ?",
            [beneficiary_id],
        ).fetchone()
        carrier_count = int(carrier_row[0]) if carrier_row else 0
        if carrier_count == 0:
            gaps.append("Annual diabetes management visit (no carrier claims found)")

    explanation = explain_care_gaps(beneficiary_id, gaps, settings)
    response: dict[str, object] = {
        "beneficiary_id": explanation.beneficiary_id,
        "gaps": explanation.gaps,
        "summary": explanation.summary,
        "model_used": explanation.model_used,
    }
    return mask_record(response, phi_read=phi_read)
