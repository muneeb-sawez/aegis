# AEGIS: Real vs. Simulated Capabilities (Phase 1)

This document provides full technical honesty and transparency regarding which components of AEGIS are real production implementations versus emulated execution in Phase 1 (Weeks 1–10).

> ⚠️ **Core Honesty Principle**: Telemetry, live clusters, and external PR merges are labeled as "simulated / emulator time" in code comments, API fields, and UI dashboards. Never present an unmeasured number as a real-world result.

---

## 1. System Truth Matrix

| Subsystem / Capability | Phase 1 Status | Detailed Implementation Description | Phase 2 Transition Path |
| :--- | :---: | :--- | :--- |
| **Graph Database & Storage** | **REAL** | Seeded 54-node / 142-edge topology in Neo4j Community (Docker) with full NetworkX in-memory fallback. All queries execute through `GraphRepository`. | Scale to larger production clusters; automated schema migrations. |
| **Blast Radius & Topology Traversal** | **REAL** | Backward BFS caller traversal walking `CALLS` dependencies with configurable hop degradation and impact scoring. | Continuous live runtime trace extraction (OpenTelemetry). |
| **Circular Dependency Detection** | **REAL** | Real Tarjan's Strongly Connected Components (SCC) algorithm detecting cycle introductions in proposed PR edges. | Multi-repo cross-boundary cycle detection. |
| **Risk Scoring Engine** | **REAL** | Multi-factor prediction formula: `Risk = W_B*B + W_C*C + W_D*D + W_H*H`. Never hard-coded; computed dynamically from graph topology. | Machine learning-calibrated risk weights. |
| **Contract Diffing** | **REAL** | AST and schema structural diffing detecting breaking field removals, type mutations, and parameter removals. | Automated OpenAPI/Protobuf/GraphQL linters in CI. |
| **Incident Feedback & Learning** | **REAL** | Incident nodes written back into graph (`Incident-[:RESOLVED_BY]->Decision-[:RESULTED_IN]->Outcome`). Causes subsequent risk evaluations to measurably rise (+5 jump). | Dynamic cross-service historical correlation models. |
| **LLM Reasoning & RCA Engine** | **REAL** | LiteLLM abstraction calling real models (Gemini / Groq / Ollama). Strict token capping (~3000 tokens) with deterministic fallback rules. | Multi-agent debate and reasoning models. |
| **Actuator Safety & Allowlist** | **REAL** | Parameter validation, scoring gate (Safety ≥ 75), per-service concurrency locks, HMAC-SHA256 request signing, and snapshot rollback. | Kubernetes custom controller and operator. |
| **Multi-Tenancy & Project Isolation** | **REAL** | Project scoping (`project_id`), hashed per-project API keys (`agk_...`), PBKDF2 authenticated encryption for secrets, and SSRF validation. | OIDC / SAML identity federation. |
| **GitHub Webhook Verification** | **REAL** | Constant-time `hmac.compare_digest` verification of `X-Hub-Signature-256`, idempotency store, changed-files scanner, and PR comments client. | Live GitHub App marketplace installation. |
| **Microservice Telemetry & Pods** | **SIMULATED** | Service latency, error rates, CPU percentages, and pod states are emulated in-memory in graph node properties. | OpenTelemetry metrics, Prometheus, and Datadog collectors. |
| **Actuation Target Cluster** | **HYBRID** | Phase 1 defaults to emulated in-memory execution; supports live HTTP actuation when connected to `aegis-target`. | Real Kubernetes API (`kubectl` / CRDs), AWS ECS, or Nomad. |
| **Evaluation Timings & MTTR** | **MEASURED (EMULATED)** | Recorded directly by `scripts/run_eval.py` on local runtime. Labeled as emulator measurements (not production cluster MTTR). | Real chaos engineering experiments via LitmusChaos. |

---

## 2. Benchmark & Baseline Policy

1. **No Fabricated Performance Claims**:
   - Do not display generic claims like *"MTTR 7.4 seconds"*, *">92% accuracy"*, or *"35 minutes saved"* unless accompanied by the specific benchmark run data from `scripts/run_eval.py` and clearly noted as emulator measurements.
2. **Honest Baseline Comparison**:
   - **Baseline (a) Rule-Only Alerter**: Fires alert thresholds instantly (~0.00 ms) but provides zero root-cause localization or automated healing.
   - **Baseline (b) Manual Timing Template**: SRE industry operational reference (40–80 min MTTR) derived from published DORA / PagerDuty benchmarks, representing human triage delays.
3. **Graph Ablation Transparency**:
   - Evaluated with `--no-graph-context`, proving that without topological relationships, the LLM fails on database and pod isolation faults (dropping from 100% to 60%).

---

## 3. Grounding Guarantees

- **No Cypher outside `backend/graph/`**: All database interactions use interface methods (`neighbors()`, `callers()`, `incidents()`).
- **Edge Direction**: `CALLS` edges strictly point `caller -> callee`. Blast radius always walks backwards.
- **Fail-Closed Actuator**: The LLM can only *propose* fixes; the guarded actuator strictly scores, snapshots, verifies, and auto-rolls back if verification fails.
