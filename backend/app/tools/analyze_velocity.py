from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.models import Transaction, Account
from app.tools.base import ToolResult, generate_evidence_id
from app.schemas.models import EvidenceItem, PatternType, Severity
from datetime import datetime, timedelta

def analyze_velocity(db: Session, account_id: str, current_txn_id: str) -> ToolResult:
    # Windows to check
    windows = {
        "5m": 5,
        "15m": 15,
        "1h": 60,
        "24h": 1440
    }

    results = {}
    # Use the timestamp of the current transaction as the anchor for windows
    # to ensure deterministic behavior across repeated runs
    txn = db.query(Transaction).filter(Transaction.id == current_txn_id).first()
    anchor_time = txn.timestamp if txn else datetime.now()

    for label, minutes in windows.items():
        start_time = anchor_time - timedelta(minutes=minutes)
        count = db.query(Transaction).filter(
            Transaction.account_id == account_id,
            Transaction.timestamp >= start_time,
            Transaction.timestamp <= anchor_time
        ).count()
        results[label] = count

    # Check for decline concentration in the most suspicious window (1h)
    # Card testing often has high decline rates in the burst
    window_start = anchor_time - timedelta(minutes=60)
    decline_count = db.query(Transaction).filter(
        Transaction.account_id == account_id,
        Transaction.timestamp >= window_start,
        Transaction.timestamp <= anchor_time,
        Transaction.status == "declined"
    ).count()

    data = {
        "velocity": results,
        "decline_count": decline_count,
        "account_id": account_id
    }

    evidence = []
    # If high velocity in short window, mark as potential evidence
    if results["15m"] > 5:
        evidence.append(EvidenceItem(
            id=generate_evidence_id("analyze_velocity", account_id, 0),
            type="VELOCITY_SPIKE",
            pattern="CARD_TESTING",
            title="High transaction velocity",
            claim="Rapid sequence of transactions detected",
            observed=f"{results['15m']} txns in 15m",
            baseline="Typical < 2 txns/15m",
            whyItMatters="Common in card testing or automated attacks",
            severity=Severity.HIGH,
            polarity="SUPPORTING",
            source={"table": "transactions", "eventId": "VELOCITY_ANALYSIS"},
            revealedAtStep=0
        ))

    return ToolResult(tool="analyze_velocity", success=True, data=data, evidence=evidence)
