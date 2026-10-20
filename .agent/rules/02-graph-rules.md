---
trigger: glob
globs: backend/graph/**, backend/sim/**, backend/tests/**
description: Graph direction, idempotency and backend-parity rules
---
# Graph rules
- **`CALLS` points caller → callee.** Blast radius = walk **backwards** (callers of the changed service). Add a unit test on a 4-node chain that proves direction.
- Seeding uses `MERGE` and is **idempotent**; running `seed.py` twice must give the same counts (**54 nodes / 142 edges** exactly).
- Labels: `Service, Database, APIEndpoint, Pod, Incident, Decision`. Edges: `CALLS {latency_p99, protocol, confidence}`, `DEPENDS_ON`, `EXPOSES`, `INSTANCE_OF`, `OCCURRED_IN`, `RESOLVED_BY`.
- The **same pytest suite must pass on both Neo4j and NetworkX** repositories (parametrize the backend fixture). `reset()` restores the demo baseline.
- Ingestion-lite (Online Boutique) edges go in a **separate namespace** (`graph='boutique'`, `source='static'`, `confidence=0.6`) and must never alter the 54-node demo graph.
- Start with the minimum labels; add one only when a query needs it.
