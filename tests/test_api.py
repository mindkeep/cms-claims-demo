from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from cms_platform.api.deps import get_db_conn
from cms_platform.api.main import app
from cms_platform.common.config import Settings, get_settings
from cms_platform.ingest.load import _ensure_raw_tables, load_synthea_data
from cms_platform.schema.transforms import build_star_schema
from tests.test_ingest import _seed_csvs


@pytest.fixture
def client(tmp_path: Path, settings: Settings) -> TestClient:
    conn = duckdb.connect()
    data_dir = _seed_csvs(tmp_path)
    _ensure_raw_tables(conn)
    load_synthea_data(data_dir, conn)
    build_star_schema(conn, settings)

    app.dependency_overrides[get_db_conn] = lambda: conn
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_cohorts_returns_list(client: TestClient) -> None:
    r = client.get("/cohorts")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if data:
        assert "total_patients" in data[0]


def test_benchmarks_returns_list(client: TestClient) -> None:
    r = client.get("/benchmarks/encounters")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_patient_risk_returns_score(client: TestClient) -> None:
    r = client.get("/patients/aaaaaaaa-0001-0001-0001-000000000001/risk")
    assert r.status_code == 200
    body = r.json()
    assert "risk_score" in body
    assert 0.0 <= body["risk_score"] <= 1.0


def test_patient_risk_masks_patient_id(client: TestClient) -> None:
    r = client.get("/patients/aaaaaaaa-0001-0001-0001-000000000001/risk")
    assert r.status_code == 200
    assert r.json()["patient_id"].startswith("****")


def test_patient_risk_phi_read_returns_plain(client: TestClient) -> None:
    r = client.get("/patients/aaaaaaaa-0001-0001-0001-000000000001/risk?phi_read=true")
    assert r.status_code == 200
    assert r.json()["patient_id"] == "aaaaaaaa-0001-0001-0001-000000000001"


def test_patient_care_gaps(client: TestClient) -> None:
    r = client.get("/patients/aaaaaaaa-0001-0001-0001-000000000001/care-gaps")
    assert r.status_code == 200
    body = r.json()
    assert "gaps" in body
    assert "summary" in body


def test_patient_not_found(client: TestClient) -> None:
    r = client.get("/patients/nonexistent-uuid/risk")
    assert r.status_code == 404
