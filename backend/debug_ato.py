from sqlalchemy.orm import sessionmaker
from app.db.models import SessionLocal, Case, Transaction, Account, Customer, LoginEvent, ProfileEvent
from app.investigation.context import InvestigationContext
from app.api.investigate import run_orchestrator
from datetime import datetime

def debug_ato():
    db = SessionLocal()
    try:
        case = db.query(Case).filter(Case.id == "CASE-1002").first()
        if not case:
            print("CASE-1002 not found")
            return

        ctx = InvestigationContext(case_id=case.id, transaction_id=case.transaction_id, start_time=datetime.now())
        run_orchestrator(ctx, db)

        print(f"Case: {case.id}")
        print(f"Evidence items found: {len(ctx.evidence)}")
        for ev_id, ev in ctx.evidence.items():
            print(f"ID: {ev_id} | Type: {ev.type} | Title: {ev.title} | Observed: {ev.observed}")
        
        for ps in ctx.pattern_scores:
            if ps.pattern == "ACCOUNT_TAKEOVER":
                print(f"\nATO Score: {ps.score}, Supporting: {ps.supporting}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_ato()
