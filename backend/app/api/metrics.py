from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.models import SessionLocal
from app.evaluation.pipeline import EvaluationPipeline
from typing import Dict, Any

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=None)
def get_metrics(db: Session = Depends(get_db)):
    # In a production system, we would load cached results from a file/DB.
    # For the demo, we run the evaluation on the fly for the current database state.
    pipeline = EvaluationPipeline(db)
    results = pipeline.run_evaluation()

    # We must enrich the results with the current queue distribution
    # as required by the frontend MetricsView.
    from app.db.models import Case, Transaction, Account
    from app.api.cases import list_cases

    # Reuse existing case list logic to get current distributions
    cases_data = list_cases(db)

    risk_dist = {}
    pattern_dist = {}

    for c in cases_data:
        # Risk Level Distribution
        level = c.riskLevel if c.riskLevel else "LOW"
        risk_dist[level] = risk_dist.get(level, 0) + 1

        # Pattern Distribution (top pattern)
        if c.patterns:
            p = c.patterns[0]
            pattern_dist[p] = pattern_dist.get(p, 0) + 1

    # Format for frontend
    formatted_risk = [
        {"level": l, "count": risk_dist.get(l, 0)}
        for l in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    ]
    formatted_patterns = [
        {"pattern": p, "count": v}
        for p, v in pattern_dist.items()
    ]

    results["riskDistribution"] = formatted_risk
    results["patternDistribution"] = formatted_patterns

    return results

@router.post("/run")
def trigger_evaluation(db: Session = Depends(get_db)):
    pipeline = EvaluationPipeline(db)
    results = pipeline.run_evaluation()
    return {"status": "success", "metrics": results}
