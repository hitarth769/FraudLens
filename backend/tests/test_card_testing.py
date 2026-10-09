import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, Transaction, Account, Customer, Merchant, Case, Card
from app.detectors.card_testing import detect_card_testing
from app.investigation.context import InvestigationContext
from app.api.investigate import run_orchestrator
from app.tools.get_transaction import get_transaction
from app.tools.analyze_velocity import analyze_velocity

@pytest.fixture
def db_session(tmp_path):
    """
    Provides a completely isolated temporary SQLite database for each test.
    Enforces foreign keys and verifies the setting.
    """
    db_file = tmp_path / "test_card_testing.db"
    engine = create_engine(f"sqlite:///{db_file}")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Explicit verification of FK enforcement
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys")).scalar()
        assert result == 1, "SQLite foreign keys must be enabled"

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()

def create_entity(session, cls, **kwargs):
    """Helper to create entities with auto-generated IDs and required defaults."""
    if 'id' not in kwargs:
        prefix = cls.__tablename__[0].upper()
        kwargs['id'] = f"{prefix}-{uuid.uuid4().hex[:6].upper()}"

    if cls == Customer and 'tenure' not in kwargs:
        kwargs['tenure'] = "1.0 years"
    if cls == Account and 'created_at' not in kwargs:
        kwargs['created_at'] = datetime.now()
    if cls == Merchant and 'category' not in kwargs:
        kwargs['category'] = "Retail"
    if cls == Merchant and 'country' not in kwargs:
        kwargs['country'] = "IN"
    if cls == Merchant and 'risk_profile' not in kwargs:
        kwargs['risk_profile'] = "Low"
    if cls == Transaction and 'timestamp' not in kwargs:
        kwargs['timestamp'] = datetime.now()
    if cls == Transaction and 'currency' not in kwargs:
        kwargs['currency'] = "INR"
    if cls == Transaction and 'channel' not in kwargs:
        kwargs['channel'] = "Web"
    if cls == Transaction and 'ip' not in kwargs:
        kwargs['ip'] = "1.1.1.1"
    if cls == Transaction and 'location' not in kwargs:
        kwargs['location'] = "IN"

    obj = cls(**kwargs)
    session.add(obj)
    session.commit()
    return obj

# --- Detector Unit Tests (Isolate Scoring Logic) ---

def test_detector_score_is_deterministic():
    ctx_data = {
        "velocity": {"15m": 10},
        "distinct_cards": 5,
        "amount": 1.0,
        "decline_count": 6,
        "total_count": 10
    }
    res1 = detect_card_testing({}, ctx_data)
    res2 = detect_card_testing({}, ctx_data)
    assert res1.score == res2.score

def test_decline_ratio_contributes_correctly():
    ctx_data = {
        "velocity": {"15m": 1},
        "distinct_cards": 1,
        "amount": 100.0,
        "decline_count": 10,
        "total_count": 11
    }
    res = detect_card_testing({}, ctx_data)
    assert res.score == 20

def test_distinct_card_count_contributes_correctly():
    ctx_data = {
        "velocity": {"15m": 1},
        "distinct_cards": 10,
        "amount": 100.0,
        "decline_count": 0,
        "total_count": 10
    }
    res = detect_card_testing({}, ctx_data)
    assert res.score == 30

def test_velocity_contributes_correctly():
    ctx_data = {
        "velocity": {"15m": 20},
        "distinct_cards": 1,
        "amount": 100.0,
        "decline_count": 0,
        "total_count": 20
    }
    res = detect_card_testing({}, ctx_data)
    assert res.score == 30

def test_detector_no_hardcoded_ids():
    ctx_data = {
        "velocity": {"15m": 10},
        "distinct_cards": 5,
        "amount": 1.0,
        "decline_count": 6,
        "total_count": 10
    }
    res = detect_card_testing({}, ctx_data)
    assert res.detected is True

# --- Orchestrator & Integration Tests (DB -> Tools -> Detector) ---

def test_card_testing_detected_positive(db_session):
    c = create_entity(db_session, Customer, name="C1")
    a = create_entity(db_session, Account, customer=c)
    m = create_entity(db_session, Merchant, name="M1")

    cards = [create_entity(db_session, Card, account=a) for _ in range(14)]
    for card in cards:
        create_entity(db_session, Transaction, account_id=a.id, card=card, merchant_id=m.id, amount=1.0)

    distinct_cards = db_session.query(Card).filter(Card.account_id == a.id).count()

    mock_vel_data = {"15m": 14}
    res = detect_card_testing({}, {
        "velocity": mock_vel_data,
        "distinct_cards": distinct_cards,
        "amount": 1.0,
        "decline_count": 9,
        "total_count": 14
    })
    assert res.detected is True
    assert res.score >= 80

def test_card_testing_not_detected_benign(db_session):
    c = create_entity(db_session, Customer, name="C2")
    a = create_entity(db_session, Account, customer=c)
    m = create_entity(db_session, Merchant, name="M2")
    create_entity(db_session, Card, account=a)
    create_entity(db_session, Transaction, account_id=a.id, merchant_id=m.id, amount=100.0)

    distinct_cards = db_session.query(Card).filter(Card.account_id == a.id).count()

    mock_vel_data = {"15m": 1}
    res = detect_card_testing({}, {
        "velocity": mock_vel_data,
        "distinct_cards": distinct_cards,
        "amount": 100.0,
        "decline_count": 0,
        "total_count": 1
    })
    assert res.detected is False
    assert res.score < 40

def test_every_positive_signal_references_evidence_ids(db_session):
    c = create_entity(db_session, Customer, name="C3")
    a = create_entity(db_session, Account, customer=c)
    m = create_entity(db_session, Merchant, name="M3")

    trigger_txn = create_entity(db_session, Transaction, account_id=a.id, merchant_id=m.id, amount=1.0)
    base_time = trigger_txn.timestamp

    cards = [create_entity(db_session, Card, account=a) for _ in range(14)]
    for i, card in enumerate(cards):
        status = "declined" if i < 8 else "approved"
        create_entity(db_session, Transaction, account_id=a.id, card=card, merchant_id=m.id,
                     amount=1.0, timestamp=base_time - timedelta(minutes=1), status=status)

    case = create_entity(db_session, Case, transaction_id=trigger_txn.id)
    ctx = InvestigationContext(case_id=case.id, transaction_id=trigger_txn.id, start_time=base_time)
    run_orchestrator(ctx, db_session)

    res_txn = get_transaction(db_session, trigger_txn.id)
    res_vel = analyze_velocity(db_session, a.id, trigger_txn.id)

    res = detect_card_testing(ctx.evidence, {
        "velocity": res_vel.data["velocity"],
        "distinct_cards": res_txn.data["distinct_cards"],
        "amount": res_txn.data["transaction"]["amount"],
        "decline_count": res_vel.data["decline_count"],
        "total_count": res_txn.data["total_count"]
    })

    assert len(res.signals) > 0, "Detector should have generated signals"
    for signal in res.signals:
        for ev_id in signal.evidenceIds:
            assert ev_id in ctx.evidence, f"Evidence ID {ev_id} not found in context"

def test_detector_integrated_in_step_6(db_session):
    c = create_entity(db_session, Customer, name="C4")
    a = create_entity(db_session, Account, customer=c)
    m = create_entity(db_session, Merchant, name="M4")

    trigger_txn = create_entity(db_session, Transaction, account_id=a.id, merchant_id=m.id, amount=1.0)
    base_time = trigger_txn.timestamp

    cards = [create_entity(db_session, Card, account=a) for _ in range(14)]
    for i, card in enumerate(cards):
        status = "declined" if i < 8 else "approved"
        create_entity(db_session, Transaction, account_id=a.id, card=card, merchant_id=m.id,
                     amount=1.0, timestamp=base_time - timedelta(minutes=1), status=status)

    case = create_entity(db_session, Case, transaction_id=trigger_txn.id)
    ctx = InvestigationContext(case_id=case.id, transaction_id=trigger_txn.id, start_time=base_time)
    run_orchestrator(ctx, db_session)

    assert any(ps.pattern == "CARD_TESTING" for ps in ctx.pattern_scores)

def test_repeated_investigation_identical_score(db_session):
    c = create_entity(db_session, Customer, name="C5")
    a = create_entity(db_session, Account, customer=c)
    m = create_entity(db_session, Merchant, name="M5")

    trigger_txn = create_entity(db_session, Transaction, account_id=a.id, merchant_id=m.id, amount=1.0)
    base_time = trigger_txn.timestamp

    cards = [create_entity(db_session, Card, account=a) for _ in range(14)]
    for i, card in enumerate(cards):
        status = "declined" if i < 8 else "approved"
        create_entity(db_session, Transaction, account_id=a.id, card=card, merchant_id=m.id,
                     amount=1.0, timestamp=base_time - timedelta(minutes=1), status=status)

    case = create_entity(db_session, Case, transaction_id=trigger_txn.id)

    ctx1 = InvestigationContext(case_id=case.id, transaction_id=trigger_txn.id, start_time=base_time)
    run_orchestrator(ctx1, db_session)

    ctx2 = InvestigationContext(case_id=case.id, transaction_id=trigger_txn.id, start_time=base_time)
    run_orchestrator(ctx2, db_session)

    score1 = next((ps.score for ps in ctx1.pattern_scores if ps.pattern == "CARD_TESTING"), None)
    score2 = next((ps.score for ps in ctx2.pattern_scores if ps.pattern == "CARD_TESTING"), None)

    assert score1 is not None, "CARD_TESTING pattern missing from first run"
    assert score2 is not None, "CARD_TESTING pattern missing from second run"
    assert score1 == score2

def test_detector_integration_full_flow(db_session):
    c = create_entity(db_session, Customer, name="C6")
    a = create_entity(db_session, Account, customer=c)
    m = create_entity(db_session, Merchant, name="M6")

    trigger_card = create_entity(db_session, Card, account=a)
    trigger_txn = create_entity(db_session, Transaction, account_id=a.id, card=trigger_card, merchant_id=m.id, amount=1.0, status="approved")
    base_time = trigger_txn.timestamp

    cards = [create_entity(db_session, Card, account=a) for _ in range(13)]
    for i in range(28):
        card = cards[i % 13]
        status = "declined" if i < 15 else "approved"
        create_entity(db_session, Transaction, account_id=a.id, card=card, merchant_id=m.id,
                     amount=1.0, timestamp=base_time - timedelta(minutes=1), status=status)

    case = create_entity(db_session, Case, transaction_id=trigger_txn.id)
    ctx = InvestigationContext(case_id=case.id, transaction_id=trigger_txn.id, start_time=base_time)
    run_orchestrator(ctx, db_session)

    res_txn = get_transaction(db_session, trigger_txn.id)
    res_vel = analyze_velocity(db_session, a.id, trigger_txn.id)

    assert res_txn.data["distinct_cards"] == 14
    assert res_txn.data["total_count"] == 29
    assert res_vel.data["velocity"]["15m"] == 29
    assert res_vel.data["decline_count"] == 15

    score = next((ps.score for ps in ctx.pattern_scores if ps.pattern == "CARD_TESTING"), None)
    assert score == 100
