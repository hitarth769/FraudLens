# FraudLens — Product Requirements Document (Backend-Integrated v2)

## Status
LOCKED for implementation against the already-created v0 frontend.

## Product
FraudLens — Autonomous Evidence-First Fraud Investigation Agent.

## North Star
Turn a flagged payment into an evidence-backed, auditable fraud case in seconds while keeping the final decision with a human analyst.

## What is already built
The frontend has been generated and its typed contracts are the integration source of truth:
- Command Center
- Case Queue
- Investigation Workspace
- Metrics
- Risk panel
- Evidence cards
- Relationship graph
- Investigation timeline
- Recommendation + human approval/override

Do not redesign the frontend unless a backend contract makes a small compatibility fix necessary.

## Target users
### Fraud analyst
Needs rapid, evidence-backed, explainable case investigation and human control.

### Fraud operations lead
Needs throughput, fraud capture, false alarms, pattern performance and investigation time.

## Core workflow
Flagged payment
→ retrieve context
→ customer baseline
→ velocity analysis
→ device analysis
→ conditional network expansion
→ fraud pattern detectors
→ evidence consolidation
→ risk score
→ recommendation
→ human approval/override
→ audit trail

## Required fraud patterns
1. CARD_TESTING
2. ACCOUNT_TAKEOVER
3. MULE_NETWORK

Also support:
4. BEHAVIOURAL_ANOMALY as a contextual/non-fraud pattern.

## Required demo scenarios
- CASE-1001: card testing
- CASE-1002: account takeover
- CASE-1003: mule network
- CASE-1004: benign anomaly / legitimate look-alike
- CASE-1005: combined fraud
- CASE-1006..1008: additional queue/decision history

The backend must preserve these IDs and semantics so the existing frontend's designed demo experience remains coherent.

## Functional requirements
- Case queue with summary fields.
- Case detail.
- Investigation endpoint.
- Evidence with source references.
- Pattern scores.
- Risk factors.
- Risk score and level.
- Graph.
- Investigation timeline.
- Recommendation.
- Human decision.
- Metrics.
- Health endpoint.

## Important product distinction
The backend is not simply a classifier.

A classifier answers:
> How risky is this transaction?

FraudLens answers:
> What happened, what evidence supports it, what fraud patterns are present, what is it connected to, what should the analyst consider, and what decision should the human make?

## Non-goals
- Real payments
- Real customer PII
- Automatic irreversible blocking
- Microservices
- Kubernetes
- Graph database
- GNN before the MVP is stable
- Multi-agent complexity without demonstrated need
- Custom model training
- More fraud patterns before the required three are reliable

## Acceptance criteria
- Existing v0 frontend can run against the backend without changing its component contracts.
- All frontend API hooks receive the exact expected JSON shapes.
- Investigate reveals a coherent timeline/evidence/graph progression.
- Human decisions persist.
- Metrics are generated from held-out evaluation, not invented fixture claims.
- LLM can fail without taking the product down.
