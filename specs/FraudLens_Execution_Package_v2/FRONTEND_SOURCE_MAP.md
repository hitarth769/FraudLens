# Frontend Source Map — inspected v0 implementation

This file records what was inspected before backend v2 was written.

## API hooks
`lib/api.ts`
- `/api/health`
- `/api/cases`
- `/api/cases/{id}`
- `/api/cases/{id}/timeline`
- `/api/cases/{id}/graph`
- `/api/metrics`
- POST `/api/cases/{id}/investigate`
- POST `/api/cases/{id}/decision`

## Type source
`lib/types.ts`

Defines:
- RiskLevel
- PatternType
- CaseStatus
- Severity
- RecommendedAction
- HumanDecision
- CaseSummary
- EvidenceItem
- PatternScore
- RiskFactor
- Recommendation
- CaseDetail
- TimelineStatus
- TimelineStep
- GraphNodeType
- GraphNode
- GraphEdgeKind
- GraphEdge
- CaseGraph
- Metrics
- Health
- DecisionRequest

## Main UI consumers
- `components/command-center.tsx`
- `components/case-table.tsx`
- `components/risk-panel.tsx`
- `components/evidence-list.tsx`
- `components/graph-view.tsx`
- `components/timeline-view.tsx`
- `components/recommendation-panel.tsx`
- `components/metrics-view.tsx`

## Current fixture cases
The v0 frontend contains CASE-1001 through CASE-1008.

The five important semantic demo cases:
- 1001 card testing
- 1002 ATO
- 1003 mule
- 1004 benign anomaly
- 1005 combined fraud

## Critical UI behaviour
`revealedAtStep` on evidence and graph elements is used by the UI to progressively reveal investigation findings.

`RecommendationPanel` requires:
- `recommendation.actions`
- `recommendation.summary`
- `recommendation.rationale[]`
- `recommendation.humanApprovalRequired`
- `recommendation.narrativeSource`
- `humanDecision`

`MetricsView` displays a warning when `measured === false`.

Therefore a backend returning placeholder evaluation numbers must keep `measured=false`.
