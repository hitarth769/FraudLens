# FraudLens — Backend Execution Phases v2

## Phase 0 — Contract Freeze
Read:
- PRD.md
- Architecture.md
- Rules.md
- Design.md
- frontend `lib/types.ts`
- frontend `lib/api.ts`
- frontend API route handlers
- fixture cases/graphs/timelines

Do not code until the exact response contracts are understood.

Deliverable:
`BACKEND_CONTRACT.md` reviewed and accepted.

## Phase 1 — FastAPI Skeleton
Build:
- app
- health
- CORS/config
- error format
- `/api/*` endpoint shells.

Done when frontend can reach backend health.

## Phase 2 — Database + Synthetic Data
Build all core entities and event tables.
Generate deterministic normal population and planted cases.

Done when:
- seed script runs,
- relationships are valid,
- ground truth is separate,
- CASE-1001..1005 exist.

## Phase 3 — Case Read
Implement:
- GET cases
- GET case
- graph
- timeline.

Initially it is acceptable to serve deterministic case data from database/seeded services.

Done when existing frontend renders without fixture store.

## Phase 4 — Card Testing Vertical Slice
Implement:
- transaction lookup,
- history,
- velocity,
- device,
- detector,
- evidence,
- risk,
- recommendation,
- timeline.

Done when CASE-1001 is fully backed by Python.

## Phase 5 — ATO
Implement ATO detector and evidence.

CASE-1002 must match the designed frontend story.

## Phase 6 — Mule
Implement NetworkX investigation and mule detector.

CASE-1003 must render a coherent relationship graph.

## Phase 7 — Benign + Combined
CASE-1004 must demonstrate legitimate contextual explanation.
CASE-1005 must demonstrate multi-pattern convergence.

## Phase 8 — Decision Persistence
Implement:
POST `/api/cases/{id}/decision`.

Support:
- APPROVE
- OVERRIDE + action + note.

## Phase 9 — Real Metrics
Run held-out evaluation.
Populate live metrics.
Set `measured=true`.

No presentation metric may come from fixtures.

## Phase 10 — Optional LLM
Only now add LLM narrative.
Preserve template fallback.

## Phase 11 — Frontend Proxy Integration
Replace Next fixture handlers with thin FastAPI proxies or configure same-origin reverse proxy.

Remove or isolate:
- fixture store,
- fixture metrics,
- fixture API business logic.

Keep fixtures only as development fallback if explicitly named as such.

## Phase 12 — End-to-End QA
Test:
- case list,
- case detail,
- investigate,
- timeline,
- graph,
- decision,
- metrics,
- health,
- errors,
- reload/persistence.

## Phase 13 — Deployment
Deploy backend and connect existing frontend.

Verify:
- clean browser,
- no localhost assumptions,
- environment variables,
- health endpoint,
- all five demo cases.

## Phase 14 — Demo Freeze
No new architecture.

Demo order:
1. CASE-1001
2. CASE-1002
3. CASE-1003
4. CASE-1004
5. CASE-1005

Use CASE-1005 as the climax.

## Emergency mode
If behind:
1. database
2. case API
3. three deterministic detectors
4. evidence
5. graph
6. decision
7. metrics
8. deployment
9. optional LLM last
