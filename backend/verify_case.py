from sqlalchemy.orm import sessionmaker
from app.db.models import SessionLocal, Case, Transaction, Account, Card
from datetime import datetime, timedelta

def verify():
    db = SessionLocal()
    try:
        case = db.query(Case).filter(Case.id == "CASE-1001").first()
        if not case:
            print("CASE-1001 not found")
            return

        txn_trigger = db.query(Transaction).filter(Transaction.id == case.transaction_id).first()
        account_id = txn_trigger.account_id
        
        # Define the window: transactions for this account in the 15 mins preceding the trigger
        window_start = txn_trigger.timestamp - timedelta(minutes=15)
        window_end = txn_trigger.timestamp
        
        burst = db.query(Transaction).filter(
            Transaction.account_id == account_id,
            Transaction.timestamp >= window_start,
            Transaction.timestamp <= window_end
        ).all()
        
        total = len(burst)
        distinct_cards = len(set(t.card_id for t in burst if t.card_id))
        approved = len([t for t in burst if t.status == "approved"])
        declined = len([t for t in burst if t.status == "declined"])
        
        print(f"Total transactions: {total}")
        print(f"Distinct cards: {distinct_cards}")
        print(f"Approved: {approved}")
        print(f"Declined: {declined}")
        print("\nTransaction Details:")
        for t in burst:
            print(f"ID: {t.id} | Card: {t.card_id} | Status: {t.status} | Time: {t.timestamp}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify()
