# Build Guide reference (condensed) — for Phase 2

*Code samples are illustrative sketches; verify versions and metric names.*

## Git connection
- **Webhook (recommended):** GitHub POSTs signed push / pull_request events to FastAPI. Verify `X-Hub-Signature-256` HMAC (`hmac.compare_digest`) before trusting the payload; return fast; enqueue work.
- **CI step** (optional PR gate) · **Polling** (fallback if webhooks blocked).
- Dev tunnel: smee.io or ngrok. Auth for clone: fine-grained PAT (read-only Contents) or a GitHub App with short-lived tokens. Never log tokens; delete clones; store metadata only, not source.
- Worker: shallow clone (`--depth 50`), checkout `after`, `git diff --name-only before after`; if `before` is all zeros (new branch) scan everything; hand only changed files to scanners.
- `repos.yaml` maps repo → services (monorepo: service→folder; single-service: name).
- PR comment: on `pull_request` (opened/synchronize) run simulation and post via GitHub REST issue-comment. GitLab: `X-Gitlab-Token` header, Push Hook / Merge Request Hook.

## Four dependency layers
1. Libraries (package.json, requirements.txt, pom.xml, go.mod) → `(Service)-[:USES_LIB]->(Library)`
2. APIs (.proto, OpenAPI) → `(Service)-[:EXPOSES]->(API)`
3. Service→service (env vars/manifests static + traces runtime) → `CALLS`
4. Infrastructure (K8s API, connection strings) → `RUNS_ON`, `READS_WRITES`

## Runtime edges
OTel Collector service-graph connector → Prometheus. Example query: `sum by (client, server) (rate(traces_service_graph_request_total[10m]))` (verify metric/label names). Fallback: Linkerd/Istio, or static only (say so honestly).

## Confidence merge
static only 0.6 · runtime only 0.8 · both 0.95 · not seen for N days ⇒ decay then stale. Tunable heuristics, not research constants.

## Upsert pattern
```cypher
MERGE (a:Service {name: $caller}) MERGE (b:Service {name: $callee})
MERGE (a)-[r:CALLS]->(b)
SET r.source = $source, r.confidence = $confidence, r.rate = $rate, r.last_seen = timestamp()
```

## Blast radius query (Neo4j)
```cypher
MATCH p = (changed:Service {name: $name})<-[:CALLS*1..4]-(affected:Service)
WHERE ALL(r IN relationships(p) WHERE r.confidence >= 0.5)
RETURN affected.name AS service, min(length(p)) AS hops ORDER BY hops, service
```

## Build Guide risk formula (Phase 2 candidate; not validated)
`risk = 0.35·blast_radius + 0.25·incident_history + 0.20·change_size + 0.20·criticality` (each 0–1).

## Evaluation
Chaos runs vs manual and rule-based baselines, repeated trials; report precision/recall separately for static, runtime and merged edges. Feasibility note: ~54–58 person-weeks needed vs ~52 usable — cut line is mandatory.
