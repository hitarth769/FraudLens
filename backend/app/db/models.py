from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from app.core.config import settings

engine = create_engine(
    settings.SQLITE_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Many-to-Many Link for Accounts and Devices
account_device = Table(
    "account_device",
    Base.metadata,
    Column("account_id", String, ForeignKey("accounts.id"), primary_key=True),
    Column("device_id", String, ForeignKey("devices.id"), primary_key=True),
)

class Customer(Base):
    __tablename__ = "customers"
    id = Column(String, primary_key=True)
    name = Column(String)
    tenure = Column(String)
    segment = Column(String)
    country = Column(String)
    accounts = relationship("Account", back_populates="customer")

class Account(Base):
    __tablename__ = "accounts"
    id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey("customers.id"))
    status = Column(String)
    created_at = Column(DateTime)
    customer = relationship("Customer", back_populates="accounts")
    cards = relationship("Card", back_populates="account")
    transactions = relationship("Transaction", foreign_keys="[Transaction.account_id]", back_populates="account")
    devices = relationship("Device", secondary=account_device, back_populates="accounts")

class Card(Base):
    __tablename__ = "cards"
    id = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey("accounts.id"))
    last4 = Column(String)
    card_type = Column(String)
    account = relationship("Account", back_populates="cards")

class Device(Base):
    __tablename__ = "devices"
    id = Column(String, primary_key=True)
    model = Column(String)
    os = Column(String)
    first_seen = Column(DateTime)
    accounts = relationship("Account", secondary=account_device, back_populates="devices")

class Merchant(Base):
    __tablename__ = "merchants"
    id = Column(String, primary_key=True)
    name = Column(String)
    category = Column(String)
    country = Column(String)
    risk_profile = Column(String)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey("accounts.id"))
    card_id = Column(String, ForeignKey("cards.id"), nullable=True)
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=True)
    # recipient_account_id = Column(String, ForeignKey("accounts.id"), nullable=True)
    amount = Column(Float)
    currency = Column(String)
    timestamp = Column(DateTime)
    channel = Column(String)
    ip = Column(String)
    location = Column(String)
    status = Column(String) # 'approved', 'declined'
    account = relationship("Account", foreign_keys=[account_id], back_populates="transactions")
    recipient_account = relationship("Account", foreign_keys=[])
    card = relationship("Card")


class LoginEvent(Base):
    __tablename__ = "logins"
    id = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey("accounts.id"))
    device_id = Column(String, ForeignKey("devices.id"))
    ip = Column(String)
    location = Column(String)
    timestamp = Column(DateTime)
    success = Column(Boolean)

class ProfileEvent(Base):
    __tablename__ = "profile_events"
    id = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey("accounts.id"))
    event_type = Column(String) # 'PASSWORD_CHANGE', 'PHONE_CHANGE', 'EMAIL_CHANGE'
    timestamp = Column(DateTime)

class Case(Base):
    __tablename__ = "cases"
    id = Column(String, primary_key=True)
    transaction_id = Column(String, ForeignKey("transactions.id"))
    status = Column(String) # 'AWAITING_DECISION', 'APPROVED', 'OVERRIDDEN'
    created_at = Column(DateTime)

    # Prediction results (updated after investigation)
    risk_score = Column(Integer)
    risk_level = Column(String)
    recommended_action = Column(String)

    # Ground Truth (normalized for evaluation)
    # Stored as a comma-separated string for SQLite simplicity
    ground_truth_patterns = Column(String)
    is_fraud = Column(Boolean)

class CaseDecision(Base):
    __tablename__ = "case_decisions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String, ForeignKey("cases.id"))
    decision = Column(String) # 'APPROVE', 'OVERRIDE'
    override_action = Column(String, nullable=True)
    note = Column(String, nullable=True)
    analyst = Column(String)
    decided_at = Column(DateTime)
