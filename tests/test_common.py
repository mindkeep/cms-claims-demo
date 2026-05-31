from pathlib import Path

import pytest


def test_package_importable() -> None:
    import cms_platform

    assert cms_platform.__version__ == "0.1.0"


# ── config ────────────────────────────────────────────────────────────────────

def test_settings_defaults() -> None:
    from cms_platform.common.config import Settings

    s = Settings()
    assert s.subsamples == [1]
    assert "cms.duckdb" in s.db_path
    assert s.log_level == "INFO"


def test_settings_override() -> None:
    from cms_platform.common.config import Settings

    s = Settings(subsamples=[1, 2, 3], log_level="DEBUG")
    assert s.subsamples == [1, 2, 3]
    assert s.log_level == "DEBUG"


def test_get_settings_returns_settings() -> None:
    from cms_platform.common.config import Settings, get_settings

    assert isinstance(get_settings(), Settings)


def test_settings_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CMS_LOG_LEVEL", "WARNING")
    from cms_platform.common.config import Settings

    s = Settings()
    assert s.log_level == "WARNING"
