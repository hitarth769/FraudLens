from sqlalchemy.orm import Session
from app.db.models import Transaction, Account, Customer, Merchant, Card
from app.tools.base import ToolResult, generate_evidence_id
from app.schemas.models import EvidenceItem, PatternType, Severity

def get_transaction(db: Session, transaction_id: str) -> ToolResult:
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        return ToolResult(tool="get_transaction", success=False, data={}, error="Transaction not found")

    acc = db.query(Account).filter(Account.id == txn.account_id).first()
    cust = db.query(Customer).filter(Customer.id == acc.customer_id).first()
    merch = db.query(Merchant).filter(Merchant.id == txn.merchant_id).first()

    # For card testing, we care about how many distinct cards are used in the burst window
    # associated with the trigger transaction.
    from datetime import timedelta
    window_start = txn.timestamp - timedelta(minutes=15)
    window_end = txn.timestamp

    distinct_cards = db.query(Transaction.card_id).filter(
        Transaction.account_id == acc.id,
        Transaction.timestamp >= window_start,
        Transaction.timestamp <= window_end
    ).distinct().count()

    total_count = db.query(Transaction).filter(
        Transaction.account_id == acc.id,
        Transaction.timestamp >= window_start,
        Transaction.timestamp <= window_end
    ).count()

    data = {
        "transaction": {
            "id": txn.id,
            "amount": txn.amount,
            "currency": txn.currency,
            "timestamp": txn.timestamp.isoformat(),
            "status": txn.status,
            "channel": txn.channel,
            "ip": txn.ip,
            "location": txn.location
        },
        "customer": {
            "id": cust.id,
            "name": cust.name,
            "accountId": acc.id
        },
        "merchant": {
            "id": merch.id,
            "name": merch.name,
            "category": merch.category
        },
        "distinct_cards": distinct_cards,
        "total_count": total_count
    }

    # Basic evidence: The fact that this transaction exists and is flagged
    evidence = [
        EvidenceItem(
            id=generate_evidence_id("get_transaction", txn.id, 0),
            type="TRANSACTION_DETAIL",
            pattern="BEHAVIOURAL_ANOMALY", # Default until detectors run
            title="Transaction identified",
            claim="Transaction exists in system",
            observed=f"Amount {txn.amount} {txn.currency}",
            baseline="N/A",
            whyItMatters="Baseline for all investigation",
            severity=Severity.LOW,
            polarity="SUPPORTING",
            source={"table": "transactions", "eventId": txn.id},
            revealedAtStep=0 # Set by orchestrator
        )
    ]

    return ToolResult(tool="get_transaction", success=True, data=data, evidence=evidence)
