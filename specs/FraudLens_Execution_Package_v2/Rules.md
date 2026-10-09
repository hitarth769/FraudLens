# FraudLens — Backend Rules v2

## 1. Source of truth
Backend is authoritative for all fraud facts and metrics.

Frontend fixture files are design references only. They must not remain the production source of truth after integration.

## 2. Never invent evidence
Every evidence item must originate from:
- database event,
- deterministic calculation,
- graph relationship,
- ML output,
- or explicit synthetic ground truth used only for evaluation.

Every material claim must be traceable.

## 3. LLM boundary
Allowed:
- orchestration,
- hypothesis synthesis,
- narrative,
- recommendation wording.

Forbidden:
- raw fact creation,
- arbitrary risk score creation,
- metric creation,
- decision execution,
- unsupported claims.

## 4. Human decision
The agent recommends.
The analyst decides.
No autonomous irreversible blocking.

## 5. Synthetic data
Use synthetic data only.
Ground truth labels must not leak into detector features.
Use fixed seeds for reproducibility.

## 6. Fraud detector philosophy
No single signal is a verdict.

### Card testing
Use combinations of:
- low value,
- card fan-out,
- velocity,
- decline rate,
- device/IP concentration.

### ATO
Use combinations of:
- device novelty,
- region novelty,
- login-time anomaly,
- credential/profile change,
- amount deviation,
- payment-method change.

### Mule
Use combinations of:
- fan-in,
- fan-out,
- pass-through,
- rapid onward movement,
- multi-hop path,
- account age,
- counterparties.

### Benign anomaly
Legitimate context can offset suspicious signals:
- travel history,
- MFA,
- established device relationships,
- known merchant/corridor,
- prior similar activity.

## 7. Risk score
0–100 project risk score.
Do not call it a probability unless statistically calibrated.

Risk factors must be returned individually because the existing frontend displays them.

## 8. Investigation
Prefer deterministic tool execution.

Conditional expansion is encouraged:
- new device → inspect device/account relationships,
- suspicious recipient → expand recipient network,
- strong velocity → inspect temporal cluster.

Do not add agent complexity that cannot be defended.

## 9. Graph
Use NetworkX.
Keep investigation local, usually depth 2.
All highlighted graph relationships must correspond to evidence.

## 10. API compatibility
Do not change:
- endpoint names,
- enum values,
- required fields,
- response shape

without coordinating with the frontend.

## 11. Errors
Return:
```json
{"error": "message"}
```
with proper HTTP status.

Never return HTTP 200 for failed investigations.

## 12. Logging
Log:
- request ID,
- case ID,
- investigation duration,
- detector statuses,
- errors.

Do not log:
- API secrets,
- raw credentials,
- sensitive personal data.

## 13. Testing
Every detector must have:
- positive planted case,
- negative benign case,
- edge case.

Integration test:
case → investigate → detail → timeline → graph → decision.

## 14. Metrics integrity
Only evaluation output may populate measured metrics.
Fixtures may be used for UI development but must remain marked `measured=false`.

## 15. Fallbacks
LLM failure → template narrative.
ML failure → deterministic detector/rule evidence.
Graph failure → linked-entity table data.
Do not fabricate a successful result.

## 16. Frontend compatibility
The backend must produce data suitable for:
- risk ring,
- pattern bars,
- evidence cards,
- graph,
- timeline,
- recommendation panel,
- metrics panels.

Do not return presentation-specific HTML.

## 17. Scope
MUST:
- API contract,
- synthetic data,
- three detectors,
- evidence,
- risk,
- graph,
- timeline,
- recommendation,
- decision,
- metrics.

DEFER:
- GNN,
- real-time streaming,
- graph database,
- advanced analyst learning,
- additional fraud types.
