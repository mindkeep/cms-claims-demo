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


# ── logging ───────────────────────────────────────────────────────────────────

def test_json_formatter_produces_valid_json() -> None:
    import json
    import logging as stdlib_logging

    from cms_platform.common.logging import JSONFormatter

    formatter = JSONFormatter()
    record = stdlib_logging.LogRecord(
        name="test",
        level=stdlib_logging.INFO,
        pathname="",
        lineno=0,
        msg="hello world",
        args=(),
        exc_info=None,
    )
    parsed = json.loads(formatter.format(record))
    assert parsed["message"] == "hello world"
    assert parsed["level"] == "INFO"
    assert "timestamp" in parsed


def test_configure_logging_does_not_raise() -> None:
    from cms_platform.common.logging import configure_logging

    configure_logging("DEBUG")
    configure_logging("INFO")
