import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, Case, Transaction, Customer, Account, Card, Device, LoginEvent, ProfileEvent
from app.investigation.context import InvestigationContext
from app.detectors.account_takeover import detect_account_takeover
from app.schemas.models import EvidenceItem
from app.api.investigate import run_orchestrator

@pytest.fixture
def db_session(tmp_path):
    """Provides a completely isolated temporary SQLite database for each test."""
    db_file = tmp_path / "test_ato.db"
    engine = create_engine(f"sqlite:///{db_file}")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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

    # Default values for non-null fields
    if cls == Customer and 'tenure' not in kwargs:
        kwargs['tenure'] = "1.0 years"
    if cls == Account and 'created_at' not in kwargs:
        kwargs['created_at'] = datetime.now()
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

def test_ato_detected_positive_case1002(db_session):
    # CASE-1002: New Device + Credential Change + Geo Anomaly + High Value + Proximity
    c = create_entity(db_session, Customer, name="C1")
    a = create_entity(db_session, Account, customer=c)
    txn = create_entity(db_session, Transaction, account_id=a.id, amount=72500.0)
    case = create_entity(db_session, Case, transaction_id=txn.id)

    ctx = InvestigationContext(case_id=case.id, transaction_id=txn.id, start_time=datetime.now())

    # Manually populate evidence that would come from tools
    ctx.evidence["ev1"] = EvidenceItem(id="ev1", type="DEVICE_NOVELTY", pattern="ACCOUNT_TAKEOVER", title="New Device", claim="New device", observed="Unknown device", baseline="Known devices", whyItMatters="...", severity="HIGH", polarity="SUPPORTING", source={}, revealedAtStep=1)
    ctx.evidence["ev2"] = EvidenceItem(id="ev2", type="CREDENTIAL_CHANGE", pattern="ACCOUNT_TAKEOVER", title="Cred Change", claim="Password change", observed="Changed 10m ago", baseline="No change", whyItMatters="...", severity="HIGH", polarity="SUPPORTING", source={}, revealedAtStep=1)
    ctx.evidence["ev3"] = EvidenceItem(id="ev3", type="GEO_ANOMALY", pattern="ACCOUNT_TAKEOVER", title="Geo Anomaly", claim="Unknown location", observed="Singapore", baseline="Mumbai", whyItMatters="...", severity="MEDIUM", polarity="SUPPORTING", source={}, revealedAtStep=1)
    ctx.evidence["ev4"] = EvidenceItem(id="ev4", type="VALUE_ANOMALY", pattern="ACCOUNT_TAKEOVER", title="Value Anomaly", claim="High amount", observed="72500", baseline="Avg 500", whyItMatters="...", severity="MEDIUM", polarity="SUPPORTING", source={}, revealedAtStep=1)
    ctx.evidence["ev5"] = EvidenceItem(id="ev5", type="LOGIN_PROXIMITY", pattern="ACCOUNT_TAKEOVER", title="Login Proximity", claim="Quick login", observed="5m ago", baseline="N/A", whyItMatters="...", severity="MEDIUM", polarity="SUPPORTING", source={}, revealedAtStep=1)

    res = detect_account_takeover(ctx.evidence, {})
    assert res.detected is True
    assert res.score >= 80

def test_ato_not_detected_benign_case1004(db_session):
    # CASE-1004: New Device but Known Location and Normal Value
    ctx = InvestigationContext(case_id="CASE-1004", transaction_id="TXN-BENIGN", start_time=datetime.now())

    # Only New Device signal (legitimate upgrade)
    ctx.evidence["ev1"] = EvidenceItem(id="ev1", type="DEVICE_NOVELTY", pattern="ACCOUNT_TAKEOVER", title="New Device", claim="New device", observed="Unknown device", baseline="Known devices", whyItMatters="...", severity="HIGH", polarity="SUPPORTING", source={}, revealedAtStep=1)

    res = detect_account_takeover(ctx.evidence, {})
    assert res.detected is False
    assert res.score < 50

def test_ato_deterministic():
    ctx_evidence = {
        "ev1": EvidenceItem(id="ev1", type="DEVICE_NOVELTY", pattern="ACCOUNT_TAKEOVER", title="New Device", claim="New device", observed="Unknown device", baseline="Known devices", whyItMatters="...", severity="HIGH", polarity="SUPPORTING", source={}, revealedAtStep=1),
        "ev2": EvidenceItem(id="ev2", type="CREDENTIAL_CHANGE", pattern="ACCOUNT_TAKEOVER", title="Cred Change", claim="Password change", observed="Changed 10m ago", baseline="No change", whyItMatters="...", severity="HIGH", polarity="SUPPORTING", source={}, revealedAtStep=1),
    }
    res1 = detect_account_takeover(ctx_evidence, {})
    res2 = detect_account_takeover(ctx_evidence, {})
    assert res1.score == res2.score
    assert res1.detected == res2.detected

def test_ato_every_signal_has_evidence_id():
    ctx_evidence = {
        "ev1": EvidenceItem(id="ev1", type="DEVICE_NOVELTY", pattern="ACCOUNT_TAKEOVER", title="New Device", claim="New device", observed="Unknown device", baseline="Known devices", whyItMatters="...", severity="HIGH", polarity="SUPPORTING", source={}, revealedAtStep=1),
        "ev2": EvidenceItem(id="ev2", type="CREDENTIAL_CHANGE", pattern="ACCOUNT_TAKEOVER", title="Cred Change", claim="Password change", observed="Changed 10m ago", baseline="No change", whyItMatters="...", severity="HIGH", polarity="SUPPORTING", source={}, revealedAtStep=1),
    }
    res = detect_account_takeover(ctx_evidence, {})
    for signal in res.signals:
        assert len(signal.evidenceIds) > 0
        assert signal.evidenceIds[0] in ctx_evidence

def test_ato_no_hardcoded_ids():
    ctx_evidence = {
        "rand1": EvidenceItem(id="rand1", type="DEVICE_NOVELTY", pattern="ACCOUNT_TAKEOVER", title="New Device", claim="New device", observed="Unknown device", baseline="Known devices", whyItMatters="...", severity="HIGH", polarity="SUPPORTING", source={}, revealedAtStep=1),
    }
    res = detect_account_takeover(ctx_evidence, {})
    assert res.score == 30

def test_ato_integration_full_flow(db_session):
    c = create_entity(db_session, Customer, name="C1")
    a = create_entity(db_session, Account, customer=c)
    txn = create_entity(db_session, Transaction, account_id=a.id, amount=72500.0)
    case = create_entity(db_session, Case, transaction_id=txn.id)

    # Create a synthetic ATO scenario in the DB
    # 1. Novel Device
    d = create_entity(db_session, Device, model="iPhone 15", os="iOS")
    create_entity(db_session, LoginEvent, account_id=a.id, device_id=d.id, timestamp=datetime.now(), success=True)

    # 2. Credential Change
    create_entity(db_session, ProfileEvent, account_id=a.id, event_type="PASSWORD_CHANGE", timestamp=datetime.now() - timedelta(minutes=10))

    ctx = InvestigationContext(case_id=case.id, transaction_id=txn.id, start_time=datetime.now())
    run_orchestrator(ctx, db_session)

    ato_score = next((ps.score for ps in ctx.pattern_scores if ps.pattern == "ACCOUNT_TAKEOVER"), None)
    assert ato_score is not None
    assert ato_score >= 50

def test_ato_repeated_investigation_idempotency(db_session):
    c = create_entity(db_session, Customer, name="C2")
    a = create_entity(db_session, Account, customer=c)
    txn = create_entity(db_session, Transaction, account_id=a.id, amount=72500.0)
    case = create_entity(db_session, Case, transaction_id=txn.id)

    # Create synthetic signals
    create_entity(db_session, ProfileEvent, account_id=a.id, event_type="PASSWORD_CHANGE", timestamp=datetime.now() - timedelta(minutes=10))

    ctx1 = InvestigationContext(case_id=case.id, transaction_id=txn.id, start_time=datetime.now())
    run_orchestrator(ctx1, db_session)

    ctx2 = InvestigationContext(case_id=case.id, transaction_id=txn.id, start_time=datetime.now())
    run_orchestrator(ctx2, db_session)

    score1 = next((ps.score for ps in ctx1.pattern_scores if ps.pattern == "ACCOUNT_TAKEOVER"), None)
    score2 = next((ps.score for ps in ctx2.pattern_scores if ps.pattern == "ACCOUNT_TAKEOVER"), None)
    assert score1 == score2

def test_ato_strong_signal_requirement():
    ctx_evidence = {
        "ev1": EvidenceItem(id="ev1", type="GEO_ANOMALY", pattern="ACCOUNT_TAKEOVER", title="Geo", claim="Geo", observed="X", baseline="Y", whyItMatters="...", severity="MEDIUM", polarity="SUPPORTING", source={}, revealedAtStep=1),
        "ev2": EvidenceItem(id="ev2", type="VALUE_ANOMALY", pattern="ACCOUNT_TAKEOVER", title="Val", claim="Val", observed="X", baseline="Y", whyItMatters="...", severity="MEDIUM", polarity="SUPPORTING", source={}, revealedAtStep=1),
    }
    res = detect_account_takeover(ctx_evidence, {})
    assert res.detected is False
    assert res.score == 40

def test_ato_strong_signal_triggers_at_40():
    ctx_evidence = {
        "ev1": EvidenceItem(id="ev1", type="DEVICE_NOVELTY", pattern="ACCOUNT_TAKEOVER", title="Device", claim="Device", observed="X", baseline="Y", whyItMatters="...", severity="HIGH", polarity="SUPPORTING", source={}, revealedAtStep=1),
        "ev2": EvidenceItem(id="ev2", type="GEO_ANOMALY", pattern="ACCOUNT_TAKEOVER", title="Geo", claim="Geo", observed="X", baseline="Y", whyItMatters="...", severity="MEDIUM", polarity="SUPPORTING", source={}, revealedAtStep=1),
    }
    res = detect_account_takeover(ctx_evidence, {})
    assert res.detected is True
    assert res.score == 50
