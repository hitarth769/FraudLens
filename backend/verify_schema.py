from sqlalchemy.orm import sessionmaker
from app.db.models import SessionLocal, Case, Transaction, Account, Card

def verify_schema():
    db = SessionLocal()
    try:
        case = db.query(Case).filter(Case.id == "CASE-1001").first()
        if not case:
            print("CASE-1001 not found")
            return

        txn_trigger = db.query(Transaction).filter(Transaction.id == case.transaction_id).first()
        account_id = txn_trigger.account_id
        
        # Check all transactions in the burst
        window_start = txn_trigger.timestamp - timedelta(minutes=15)
        window_end = txn_trigger.timestamp
        
        burst = db.query(Transaction).filter(
            Transaction.account_id == account_id,
            Transaction.timestamp >= window_start,
            Transaction.timestamp <= window_end
        ).all()
        
        all_have_card_id = True
        all_cards_belong_to_acc = True
        
        for t in burst:
            if t.card_id is None:
                all_have_card_id = False
                print(f"Transaction {t.id} has NULL card_id")
            else:
                card = db.query(Card).filter(Card.id == t.card_id).first()
                if not card or card.account_id != account_id:
                    all_cards_belong_to_acc = False
                    print(f"Card {t.card_id} does not belong to account {account_id}")
        
        print(f"All transactions have card_id: {all_have_card_id}")
        print(f"All cards belong to account: {all_cards_belong_to_acc}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

from datetime import timedelta
if __name__ == "__main__":
    verify_schema()
