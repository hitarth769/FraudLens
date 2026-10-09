from sqlalchemy.orm import Session
from app.db.models import Base
from app.core.config import settings
from app.db.models import Customer, Account, Card, Device, Transaction, LoginEvent, ProfileEvent, Case
from app.data.generator import DataGenerator

def get_db_stats(session: Session):
    return {
        "customers": session.query(Customer).count(),
        "accounts": session.query(Account).count(),
        "cards": session.query(Card).count(),
        "devices": session.query(Device).count(),
        "transactions": session.query(Transaction).count(),
        "logins": session.query(LoginEvent).count(),
        "profile_events": session.query(ProfileEvent).count(),
        "cases": session.query(Case).count(),
        "fraud_counts": {
            p: session.query(Case).filter(Case.ground_truth_patterns.contains(p)).count()
            for p in ['CARD_TESTING', 'ACCOUNT_TAKEOVER', 'MULE_NETWORK', 'COMBINED_FRAUD', 'BENIGN_ANOMALY']
        }
    }

def init_db(session: Session):
    # Clear existing data
    Base.metadata.drop_all(bind=session.get_bind())
    Base.metadata.create_all(bind=session.get_bind())

    gen = DataGenerator(session)

    # 1. Generate general population
    gen.generate_population(n_customers=200)

    # 2. Generate the required demo cases
    gen.generate_fraud_scenario('CARD_TESTING', 'CASE-1001')
    gen.generate_fraud_scenario('ACCOUNT_TAKEOVER', 'CASE-1002')
    gen.generate_fraud_scenario('MULE_NETWORK', 'CASE-1003')
    gen.generate_fraud_scenario('BENIGN_ANOMALY', 'CASE-1004')
    gen.generate_fraud_scenario('COMBINED_FRAUD', 'CASE-1005')

    # 3. Generate additional fraud for evaluation (10 of each)
    for p in ['CARD_TESTING', 'ACCOUNT_TAKEOVER', 'MULE_NETWORK', 'COMBINED_FRAUD']:
        for i in range(10):
            gen.generate_fraud_scenario(p, None)

    # 4. Generate additional benign look-alikes
    for i in range(10):
        gen.generate_fraud_scenario('BENIGN_ANOMALY', None)

    session.commit()

    return {
        "customers": session.query(Customer).count(),
        "accounts": session.query(Account).count(),
        "cards": session.query(Card).count(),
        "devices": session.query(Device).count(),
        "transactions": session.query(Transaction).count(),
        "logins": session.query(LoginEvent).count(),
        "profile_events": session.query(ProfileEvent).count(),
        "cases": session.query(Case).count(),
        "fraud_counts": {
            p: session.query(Case).filter(Case.ground_truth_patterns.contains(p)).count()
            for p in ['CARD_TESTING', 'ACCOUNT_TAKEOVER', 'MULE_NETWORK', 'COMBINED_FRAUD', 'BENIGN_ANOMALY']
        }
    }
