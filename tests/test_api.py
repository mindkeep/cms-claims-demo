"""Integration tests for the FastAPI route layer (WP5)."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from cms_platform.api.main import app
from cms_platform.common.config import Settings

# ---------------------------------------------------------------------------
# Fixture: build a complete star schema in a tmp DuckDB and return a TestClient
# ---------------------------------------------------------------------------

def _build_test_db(tmp_path: Path) -> Settings:
    """Write synthetic CSVs, ingest, and build star schema. Returns Settings."""
    from cms_platform.common.db import get_connection
    from cms_platform.ingest.load import load_subsamples
    from cms_platform.schema.transforms import build_star_schema

    # Reuse the _write_sample_files helper from test_ingest
    from tests.test_ingest import _write_sample_files

    _write_sample_files(tmp_path / "raw", 1)

    settings = Settings(
        db_path=str(tmp_path / "test.duckdb"),
        raw_data_dir=str(tmp_path / "raw"),
        manifests_dir=str(tmp_path / "manifests"),
    )
    load_subsamples([1], settings)
    conn = get_connection(settings)
    build_star_schema(conn, settings)
    conn.close()
    return settings


@pytest.fixture
def client(tmp_path: Path) -> Generator[TestClient]:
    """TestClient with a loaded DuckDB (star schema built)."""
    from cms_platform.api.deps import get_db_conn, get_settings_dep
    from cms_platform.common.db import get_connection

    settings = _build_test_db(tmp_path)

    def override_settings() -> Settings:
        return settings

    def override_db() -> duckdb.DuckDBPyConnection:
        return get_connection(settings)

    app.dependency_overrides[get_settings_dep] = override_settings
    app.dependency_overrides[get_db_conn] = override_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# /cohorts
# ---------------------------------------------------------------------------

def test_cohorts_returns_list(client: TestClient) -> None:
    resp = client.get("/cohorts")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_cohorts_has_expected_fields(client: TestClient) -> None:
    resp = client.get("/cohorts")
    assert resp.status_code == 200
    data = resp.json()
    if data:  # may be empty if no data, but should have at least one row with real DB
        row = data[0]
        assert "total_beneficiaries" in row
        assert "diabetes_cohort" in row


# ---------------------------------------------------------------------------
# /beneficiary/{id}/risk
# ---------------------------------------------------------------------------

def test_beneficiary_risk_not_found(client: TestClient) -> None:
    resp = client.get("/beneficiary/NONEXISTENT_BENE_XYZ/risk")
    assert resp.status_code == 404


def test_beneficiary_risk_found(client: TestClient) -> None:
    # B001 is the beneficiary written by _write_sample_files
    resp = client.get("/beneficiary/B001/risk")
    assert resp.status_code == 200
    data = resp.json()
    assert data["beneficiary_id"] == "B001"
    assert "risk_score" in data
    assert 0.0 <= data["risk_score"] <= 1.0
    assert "claim_year" in data
    assert data["model_version"] == "logistic_regression_v1"


# ---------------------------------------------------------------------------
# /beneficiary/{id}/care-gaps
# ---------------------------------------------------------------------------

def test_beneficiary_care_gaps_not_found(client: TestClient) -> None:
    resp = client.get("/beneficiary/NONEXISTENT_BENE_XYZ/care-gaps")
    assert resp.status_code == 404


def test_beneficiary_care_gaps_found(client: TestClient) -> None:
    # B001 has sp_diabetes='2' → not diabetic → gaps will be []
    resp = client.get("/beneficiary/B001/care-gaps")
    assert resp.status_code == 200
    data = resp.json()
    assert data["beneficiary_id"] == "B001"
    assert isinstance(data["gaps"], list)
    assert "summary" in data
    assert "model_used" in data


# ---------------------------------------------------------------------------
# /benchmarks/providers
# ---------------------------------------------------------------------------

def test_benchmarks_providers_returns_list(client: TestClient) -> None:
    resp = client.get("/benchmarks/providers")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
