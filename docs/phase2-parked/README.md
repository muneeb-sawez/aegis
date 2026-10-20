# Phase 2 (Weeks 11–20) — PARKED. Do NOT implement in Phase 1.

| Weeks | Focus |
|---|---|
| 11–12 | kind cluster, Online Boutique deployed, Prometheus + Grafana; graph switches from seed to scanned data |
| 13–14 | Live Git webhook, HMAC verification, worker, `repos.yaml`, PR comments |
| 15–16 | OpenTelemetry service-graph edges, confidence merge (static 0.6 / runtime 0.8 / both 0.95), edge precision & recall |
| 17 | Alertmanager trigger, RCA agent on real alerts |
| 18 | Real kubectl actuator (allowlist), rollback tested first |
| 19 | LitmusChaos runs, 4+ fault types, repeated trials, manual & rule-based baselines |
| 20 | Evaluation report, final demo, paper |

Phase 1 code should keep seams that make this easy (the `GraphRepository` interface, the allowlisted action interface, the SSE envelope) — but must not implement any of the above.

Reference material for later: `build-guide-reference.md` in this folder.
