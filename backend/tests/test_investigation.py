import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, Case, Transaction, Customer, Account, Device, LoginEvent
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
    db_file = tmp_path / "test_inv.db"
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

def test_investigation_context_initialization():
    ctx = InvestigationContext(
        case_id="CASE-123",
        transaction_id="TXN-456",
        start_time=datetime.now()
    )
    assert ctx.case_id == "CASE-123"
    assert ctx.current_step == 1
    assert len(ctx.timeline) == 0

def test_sequential_timeline_steps():
    ctx = InvestigationContext(case_id="C1", transaction_id="T1", start_time=datetime.now())
    ctx.add_timeline_step("Step 1", "tool1", "completed", "summary1", 100)
    ctx.add_timeline_step("Step 2", "tool2", "warning", "summary2", 200)

    assert len(ctx.timeline) == 2
    assert ctx.timeline[0].step == 1
    assert ctx.timeline[1].step == 2
    assert ctx.timeline[1].status == "warning"
    assert ctx.current_step == 2

def test_idempotent_investigation_logic(db_session):
    from app.api.investigate import run_orchestrator

    c = create_entity(db_session, Customer, name="C1")
    a = create_entity(db_session, Account, customer=c)
    txn = create_entity(db_session, Transaction, account_id=a.id, amount=100.0)
    case = create_entity(db_session, Case, transaction_id=txn.id)

    ctx1 = InvestigationContext(case_id=case.id, transaction_id=case.transaction_id, start_time=datetime.now())
    run_orchestrator(ctx1, db_session)

    ctx2 = InvestigationContext(case_id=case.id, transaction_id=case.transaction_id, start_time=datetime.now())
    run_orchestrator(ctx2, db_session)

    assert len(ctx1.timeline) == len(ctx2.timeline)
    assert ctx1.timeline[0].label == ctx2.timeline[0].label

def test_revealed_at_step_handling():
    reveal_step = 2
    evidence_items = [
        {"id": "E1", "revealedAtStep": 1},
        {"id": "E2", "revealedAtStep": 2},
        {"id": "E3", "revealedAtStep": 3},
    ]
    visible = [e for e in evidence_items if e["revealedAtStep"] <= reveal_step]
    assert len(visible) == 2
    assert "E3" not in [e["id"] for e in visible]
