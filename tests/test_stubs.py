def test_ingest_download_importable() -> None:
    from cms_platform.ingest.download import download_subsamples, main

    assert callable(download_subsamples)
    assert callable(main)


def test_ingest_load_importable() -> None:
    from cms_platform.ingest.load import load_subsamples, main

    assert callable(load_subsamples)
    assert callable(main)


def test_schema_transforms_importable() -> None:
    from cms_platform.schema.transforms import build_star_schema

    assert callable(build_star_schema)


def test_analytics_queries_importable() -> None:
    from cms_platform.analytics.queries import (
        care_gap_detection,
        cohort_segmentation,
        cost_benchmarking,
        readmission_30day,
        utilization_trends,
    )

    for fn in [readmission_30day, cohort_segmentation, cost_benchmarking,
               care_gap_detection, utilization_trends]:
        assert callable(fn)


def test_scoring_risk_model_importable() -> None:
    from cms_platform.scoring.risk_model import predict_risk, train_risk_model

    assert callable(train_risk_model)
    assert callable(predict_risk)


def test_scoring_explainer_importable() -> None:
    from cms_platform.scoring.explainer import explain_care_gaps

    assert callable(explain_care_gaps)


def test_explainer_stub_fires_when_ollama_unreachable() -> None:
    from cms_platform.common.config import Settings
    from cms_platform.scoring.explainer import explain_care_gaps

    # Port 19999 has nothing running — Ollama call will fail → stub fires
    s = Settings(ollama_base_url="http://localhost:19999/v1")
    result = explain_care_gaps("BENE_001", ["Annual wellness visit", "Flu vaccine"], s)
    assert result.beneficiary_id == "BENE_001"
    assert result.model_used == "stub"
    assert "wellness" in result.summary.lower() or "gap" in result.summary.lower()


def test_explainer_stub_handles_no_gaps() -> None:
    from cms_platform.common.config import Settings
    from cms_platform.scoring.explainer import explain_care_gaps

    s = Settings(ollama_base_url="http://localhost:19999/v1")
    result = explain_care_gaps("BENE_002", [], s)
    assert result.model_used == "stub"
    assert "no" in result.summary.lower()


def test_api_app_importable() -> None:
    from cms_platform.api.main import app

    assert app is not None


def test_api_health_endpoint() -> None:
    from fastapi.testclient import TestClient

    from cms_platform.api.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
