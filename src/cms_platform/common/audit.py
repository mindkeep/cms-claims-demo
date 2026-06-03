import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


@dataclass
class AuditRecord:
    patient_id: str
    action: str
    accessor: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    context: dict[str, object] = field(default_factory=dict)


def log_access(
    patient_id: str,
    action: str,
    accessor: str,
    **context: object,
) -> AuditRecord:
    record = AuditRecord(
        patient_id=patient_id,
        action=action,
        accessor=accessor,
        context=dict(context),
    )
    logger.info(
        "PHI_ACCESS patient=%s action=%s accessor=%s",
        record.patient_id,
        record.action,
        record.accessor,
        extra={
            "audit": True,
            "patient_id": record.patient_id,
            "action": record.action,
            "accessor": record.accessor,
            "context": record.context,
        },
    )
    return record
