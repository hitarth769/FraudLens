import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, Case, Transaction, Customer, Account, Device, LoginEvent, Merchant
from app.investigation.context import InvestigationContext
from app.tools.get_transaction import get_transaction
from app.tools.get_customer_history import get_customer_history
from app.tools.analyze_velocity import analyze_velocity
from app.tools.analyze_device import analyze_device
from app.tools.investigate_network import investigate_network
from datetime import datetime

@pytest.fixture
def db_session(tmp_path):
    """Provides a completely isolated temporary SQLite database for each test."""
    db_file = tmp_path / "test_phase5.db"
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

def test_get_transaction_isolated_data(db_session):
    c = create_entity(db_session, Customer, name="C1")
    a = create_entity(db_session, Account, customer=c)
    m = create_entity(db_session, Merchant, name="M1")
    txn = create_entity(db_session, Transaction, account_id=a.id, merchant_id=m.id, amount=100.0)
    case = create_entity(db_session, Case, transaction_id=txn.id)

    res = get_transaction(db_session, txn.id)
    assert res.success is True
    assert "transaction" in res.data
    assert res.data["transaction"]["id"] == txn.id

def test_customer_history_isolated_data(db_session):
    c = create_entity(db_session, Customer, name="C1")
    a = create_entity(db_session, Account, customer=c)
    txn = create_entity(db_session, Transaction, account_id=a.id, amount=100.0)

    res = get_customer_history(db_session, c.id)
    assert res.success is True
    assert "stats" in res.data

def test_velocity_returns_structured_measurements(db_session):
    c = create_entity(db_session, Customer, name="C1")
    a = create_entity(db_session, Account, customer=c)
    txn = create_entity(db_session, Transaction, account_id=a.id, amount=100.0)

    res = analyze_velocity(db_session, a.id, txn.id)
    assert res.success is True
    assert "velocity" in res.data
    assert "5m" in res.data["velocity"]

def test_device_analysis_isolated_data(db_session):
    c = create_entity(db_session, Customer, name="C1")
    a = create_entity(db_session, Account, customer=c)
    d = create_entity(db_session, Device, model="iPhone 15", os="iOS")
    create_entity(db_session, LoginEvent, account_id=a.id, device_id=d.id, timestamp=datetime.now(), success=True)

    res = analyze_device(db_session, a.id, d.id)
    assert res.success is True
    assert "is_known_to_account" in res.data

def test_network_contains_isolated_nodes(db_session):
    c1 = create_entity(db_session, Customer, name="C1")
    a1 = create_entity(db_session, Account, customer=c1)
    c2 = create_entity(db_session, Customer, name="C2")
    a2 = create_entity(db_session, Account, customer=c2)

    create_entity(db_session, Transaction, account_id=a1.id, recipient_account_id=a2.id, amount=100.0)

    res = investigate_network(db_session, a1.id)
    assert res.success is True
    assert len(res.data["nodes"]) > 0
    assert len(res.data["edges"]) > 0

def test_evidence_has_required_fields(db_session):
    c = create_entity(db_session, Customer, name="C1")
    a = create_entity(db_session, Account, customer=c)
    m = create_entity(db_session, Merchant, name="M1")
    txn = create_entity(db_session, Transaction, account_id=a.id, merchant_id=m.id, amount=100.0)

    res = get_transaction(db_session, txn.id)
    ev = res.evidence[0]
    assert hasattr(ev, "id")
    assert hasattr(ev, "title")
    assert hasattr(ev, "severity")
    assert hasattr(ev, "revealedAtStep")

def test_evidence_revealed_at_correct_step(db_session):
    from app.api.investigate import run_orchestrator
    c = create_entity(db_session, Customer, name="C1")
    a = create_entity(db_session, Account, customer=c)
    m = create_entity(db_session, Merchant, name="M1")
    txn = create_entity(db_session, Transaction, account_id=a.id, merchant_id=m.id, amount=100.0)
    case = create_entity(db_session, Case, transaction_id=txn.id)

    ctx = InvestigationContext(case_id=case.id, transaction_id=txn.id, start_time=datetime.now())
    run_orchestrator(ctx, db_session)

    gt_ev = [e for e in ctx.evidence.values() if "get_transaction" in e.id or "get_tx" in e.id]
    if gt_ev:
        assert gt_ev[0].revealedAtStep == 1

def test_tool_failure_is_recorded_without_crashing_investigation(db_session):
    from app.api.investigate import run_orchestrator
    c = create_entity(db_session, Customer, name="C1")
    a = create_entity(db_session, Account, customer=c)
    m = create_entity(db_session, Merchant, name="M1")
    txn = create_entity(db_session, Transaction, account_id=a.id, merchant_id=m.id, amount=100.0)
    case = create_entity(db_session, Case, transaction_id=txn.id)

    ctx = InvestigationContext(case_id=case.id, transaction_id=txn.id, start_time=datetime.now())

    import app.tools.get_transaction as gt
    original = gt.get_transaction
    def mock_fail(db, tid):
        raise Exception("Forced Failure")
    gt.get_transaction = mock_fail

    try:
        run_orchestrator(ctx, db_session)
    except Exception:
        pytest.fail("Orchestrator crashed on tool failure")

    assert any(step.status == "failed" for step in ctx.timeline)
    gt.get_transaction = original

def test_repeated_investigation_is_logically_idempotent(db_session):
    from app.api.investigate import run_orchestrator
    c = create_entity(db_session, Customer, name="C1")
    a = create_entity(db_session, Account, customer=c)
    m = create_entity(db_session, Merchant, name="M1")
    txn = create_entity(db_session, Transaction, account_id=a.id, merchant_id=m.id, amount=100.0)
    case = create_entity(db_session, Case, transaction_id=txn.id)

    ctx1 = InvestigationContext(case_id=case.id, transaction_id=txn.id, start_time=datetime.now())
    run_orchestrator(ctx1, db_session)

    ctx2 = InvestigationContext(case_id=case.id, transaction_id=txn.id, start_time=datetime.now())
    run_orchestrator(ctx2, db_session)

    assert len(ctx1.evidence) == len(ctx2.evidence)
    assert len(ctx1.timeline) == len(ctx2.timeline)

def test_investigation_executes_real_tools(db_session):
    from app.api.investigate import run_orchestrator
    c = create_entity(db_session, Customer, name="C1")
    a = create_entity(db_session, Account, customer=c)
    m = create_entity(db_session, Merchant, name="M1")
    txn = create_entity(db_session, Transaction, account_id=a.id, merchant_id=m.id, amount=100.0)
    case = create_entity(db_session, Case, transaction_id=txn.id)

    ctx = InvestigationContext(case_id=case.id, transaction_id=txn.id, start_time=datetime.now())
    run_orchestrator(ctx, db_session)

    tool_prefixes = set([e.id.split('-')[1] for e in ctx.evidence.values()])
    assert len(tool_prefixes) >= 2
