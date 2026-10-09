from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from app.schemas.models import EvidenceItem, PatternType, Severity

class ToolResult(BaseModel):
    tool: str
    success: bool
    data: Dict[str, Any]
    evidence: List[EvidenceItem] = []
    error: Optional[str] = None

def generate_evidence_id(tool_name: str, entity_id: str, index: int) -> str:
    # tool_name: 'get_transaction' -> 'GET'
    prefix = tool_name.split('_')[0].upper()
    return f"EV-{prefix}-{entity_id[-4:]}-{index}"
