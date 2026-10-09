# FraudLens — Backend-to-Frontend Design Compatibility

## Purpose
This file is not a second frontend design spec.

It translates the already-created v0 frontend into backend presentation contracts.

## Existing visual system observed from the frontend

- Light theme
- Background `#f8f8f6`
- White cards
- Primary text `#171717`
- Brand orange `#f97316`
- Brand dark `#c2410c`
- Soft orange `#fff1e8`
- Success green `#16a34a`
- Warning amber `#d97706`
- Danger red `#dc2626`
- Info blue `#2563eb`
- Inter
- JetBrains/system monospace
- compact 11–14px metadata
- 32px command-center heading
- 6px-ish card radius
- thin borders
- restrained animation

The backend must not attempt to reproduce these styles. It must supply semantic data that the existing components already know how to display.

## Frontend component → backend dependency

### CommandCenter
Consumes:
`GET /api/metrics`
`GET /api/cases`

Requires:
- overview
- riskDistribution
- patternDistribution
- case summaries

### CaseTable
Consumes:
`GET /api/cases`

Requires:
- caseId
- transactionId
- amount/currency
- customerName
- riskScore/riskLevel
- patterns
- status
- timestamp

### RiskPanel
Consumes:
`GET /api/cases/{id}`

Requires:
- riskScore
- riskLevel
- patternScores
- riskFactors

### EvidenceList
Consumes:
`GET /api/cases/{id}`

Requires:
- evidence
- polarity
- severity
- observed
- baseline
- whyItMatters
- source
- revealedAtStep

### GraphView
Consumes:
`GET /api/cases/{id}/graph`

Requires:
- typed nodes
- layer
- suspicious
- attributes
- revealedAtStep
- typed edges
- suspicious
- labels
- revealedAtStep

### TimelineView
Consumes:
`GET /api/cases/{id}/timeline`

Requires:
- sequential step
- label
- tool
- status
- summary
- timestamp
- durationMs

### RecommendationPanel
Consumes:
`GET /api/cases/{id}`
`POST /api/cases/{id}/decision`

Requires:
- actions
- summary
- rationale
- evidenceIds
- humanApprovalRequired
- narrativeSource
- humanDecision

### MetricsView
Consumes:
`GET /api/metrics`

Requires:
- measured flag
- evaluation
- confusion
- perPattern
- lookalikes
- agent behaviour
- distributions

## Demo progression requirement

The existing frontend deliberately reveals investigation information by step.

Therefore backend-generated `revealedAtStep` is part of the product experience, not decorative metadata.

Recommended CASE-1005 progression:

1. transaction context
2. customer baseline
3. velocity anomaly
4. device anomaly
5. network expansion
6. mule pattern
7. evidence consolidation
8. risk
9. recommendation

The evidence/graph should reveal naturally at the corresponding step.

## Visual semantics

Backend should use these semantic levels:
- LOW
- MEDIUM
- HIGH
- CRITICAL

Patterns:
- CARD_TESTING
- ACCOUNT_TAKEOVER
- MULE_NETWORK
- BEHAVIOURAL_ANOMALY

Actions:
- APPROVE
- HOLD
- ESCALATE
- BLOCK

Do not introduce arbitrary display labels in the API.

## Important frontend behaviour

The current frontend:
- sorts case queue by risk,
- renders evidence as cards,
- shows a score ring,
- displays factor contributions,
- renders a layered SVG graph,
- progressively reveals timeline/graph/evidence,
- supports analyst approval/override,
- displays a measured/unmeasured warning on metrics.

Backend must support those behaviours rather than redesigning them.
