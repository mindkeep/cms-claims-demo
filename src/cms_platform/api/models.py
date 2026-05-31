from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class RiskResponse(BaseModel):
    patient_id: str
    risk_score: float
    model_version: str


class CareGapResponse(BaseModel):
    patient_id: str
    gaps: list[str]
    summary: str
    model_used: str


class CohortRow(BaseModel):
    encounter_year: int | None
    total_patients: int
    diabetes_cohort: int
    heart_failure_cohort: int
    copd_asthma_cohort: int
    hypertension_cohort: int
    avg_condition_count: float | None


class BenchmarkRow(BaseModel):
    encounter_year: int | None
    patient_count: int
    avg_cost: float | None
    p50_cost: float | None
    p90_cost: float | None
    p99_cost: float | None
    max_cost: float | None
    top_quartile_count: int
