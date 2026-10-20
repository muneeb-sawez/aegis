# Integration contracts (FROZEN after Week 1)

## 1. Graph schema (owner: A)
- **Node labels:** `Service`, `Database`, `APIEndpoint`, `Pod`, `Incident`, `Decision`.
- **Edges:** `CALLS {latency_p99, protocol, confidence}`, `DEPENDS_ON`, `EXPOSES`, `INSTANCE_OF`, `OCCURRED_IN`, `RESOLVED_BY`.
- Seed target: **8 services, 6 datastores, 40 endpoints/pods = 54 nodes; 142 edges.** Includes the demo dependency **PaymentService → Postgres** with realistic latencies. Kafka appears only as a node.
- Telemetry properties on nodes (emulated): e.g. `p99_ms`, `baseline_p99_ms`, `error_rate`, `connections`, `pool_size`, `status`.
- Neo4j constraints in `backend/graph/schema.cypher` (uniqueness on node ids/names).

## 2. Edge direction rule
`CALLS` = **caller → callee**. Blast radius walks **backwards** (callers of the changed service).

## 3. `GraphRepository` interface (owner: A) — the only graph access outside `graph/`
```python
get_topology() -> Topology                      # nodes + edges + telemetry
neighbors(node: str, hops: int) -> Subgraph
callers(node: str, depth: int) -> list[Caller]  # [(node, hops)] walking backwards over CALLS
incidents(node: str, days: int) -> list[Incident]
set_telemetry(node: str, fields: dict) -> None
add_incident(...) -> Incident                   # also creates Decision, OCCURRED_IN, RESOLVED_BY
reset() -> None                                 # restore demo baseline
```
Implementations: `neo4j_repo.py`, `networkx_repo.py`; selected by `GRAPH_BACKEND`.

## 4. REST/SSE API (owner: D publishes OpenAPI in Week 1 with stub responses)
| Endpoint | Purpose |
|---|---|
| `GET /api/graph/topology` | nodes, edges, telemetry for the canvas |
| `POST /api/simulate-pr` | body: PR id/payload → score, category breakdown, gate verdict, blast radius with `impact_weight`, contract diff |
| `POST /api/chaos/inject` | body: fault id → starts emulated fault |
| `GET /api/heal/stream` | **SSE** stream of the diagnosis/heal run |
| `POST /api/actuator/execute` | execute an allowlisted action (guarded) |
| `POST /api/memory/commit` | write Incident/Decision back to the graph |
| `POST /api/reset` | restore demo baseline in one click |
| `GET /api/heal/events` | polling fallback if SSE is blocked |

## 5. SSE event envelope
```json
{ "type": "thought | cypher | result | candidates | done", "ts": "ISO-8601", "payload": { } }
```
UI renders by `type` (`thought` and `cypher` look different in the terminal; `candidates` renders ranked fix cards).

## 6. Data files
`data/topology.yaml` · `data/prs/*.json` (Safe, Moderate, Breaking #142, Cyclic, + leaf-service and gateway cases) · `data/faults/*.json` · `data/cached_rca/*.json`.
Fault example: pool exhaustion ⇒ Payment p99 38 → 3400 ms, Postgres `connections=100/100`, error rate 0.4.
