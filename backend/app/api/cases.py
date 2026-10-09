from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.models import Case as CaseModel, Transaction as TransactionModel, Customer as CustomerModel, Account as AccountModel, Card as CardModel, SessionLocal
from app.schemas.models import CaseSummary, CaseDetail
from app.core.config import settings

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[CaseSummary])
def list_cases(db: Session = Depends(get_db)):
    cases = db.query(CaseModel).all()
    summaries = []
    for c in cases:
        txn = db.query(TransactionModel).filter(TransactionModel.id == c.transaction_id).first()
        if not txn: continue
        acc = db.query(AccountModel).filter(AccountModel.id == txn.account_id).first()
        if not acc: continue
        cust = db.query(CustomerModel).filter(CustomerModel.id == acc.customer_id).first()
        if not cust: continue

        summaries.append(CaseSummary(
            caseId=c.id,
            transactionId=txn.id,
            amount=txn.amount,
            currency=txn.currency,
            customerName=cust.name,
            accountId=acc.id,
            counterparty="Unknown",
            timestamp=txn.timestamp.isoformat(),
            riskScore=c.risk_score or 0,
            riskLevel=c.risk_level or "LOW",
            patterns=[],
            status=c.status,
            recommendedActions=[],
            investigationDurationSec=0.0,
            scenario=c.ground_truth_patterns or "Unknown"
        ))
    return summaries

@router.get("/{case_id}", response_model=CaseDetail)
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = db.query(CaseModel).filter(CaseModel.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    txn = db.query(TransactionModel).filter(TransactionModel.id == case.transaction_id).first()
    if not txn:
        raise HTTPException(status_code=500, detail="Case transaction not found")

    acc = db.query(AccountModel).filter(AccountModel.id == txn.account_id).first()
    if not acc:
        raise HTTPException(status_code=500, detail="Transaction account not found")

    cust = db.query(CustomerModel).filter(CustomerModel.id == acc.customer_id).first()
    if not cust:
        raise HTTPException(status_code=500, detail="Account customer not found")

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
        evidence=[],
        patternScores=[],
        riskFactors=[],
        recommendation={
            "actions": [],
            "summary": "No investigation performed yet.",
            "rationale": [],
            "humanApprovalRequired": True,
            "narrativeSource": "TEMPLATE"
        },
        humanDecision=None
    )
