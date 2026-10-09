from pydantic import BaseModel, Field
from typing import List, Optional, Set, Dict
from datetime import datetime
from app.schemas.models import TimelineStep, EvidenceItem, RiskFactor, PatternScore, Recommendation

class InvestigationContext(BaseModel):
    case_id: str
    transaction_id: str
    start_time: datetime
    current_step: int = 1

    # Collected results
    timeline: List[TimelineStep] = []
    evidence: Dict[str, EvidenceItem] = {}
    patterns: Set[str] = set()
    graph_nodes: List[Dict] = []
    graph_edges: List[Dict] = []
    risk_factors: List[RiskFactor] = []
    pattern_scores: List[PatternScore] = []

    # Final output
    final_recommendation: Optional[Recommendation] = None

    def add_timeline_step(self, label: str, tool: str, status: str, summary: str, duration_ms: int):
        step_num = len(self.timeline) + 1
        step = TimelineStep(
            step=step_num,
            label=label,
            tool=tool,
            status=status,
            summary=summary,
            timestamp=datetime.now().isoformat(),
            durationMs=duration_ms
        )
        self.timeline.append(step)
        self.current_step = step_num
        return step
