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

def detect_account_takeover(ctx_evidence: Dict[str, Any], ctx_data: Dict[str, Any]) -> DetectorResult:
    """
    Deterministic Account Takeover (ATO) Detector.

    Scoring Logic:
    - New Device (DEVICE_NOVELTY): +30
    - Credential Change (CREDENTIAL_CHANGE): +30
    - Geo Anomaly (GEO_ANOMALY): +20
    - Value Anomaly (VALUE_ANOMALY): +20
    - Login Proximity (LOGIN_PROXIMITY): +10

    Decision Rule:
    - Detected if (score >= 50) AND has_compromise_signal
    - Compromise signals: CREDENTIAL_CHANGE, GEO_ANOMALY, VALUE_ANOMALY
    """
    score = 0
    signals = []
    has_compromise_signal = False

    # 1. New Device
    dev_ev = next((ev for ev in ctx_evidence.values() if ev.type == "DEVICE_NOVELTY"), None)
    if dev_ev:
        pts = 30
        score += pts
        signals.append(Signal(
            label="New Device",
            value=dev_ev.observed,
            points=pts,
            evidenceIds=[dev_ev.id]
        ))

    # 2. Credential Change
    cred_ev = next((ev for ev in ctx_evidence.values() if ev.type == "CREDENTIAL_CHANGE"), None)
    if cred_ev:
        pts = 30
        score += pts
        has_compromise_signal = True
        signals.append(Signal(
            label="Recent Credential Change",
            value=cred_ev.observed,
            points=pts,
            evidenceIds=[cred_ev.id]
        ))

    # 3. Geo Anomaly
    geo_ev = next((ev for ev in ctx_evidence.values() if ev.type == "GEO_ANOMALY"), None)
    if geo_ev:
        pts = 20
        score += pts
        has_compromise_signal = True
        signals.append(Signal(
            label="Geographic Anomaly",
            value=geo_ev.observed,
            points=pts,
            evidenceIds=[geo_ev.id]
        ))

    # 4. Value Anomaly
    val_ev = next((ev for ev in ctx_evidence.values() if ev.type == "VALUE_ANOMALY"), None)
    if val_ev:
        pts = 20
        score += pts
        has_compromise_signal = True
        signals.append(Signal(
            label="Transaction Value Anomaly",
            value=val_ev.observed,
            points=pts,
            evidenceIds=[val_ev.id]
        ))

    # 5. Login Proximity
    prox_ev = next((ev for ev in ctx_evidence.values() if ev.type == "LOGIN_PROXIMITY"), None)
    if prox_ev:
        pts = 10
        score += pts
        signals.append(Signal(
            label="Login Proximity",
            value=prox_ev.observed,
            points=pts,
            evidenceIds=[prox_ev.id]
        ))

    # Final Decision Logic
    detected = (score >= 50) and has_compromise_signal

    # Cap score at 100
    final_score = min(score, 100)

    severity = Severity.LOW
    if final_score >= 80: severity = Severity.HIGH
    elif final_score >= 50: severity = Severity.MEDIUM

    return DetectorResult(
        pattern=PatternType.ACCOUNT_TAKEOVER,
        score=final_score,
        detected=detected,
        severity=severity,
        signals=signals
    )
