---
trigger: always_on
description: Frozen integration contracts and architecture boundaries for AEGIS Phase 1
---
# Architecture & contract rules
- Contracts in `docs/02-CONTRACTS.md` are frozen after Week 1. Changing one requires: a written proposal, human approval, an update to the doc, and updates to every consumer in the same PR.
- Only the **Graph & Data owner (A)** edits `schema.cypher` and `data/topology.yaml`. Others request changes via an issue/note.
- All Neo4j/Cypher lives in `backend/graph/`. Outside that folder call only `GraphRepository` methods: `get_topology()`, `neighbors(node, hops)`, `callers(node, depth)`, `incidents(node, days)`, `set_telemetry(node, fields)`, `add_incident(...)`, `reset()`.
- Python only. No new languages, no real Kafka, no message broker.
- The UI is built against the OpenAPI stubs first; real endpoints replace stubs without changing the response shape.
- SSE events always use the envelope `{type: 'thought'|'cypher'|'result'|'candidates'|'done', ts, payload}`. The UI renders by `type`.
- Weights/thresholds live in one place: `backend/sim/config.py`. No magic numbers elsewhere.
