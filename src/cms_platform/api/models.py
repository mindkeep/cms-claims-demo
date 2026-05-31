from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class RiskResponse(BaseModel):
    beneficiary_id: str
    risk_score: float
    claim_year: int
    model_version: str


class CareGapResponse(BaseModel):
    beneficiary_id: str
    gaps: list[str]
    summary: str
    model_used: str


class CohortRow(BaseModel):
    claim_year: int | None
    total_beneficiaries: int
    diabetes_cohort: int
    chf_cohort: int
    copd_cohort: int
    cancer_cohort: int
    avg_comorbidities: float | None
    max_comorbidities: int | None


class BenchmarkRow(BaseModel):
    claim_year: int | None
    beneficiary_count: int
    avg_cost: float | None
    p50_cost: float | None
    p90_cost: float | None
    p99_cost: float | None
    max_cost: float | None
    top_quartile_count: int
