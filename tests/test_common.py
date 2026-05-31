from pathlib import Path

import pytest

from cms_platform.common.config import Settings


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


# ── db ────────────────────────────────────────────────────────────────────────

def test_get_connection_returns_duckdb(settings: Settings) -> None:
    import duckdb

    from cms_platform.common.db import get_connection

    conn = get_connection(settings)
    assert isinstance(conn, duckdb.DuckDBPyConnection)
    conn.close()


def test_get_connection_creates_parent_dirs(tmp_path: Path) -> None:
    from cms_platform.common.db import get_connection

    nested = Settings(db_path=str(tmp_path / "a" / "b" / "c.duckdb"))
    conn = get_connection(nested)
    conn.close()
    assert (tmp_path / "a" / "b" / "c.duckdb").exists()


def test_connection_executes_query(settings: Settings) -> None:
    from cms_platform.common.db import get_connection

    conn = get_connection(settings)
    result = conn.execute("SELECT 42 AS answer").fetchone()
    conn.close()
    assert result is not None and result[0] == 42


# ── audit ─────────────────────────────────────────────────────────────────────

def test_log_access_returns_audit_record() -> None:
    from cms_platform.common.audit import AuditRecord, log_access

    record = log_access("BENE_001", "read", "api/beneficiary")
    assert isinstance(record, AuditRecord)
    assert record.beneficiary_id == "BENE_001"
    assert record.action == "read"
    assert record.accessor == "api/beneficiary"
    assert record.context == {}


def test_log_access_captures_context() -> None:
    from cms_platform.common.audit import log_access

    record = log_access("BENE_002", "read", "api/risk", endpoint="/risk", ip="127.0.0.1")
    assert record.context["endpoint"] == "/risk"
    assert record.context["ip"] == "127.0.0.1"


def test_log_access_emits_log_record(caplog: pytest.LogCaptureFixture) -> None:
    import logging

    from cms_platform.common.audit import log_access

    with caplog.at_level(logging.INFO, logger="cms_platform.common.audit"):
        log_access("BENE_003", "read", "test_caller")
    assert any("BENE_003" in r.message for r in caplog.records)
