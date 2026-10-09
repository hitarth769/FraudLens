from sqlalchemy.orm import sessionmaker
from app.db.models import Base, engine, SessionLocal
from app.data.generator import DataGenerator

def seed():
    # Clear existing data
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        gen = DataGenerator(db)
        print("Generating population...")
        gen.generate_population(n_customers=100)
        
        print("Generating fraud scenarios...")
        gen.generate_fraud_scenario('CARD_TESTING', 'CASE-1001')
        gen.generate_fraud_scenario('ACCOUNT_TAKEOVER', 'CASE-1002')
        gen.generate_fraud_scenario('MULE_NETWORK', 'CASE-1003')
        gen.generate_fraud_scenario('BENIGN_ANOMALY', 'CASE-1004')
        gen.generate_fraud_scenario('COMBINED_FRAUD', 'CASE-1005')
        
        db.commit()
        print("Database seeded successfully.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
