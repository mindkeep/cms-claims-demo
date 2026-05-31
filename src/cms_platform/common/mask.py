from __future__ import annotations

import hashlib

# Fields treated as PHI in external API responses.
# phi_read=True bypasses masking for callers with explicit PHI_READ scope.
# TODO(future-auth): enforce phi_read via JWT claim rather than query param.
PHI_FIELDS: frozenset[str] = frozenset(
    {
        "patient_id",
        "birthdate",
        "deathdate",
        "ssn",
        "first",
        "last",
    }
)


def mask_field(field_name: str, value: str | None, *, phi_read: bool = False) -> str | None:
    """Mask a PHI field unless the caller holds PHI_READ scope.

    Returns '****' + first 8 hex chars of SHA-256(value).
    In production: replace with format-preserving encryption.
    """
    if phi_read or value is None:
        return value
    if field_name not in PHI_FIELDS:
        return value
    return "****" + hashlib.sha256(value.encode()).hexdigest()[:8]


def mask_record(
    record: dict[str, object],
    *,
    phi_read: bool = False,
) -> dict[str, object]:
    """Apply mask_field to every PHI field in a flat record dict."""
    result: dict[str, object] = {}
    for k, v in record.items():
        if k in PHI_FIELDS and isinstance(v, str):
            result[k] = mask_field(k, v, phi_read=phi_read)
        else:
            result[k] = v
    return result
