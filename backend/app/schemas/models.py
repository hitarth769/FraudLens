from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

# Enums matching frontend types.ts
class RiskLevel(str, Enum):
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'

class PatternType(str, Enum):
    CARD_TESTING = 'CARD_TESTING'
    ACCOUNT_TAKEOVER = 'ACCOUNT_TAKEOVER'
    MULE_NETWORK = 'MULE_NETWORK'
    BEHAVIOURAL_ANOMALY = 'BEHAVIOURAL_ANOMALY'

class CaseStatus(str, Enum):
    AWAITING_DECISION = 'AWAITING_DECISION'
    APPROVED = 'APPROVED'
    OVERRIDDEN = 'OVERRIDDEN'

class Severity(str, Enum):
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'

class RecommendedAction(str, Enum):
    APPROVE = 'APPROVE'
    HOLD = 'HOLD'
    ESCALATE = 'ESCALATE'
    BLOCK = 'BLOCK'

class TimelineStatus(str, Enum):
    completed = 'completed'
    warning = 'warning'
    suspicious = 'suspicious'
    failed = 'failed'

class GraphNodeType(str, Enum):
    customer = 'customer'
    account = 'account'
    device = 'device'
    card = 'card'
    merchant = 'merchant'
    transaction = 'transaction'
    ip = 'ip'

class GraphEdgeKind(str, Enum):
    owns = 'owns'
    uses = 'uses'
    paid = 'paid'
    transferred = 'transferred'
    logged_in = 'logged_in'

# Schemas
class HumanDecision(BaseModel):
    decision: str # 'APPROVE' | 'OVERRIDE'
    overrideAction: Optional[RecommendedAction] = None
    note: Optional[str] = None
    analyst: str
    decidedAt: str

class CaseSummary(BaseModel):
    caseId: str
    transactionId: str
    amount: float
    currency: str
    customerName: str
    accountId: str
    counterparty: str
    timestamp: str
    riskScore: int
    riskLevel: RiskLevel
    patterns: List[PatternType]
    status: CaseStatus
    recommendedActions: List[RecommendedAction]
    investigationDurationSec: float
    scenario: str

class EvidenceItem(BaseModel):
    id: str
    type: str
    pattern: PatternType
    title: str
    claim: str
    observed: str
    baseline: str
    whyItMatters: str
    severity: Severity
    polarity: str # 'SUPPORTING' | 'CONTRADICTING'
    source: Dict[str, str]
    revealedAtStep: int

class PatternScore(BaseModel):
    pattern: PatternType
    score: int
    confidence: str # 'LOW' | 'MEDIUM' | 'HIGH'
    supporting: int
    contradicting: int

class RiskFactor(BaseModel):
    label: str
    channel: str
    points: int

class RecommendationRationale(BaseModel):
    text: str
    evidenceIds: List[str]

class Recommendation(BaseModel):
    actions: List[RecommendedAction]
    summary: str
    rationale: List[RecommendationRationale]
    humanApprovalRequired: bool
    narrativeSource: str # 'LLM' | 'TEMPLATE'

class CaseDetail(CaseSummary):
    customer: Dict[str, str]
    transaction: Dict[str, str]
    evidence: List[EvidenceItem]
    patternScores: List[PatternScore]
    riskFactors: List[RiskFactor]
    recommendation: Recommendation
    humanDecision: Optional[HumanDecision] = None

class TimelineStep(BaseModel):
    step: int
    label: str
    tool: str
    status: TimelineStatus
    summary: str
    timestamp: str
    durationMs: int

class GraphNode(BaseModel):
    id: str
    type: GraphNodeType
    label: str
    sublabel: str
    layer: int
    suspicious: bool
    attributes: Dict[str, str]
    revealedAtStep: int

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    kind: GraphEdgeKind
    label: Optional[str] = None
    suspicious: bool
    revealedAtStep: int

class CaseGraph(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]

class Health(BaseModel):
    status: str # 'ok' | 'degraded'
    mode: str # 'fixture' | 'live'
    llm: str # 'available' | 'unavailable'
    version: str

class DecisionRequest(BaseModel):
    decision: str # 'APPROVE' | 'OVERRIDE'
    overrideAction: Optional[RecommendedAction] = None
    note: Optional[str] = None
