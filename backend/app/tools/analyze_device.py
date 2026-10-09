from sqlalchemy.orm import Session
from app.db.models import Device, LoginEvent, Account
from app.tools.base import ToolResult, generate_evidence_id
from app.schemas.models import EvidenceItem, PatternType, Severity

def analyze_device(db: Session, account_id: str, current_device_id: str) -> ToolResult:
    if not current_device_id:
        return ToolResult(tool="analyze_device", success=False, data={}, error="No device ID provided")

    device = db.query(Device).filter(Device.id == current_device_id).first()
    if not device:
        return ToolResult(tool="analyze_device", success=False, data={}, error="Device not found in registry")

    # Check if device is known to this account
    is_known = db.query(LoginEvent).filter(
        LoginEvent.account_id == account_id,
        LoginEvent.device_id == current_device_id
    ).count() > 1

    # Check how many accounts use this device
    linked_accounts = db.query(LoginEvent.account_id).filter(
        LoginEvent.device_id == current_device_id
    ).distinct().count()

    data = {
        "device_id": current_device_id,
        "is_known_to_account": is_known,
        "linked_accounts_count": linked_accounts,
        "device_info": {
            "model": device.model,
            "os": device.os
        }
    }

    evidence = []
    if not is_known:
        evidence.append(EvidenceItem(
            id=generate_evidence_id("analyze_device", current_device_id, 0),
            type="DEVICE_NOVELTY",
            pattern="ACCOUNT_TAKEOVER",
            title="Unknown device detected",
            claim="Device has no prior history with this account",
            observed=f"Device {current_device_id} not seen before",
            baseline="Device should be recognized",
            whyItMatters="Strong indicator of account takeover",
            severity=Severity.HIGH,
            polarity="SUPPORTING",
            source={"table": "logins", "eventId": "DEVICE_CHECK"},
            revealedAtStep=0
        ))

    if linked_accounts > 3:
        evidence.append(EvidenceItem(
            id=generate_evidence_id("analyze_device", current_device_id, 1),
            type="DEVICE_SHARING",
            pattern="MULE_NETWORK",
            title="Device shared across multiple accounts",
            claim="One device linked to many separate accounts",
            observed=f"{linked_accounts} accounts on one device",
            baseline="Typical 1-2 accounts per device",
            whyItMatters="Suggests professional fraud operation or mule controller",
            severity=Severity.MEDIUM,
            polarity="SUPPORTING",
            source={"table": "logins", "eventId": "DEVICE_SHARING"},
            revealedAtStep=0
        ))

    return ToolResult(tool="analyze_device", success=True, data=data, evidence=evidence)
