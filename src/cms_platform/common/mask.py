from __future__ import annotations

import hashlib

# Fields that are always masked in external API responses unless PHI_READ scope is granted
PHI_FIELDS: frozenset[str] = frozenset({
    "desynpuf_id",
    "beneficiary_id",
    "birth_dt",
    "death_dt",
})


def mask_field(field_name: str, value: str | None, *, phi_read: bool = False) -> str | None:
    """Mask a PHI field unless the caller holds PHI_READ scope.

    For portfolio demo: masking is a deterministic SHA-256 hash prefix.
    In production: replace with a format-preserving encryption scheme.
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
    """Apply mask_field to all PHI fields in a flat record dict."""
    result: dict[str, object] = {}
    for k, v in record.items():
        if k in PHI_FIELDS and isinstance(v, str):
            result[k] = mask_field(k, v, phi_read=phi_read)
        else:
            result[k] = v
    return result
