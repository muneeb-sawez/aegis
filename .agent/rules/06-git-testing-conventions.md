---
trigger: always_on
description: Git, CI, testing and code conventions
---
# Conventions
- `main` is always runnable. Short feature branches; PR needs one review; CI must pass: **ruff + pytest + `npm run build`**.
- Commit format: `type(module): message`, e.g. `feat(M4): add BFS blast radius`.
- Tests: pytest; target **≥ 70% coverage** on `backend/sim/` and `backend/executor/`. Unit tests for blast radius, contract diff, Tarjan, risk formula, candidate scoring, allowlist, rollback.
- Python: type hints, Pydantic models for all API schemas, `ruff` clean. TypeScript: strict mode.
- Config via env vars (`GRAPH_BACKEND`, `LLM_PROVIDER`, `LLM_MODEL`, API keys). Provide `.env.example`; never commit secrets.
- After finishing any task, run the relevant tests and report pass/fail with output — do not claim "done" without running them.
- Each Friday the **whole loop** must run end to end, even crudely. If it is broken, fixing the loop outranks new features.
- Cut order if behind: timeline scrubber → Online Boutique view → cyclic-PR UI → CPU fault → fancy animation.
