import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.models import Case as CaseModel, Transaction as TransactionModel, SessionLocal, Account as AccountModel, Customer as CustomerModel, LoginEvent
from app.schemas.models import CaseDetail, PatternScore
from app.investigation.context import InvestigationContext
from app.core.config import settings

# Tool imports
from app.tools.get_transaction import get_transaction
from app.tools.get_customer_history import get_customer_history
from app.tools.analyze_velocity import analyze_velocity
from app.tools.analyze_device import analyze_device
from app.tools.investigate_network import investigate_network
from app.tools.analyze_location import analyze_location

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def execute_tool(ctx: InvestigationContext, db: Session, tool_fn, label: str, tool_name: str, **kwargs):
    start = time.time()
    try:
        result = tool_fn(db, **kwargs)
        duration = int((time.time() - start) * 1000)

        if result and result.success:
            # Add evidence and set revealedAtStep
            for ev in result.evidence:
                ev.revealedAtStep = ctx.current_step + 1
                ctx.evidence[ev.id] = ev

            ctx.add_timeline_step(label, tool_name, "completed", result.data.get("summary", "Execution successful"), duration)
            return result
        else:
            error_msg = result.error if result else "Tool returned no result"
            ctx.add_timeline_step(label, tool_name, "failed", error_msg or "Tool failed", duration)
            return result
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        ctx.add_timeline_step(label, tool_name, "failed", f"Error: {str(e)}", duration)
        return None

def run_orchestrator(ctx: InvestigationContext, db: Session):
    # To resolve dependencies between tools, we fetch the core IDs first
    case = db.query(CaseModel).filter(CaseModel.id == ctx.case_id).first()
    txn = db.query(TransactionModel).filter(TransactionModel.id == case.transaction_id).first()
    acc = db.query(AccountModel).filter(AccountModel.id == txn.account_id).first()
    cust = db.query(CustomerModel).filter(CustomerModel.id == acc.customer_id).first()
    txn_ts = txn.timestamp

    # Find current device from most recent login
    last_login = db.query(LoginEvent).filter(LoginEvent.account_id == acc.id).order_by(LoginEvent.timestamp.desc()).first()
    device_id = last_login.device_id if last_login else None

    # --- Phase 5: Evidence Tools ---
    res_txn = execute_tool(ctx, db, get_transaction, "Transaction context retrieved", "get_transaction", transaction_id=txn.id)
    # Passing txn_ts to ensure causal temporal checks in tools
    execute_tool(ctx, db, get_customer_history, "Customer baseline calculated", "get_customer_history", customer_id=cust.id, current_txn_amount=txn.amount, current_txn_id=txn.id, txn_timestamp=txn_ts)
    res_vel = execute_tool(ctx, db, analyze_velocity, "Velocity analysed", "analyze_velocity", account_id=acc.id, current_txn_id=txn.id)
    execute_tool(ctx, db, analyze_device, "Device anomaly detected", "analyze_device", account_id=acc.id, current_device_id=device_id)
    execute_tool(ctx, db, analyze_location, "Location anomaly detected", "analyze_location", account_id=acc.id, current_txn_id=txn.id)

    # Mule behavior analysis
    from app.tools.analyze_mule_behavior import analyze_mule_behavior
    execute_tool(ctx, db, analyze_mule_behavior, "Mule behavior analyzed", "analyze_mule_behavior", account_id=acc.id)

    network_res = execute_tool(ctx, db, investigate_network, "Network expanded", "investigate_network", account_id=acc.id)
    if network_res and network_res.success:
        ctx.graph_nodes = network_res.data.get("nodes", [])
        ctx.graph_edges = network_res.data.get("edges", [])

    # Login Proximity Evidence
    last_login = db.query(LoginEvent).filter(
        LoginEvent.account_id == acc.id,
        LoginEvent.device_id == device_id,
        LoginEvent.timestamp <= txn_ts
    ).order_by(LoginEvent.timestamp.desc()).first()

    if last_login:
        time_diff = (txn_ts - last_login.timestamp).total_seconds()
        if 0 <= time_diff <= 3600: # Within 1 hour AND occurred BEFORE txn
            from app.tools.base import EvidenceItem, generate_evidence_id
            from app.schemas.models import Severity
            ctx.evidence[generate_evidence_id("orchestrator", txn.id, 1)] = EvidenceItem(
                id=generate_evidence_id("orchestrator", txn.id, 1),
                type="LOGIN_PROXIMITY",
                pattern="ACCOUNT_TAKEOVER",
                title="Login proximity detected",
                claim="Login from the transaction device occurred within 1 hour before the transaction",
                observed=f"Login {time_diff/60:.1f} minutes before txn",
                baseline="N/A",
                whyItMatters="Provides context on device usage immediately preceding the transaction",
                severity=Severity.MEDIUM,
                polarity="SUPPORTING",
                source={"table": "logins", "eventId": last_login.id},
                revealedAtStep=ctx.current_step + 1
            )



    # --- Phase 6: Detectors ---
    from app.detectors.card_testing import detect_card_testing
    from app.detectors.account_takeover import detect_account_takeover

    # Prepare data for card testing detector
    detector_data = {
        "velocity": res_vel.data.get("velocity", {}) if res_vel and res_vel.success else {},
        "distinct_cards": res_txn.data.get("distinct_cards", 0) if res_txn and res_txn.success else 0,
        "amount": res_txn.data.get("transaction", {}).get("amount", 0) if res_txn and res_txn.success else 0,
        "decline_count": res_vel.data.get("decline_count", 0) if res_vel and res_vel.success else 0,
        "total_count": res_txn.data.get("total_count", 1) if res_txn and res_txn.success else 1,
    }

    det_res_ct = detect_card_testing(ctx.evidence, detector_data)
    det_res_ato = detect_account_takeover(ctx.evidence, {})
    from app.detectors.mule_network import detect_mule_network
    det_res_mule = detect_mule_network(ctx.evidence, {})

    # Record the detector execution in the timeline
    ctx.add_timeline_step(
        "Fraud patterns evaluated",
        "detectors",
        "suspicious" if (det_res_ct.detected or det_res_ato.detected or det_res_mule.detected) else "completed",
        f"Card Testing: {det_res_ct.score}, ATO: {det_res_ato.score}, Mule: {det_res_mule.score}",
        150 # Estimated duration
    )

    # Add to PatternScores
    ctx.pattern_scores.append(PatternScore(
        pattern=det_res_ct.pattern,
        score=det_res_ct.score,
        confidence="HIGH",
        supporting=len(det_res_ct.signals),
        contradicting=0
    ))
    ctx.pattern_scores.append(PatternScore(
        pattern=det_res_ato.pattern,
        score=det_res_ato.score,
        confidence="HIGH",
        supporting=len(det_res_ato.signals),
        contradicting=0
    ))
    ctx.pattern_scores.append(PatternScore(
        pattern=det_res_mule.pattern,
        score=det_res_mule.score,
        confidence="HIGH",
        supporting=len(det_res_mule.signals),
        contradicting=0
    ))


    # Placeholder for future phases
    ctx.add_timeline_step("Evidence consolidated", "build_evidence", "completed", "Evidence consolidated", 50)
    ctx.add_timeline_step("Risk score calculated", "calculate_risk", "completed", "Risk score pending", 50)
    ctx.add_timeline_step("Recommendation generated", "generate_recommendation", "completed", "Rec pending", 50)

@router.post("/cases/{case_id}/investigate", response_model=CaseDetail)
def investigate(case_id: str, db: Session = Depends(get_db)):
    case = db.query(CaseModel).filter(CaseModel.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    txn = db.query(TransactionModel).filter(TransactionModel.id == case.transaction_id).first()
    acc = db.query(AccountModel).filter(AccountModel.id == txn.account_id).first()
    cust = db.query(CustomerModel).filter(CustomerModel.id == acc.customer_id).first()

    ctx = InvestigationContext(
        case_id=case.id,
        transaction_id=case.transaction_id,
        start_time=datetime.now()
    )

    run_orchestrator(ctx, db)

    return CaseDetail(
        caseId=case.id,
        transactionId=txn.id,
        amount=txn.amount,
        currency=txn.currency,
        customerName=cust.name,
        accountId=acc.id,
        counterparty="Unknown",
        timestamp=txn.timestamp.isoformat(),
        riskScore=case.risk_score or 0,
        riskLevel=case.risk_level or "LOW",
        patterns=[],
        status=case.status,
        recommendedActions=[],
        investigationDurationSec=0.0,
        scenario=case.ground_truth_patterns or "Unknown",
        customer={
            "customerId": cust.id,
            "name": cust.name,
            "tenure": cust.tenure,
            "segment": cust.segment,
            "country": cust.country,
        },
        transaction={
            "channel": txn.channel,
            "card": "Unknown",
            "deviceId": "Unknown",
            "ip": txn.ip,
            "location": txn.location,
        },
        evidence=list(ctx.evidence.values()),
        patternScores=ctx.pattern_scores,
        riskFactors=ctx.risk_factors,
        recommendation={
            "actions": [],
            "summary": "Investigation completed. No fraud detected yet.",
            "rationale": [],
            "humanApprovalRequired": True,
            "narrativeSource": "TEMPLATE"
        },
        humanDecision=None
    )
