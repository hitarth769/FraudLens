from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.models import Transaction, LoginEvent, Customer
from app.tools.base import ToolResult, generate_evidence_id
from app.schemas.models import EvidenceItem, PatternType, Severity
from datetime import datetime, timedelta
from app.utils.normalization import normalize_location

def analyze_location(db: Session, account_id: str, current_txn_id: str) -> ToolResult:
    """
    Analyze current transaction location against historical account behavior.
    Generates GEO_ANOMALY evidence if the current location is unusual.
    """
    txn = db.query(Transaction).filter(Transaction.id == current_txn_id).first()
    if not txn:
        return ToolResult(tool="analyze_location", success=False, data={}, error="Transaction not found")

    current_loc = txn.location
    txn_ts = txn.timestamp
    normalized_current = normalize_location(current_loc)

    # Fetch all historical locations from transactions and logins occurring BEFORE the trigger txn
    hist_txn_locs = db.query(Transaction.location).filter(
        Transaction.account_id == account_id,
        Transaction.timestamp < txn_ts,
        Transaction.id != current_txn_id
    ).all()

    hist_login_locs = db.query(LoginEvent.location).filter(
        LoginEvent.account_id == account_id,
        LoginEvent.timestamp < txn_ts
    ).all()

    # Normalize and flatten list of locations
    historical_normalized = set([normalize_location(loc[0]) for loc in hist_txn_locs]) | set([normalize_location(loc[0]) for loc in hist_login_locs])

    # A location is an anomaly if its normalized form has never been seen before the trigger transaction
    is_anomaly = normalized_current != "unknown" and normalized_current not in historical_normalized

    data = {
        "current_location": current_loc,
        "normalized_current": normalized_current,
        "historical_normalized": list(historical_normalized),
        "is_anomaly": is_anomaly
    }

    evidence = []
    if is_anomaly:
        evidence.append(EvidenceItem(
            id=generate_evidence_id("analyze_location", current_txn_id, 0),
            type="GEO_ANOMALY",
            pattern="ACCOUNT_TAKEOVER",
            title="Geographic location anomaly",
            claim="Transaction location is unusual for this account",
            observed=f"Location: {current_loc}",
            baseline=f"Known normalized locations before txn: {', '.join(list(historical_normalized)[:3])}...",
            whyItMatters="Transactions from unknown locations often indicate takeover",
            severity=Severity.MEDIUM,
            polarity="SUPPORTING",
            source={"table": "transactions", "eventId": current_txn_id},
            revealedAtStep=0
        ))

    return ToolResult(tool="analyze_location", success=True, data=data, evidence=evidence)
