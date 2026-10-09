from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.schemas.models import PatternScore, PatternType, Severity

class Signal(BaseModel):
    label: str
    value: str
    points: int
    evidenceIds: List[str]

class DetectorResult(BaseModel):
    pattern: PatternType
    score: int
    detected: bool
    severity: Severity
    signals: List[Signal]

def detect_card_testing(ctx_evidence: Dict[str, Any], ctx_data: Dict[str, Any]) -> DetectorResult:
    """
    Deterministic Card Testing Detector.

    Scoring Logic:
    - High Velocity (> 5 txns in 15m): +30
    - Card Fan-out (> 3 distinct cards): +30
    - Low Value Pattern (amount <= 5): +20
    - High Decline Ratio (> 50% declines): +20

    Max Score: 100
    Threshold for 'detected': 40
    """
    score = 0
    signals = []

    # 1. Velocity Analysis
    velocity_data = ctx_data.get("velocity", {})
    v15 = velocity_data.get("15m", 0)
    if v15 > 5:
        pts = 30
        score += pts
        ev_id = next((id for id, ev in ctx_evidence.items() if ev.type == "VELOCITY_SPIKE"), None)
        signals.append(Signal(
            label="High Velocity Burst",
            value=f"{v15} txns in 15m",
            points=pts,
            evidenceIds=[ev_id] if ev_id else []
        ))

    # 2. Card Fan-out (Distinct cards)
    card_count = ctx_data.get("distinct_cards", 0)
    if card_count > 3:
        pts = 30
        score += pts
        ev_id = next((id for id, ev in ctx_evidence.items() if ev.type == "TRANSACTION_DETAIL"), None)
        signals.append(Signal(
            label="Card Fan-out",
            value=f"{card_count} distinct cards",
            points=pts,
            evidenceIds=[ev_id] if ev_id else []
        ))

    # 3. Low Value Pattern
    txn_amount = ctx_data.get("amount", 100.0)
    if txn_amount <= 5.0:
        pts = 20
        score += pts
        ev_id = next((id for id, ev in ctx_evidence.items() if ev.type == "TRANSACTION_DETAIL"), None)
        signals.append(Signal(
            label="Low Value Attempt",
            value=f"Amount {txn_amount}",
            points=pts,
            evidenceIds=[ev_id] if ev_id else []
        ))

    # 4. Decline Concentration
    decline_count = ctx_data.get("decline_count", 0)
    total_count = ctx_data.get("total_count", 1)
    decline_ratio = decline_count / total_count if total_count > 0 else 0
    if decline_ratio > 0.5:
        pts = 20
        score += pts
        ev_id = next((id for id, ev in ctx_evidence.items() if ev.type == "VELOCITY_SPIKE"), None)
        signals.append(Signal(
            label="High Decline Ratio",
            value=f"{decline_ratio:.1%} declines",
            points=pts,
            evidenceIds=[ev_id] if ev_id else []
        ))

    detected = score >= 40
    severity = Severity.LOW
    if score >= 80: severity = Severity.HIGH
    elif score >= 50: severity = Severity.MEDIUM

    return DetectorResult(
        pattern=PatternType.CARD_TESTING,
        score=score,
        detected=detected,
        severity=severity,
        signals=signals
    )
