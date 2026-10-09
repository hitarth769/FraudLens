import random
from datetime import datetime, timedelta
import uuid
from typing import List, Tuple, Any
from sqlalchemy.orm import Session
from app.db.models import (
    Customer, Account, Card, Device, Merchant, Transaction,
    LoginEvent, ProfileEvent, Case, CaseDecision
)
from app.core.config import settings

def generate_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:6].upper()}"

class DataGenerator:
    def __init__(self, session: Session):
        self.session = session
        random.seed(settings.RANDOM_SEED)

        # Constants
        self.currencies = ["INR", "USD", "EUR", "GBP"]
        self.segments = ["Retail", "Affluent", "Corporate", "Student"]
        self.countries = ["IN", "US", "GB", "SG", "DE"]
        self.channels = ["Web checkout", "Mobile App", "Card present", "Bank transfer"]
        self.merchant_categories = ["Digital goods", "Gift cards", "Retail", "Travel", "Food"]

    def create_customer(self, name: str = None, country: str = None, segment: str = None) -> Customer:
        cust = Customer(
            id=generate_id("C"),
            name=name or f"Customer_{random.randint(1, 10000)}",
            tenure=f"{random.uniform(0.1, 10):.1f} years",
            segment=segment or random.choice(self.segments),
            country=country or random.choice(self.countries)
        )
        self.session.add(cust)
        return cust

    def create_account(self, customer: Customer, status: str = "Active") -> Account:
        acc = Account(
            id=generate_id("A"),
            customer_id=customer.id,
            status=status,
            created_at=datetime.now() - timedelta(days=random.randint(1, 365*5))
        )
        self.session.add(acc)
        return acc

    def create_card(self, account: Account) -> Card:
        card = Card(
            id=generate_id("K"),
            account_id=account.id,
            last4=str(random.randint(1000, 9999)),
            card_type=random.choice(["Visa", "Mastercard", "Amex"])
        )
        self.session.add(card)
        return card

    def create_device(self, model: str = None) -> Device:
        dev = Device(
            id=generate_id("D"),
            model=model or random.choice(["iPhone 14", "Samsung S23", "Windows Chrome", "MacBook Pro"]),
            os=random.choice(["iOS", "Android", "Windows", "macOS"]),
            first_seen=datetime.now() - timedelta(days=random.randint(0, 1000))
        )
        self.session.add(dev)
        return dev

    def create_merchant(self, name: str = None, category: str = None) -> Merchant:
        merch = Merchant(
            id=generate_id("M"),
            name=name or f"Merchant_{random.randint(1, 1000)}",
            category=category or random.choice(self.merchant_categories),
            country=random.choice(self.countries),
            risk_profile=random.choice(["Low", "Medium", "High"])
        )
        self.session.add(merch)
        return merch

    def create_transaction(self, account: Account, recipient: Any, amount: float,
                              timestamp: datetime = None, channel: str = None,
                              ip: str = None, location: str = None, status: str = "approved",
                              card: Card = None) -> Transaction:
        merchant_id = None
        recipient_account_id = None

        if isinstance(recipient, Account):
            recipient_account_id = recipient.id
        elif isinstance(recipient, Merchant):
            merchant_id = recipient.id
        elif isinstance(recipient, str):
            # Explicitly verify ID type instead of using heuristics
            is_acc = self.session.query(Account).filter(Account.id == recipient).first()
            is_merch = self.session.query(Merchant).filter(Merchant.id == recipient).first()

            if is_acc and not is_merch:
                recipient_account_id = recipient
            elif is_merch and not is_acc:
                merchant_id = recipient
            else:
                raise ValueError(f"Ambiguous or unknown recipient ID: {recipient}")
        else:
            raise TypeError("Recipient must be an Account, Merchant, or valid ID string")

        txn = Transaction(
            id=generate_id("TXN"),
            account_id=account.id,
            card_id=card.id if card else None,
            merchant_id=merchant_id,
            recipient_account_id=recipient_account_id,
            amount=amount,
            currency=random.choice(self.currencies),
            timestamp=timestamp or datetime.now(),
            channel=channel or random.choice(self.channels),
            ip=ip or f"I-{random.randint(1000, 9999)}",
            location=location or "Unknown",
            status=status
        )
        self.session.add(txn)
        return txn


    def create_login(self, account: Account, device: Device, timestamp: datetime = None,
                     ip: str = None, location: str = None, success: bool = True) -> LoginEvent:
        login = LoginEvent(
            id=generate_id("L"),
            account_id=account.id,
            device_id=device.id,
            ip=ip or f"I-{random.randint(1000, 9999)}",
            location=location or "Unknown",
            timestamp=timestamp or datetime.now(),
            success=success
        )
        self.session.add(login)
        return login

    def create_profile_event(self, account: Account, event_type: str, timestamp: datetime = None) -> ProfileEvent:
        event = ProfileEvent(
            id=generate_id("PE"),
            account_id=account.id,
            event_type=event_type,
            timestamp=timestamp or datetime.now(),
        )
        self.session.add(event)
        return event

    def generate_population(self, n_customers=500):
        merchants = [self.create_merchant() for _ in range(50)]
        devices = [self.create_device() for _ in range(200)]

        for _ in range(n_customers):
            cust = self.create_customer()
            acc = self.create_account(cust)
            card = self.create_card(acc)
            acc.devices.append(random.choice(devices))

            for _ in range(random.randint(1, 10)):
                self.create_transaction(acc, random.choice(merchants),
                                      random.uniform(100, 5000),
                                      timestamp=datetime.now() - timedelta(days=random.randint(0, 30)),
                                      card=card)
                self.create_login(acc, random.choice(devices),
                                    timestamp=datetime.now() - timedelta(days=random.randint(0, 30)))

    def generate_fraud_scenario(self, scenario_type: str, case_id: str):
        cust = self.create_customer()
        acc = self.create_account(cust)

        if scenario_type == 'CARD_TESTING':
            dev = self.create_device("Android 13")
            acc.devices.append(dev)
            merch = self.create_merchant("Streamly Digital", "Digital goods")

            # Exactly 14 distinct cards for the burst
            burst_cards = [self.create_card(acc) for _ in range(14)]

            # Total 29 transactions in the burst
            # 12 declined, 17 approved
            statuses = ['declined'] * 12 + ['approved'] * 17
            random.shuffle(statuses)

            last_txn = None
            for i in range(29):
                # Ensure we use all 14 cards at least once
                card = burst_cards[i] if i < 14 else random.choice(burst_cards)
                is_last = (i == 28)
                # FIX: Ensure all transactions fall within 15m of the last one
                # By anchoring them to a fixed base time
                base_time = datetime.now()
                ts = base_time - timedelta(seconds=random.randint(0, 899)) if not is_last else base_time

                last_txn = self.create_transaction(acc, merch, 1.0,
                                                  timestamp=ts,
                                                  status=statuses[i],
                                                  card=card)

            if last_txn:
                self.create_case(last_txn, 'CARD_TESTING', case_id)
            else:
                txn = self.session.query(Transaction).order_by(Transaction.timestamp.desc()).first()
                self.create_case(txn, 'CARD_TESTING', case_id)

        elif scenario_type == 'ACCOUNT_TAKEOVER':
            dev_old = self.create_device("iPhone 14")
            acc.devices.append(dev_old)
            # Add historical activity to ensure a baseline exists
            for _ in range(5):
                self.create_transaction(acc, self.create_merchant(), random.uniform(100, 1000),
                                        location="Mumbai, IN", timestamp=datetime.now() - timedelta(days=random.randint(1, 30)))
                self.create_login(acc, dev_old, location="Mumbai, IN", timestamp=datetime.now() - timedelta(days=random.randint(1, 30)))

            self.create_login(acc, dev_old, timestamp=datetime.now() - timedelta(days=10), location="Mumbai, IN")
            dev_new = self.create_device("Windows Chrome")
            acc.devices.append(dev_new)
            self.create_profile_event(acc, "PASSWORD_CHANGE", timestamp=datetime.now() - timedelta(minutes=10))
            self.create_login(acc, dev_new, ip="I-8812", location="Singapore, SG",
                                timestamp=datetime.now() - timedelta(minutes=5))
            merch = self.create_merchant("GiftCardHub", "Gift cards")
            txn = self.create_transaction(acc, merch, 72500.0, location="Singapore, SG")
            self.create_case(txn, ['ACCOUNT_TAKEOVER'], case_id)

        elif scenario_type == 'MULE_NETWORK':
            acc = self.create_account(cust, status="Active")
            acc.id = generate_id("A")
            for _ in range(3):
                sender_cust = self.create_customer()
                sender_acc = self.create_account(sender_cust)
                # Corrected: Send money TO the mule account 'acc'
                self.create_transaction(sender_acc, acc, 31000.0,
                                        timestamp=datetime.now() - timedelta(minutes=random.randint(1, 10)))
            recipient_acc = self.create_account(self.create_customer())
            self.create_transaction(acc, self.create_merchant(), 31000.0,
                                    timestamp=datetime.now() - timedelta(minutes=5))
            txn = self.create_transaction(acc, self.create_merchant(), 31000.0)
            self.create_case(txn, ['MULE_NETWORK'], case_id)

        elif scenario_type == 'BENIGN_ANOMALY':
            dev_new = self.create_device("iPad (new)")
            acc.devices.append(dev_new)
            self.create_login(acc, dev_new, timestamp=datetime.now(), success=True)
            merch = self.create_merchant("Heathrow Duty Free", "Retail")
            txn = self.create_transaction(acc, merch, 21400.0, location="London, GB")
            self.create_case(txn, ['BENIGN_ANOMALY'], case_id)

        elif scenario_type == 'COMBINED_FRAUD':
            dev_new = self.create_device("Windows Chrome")
            acc.devices.append(dev_new)
            self.create_profile_event(acc, "PASSWORD_CHANGE", timestamp=datetime.now() - timedelta(minutes=15))
            self.create_login(acc, dev_new, ip="I-4471", location="Lagos, NG")

            recipient_acc = self.create_account(self.create_customer())
            self.create_transaction(acc, self.create_merchant(), 48000.0)

            txn = self.create_transaction(acc, self.create_merchant(), 48000.0)
            self.create_case(txn, ['ACCOUNT_TAKEOVER', 'MULE_NETWORK', 'BEHAVIOURAL_ANOMALY'], case_id)

    def create_case(self, txn: Transaction, patterns: List[str], case_id: str = None):
        case = Case(
            id=case_id or generate_id("CASE"),
            transaction_id=txn.id,
            status="AWAITING_DECISION",
            created_at=datetime.now(),
            ground_truth_patterns=",".join(patterns),
            is_fraud=any(p != 'NORMAL' and p != 'BENIGN_ANOMALY' for p in patterns)
        )
        self.session.add(case)
        return case
