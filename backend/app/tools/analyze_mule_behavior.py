from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.models import Transaction, Account
from app.tools.base import ToolResult, generate_evidence_id
from app.schemas.models import EvidenceItem, PatternType, Severity
from datetime import datetime, timedelta
import statistics
from typing import List, Tuple, Dict, Any

def analyze_mule_behavior(db: Session, account_id: str) -> ToolResult:
    """
    Analyze account behavior for mule-like patterns using actual transaction flow.
    Implementation follows an evidence-first approach with strict FIFO matching
    to determine pass-through and holding-time metrics.
    """
    # 1. Gather all relevant transactions
    # Inbound: transactions where the target account is the recipient.
    # Canonical A2A transfers use recipient_account_id.
    inbound_txns = db.query(Transaction).filter(
        Transaction.recipient_account_id == account_id
    ).order_by(Transaction.timestamp.asc()).all()



    # Outbound: transactions where the target account is the sender (account_id)
    outbound_txns = db.query(Transaction).filter(
        Transaction.account_id == account_id
    ).order_by(Transaction.timestamp.asc()).all()

    # Distinct entity counts
    distinct_senders = set(t.account_id for t in inbound_txns)
    distinct_recipients = set(t.merchant_id for t in outbound_txns)

    # 2. FIFO Matching for Holding Time and Pass-Through
    # One-to-one matching: each inbound matches at most one outbound, and vice versa.
    # Outbound must occur strictly AFTER inbound.
    matched_pairs = []
    used_outbound_indices = set()

    for in_txn in inbound_txns:
        for j, out_txn in enumerate(outbound_txns):
            if j not in used_outbound_indices and out_txn.timestamp > in_txn.timestamp:
                matched_pairs.append((in_txn, out_txn))
                used_outbound_indices.add(j)
                break

    # Calculations based on matched flow
    matched_in_total = sum(p[0].amount for p in matched_pairs)
    matched_out_total = sum(p[1].amount for p in matched_pairs)
    pass_through_ratio = matched_out_total / matched_in_total if matched_in_total > 0 else 0.0

    holding_times = [(p[1].timestamp - p[0].timestamp).total_seconds() for p in matched_pairs]
    median_hold = statistics.median(holding_times) if holding_times else None

    # 3. Data for ToolResult
    data = {
        "account_id": account_id,
        "inbound_count": len(inbound_txns),
        "outbound_count": len(outbound_txns),
        "distinct_senders": len(distinct_senders),
        "distinct_recipients": len(distinct_recipients),
        "inbound_total": sum(t.amount for t in inbound_txns),
        "outbound_total": sum(t.amount for t in outbound_txns),
        "matched_pair_count": len(matched_pairs),
        "matched_inbound_total": matched_in_total,
        "matched_outbound_total": matched_out_total,
        "pass_through_ratio": pass_through_ratio,
        "holding_times_seconds": holding_times,
        "median_holding_time_seconds": median_hold,
        "matched_pairs": [{"inboundId": p[0].id, "outboundId": p[1].id} for p in matched_pairs],
        "fan_in_transaction_ids": [t.id for t in inbound_txns],
        "fan_out_transaction_ids": [t.id for t in outbound_txns],
    }

    evidence = []

    # Signal: FAN_IN (>= 2 distinct senders)
    if len(distinct_senders) >= 2:
        evidence.append(EvidenceItem(
            id=generate_evidence_id("analyze_mule_behavior", account_id, 0),
            type="FAN_IN",
            pattern="MULE_NETWORK",
            title="High Fan-In",
            claim="Account receives funds from multiple distinct source accounts",
            observed=f"{len(distinct_senders)} distinct senders: {', '.join(list(distinct_senders))}",
            baseline="N/A",
            whyItMatters="Mules often aggregate funds from multiple victims/sources",
            severity=Severity.MEDIUM,
            polarity="SUPPORTING",
            source={
                "table": "transactions",
                "transactionIds": ", ".join([t.id for t in inbound_txns])
            },
            revealedAtStep=0
        ))

    # Signal: FAN_OUT (>= 2 distinct recipients)
    if len(distinct_recipients) >= 2:
        evidence.append(EvidenceItem(
            id=generate_evidence_id("analyze_mule_behavior", account_id, 1),
            type="FAN_OUT",
            pattern="MULE_NETWORK",
            title="High Fan-Out",
            claim="Account distributes funds to multiple distinct recipients",
            observed=f"{len(distinct_recipients)} distinct recipients: {', '.join(list(distinct_recipients))}",
            baseline="N/A",
            whyItMatters="Mules often distribute funds to multiple cash-out points",
            severity=Severity.MEDIUM,
            polarity="SUPPORTING",
            source={
                "table": "transactions",
                "transactionIds": ", ".join([t.id for t in outbound_txns])
            },
            revealedAtStep=0
        ))

    # Signal: PASS_THROUGH (Ratio [0.9, 1.1])
    if 0.9 <= pass_through_ratio <= 1.1 and matched_pairs:
        evidence.append(EvidenceItem(
            id=generate_evidence_id("analyze_mule_behavior", account_id, 2),
            type="PASS_THROUGH",
            pattern="MULE_NETWORK",
            title="High Pass-Through Ratio",
            claim="Matched inbound and outbound funds are nearly equal",
            observed=f"Ratio {pass_through_ratio:.2f} ({matched_out_total}/{matched_in_total})",
            baseline="N/A",
            whyItMatters="Core characteristic of mule accounts",
            severity=Severity.HIGH,
            polarity="SUPPORTING",
            source={
                "table": "transactions",
                "inboundIds": ", ".join([p[0].id for p in matched_pairs]),
                "outboundIds": ", ".join([p[1].id for p in matched_pairs])
            },
            revealedAtStep=0
        ))

    # Signal: SHORT_HOLD (Median <= 600s)
    if median_hold is not None and median_hold <= 600:
        evidence.append(EvidenceItem(
            id=generate_evidence_id("analyze_mule_behavior", account_id, 3),
            type="SHORT_HOLD",
            pattern="MULE_NETWORK",
            title="Rapid Fund Transit",
            claim="Funds are transferred onward shortly after receipt",
            observed=f"Median holding time: {median_hold:.1f}s",
            baseline="N/A",
            whyItMatters="Rapid transit is typical of coordinated mule networks",
            severity=Severity.HIGH,
            polarity="SUPPORTING",
            source={
                "table": "transactions",
                "inboundIds": ", ".join([p[0].id for p in matched_pairs]),
                "outboundIds": ", ".join([p[1].id for p in matched_pairs])
            },
            revealedAtStep=0
        ))

    # Signal: MULTI_HOP (Source -> Account -> Destination)
    if matched_pairs:
        pair = matched_pairs[0]
        in_txn, out_txn = pair

        # Resolve destination based on exclusive semantics:
        # A2A transfers use recipient_account_id; Commercial use merchant_id.
        # If both are set, it's a conflict. If neither, it's missing.
        destination = None
        if out_txn.recipient_account_id and not out_txn.merchant_id:
            destination = out_txn.recipient_account_id
        elif out_txn.merchant_id and not out_txn.recipient_account_id:
            destination = out_txn.merchant_id

        # Only emit evidence if a single, unambiguous destination was resolved
        if destination:
            evidence.append(EvidenceItem(
                id=generate_evidence_id("analyze_mule_behavior", account_id, 4),
                type="MULTI_HOP",
                pattern="MULE_NETWORK",
                title="Network Intermediary Position",
                claim="Account acts as a bridge between source and destination",
                observed=f"Chain: {in_txn.account_id} -> {account_id} -> {destination}",
                baseline="N/A",
                whyItMatters="Mules are intermediaries in a flow chain",
                severity=Severity.MEDIUM,
                polarity="SUPPORTING",
                source={
                    "table": "transactions",
                    "inboundId": in_txn.id,
                    "outboundId": out_txn.id,
                    "sourceAccount": in_txn.account_id,
                    "muleAccount": account_id,
                    "destination": destination
                },
                revealedAtStep=0
            ))

    return ToolResult(tool="analyze_mule_behavior", success=True, data=data, evidence=evidence)
