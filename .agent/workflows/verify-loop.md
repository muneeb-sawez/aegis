---
description: AEGIS — Friday end-to-end loop check (run every week)
---
# /verify-loop — run the whole loop, even if crude

Run and report pass/fail for each step (use whichever parts exist for the current week):
1. `docker compose up` (or `GRAPH_BACKEND=networkx`) starts cleanly; `GET /api/graph/topology` returns **54 nodes / 142 edges**.
2. `POST /api/simulate-pr` for PR #142 returns a score **computed by code**; record it (call it X).
3. `POST /api/chaos/inject` with pool exhaustion → telemetry changes → **exactly one** anomaly event.
4. `GET /api/heal/stream` streams `thought`/`cypher`/`result`/`candidates`/`done` events (LLM or fallback).
5. `POST /api/actuator/execute`: good fix heals; bad fix rolls back; non-allowlisted action refused.
6. `POST /api/memory/commit` writes the Incident; re-run PR #142 → score is **X + 5** (or the honest increase).
7. `POST /api/reset` restores X.
8. `ruff`, `pytest`, and the frontend build all pass.

Output a table of step → pass/fail → evidence. If any step fails, **fixing the loop outranks new features**. Do not mark anything passing without running it.
