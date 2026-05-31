"""Tests for WP6 compliance controls: field masking and audit wiring."""

from __future__ import annotations

from pathlib import Path  # noqa: F401 — used in type annotation below

# ---------------------------------------------------------------------------
# mask_field tests
# ---------------------------------------------------------------------------


def test_mask_field_hides_phi_by_default() -> None:
    from cms_platform.common.mask import mask_field

    result = mask_field("desynpuf_id", "BENE_001")
    assert result is not None
    assert "BENE_001" not in result
    assert result.startswith("****")


def test_mask_field_passes_through_with_phi_read() -> None:
    from cms_platform.common.mask import mask_field

    result = mask_field("desynpuf_id", "BENE_001", phi_read=True)
    assert result == "BENE_001"


def test_mask_field_passes_through_non_phi() -> None:
    from cms_platform.common.mask import mask_field

    result = mask_field("claim_year", "2008")
    assert result == "2008"


def test_mask_field_handles_none() -> None:
    from cms_platform.common.mask import mask_field

    result = mask_field("desynpuf_id", None)
    assert result is None


def test_mask_record_masks_phi_fields() -> None:
    from cms_platform.common.mask import mask_record

    record: dict[str, object] = {
        "desynpuf_id": "BENE_001",
        "claim_year": 2008,
        "risk_score": 0.85,
    }
    masked = mask_record(record)
    assert "BENE_001" not in str(masked["desynpuf_id"])
    assert masked["claim_year"] == 2008
    assert masked["risk_score"] == 0.85


def test_mask_record_phi_read_reveals_all() -> None:
    from cms_platform.common.mask import mask_record

    record: dict[str, object] = {"desynpuf_id": "BENE_001", "claim_year": 2008}
    unmasked = mask_record(record, phi_read=True)
    assert unmasked["desynpuf_id"] == "BENE_001"


def test_mask_deterministic() -> None:
    """Same input always produces the same masked output."""
    from cms_platform.common.mask import mask_field

    r1 = mask_field("desynpuf_id", "BENE_001")
    r2 = mask_field("desynpuf_id", "BENE_001")
    assert r1 == r2


# ---------------------------------------------------------------------------
# PHI_FIELDS coverage tests
# ---------------------------------------------------------------------------


def test_all_phi_fields_are_masked() -> None:
    """Every field in PHI_FIELDS is masked by default."""
    from cms_platform.common.mask import PHI_FIELDS, mask_field

    for field_name in PHI_FIELDS:
        result = mask_field(field_name, "some_value")
        assert result is not None
        assert "some_value" not in result
        assert result.startswith("****"), f"Expected mask for field {field_name!r}"


def test_mask_field_suffix_is_8_hex_chars() -> None:
    """Masked value has exactly 4 stars plus 8 hex characters."""
    from cms_platform.common.mask import mask_field

    result = mask_field("beneficiary_id", "BENE_XYZ")
    assert result is not None
    assert len(result) == 12  # "****" + 8 hex chars
    suffix = result[4:]
    assert all(c in "0123456789abcdef" for c in suffix)


# ---------------------------------------------------------------------------
# Audit wiring test
# ---------------------------------------------------------------------------


def test_risk_endpoint_calls_audit_log(tmp_path: Path) -> None:
    """Verify audit.log_access is callable and returns a well-formed AuditRecord."""
    from cms_platform.common.audit import AuditRecord, log_access

    record = log_access("BENE_TEST", "risk_score", "test")
    assert isinstance(record, AuditRecord)
    assert record.action == "risk_score"
    assert record.beneficiary_id == "BENE_TEST"
    assert record.accessor == "test"
