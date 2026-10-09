from typing import List, Dict, Any, Tuple
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

def detect_mule_network(ctx_evidence: Dict[str, Any], ctx_data: Dict[str, Any]) -> DetectorResult:
    """
    Deterministic Mule Network Detector.

    Scoring Logic (Approved Phase 8 Contract):
    - FAN_IN: +20
    - FAN_OUT: +20
    - PASS_THROUGH: +30
    - SHORT_HOLD: +30
    - MULTI_HOP: +20

    Decision Rule:
    - Detected if final_score >= 70
    - Score capped at 100
    """
    score = 0
    signals = []

    # Signal Mapping: (Evidence Type, Points, Label)
    SIGNAL_MAP = {
        "FAN_IN": (20, "High Fan-In"),
        "FAN_OUT": (20, "High Fan-Out"),
        "PASS_THROUGH": (30, "High Pass-Through Ratio"),
        "SHORT_HOLD": (30, "Rapid Fund Transit"),
        "MULTI_HOP": (20, "Network Intermediary Position"),
    }

    # track processed types to ensure each signal contributes at most once
    processed_types = set()

    for ev in ctx_evidence.values():
        if ev.type in SIGNAL_MAP and ev.type not in processed_types:
            points, label = SIGNAL_MAP[ev.type]
            score += points

            signals.append(Signal(
                label=label,
                value=ev.observed,
                points=points,
                evidenceIds=[ev.id]
            ))
            processed_types.add(ev.type)

    # Cap score at 100
    final_score = min(score, 100)

    # Decision Rule: detected iff final score >= 70
    detected = (final_score >= 70)

    # Assign severity based on score
    severity = Severity.LOW
    if final_score >= 80:
        severity = Severity.HIGH
    elif final_score >= 50:
        severity = Severity.MEDIUM

    return DetectorResult(
        pattern=PatternType.MULE_NETWORK,
        score=final_score,
        detected=detected,
        severity=severity,
        signals=signals
    )
