# FraudLens — MASTER BACKEND EXECUTION PROMPT v2

You are the senior backend/AI engineer taking over the FraudLens project after the frontend has already been created in v0.

Your job is NOT to redesign the frontend.

Your job is to build the production-quality hackathon backend that makes the existing frontend truthful, live and demonstrable.

Before coding, read:
1. PRD.md
2. Architecture.md
3. Rules.md
4. Phases.md
5. Design.md
6. BACKEND_CONTRACT.md

Also inspect the frontend source itself, especially:
- `lib/types.ts`
- `lib/api.ts`
- `lib/fixtures/cases.ts`
- `lib/fixtures/graphs.ts`
- `lib/fixtures/timelines.ts`
- `lib/fixtures/store.ts`
- all `app/api/*` route handlers
- `components/case-workspace.tsx`
- `components/risk-panel.tsx`
- `components/evidence-list.tsx`
- `components/graph-view.tsx`
- `components/timeline-view.tsx`
- `components/recommendation-panel.tsx`
- `components/metrics-view.tsx`

The frontend is the contract.

---

# 1. PRODUCT NORTH STAR

FraudLens:

> An evidence-first autonomous fraud investigation agent that turns a flagged payment into an auditable case, identifies multiple fraud patterns with proof, recommends an action, and keeps the final decision with a human analyst.

Do not reduce the product to:
> transaction → model → fraud probability.

The investigation is the product.

---

# 2. NON-NEGOTIABLE FRONTEND COMPATIBILITY

The current v0 frontend already works against fixture Next.js routes.

Your job is to replace the fixture business logic with FastAPI without breaking the existing UI.

The browser should continue to call:
```text
/api/cases
/api/cases/{id}
/api/cases/{id}/investigate
/api/cases/{id}/decision
/api/cases/{id}/timeline
/api/cases/{id}/graph
/api/metrics
/api/health
```

Preferred integration:
- Next route handlers become thin HTTP proxies to FastAPI.
- FastAPI owns all business logic.
- Frontend component types remain unchanged.

Do NOT make frontend components call a new endpoint structure unless absolutely necessary.

Do NOT make the frontend read SQLite.

Do NOT duplicate fraud logic in TypeScript.

---

# 3. EXACT DATA CONTRACT

Match the existing frontend `lib/types.ts` exactly.

Important types:

RiskLevel:
```text
LOW | MEDIUM | HIGH | CRITICAL
```

PatternType:
```text
CARD_TESTING
ACCOUNT_TAKEOVER
MULE_NETWORK
BEHAVIOURAL_ANOMALY
```

CaseStatus:
```text
AWAITING_DECISION
APPROVED
OVERRIDDEN
```

Severity:
```text
LOW | MEDIUM | HIGH
```

RecommendedAction:
```text
APPROVE | HOLD | ESCALATE | BLOCK
```

Do not introduce new enum values without first updating the frontend contract.

---

# 4. FIRST TASK — CONTRACT VERIFICATION

Before implementing business logic:

1. inspect frontend types,
2. inspect frontend API hooks,
3. inspect all fixture response shapes,
4. create Pydantic schemas matching them,
5. add contract tests.

A Python response must serialize into JSON that can be consumed directly by the existing TypeScript interfaces.

No:
```json
{"data": ...}
```

unless the frontend is changed.

---

# 5. BUILD ORDER

Do not start with the LLM.

Build in this order:

## Phase A
FastAPI + health + CORS + config.

## Phase B
SQLite + models + deterministic synthetic data.

## Phase C
GET cases + GET case + graph + timeline.

## Phase D
Card-testing vertical slice.

## Phase E
ATO.

## Phase F
Mule network.

## Phase G
Benign anomaly + combined case.

## Phase H
Risk engine + recommendation.

## Phase I
Human decisions.

## Phase J
Evaluation metrics.

## Phase K
Optional LLM narrative.

## Phase L
Next proxy integration.

## Phase M
Deployment + QA.

---

# 6. DATA MODEL

Implement:
- customers
- accounts
- cards
- devices
- ips
- merchants
- transactions
- logins
- profile_events
- cases
- evidence
- patterns
- investigation_steps
- decisions if useful

Use SQLite.

Use deterministic seed data.

Keep evaluation ground truth separate from detector-accessible fields.

---

# 7. SYNTHETIC WORLD

Generate realistic normal behaviour.

Do not make legitimate customers identical.

Include:
- regular customers,
- frequent shoppers,
- high-value customers,
- travellers,
- multi-device users.

Include legitimate look-alikes.

Fraud scenarios:
- card testing,
- account takeover,
- mule chain,
- combined fraud.

---

# 8. DEMO CASES MUST EXIST

Preserve:

### CASE-1001
Card testing.

### CASE-1002
Account takeover.

### CASE-1003
Mule network.

### CASE-1004
Benign anomaly.

### CASE-1005
Combined fraud.

The existing frontend is visually designed around these cases.

The backend should reproduce their semantic stories.

---

# 9. CARD TESTING

Detect combinations of:
- many cards,
- low-value attempts,
- compressed time,
- elevated decline rate,
- device/IP concentration.

Produce evidence objects with:
- observed,
- baseline,
- whyItMatters,
- source,
- revealedAtStep.

CASE-1001 should reveal:
1 transaction,
2 baseline,
3 velocity,
4 device,
5 detector,
6 evidence,
7 risk,
8 recommendation.

---

# 10. ACCOUNT TAKEOVER

Detect combinations of:
- device novelty,
- region novelty,
- unusual login time,
- credential/profile changes,
- new payment method,
- transaction amount deviation.

New device alone is NOT enough.

CASE-1002 should tell the same story as the existing frontend fixture.

---

# 11. MULE NETWORK

Use NetworkX.

Detect:
- fan-in,
- fan-out,
- rapid onward transfers,
- pass-through ratio,
- multi-hop paths,
- new account context,
- suspicious counterparties.

CASE-1003 must produce a graph compatible with the frontend's current SVG graph renderer.

The graph renderer expects:
- layer,
- node type,
- label,
- sublabel,
- suspicious,
- attributes,
- revealedAtStep.

---

# 12. COMBINED CASE

CASE-1005 is the demo climax.

It should show:
- new device,
- unusual region,
- credential change,
- large amount deviation,
- suspicious recipient,
- pass-through,
- fan-out,
- multiple fraud patterns.

The backend should calculate multiple PatternScore objects.

---

# 13. BENIGN CASE

CASE-1004 is equally important.

It demonstrates that the product does not simply equate anomaly with fraud.

Use:
- new device,
- travel,
- MFA,
- known travel history,
- known corridor,
- no suspicious network.

Recommendation:
APPROVE.

This is critical to the problem statement's false-alarm requirement.

---

# 14. EVIDENCE-FIRST ARCHITECTURE

Every detector returns structured evidence.

Example:
```json
{
  "id": "EV-501",
  "type": "DEVICE_NOVELTY",
  "pattern": "ACCOUNT_TAKEOVER",
  "title": "New device detected",
  "claim": "New device detected",
  "observed": "D981",
  "baseline": "D014",
  "whyItMatters": "Device has never previously appeared in this account's login history.",
  "severity": "HIGH",
  "polarity": "SUPPORTING",
  "source": {
    "table": "logins",
    "eventId": "L9281"
  },
  "revealedAtStep": 4
}
```

Never generate evidence only as prose.

---

# 15. RISK ENGINE

Risk score is 0–100.

Use evidence channels:
- behaviour,
- velocity,
- device,
- graph,
- ML,
- pattern scores.

Return RiskFactor objects because the frontend displays each contribution.

Do not call the score a fraud probability unless calibrated.

---

# 16. RECOMMENDATION

Return:
- actions,
- summary,
- rationale,
- evidenceIds,
- humanApprovalRequired,
- narrativeSource.

Every rationale statement should point to evidence IDs.

If LLM is disabled:
`narrativeSource = "TEMPLATE"`.

If an LLM safely generated the narrative:
`narrativeSource = "LLM"`.

Do not claim an LLM was used if it wasn't.

---

# 17. HUMAN DECISION

Implement:

POST `/api/cases/{id}/decision`

APPROVE:
```json
{"decision":"APPROVE"}
```

OVERRIDE:
```json
{
  "decision":"OVERRIDE",
  "overrideAction":"APPROVE",
  "note":"Customer confirmed..."
}
```

Return updated CaseDetail.

Persist the decision.

---

# 18. INVESTIGATION TIMELINE

The existing frontend animates timeline steps and reveals evidence/graph elements according to step numbers.

Therefore:
- steps start at 1,
- steps are sequential,
- durations are numeric milliseconds,
- statuses use the existing enum,
- evidence and graph elements reference valid steps.

Recommended combined case:

1. Transaction context retrieved
2. Customer baseline calculated
3. Velocity analysed
4. Device anomaly detected
5. Network expanded
6. Mule pattern detected
7. Evidence consolidated
8. Risk score calculated
9. Recommendation generated

---

# 19. GRAPH CONTRACT

Allowed node types:
- customer
- account
- device
- card
- merchant
- transaction
- ip

Allowed edges:
- owns
- uses
- paid
- transferred
- logged_in

Each graph node must include:
- id
- type
- label
- sublabel
- layer
- suspicious
- attributes
- revealedAtStep

Each edge:
- id
- source
- target
- kind
- optional label
- suspicious
- revealedAtStep

Do not return a graph image.
Return structured graph data.

---

# 20. METRICS

The existing MetricsView explicitly distinguishes measured and fixture values.

During development:
```text
measured = false
```

After evaluation:
```text
mode = "live"
measured = true
```

Metrics must be calculated from a held-out test set.

Required:
- TP
- FP
- TN
- FN
- precision
- recall
- F1
- false-positive rate
- per-pattern detection
- look-alike clearance
- average evidence/case
- average graph entities
- human override rate

Never put placeholder numbers into a measured response.

---

# 21. ML

Use ML as one evidence channel.

Preferred:
- GradientBoosting / HistGradientBoosting or XGBoost if already available and stable.
- IsolationForest optionally.

Features:
- amount deviation,
- velocity,
- decline rate,
- new device,
- new IP,
- new merchant,
- hour deviation,
- location deviation,
- account age,
- recipient degree,
- fan-in,
- fan-out,
- onward-transfer delay.

Do not make ML the only detector.

Do not start with GNN.

---

# 22. AGENT

Only add the LLM/agent after deterministic investigation works.

A single investigator is enough.

The agent may:
- choose next investigation tool,
- compare hypotheses,
- synthesize evidence,
- generate narrative.

It may not:
- invent evidence,
- invent metrics,
- directly access raw database without controlled tools,
- make final decisions.

Use LangGraph only if it is fast to integrate.

Otherwise implement an explicit Python state machine.

Do not lose hackathon time proving that a framework is "agentic."

---

# 23. FAILURE MODE

LLM failure:
→ template narrative.

ML failure:
→ deterministic detector evidence.

Graph failure:
→ structured linked entities.

Database failure:
→ only explicit demo fixture fallback.

Never silently substitute fake data.

---

# 24. TESTING

Create:
- detector unit tests,
- risk tests,
- schema/contract tests,
- API tests,
- end-to-end case tests.

Golden tests:
- CASE-1001 → card testing
- CASE-1002 → ATO
- CASE-1003 → mule
- CASE-1004 → benign
- CASE-1005 → combined

End-to-end:
```text
GET case
→ POST investigate
→ GET timeline
→ GET graph
→ GET case
→ POST decision
→ GET case
```

---

# 25. NEXT.JS PROXY

The existing frontend currently has Next route handlers that return fixture data.

Replace their business logic with proxy calls to:
`FRAUDLENS_BACKEND_URL`

Example:
```text
GET /api/cases
→ Next route
→ GET ${FRAUDLENS_BACKEND_URL}/api/cases
→ return backend JSON
```

Do this for all `/api/*` routes.

Do not leave old fixture store logic active after live integration.

Keep fixtures only for explicit offline UI development.

---

# 26. ENVIRONMENT

Backend:
```text
DATABASE_URL=sqlite:///./fraudlens.db
LLM_API_KEY=
LLM_MODEL=
ENABLE_LLM=false
CORS_ORIGINS=
```

Frontend:
```text
FRAUDLENS_BACKEND_URL=
```

Never hard-code secrets.

---

# 27. DEPLOYMENT

The final system should be:

```text
Browser
 ↓
Next.js
 ↓
Next /api proxy
 ↓
FastAPI
 ↓
SQLite
```

If hosting supports a unified reverse proxy, preserve the same public `/api/*` paths.

---

# 28. DO NOT TOUCH UNNECESSARILY

Do not redesign:
- colors,
- typography,
- card structure,
- risk ring,
- graph layout,
- evidence layout,
- timeline,
- recommendation panel,
- metrics layout.

The frontend has already been deliberately designed.

Your job is to make it real.

---

# 29. DEFINITION OF DONE

Backend is complete only when:

- FastAPI health works.
- Frontend can reach backend.
- `/api/cases` renders real backend cases.
- Case detail renders real evidence.
- Investigation works.
- Timeline is generated by backend.
- Graph is generated by backend.
- Risk factors are generated by backend.
- Recommendation is generated by backend.
- Human decision persists.
- Metrics come from evaluation.
- LLM fallback works.
- CASE-1001..1005 work.
- deployment works.
- no frontend fixture business logic remains in live mode.

---

# 30. FINAL PRIORITY ORDER

When time is limited:

1. contract correctness,
2. synthetic data,
3. three detectors,
4. evidence,
5. risk,
6. graph,
7. human decision,
8. API integration,
9. evaluation,
10. deployment,
11. LLM,
12. polish.

A complete deterministic investigator is better than an impressive but unreliable agent.

Build the system the frontend already promises.

Make every visible claim true.

Then make it intelligent.
