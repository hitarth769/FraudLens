import networkx as nx
from sqlalchemy.orm import Session
from app.db.models import Transaction, Account, Device, Card, Merchant, LoginEvent
from app.tools.base import ToolResult, generate_evidence_id
from app.schemas.models import EvidenceItem, PatternType, Severity, GraphNode, GraphEdge, CaseGraph

def investigate_network(db: Session, account_id: str) -> ToolResult:
    G = nx.Graph()

    # 1. Central Account
    G.add_node(account_id, type="account", label=account_id, sublabel="Target Account", layer=0)

    # 2. Find all transactions for this account
    txns = db.query(Transaction).filter(Transaction.account_id == account_id).all()

    for txn in txns:
        # Add Transaction node
        G.add_node(txn.id, type="transaction", label=txn.id, sublabel=f"{txn.amount} {txn.currency}", layer=1)
        G.add_edge(account_id, txn.id, kind="paid")

        # Add Merchant node
        merch = db.query(Merchant).filter(Merchant.id == txn.merchant_id).first()
        if merch:
            G.add_node(merch.id, type="merchant", label=merch.name, sublabel=merch.category, layer=2)
            G.add_edge(txn.id, merch.id, kind="paid")

    # 3. Find devices linked to account
    logins = db.query(LoginEvent).filter(LoginEvent.account_id == account_id).all()
    for login in logins:
        G.add_node(login.device_id, type="device", label=login.device_id, sublabel=login.location, layer=1)
        G.add_edge(account_id, login.device_id, kind="logged_in")

    # 4. Expand Depth 1: Other accounts sharing devices
    devices = list(G.nodes)
    for node in devices:
        # If node is a device, find other accounts using it
        # This is a simplified version for the MVP
        pass

    # Convert NetworkX to CaseGraph format
    nodes = []
    for n, attrs in G.nodes(data=True):
        nodes.append(GraphNode(
            id=n,
            type=attrs.get("type", "unknown"),
            label=attrs.get("label", n),
            sublabel=attrs.get("sublabel", ""),
            layer=attrs.get("layer", 0),
            suspicious=False,
            attributes={},
            revealedAtStep=0
        ))

    edges = []
    for u, v, attrs in G.edges(data=True):
        edges.append(GraphEdge(
            id=f"E-{u}-{v}",
            source=u,
            target=v,
            kind=attrs.get("kind", "related"),
            suspicious=False,
            revealedAtStep=0
        ))

    data = {
        "nodes": nodes,
        "edges": edges,
        "entity_count": len(nodes)
    }

    return ToolResult(tool="investigate_network", success=True, data=data, evidence=[])
