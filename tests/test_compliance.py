from __future__ import annotations

import hashlib

from cms_platform.common.mask import PHI_FIELDS, mask_field, mask_record


def test_phi_fields_contains_patient_id() -> None:
    assert "patient_id" in PHI_FIELDS


def test_phi_fields_contains_dates() -> None:
    assert "birthdate" in PHI_FIELDS
    assert "deathdate" in PHI_FIELDS


def test_mask_field_phi_returns_hash_prefix() -> None:
    result = mask_field("patient_id", "abc-uuid", phi_read=False)
    assert result is not None
    assert result.startswith("****")
    expected_hash = hashlib.sha256(b"abc-uuid").hexdigest()[:8]
    assert result == f"****{expected_hash}"


def test_mask_field_phi_read_returns_plaintext() -> None:
    assert mask_field("patient_id", "abc-uuid", phi_read=True) == "abc-uuid"


def test_mask_field_non_phi_passthrough() -> None:
    assert mask_field("encounter_class", "inpatient", phi_read=False) == "inpatient"


def test_mask_record_masks_phi_fields() -> None:
    record: dict[str, object] = {
        "patient_id": "some-uuid",
        "birthdate": "1960-01-01",
        "encounter_class": "inpatient",
    }
    masked = mask_record(record)
    assert masked["patient_id"] != "some-uuid"
    assert masked["birthdate"] != "1960-01-01"
    assert masked["encounter_class"] == "inpatient"


def test_mask_record_phi_read_passthrough() -> None:
    record: dict[str, object] = {"patient_id": "some-uuid", "birthdate": "1960-01-01"}
    result = mask_record(record, phi_read=True)
    assert result["patient_id"] == "some-uuid"
    assert result["birthdate"] == "1960-01-01"
