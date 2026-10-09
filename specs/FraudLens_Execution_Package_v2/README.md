# FraudLens Execution Package v2

This package is the backend-focused continuation of the FraudLens war room after the v0 frontend was generated.

## Source of truth

The frontend ZIP was inspected directly.

The backend package is therefore aligned to:
- existing TypeScript interfaces,
- existing API hooks,
- existing API paths,
- existing fixture semantics,
- existing graph/timeline reveal behaviour,
- existing decision flow,
- existing metrics UI,
- existing light/orange design system.

## Files

- `MASTER_PROMPT.md` — give this to Claude as the backend execution prompt.
- `BACKEND_CONTRACT.md` — exact frontend/backend contract.
- `PRD.md` — product requirements.
- `Architecture.md` — runtime and backend architecture.
- `Rules.md` — engineering and AI boundaries.
- `Phases.md` — execution sequence.
- `Design.md` — backend compatibility with the existing v0 visual experience.

## Important

The frontend is already designed. Do not redesign it.

The Next.js `/api/*` routes currently contain fixture business logic. Convert them to thin proxies to FastAPI or use a same-origin reverse proxy.

FastAPI becomes the source of truth.

## Memory.md

Create `Memory.md` only once backend implementation begins.

Track:
- current phase,
- completed tasks,
- API changes,
- schema changes,
- blockers,
- bugs,
- decisions,
- deployment,
- demo status,
- exact next task.

Update it after each meaningful coding session.
