import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.db.models import Base, Transaction, Account, Customer, Merchant
from app.tools.analyze_mule_behavior import analyze_mule_behavior
from app.detectors.mule_network import detect_mule_network
from app.schemas.models import EvidenceItem, Severity

@pytest.fixture
def db_session(tmp_path):
    """
    Provides a completely isolated temporary SQLite database for each test.
    Uses tmp_path for disposable storage and enforces foreign keys.
    """
    db_file = tmp_path / "test_fraudlens.db"
    engine = create_engine(f"sqlite:///{db_file}")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Verify PRAGMA foreign_keys is actually 1 on the connection
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys")).scalar()
        assert result == 1, "SQLite foreign keys must be enabled for these tests"

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
    # Primary Key handling: Generate ID if not provided
    if 'id' not in kwargs:
        prefix = cls.__tablename__[0].upper()
        kwargs['id'] = f"{prefix}-{uuid.uuid4().hex[:6].upper()}"

    # Default values for non-null fields to avoid IntegrityErrors
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

def test_mule_inbound_detection(db_session):
    """Verify inbound A2A transfers are correctly identified as fan-in."""
    c1 = create_entity(db_session, Customer, name="C1", country="IN", segment="Retail")
    a1 = create_entity(db_session, Account, customer=c1, status="Active")
    c2 = create_entity(db_session, Customer, name="C2", country="IN", segment="Retail")
    a2 = create_entity(db_session, Account, customer=c2, status="Active")
    cm = create_entity(db_session, Customer, name="Mule", country="IN", segment="Retail")
    am = create_entity(db_session, Account, customer=cm, status="Active")

    db_session.add_all([
        Transaction(id="T1", account_id=a1.id, recipient_account_id=am.id, amount=100.0, timestamp=datetime.now(), status="approved", currency="INR", channel="Web", ip="1.1.1.1", location="IN"),
        Transaction(id="T2", account_id=a2.id, recipient_account_id=am.id, amount=100.0, timestamp=datetime.now(), status="approved", currency="INR", channel="Web", ip="1.1.1.1", location="IN")
    ])
    db_session.commit()

    res = analyze_mule_behavior(db_session, am.id)
    assert res.data["distinct_senders"] == 2
    assert any(ev.type == "FAN_IN" for ev in res.evidence)

def test_mule_fifo_and_non_reuse(db_session):
    """Verify FIFO matching and that outbound transactions are not reused."""
    c = create_entity(db_session, Customer, name="C", country="IN", segment="Retail")
    am = create_entity(db_session, Account, customer=c, status="Active")

    cs1 = create_entity(db_session, Customer, name="S1", country="IN", segment="Retail")
    asrc1 = create_entity(db_session, Account, customer=cs1, status="Active")
    cs2 = create_entity(db_session, Customer, name="S2", country="IN", segment="Retail")
    asrc2 = create_entity(db_session, Account, customer=cs2, status="Active")

    cd = create_entity(db_session, Customer, name="D", country="IN", segment="Retail")
    adst = create_entity(db_session, Account, customer=cd, status="Active")

    t_in1 = Transaction(id="T_IN1", account_id=asrc1.id, recipient_account_id=am.id, amount=100.0, timestamp=datetime(2026, 1, 1, 10, 0), status="approved", currency="INR", channel="Web", ip="1.1.1.1", location="IN")
    t_in2 = Transaction(id="T_IN2", account_id=asrc2.id, recipient_account_id=am.id, amount=100.0, timestamp=datetime(2026, 1, 1, 10, 10), status="approved", currency="INR", channel="Web", ip="1.1.1.1", location="IN")
    t_out = Transaction(id="T_OUT", account_id=am.id, recipient_account_id=adst.id, amount=100.0, timestamp=datetime(2026, 1, 1, 10, 15), status="approved", currency="INR", channel="Web", ip="1.1.1.1", location="IN")

    db_session.add_all([t_in1, t_in2, t_out])
    db_session.commit()

    res = analyze_mule_behavior(db_session, am.id)
    assert res.data["matched_pair_count"] == 1
    assert res.data["matched_pairs"][0]["inboundId"] == "T_IN1"
    assert res.data["matched_pairs"][0]["outboundId"] == "T_OUT"

def test_mule_pass_through_ratios(db_session):
    """Verify pass-through ratio calculations."""
    c = create_entity(db_session, Customer, name="C", country="IN", segment="Retail")
    am = create_entity(db_session, Account, customer=c, status="Active")
    cs = create_entity(db_session, Customer, name="S", country="IN", segment="Retail")
    asrc = create_entity(db_session, Account, customer=cs, status="Active")
    cd = create_entity(db_session, Customer, name="D", country="IN", segment="Retail")
    adst = create_entity(db_session, Account, customer=cd, status="Active")

    t_in = Transaction(id="T_IN", account_id=asrc.id, recipient_account_id=am.id, amount=100.0, timestamp=datetime(2026, 1, 1, 10, 0), status="approved", currency="INR", channel="Web", ip="1.1.1.1", location="IN")
    t_out = Transaction(id="T_OUT", account_id=am.id, recipient_account_id=adst.id, amount=50.0, timestamp=datetime(2026, 1, 1, 10, 5), status="approved", currency="INR", channel="Web", ip="1.1.1.1", location="IN")
    db_session.add_all([t_in, t_out])
    db_session.commit()

    res = analyze_mule_behavior(db_session, am.id)
    assert res.data["pass_through_ratio"] == 0.5

def test_mule_multi_hop_a2a(db_session):
    """Verify MULTI_HOP resolves A2A destination correctly."""
    cm = create_entity(db_session, Customer, name="Mule", country="IN", segment="Retail")
    am = create_entity(db_session, Account, customer=cm, status="Active")
    cs = create_entity(db_session, Customer, name="S", country="IN", segment="Retail")
    asrc = create_entity(db_session, Account, customer=cs, status="Active")
    cd = create_entity(db_session, Customer, name="D", country="IN", segment="Retail")
    adst = create_entity(db_session, Account, customer=cd, status="Active")

    t_in = Transaction(id="T_IN", account_id=asrc.id, recipient_account_id=am.id, amount=100.0, timestamp=datetime(2026, 1, 1, 10, 0), status="approved", currency="INR", channel="Web", ip="1.1.1.1", location="IN")
    t_out = Transaction(id="T_OUT", account_id=am.id, recipient_account_id=adst.id, amount=100.0, timestamp=datetime(2026, 1, 1, 10, 5), status="approved", currency="INR", channel="Web", ip="1.1.1.1", location="IN")
    db_session.add_all([t_in, t_out])
    db_session.commit()

    res = analyze_mule_behavior(db_session, am.id)
    ev = next((ev for ev in res.evidence if ev.type == "MULTI_HOP"), None)
    assert ev is not None
    assert ev.source["destination"] == adst.id
    assert f"{asrc.id} -> {am.id} -> {adst.id}" in ev.observed

def test_mule_multi_hop_merchant(db_session):
    """Verify MULTI_HOP resolves Commercial destination correctly."""
    cm = create_entity(db_session, Customer, name="Mule", country="IN", segment="Retail")
    am = create_entity(db_session, Account, customer=cm, status="Active")
    cs = create_entity(db_session, Customer, name="S", country="IN", segment="Retail")
    asrc = create_entity(db_session, Account, customer=cs, status="Active")
    merch = create_entity(db_session, Merchant, name="Store", category="Retail", country="IN", risk_profile="Low")

    t_in = Transaction(id="T_IN", account_id=asrc.id, recipient_account_id=am.id, amount=100.0, timestamp=datetime(2026, 1, 1, 10, 0), status="approved", currency="INR", channel="Web", ip="1.1.1.1", location="IN")
    t_out = Transaction(id="T_OUT", account_id=am.id, merchant_id=merch.id, amount=100.0, timestamp=datetime(2026, 1, 1, 10, 5), status="approved", currency="INR", channel="Web", ip="1.1.1.1", location="IN")
    db_session.add_all([t_in, t_out])
    db_session.commit()

    res = analyze_mule_behavior(db_session, am.id)
    ev = next((ev for ev in res.evidence if ev.type == "MULTI_HOP"), None)
    assert ev is not None
    assert ev.source["destination"] == merch.id
    assert f"{asrc.id} -> {am.id} -> {merch.id}" in ev.observed

def test_mule_conflicting_destinations(db_session):
    """Verify that conflicting destinations (both set) emit no MULTI_HOP evidence."""
    cm = create_entity(db_session, Customer, name="Mule", country="IN", segment="Retail")
    am = create_entity(db_session, Account, customer=cm, status="Active")
    cs = create_entity(db_session, Customer, name="S", country="IN", segment="Retail")
    asrc = create_entity(db_session, Account, customer=cs, status="Active")
    cd = create_entity(db_session, Customer, name="D", country="IN", segment="Retail")
    adst = create_entity(db_session, Account, customer=cd, status="Active")
    merch = create_entity(db_session, Merchant, name="M", category="Retail", country="IN", risk_profile="Low")

    t_in = Transaction(id="T_IN", account_id=asrc.id, recipient_account_id=am.id, amount=100.0, timestamp=datetime(2026, 1, 1, 10, 0), status="approved", currency="INR", channel="Web", ip="1.1.1.1", location="IN")
    t_out = Transaction(id="T_OUT", account_id=am.id, recipient_account_id=adst.id, merchant_id=merch.id, amount=100.0, timestamp=datetime(2026, 1, 1, 10, 5), status="approved", currency="INR", channel="Web", ip="1.1.1.1", location="IN")

    db_session.add_all([t_in, t_out])
    db_session.commit()

    res = analyze_mule_behavior(db_session, am.id)
    assert not any(ev.type == "MULTI_HOP" for ev in res.evidence)

def test_mule_missing_destination(db_session):
    """Verify that missing destinations emit no MULTI_HOP evidence."""
    cm = create_entity(db_session, Customer, name="Mule", country="IN", segment="Retail")
    am = create_entity(db_session, Account, customer=cm, status="Active")
    cs = create_entity(db_session, Customer, name="S", country="IN", segment="Retail")
    asrc = create_entity(db_session, Account, customer=cs, status="Active")

    t_in = Transaction(id="T_IN", account_id=asrc.id, recipient_account_id=am.id, amount=100.0, timestamp=datetime(2026, 1, 1, 10, 0), status="approved", currency="INR", channel="Web", ip="1.1.1.1", location="IN")
    t_out = Transaction(id="T_OUT", account_id=am.id, recipient_account_id=None, merchant_id=None, amount=100.0, timestamp=datetime(2026, 1, 1, 10, 5), status="approved", currency="INR", channel="Web", ip="1.1.1.1", location="IN")

    db_session.add_all([t_in, t_out])
    db_session.commit()

    res = analyze_mule_behavior(db_session, am.id)
    assert not any(ev.type == "MULTI_HOP" for ev in res.evidence)

def test_mule_fk_rejection(db_session):
    """Verify DB rejects transactions with non-existent accounts (FK enforcement)."""
    with pytest.raises(IntegrityError):
        t = Transaction(id="T1", account_id="GHOST", recipient_account_id="A1", amount=100.0, timestamp=datetime.now(), status="approved", currency="INR", channel="Web", ip="1.1.1.1", location="IN")
        db_session.add(t)
        db_session.commit()
    db_session.rollback()

def test_mule_detector_thresholds(db_session):
    """Verify the deterministic scoring logic of the detector."""
    evidence = {
        "e1": EvidenceItem(id="e1", type="PASS_THROUGH", pattern="MULE_NETWORK", title="T", claim="C", observed="O", baseline="B", whyItMatters="W", severity=Severity.HIGH, polarity="SUPPORTING", source={}, revealedAtStep=0),
        "e2": EvidenceItem(id="e2", type="SHORT_HOLD", pattern="MULE_NETWORK", title="T", claim="C", observed="O", baseline="B", whyItMatters="W", severity=Severity.HIGH, polarity="SUPPORTING", source={}, revealedAtStep=0),
        "e3": EvidenceItem(id="e3", type="MULTI_HOP", pattern="MULE_NETWORK", title="T", claim="C", observed="O", baseline="B", whyItMatters="W", severity=Severity.MEDIUM, polarity="SUPPORTING", source={}, revealedAtStep=0),
        "e4": EvidenceItem(id="e4", type="FAN_OUT", pattern="MULE_NETWORK", title="T", claim="C", observed="O", baseline="B", whyItMatters="W", severity=Severity.MEDIUM, polarity="SUPPORTING", source={}, revealedAtStep=0),
    }
    res = detect_mule_network(evidence, {})
    assert res.score == 100
    assert res.detected is True

def test_mule_detector_idempotency(db_session):
    """Verify that repeated scoring of identical evidence is deterministic."""
    evidence = {
        "e1": EvidenceItem(id="e1", type="PASS_THROUGH", pattern="MULE_NETWORK", title="T", claim="C", observed="O", baseline="B", whyItMatters="W", severity=Severity.HIGH, polarity="SUPPORTING", source={}, revealedAtStep=0),
    }
    res1 = detect_mule_network(evidence, {})
    res2 = detect_mule_network(evidence, {})
    assert res1.score == res2.score
    assert res1.detected == res2.detected

def test_mule_detector_duplicate_evidence(db_session):
    """Verify that duplicate evidence of the same type only scores once."""
    evidence = {
        "ev1": EvidenceItem(id="ev1", type="FAN_IN", pattern="MULE_NETWORK", title="T", claim="C", observed="O", baseline="B", whyItMatters="W", severity=Severity.MEDIUM, polarity="SUPPORTING", source={}, revealedAtStep=0),
        "ev2": EvidenceItem(id="ev2", type="FAN_IN", pattern="MULE_NETWORK", title="T", claim="C", observed="O", baseline="B", whyItMatters="W", severity=Severity.MEDIUM, polarity="SUPPORTING", source={}, revealedAtStep=0),
    }
    res = detect_mule_network(evidence, {})
    assert res.score == 20 # Only one FAN_IN counted

def test_mule_detector_empty_evidence(db_session):
    """Verify detector handles empty evidence."""
    res = detect_mule_network({}, {})
    assert res.score == 0
    assert res.detected is False
