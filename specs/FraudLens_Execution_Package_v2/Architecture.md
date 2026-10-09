# FraudLens — Backend Architecture v2

## 1. Critical integration decision

The uploaded v0 frontend is the visual and interaction source of truth.

The Python backend is the source of truth for:
- cases,
- evidence,
- risk,
- patterns,
- graph,
- timeline,
- recommendations,
- decisions,
- metrics.

Do NOT duplicate fraud logic in Next.js.

### Runtime

```text
Browser
  │
  ▼
Next.js / v0 Frontend
  │
  │ /api/*
  ▼
Next API proxy routes
  │
  │ HTTP/JSON
  ▼
FastAPI
  │
  ├── Case service
  ├── Investigation orchestrator
  ├── Evidence service
  ├── Pattern detectors
  ├── Risk engine
  ├── Graph investigator
  ├── Evaluation service
  └── Optional LLM narrative
  │
  ▼
SQLite + generated synthetic dataset
```

The Next route handlers already present in the frontend should become thin proxy adapters. If deployment supports a same-origin reverse proxy directly to FastAPI, they may instead be removed; do not make the frontend depend on a new client-side API shape.

## 2. Exact frontend contract

The backend MUST match the TypeScript contracts currently defined by the frontend.

### CaseSummary
```json
{
  "caseId": "CASE-1005",
  "transactionId": "TXN-50291",
  "amount": 48000,
  "currency": "INR",
  "customerName": "Aarav Mehta",
  "accountId": "A-7741",
  "counterparty": "A-9902",
  "timestamp": "2026-10-08T03:18:42+05:30",
  "riskScore": 91,
  "riskLevel": "HIGH",
  "patterns": ["ACCOUNT_TAKEOVER", "MULE_NETWORK", "BEHAVIOURAL_ANOMALY"],
  "status": "AWAITING_DECISION",
  "recommendedActions": ["HOLD", "ESCALATE"],
  "investigationDurationSec": 7.2,
  "scenario": "COMBINED_FRAUD"
}
```

### CaseDetail
Must contain:
- all CaseSummary fields,
- `customer`
- `transaction`
- `evidence`
- `patternScores`
- `riskFactors`
- `recommendation`
- `humanDecision`

### EvidenceItem
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

### PatternScore
```json
{
  "pattern": "MULE_NETWORK",
  "score": 84,
  "confidence": "HIGH",
  "supporting": 4,
  "contradicting": 0
}
```

### RiskFactor
```json
{
  "label": "Recipient connected to suspicious accounts",
  "channel": "Graph",
  "points": 30
}
```

### Recommendation
```json
{
  "actions": ["HOLD", "ESCALATE"],
  "summary": "Three independent evidence channels converge on coordinated fraud.",
  "rationale": [
    {
      "text": "Recipient forwards 97% of inbound funds.",
      "evidenceIds": ["EV-507", "EV-508"]
    }
  ],
  "humanApprovalRequired": true,
  "narrativeSource": "LLM"
}
```

### HumanDecision
```json
{
  "decision": "OVERRIDE",
  "overrideAction": "APPROVE",
  "note": "Customer confirmed...",
  "analyst": "Analyst",
  "decidedAt": "2026-10-08T..."
}
```

## 3. Exact endpoints

```text
GET  /api/health
GET  /api/cases
GET  /api/cases/{id}
POST /api/cases/{id}/investigate
POST /api/cases/{id}/decision
GET  /api/cases/{id}/timeline
GET  /api/cases/{id}/graph
GET  /api/metrics
```

All success responses are JSON matching the frontend's existing TypeScript interfaces.

All errors:
```json
{
  "error": "human-readable message"
}
```

## 4. Decision contract

Request:
```json
{
  "decision": "APPROVE"
}
```

or:
```json
{
  "decision": "OVERRIDE",
  "overrideAction": "APPROVE",
  "note": "Customer confirmed the purchase."
}
```

Rules:
- `APPROVE` does not require `overrideAction`.
- `OVERRIDE` requires `overrideAction` and a non-empty note.
- Persist analyst decision.
- Return updated `CaseDetail`.

## 5. Investigation response contract

`POST /api/cases/{id}/investigate` returns the updated full `CaseDetail`.

The frontend does not expect a separate job ID.

Therefore the backend may execute synchronously for the hackathon.

If the implementation uses an internal job/state machine, wait for completion before returning unless the frontend is deliberately changed.

## 6. Reveal/progression contract

The existing frontend reveals graph nodes and evidence according to `revealedAtStep`, and timeline according to `step`.

Therefore:
- every evidence item must have a valid `revealedAtStep`,
- every graph node must have `revealedAtStep`,
- every graph edge must have `revealedAtStep`,
- timeline steps must be sequential integers starting at 1.

The investigation should produce these deterministically.

## 7. Graph contract

```json
{
  "nodes": [
    {
      "id": "A-9902",
      "type": "account",
      "label": "A-9902",
      "sublabel": "Recipient",
      "layer": 3,
      "suspicious": true,
      "attributes": {
        "Account age": "17 days",
        "Pass-through": "97%"
      },
      "revealedAtStep": 5
    }
  ],
  "edges": [
    {
      "id": "E-A9902-A9913",
      "source": "A-9902",
      "target": "A-9913",
      "kind": "transferred",
      "label": "₹15,200 · 6m",
      "suspicious": true,
      "revealedAtStep": 6
    }
  ]
}
```

Allowed node types:
- customer
- account
- device
- card
- merchant
- transaction
- ip

Allowed edge kinds:
- owns
- uses
- paid
- transferred
- logged_in

Do not invent new enum values unless the frontend is updated first.

## 8. Timeline contract

Each step:
```json
{
  "step": 1,
  "label": "Transaction context retrieved",
  "tool": "get_transaction",
  "status": "completed",
  "summary": "TXN-50291 · ₹48,000 · bank transfer to A-9902",
  "timestamp": "2026-10-08T...",
  "durationMs": 190
}
```

Allowed statuses:
- completed
- warning
- suspicious
- failed

## 9. Metrics contract

The frontend expects:
- mode: `fixture` or `live`
- measured: boolean
- evaluatedAt
- overview
- riskDistribution
- patternDistribution
- evaluation

When evaluation is not actually run:
- `measured` MUST be false.
- Do not present illustrative values as measured.

Once evaluation is wired:
- `mode = "live"`
- `measured = true`
- values come from the held-out evaluation output.

## 10. Backend modules

```text
backend/
  app/
    main.py
    api/
      health.py
      cases.py
      decisions.py
      metrics.py
    core/
      config.py
    db/
      session.py
      models.py
      seed.py
    schemas/
      case.py
      graph.py
      timeline.py
      metrics.py
      decision.py
    investigation/
      state.py
      orchestrator.py
      timeline.py
    tools/
      transaction.py
      history.py
      velocity.py
      device.py
      network.py
    detectors/
      card_testing.py
      account_takeover.py
      mule_network.py
      behavioural.py
    risk/
      scoring.py
      calibration.py
    evidence/
      builder.py
    narrative/
      llm.py
      template.py
    evaluation/
      evaluate.py
      metrics.py
    data/
      generator.py
      scenarios.py
```

Keep the package structure simple if the team prefers fewer files, but preserve these responsibilities.

## 11. Persistence

SQLite is sufficient.

Use SQLAlchemy + Pydantic if time permits.

Do not introduce PostgreSQL unless deployment requires it.

The frontend must never access SQLite directly.

## 12. LLM architecture

The LLM receives:
- case context,
- structured evidence,
- pattern scores,
- risk factors,
- recommendation candidates.

It does not query the database directly.

It must return structured narrative data or fall back to templates.

The backend must validate any LLM output before returning it.

## 13. Deployment

Preferred:
- Next.js frontend,
- FastAPI backend,
- SQLite/data assets.

Use environment variable:
`FRAUDLENS_BACKEND_URL`

The Next API routes can proxy requests to FastAPI using this variable.

If the frontend and backend are deployed under one origin through a reverse proxy, retain the same `/api/*` paths.

## 14. Compatibility rule

Do not change frontend TypeScript types just to make backend implementation easier.

If a backend need conflicts with the current types, adapt the backend first.

Only change frontend types when a real product requirement is impossible under the existing contract.
