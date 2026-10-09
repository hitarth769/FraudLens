# FraudLens — Backend Contract Lock

This is the single implementation checklist for Claude/backend.

## Existing frontend files inspected

- `lib/types.ts`
- `lib/api.ts`
- `lib/fixtures/cases.ts`
- `lib/fixtures/graphs.ts`
- `lib/fixtures/timelines.ts`
- `lib/fixtures/store.ts`
- `app/api/cases/route.ts`
- `app/api/cases/[id]/route.ts`
- `app/api/cases/[id]/investigate/route.ts`
- `app/api/cases/[id]/decision/route.ts`
- `app/api/cases/[id]/graph/route.ts`
- `app/api/cases/[id]/timeline/route.ts`
- `app/api/metrics/route.ts`
- `app/api/health/route.ts`
- `components/case-workspace.tsx`
- `components/risk-panel.tsx`
- `components/evidence-list.tsx`
- `components/graph-view.tsx`
- `components/timeline-view.tsx`
- `components/recommendation-panel.tsx`
- `components/metrics-view.tsx`

## Exact API response rule

The backend must return JSON matching the existing TypeScript interfaces exactly.

Do not wrap successful responses in:
```json
{"data": ...}
```
unless the frontend is changed.

Current frontend expects:
- `/api/cases` → `CaseSummary[]`
- `/api/cases/{id}` → `CaseDetail`
- `/api/cases/{id}/investigate` → `CaseDetail`
- `/api/cases/{id}/timeline` → `TimelineStep[]`
- `/api/cases/{id}/graph` → `CaseGraph`
- `/api/metrics` → `Metrics`
- `/api/health` → `Health`
- decision → updated `CaseDetail`

## Decision semantics

APPROVE:
- records recommendation approval,
- status becomes APPROVED.

OVERRIDE:
- requires overrideAction,
- requires non-empty note,
- status becomes OVERRIDDEN.

## Investigation semantics

`POST /investigate` must be idempotent enough for demo re-runs.

A re-run may:
- reuse deterministic evidence,
- update investigation timestamps/duration,
- regenerate the same semantic findings.

It must not duplicate evidence endlessly.

## Current fixture semantics that backend should preserve

### CASE-1001
Card testing:
- 29 attempts
- 14 cards
- 11-minute burst
- 66% declined
- device D555
- risk ~94
- critical
- BLOCK recommendation

### CASE-1002
ATO:
- new device D774
- Singapore login vs Mumbai baseline
- password reset before payment
- ₹72,500
- risk ~87
- HOLD + ESCALATE

### CASE-1003
Mule:
- recipient A-5520
- 3 inbound senders
- 96% pass-through
- rapid onward transfers
- multi-hop/cash-out relationship
- risk ~89
- HOLD + ESCALATE

### CASE-1004
Benign anomaly:
- travel customer
- new device
- UK purchase
- MFA passed
- historical foreign travel
- risk ~24
- APPROVE

### CASE-1005
Combined:
- new device D981
- unusual region
- credential changes
- ₹48,000
- recipient A-9902
- 97% pass-through
- 3-way fan-out
- multiple patterns
- risk ~91
- HOLD + ESCALATE

These are demo semantics. The backend may calculate the values rather than hard-code them, but the seeded scenario should reproduce the same story.

## Health

Current frontend expects:
```json
{
  "status": "ok",
  "mode": "live",
  "llm": "available",
  "version": "backend-0.1"
}
```

If LLM is disabled:
```json
{
  "status": "ok",
  "mode": "live",
  "llm": "unavailable",
  "version": "backend-0.1"
}
```

## Metrics

Development:
`measured=false`

Final:
`measured=true`

Never show placeholder evaluation as measured.

## Proxy integration

Recommended:
Next.js route handlers call:

`FRAUDLENS_BACKEND_URL + request.path`

and forward:
- method,
- body,
- content type,
- relevant headers.

This lets the browser continue using `/api/*` exactly as currently coded.

The Next layer should not contain fraud logic after integration.
