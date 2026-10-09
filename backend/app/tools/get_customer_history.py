from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.models import Customer, Account, Transaction, LoginEvent, ProfileEvent
from app.tools.base import ToolResult, generate_evidence_id
from app.schemas.models import EvidenceItem, PatternType, Severity
from datetime import datetime, timedelta

def get_customer_history(db: Session, customer_id: str, current_txn_amount: float = None, current_txn_id: str = None, txn_timestamp: datetime = None) -> ToolResult:
    cust = db.query(Customer).filter(Customer.id == customer_id).first()
    if not cust:
        return ToolResult(tool="get_customer_history", success=False, data={}, error="Customer not found")

    # Find all accounts for customer
    accounts = db.query(Account).filter(Account.customer_id == customer_id).all()
    account_ids = [a.id for a in accounts]

    # Historical stats (last 90 days)
    ninety_days_ago = datetime.now() - timedelta(days=90)
    txn_stats = db.query(
        func.count(Transaction.id),
        func.avg(Transaction.amount),
        func.sum(Transaction.amount)
    ).filter(Transaction.account_id.in_(account_ids), Transaction.timestamp >= ninety_days_ago).first()

    count, avg_amt, total_amt = txn_stats if txn_stats else (0, 0.0, 0.0)

    # Security events
    security_events = db.query(ProfileEvent).filter(ProfileEvent.account_id.in_(account_ids)).all()

    data = {
        "customer_id": customer_id,
        "stats": {
            "txn_count_90d": count,
            "avg_txn_amount": avg_amt or 0.0,
            "total_volume_90d": total_amt or 0.0,
        },
        "security_events_count": len(security_events),
        "accounts_count": len(accounts)
    }

    evidence = []
    if count > 0:
        evidence.append(EvidenceItem(
            id=generate_evidence_id("get_customer_history", customer_id, 0),
            type="CUSTOMER_BASELINE",
            pattern="BEHAVIOURAL_ANOMALY",
            title="Customer historical volume",
            claim="Customer has established history",
            observed=f"Avg txn: {avg_amt:.2f}",
            baseline="N/A",
            whyItMatters="Establishes typical behavior",
            severity=Severity.LOW,
            polarity="CONTRADICTING",
            source={"table": "transactions", "eventId": "AGGREGATE"},
            revealedAtStep=0
        ))

    # 1. Credential Change Detection (Last 48 hours, but only BEFORE the trigger txn)
    ref_ts = txn_timestamp or datetime.now()
    window_start = ref_ts - timedelta(hours=48)

    recent_security_changes = [
        ev for ev in security_events
        if ev.event_type in ["PASSWORD_CHANGE", "PHONE_CHANGE", "EMAIL_CHANGE"]
        and ev.timestamp >= window_start
        and ev.timestamp <= ref_ts
    ]

    if recent_security_changes:
        # Use the most recent one for the evidence claim
        latest_change = max(recent_security_changes, key=lambda x: x.timestamp)
        evidence.append(EvidenceItem(
            id=generate_evidence_id("get_customer_history", customer_id, 1),
            type="CREDENTIAL_CHANGE",
            pattern="ACCOUNT_TAKEOVER",
            title="Recent security credential change",
            claim="Sensitive account detail was updated shortly before transaction",
            observed=f"Event {latest_change.event_type} at {latest_change.timestamp}",
            baseline="No changes in recent window",
            whyItMatters="Common precursor to account takeover",
            severity=Severity.HIGH,
            polarity="SUPPORTING",
            source={"table": "profile_events", "eventId": latest_change.id}, # Fixed source to real event ID
            revealedAtStep=0
        ))

    # 2. Value Anomaly Detection
    if current_txn_amount is not None and count >= 3: # Ensure meaningful sample
        if current_txn_amount > (avg_amt * 3):
            evidence.append(EvidenceItem(
                id=generate_evidence_id("get_customer_history", customer_id, 2),
                type="VALUE_ANOMALY",
                pattern="ACCOUNT_TAKEOVER",
                title="Transaction value anomaly",
                claim="Transaction amount significantly exceeds historical average",
                observed=f"Amount {current_txn_amount:.2f} is {current_txn_amount/avg_amt:.1f}x average",
                baseline=f"Historical average: {avg_amt:.2f}",
                whyItMatters="High value transfers are common in ATO draining",
                severity=Severity.MEDIUM,
                polarity="SUPPORTING",
                source={"table": "transactions", "eventId": current_txn_id or "CURRENT"},
                revealedAtStep=0
            ))

    return ToolResult(tool="get_customer_history", success=True, data=data, evidence=evidence)
