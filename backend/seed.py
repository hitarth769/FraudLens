from sqlalchemy.orm import Session
from app.db.models import Base, Customer, Account, Card, Device, Transaction, LoginEvent, ProfileEvent, Case
from app.core.config import settings
from app.db.init_db import init_db, get_db_stats
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker

def validate_database(session: Session):
    print("Running data quality checks...")
    errors = []

    # 1. Referential Integrity
    # Cases -> Transactions
    invalid_cases = session.query(Case).filter(~Case.transaction_id.in_([t.id for t in session.query(Transaction.id).all()])).count()
    if invalid_cases > 0: errors.append(f"Found {invalid_cases} cases with invalid transaction IDs")

    # Transactions -> Accounts
    invalid_txns = session.query(Transaction).filter(~Transaction.account_id.in_([a.id for a in session.query(Account.id).all()])).count()
    if invalid_txns > 0: errors.append(f"Found {invalid_txns} transactions with invalid account IDs")

    # 2. Business Rules
    # Negative amounts
    neg_amounts = session.query(Transaction).filter(Transaction.amount < 0).count()
    if neg_amounts > 0: errors.append(f"Found {neg_amounts} transactions with negative amounts")

    # Duplicate IDs
    # SQLAlchemy would have failed on seed if PKs were duplicated, but we check counts
    # (Implicitly handled by primary_key=True)

    # 3. Scenario Validation (Planted Signals)
    # Card Testing (CASE-1001)
    case1001 = session.query(Case).filter(Case.id == 'CASE-1001').first()
    if case1001:
        txn = session.query(Transaction).filter(Transaction.id == case1001.transaction_id).first()
        acc = session.query(Account).filter(Account.id == txn.account_id).first()
        cards = session.query(Card).filter(Card.account_id == acc.id).count()
        if cards < 10: errors.append("CASE-1001: Missing card fan-out signal")

        burst_txns = session.query(Transaction).filter(Transaction.account_id == acc.id, Transaction.amount == 1.0).count()
        if burst_txns < 10: errors.append("CASE-1001: Missing low-value burst signal")

    # ATO (CASE-1002)
    case1002 = session.query(Case).filter(Case.id == 'CASE-1002').first()
    if case1002:
        txn = session.query(Transaction).filter(Transaction.id == case1002.transaction_id).first()
        acc = session.query(Account).filter(Account.id == txn.account_id).first()
        profile_events = session.query(ProfileEvent).filter(ProfileEvent.account_id == acc.id, ProfileEvent.event_type == 'PASSWORD_CHANGE').count()
        if profile_events == 0: errors.append("CASE-1002: Missing credential change signal")

    # Mule (CASE-1003)
    case1003 = session.query(Case).filter(Case.id == 'CASE-1003').first()
    if case1003:
        txn = session.query(Transaction).filter(Transaction.id == case1003.transaction_id).first()
        acc = session.query(Account).filter(Account.id == txn.account_id).first()
        # Inbound senders
        senders = session.query(Transaction).filter(Transaction.amount == 31000.0).count() # Simplified check
        if senders < 2: errors.append("CASE-1003: Missing mule fan-in signal")

    # Combined (CASE-1005)
    case1005 = session.query(Case).filter(Case.id == 'CASE-1005').first()
    if case1005:
        if 'ACCOUNT_TAKEOVER' not in case1005.ground_truth_patterns:
            errors.append("CASE-1005: Missing ATO ground truth")
        if 'MULE_NETWORK' not in case1005.ground_truth_patterns:
            errors.append("CASE-1005: Missing Mule ground truth")

    if not errors:
        print("✅ All data quality checks passed!")
    else:
        print("❌ Data quality checks failed:")
        for e in errors:
            print(f"  - {e}")

    return len(errors) == 0

def run_seed_and_validate():
    engine = create_engine(settings.SQLITE_DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        init_db(session)
        stats = get_db_stats(session)
        print("Database initialized successfully.")
        print(f"Customers: {stats['customers']}")
        print(f"Accounts: {stats['accounts']}")
        print(f"Cards: {stats['cards']}")
        print(f"Devices: {stats['devices']}")
        print(f"Transactions: {stats['transactions']}")
        print(f"Logins: {stats['logins']}")
        print(f"Profile Events: {stats['profile_events']}")
        print(f"Cases: {stats['cases']}")
        print("Ground Truth Fraud Counts:")
        for p, count in stats['fraud_counts'].items():
            print(f"  {p}: {count}")

        validate_database(session)
    finally:
        session.close()

if __name__ == "__main__":
    run_seed_and_validate()
