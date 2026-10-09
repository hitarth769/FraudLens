from sqlalchemy.orm import sessionmaker
from app.db.models import SessionLocal, Case, Transaction, Account, LoginEvent
from app.api.investigate import run_orchestrator
from app.investigation.context import InvestigationContext
from datetime import datetime

def debug_device():
    db = SessionLocal()
    try:
        case = db.query(Case).filter(Case.id == "CASE-1002").first()
        txn = db.query(Transaction).filter(Transaction.id == case.transaction_id).first()
        acc = db.query(Account).filter(Account.id == txn.account_id).first()
        
        # The orchestrator finds the device from the MOST RECENT login
        last_login = db.query(LoginEvent).filter(LoginEvent.account_id == acc.id).order_by(LoginEvent.timestamp.desc()).first()
        print(f"Last login device: {last_login.device_id}")
        
        # Check if this device has any other logins
        count = db.query(LoginEvent).filter(LoginEvent.account_id == acc.id, LoginEvent.device_id == last_login.device_id).count()
        print(f"Count of logins for this device: {count}")
        
    finally:
        db.close()

if __name__ == "__main__":
    debug_device()
