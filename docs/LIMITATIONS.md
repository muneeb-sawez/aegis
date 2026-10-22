# AEGIS Technical Limitations & Roadmap

> **Document Version**: 2.0.0-RELEASE  
> **Audited Date**: October 2026  
> **Source Repository**: `muneeb-sawez/aegis`

---

## 1. Real vs. Simulated Boundaries (Phase 1)

In Phase 1, AEGIS is focused on proving graph-grounded reasoning, closed-loop safety, and algorithmic prediction on standard developer hardware without requiring cloud billing accounts.

| Subsystem / Operation | Real Implementation in Phase 1 | Simulated / Emulated in Phase 1 |
| :--- | :--- | :--- |
| **Knowledge Graph** | Full in-memory NetworkX or Docker Neo4j graph with 54 nodes and 142 edges. Cypher queries and graph algorithms are 100% real. | No real microservice pods or physical host machines are deployed. |
| **PREDICT Risk Model** | Real backward BFS caller traversal, real AST contract diffing, real Tarjan SCC cycle detection, and composite formula. | Evaluates structured change payloads and OpenAPI specs rather than raw Git commit patches. |
| **MONITOR Telemetry** | Asynchronous HTTP prober with live SSRF IP validation. | Telemetry metrics (latency spikes, pool exhaustion, error percentages) are mathematically simulated in-memory. |
| **RCA Diagnostic Agent** | Real LiteLLM API calls to Gemini/Groq/Ollama. Real Pydantic schema validation and graph context extraction. | Operates over graph-supplied metric drift rather than reading raw log files or Prometheus time-series streams. |
| **HEAL Actuator** | Strict allowlist gating, per-service `asyncio.Lock`, atomic snapshotting, and automated health rollback watchdog. | Modifies graph telemetry records and simulated service states rather than executing `kubectl apply` on a cloud cluster. |
| **Feedback Learning Loop** | Real `(:Incident)` and `(:Outcome)` nodes written to the graph repository, causing subsequent risk scores to measurably shift $+5.0$. | Operates in-process on the active graph database. |

---

## 2. Present Technical Limitations

1. **Structured Change Specifications Only**: The Change-Risk Engine accepts JSON/YAML schema definitions and proposed edge lists. It does not parse arbitrary multi-language source code ASTs (e.g. Java, C++, Go) directly from Git diffs.
2. **Single-Process Synchronization**: The actuator lock registry (`_SERVICE_LOCKS`) is built using Python's `asyncio.Lock`, which enforces concurrency boundaries within a single process. Scaling horizontally across multiple worker nodes requires an external Redis lock manager (`Redlock`).
3. **Simulated Runtime Telemetry**: Production deployments require connecting the monitoring engine to live OpenTelemetry collectors or Prometheus exporters rather than the in-memory metric generator.
4. **Local Secret Storage**: Service secrets are encrypted at rest in `data/endpoints.json` using PBKDF2 and AES-256 GCM. In enterprise environments, this should be integrated with an external key vault (e.g., HashiCorp Vault or AWS KMS).

---

## 3. Phase 2 Parked Roadmap (Weeks 11–20)

Phase 2 items are explicitly parked in `docs/phase2-parked/` and are not part of the active Phase 1 release:

1. **Kubernetes Actuation Driver**: Transitioning from in-memory state updates to live Kubernetes API client operations (`apps/v1` `Deployment` patches, pod rolling restarts, and Horizontal Pod Autoscaler updates).
2. **Live Chaos Operators**: Replacing simulated telemetry faults with LitmusChaos or Chaos Mesh Custom Resource Definitions (CRDs) executing real network packet drops and CPU stress tests.
3. **OpenTelemetry Collector Pipeline**: Dynamic extraction of runtime `CALLS` edges from distributed trace spans (`trace_id`, `parent_span_id`) to automatically weight graph edges by observed request frequency.
4. **Machine Learning Risk Calibration**: Replacing static risk formula weights ($0.35, 0.25, 0.20, 0.20$) with an empirical logistic regression model trained on historical repository incident records.
5. **eBPF Kernel-Level Discovery**: Non-invasive kernel socket tracing using eBPF programs on `tcp_connect` syscalls to dynamically map microservice dependencies without application-level instrumentation.

---

*This roadmap establishes the transparent cut line between active Phase 1 deliverables and planned Phase 2 extensions.*
