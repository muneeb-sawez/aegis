# 00 — Project Overview & Executive Brief

> **Target Audience**: Final-year engineering student defending the AEGIS project before external evaluators, technical auditors, and academic examiners.  
> **Pedagogical Standard**: Clear, simple analogies; precise definitions on first use; absolute technical rigor; zero hand-waving; code-backed evidence for every claim.

---

## Table of Contents
1. [Executive Summary: Three Levels of Explanation](#1-executive-summary-three-levels-of-explanation)
2. [The Core Problem: Why Modern Software Fails Siloed](#2-the-core-problem-why-modern-software-fails-siloed)
3. [The Core Solution: One Graph for Predict and Heal](#3-the-core-solution-one-graph-for-predict-and-heal)
4. [The Closed Autonomous Loop](#4-the-closed-autonomous-loop)
5. [Target Users & Stakeholders](#5-target-users--stakeholders)
6. [Concrete Real-World Use-Case Scenarios](#6-concrete-real-world-use-case-scenarios)
7. [Implementation Status: Built vs. Planned](#7-implementation-status-built-vs-planned)
8. [Chronological Build History](#8-chronological-build-history)
9. [Verification Notes & Document Discrepancy Ledger](#9-verification-notes--document-discrepancy-ledger)

---

## 1. Executive Summary: Three Levels of Explanation

### 1.1 In One Sentence
**AEGIS** (*Autonomous Enterprise Graph-Grounded Immune System*) is an automated resilience platform that uses a single, continuously updated **Knowledge Graph** to predict the risk of code changes *before* they ship, diagnose and remediate runtime microservice failures *after* they occur, and automatically update its graph memory so every incident measurably improves future deployment decisions.

### 1.2 The 30-Second Elevator Pitch
> *"In modern cloud software, the people shipping code and the systems running it operate blind to each other. Developers merge pull requests without knowing which upstream callers will break, and monitoring tools sound alarms after an outage without knowing what changed or how to fix it safely.  
> AEGIS breaks down this wall by acting as a digital immune system. Before code ships, AEGIS walks a live architectural dependency graph to compute a mathematical risk score and block dangerous breaking changes. If an incident happens at runtime, an AI reasoning agent—strictly constrained by graph relationships—diagnoses the true root cause and safely applies allowlisted, auto-rollback remedies. Finally, AEGIS writes the incident back into the graph, ensuring the system never makes the same mistake twice."*

### 1.3 The 2-Minute Deep Explanation
To understand AEGIS, consider the analogy of a **hospital emergency room paired with a preventative healthcare clinic**:
- Traditional CI/CD tools (like GitHub Actions) are like an **allergy test in an empty laboratory**. They run unit tests on a pull request in total isolation, unaware that the patient (the production cluster) is currently running low on database connections.
- Traditional monitoring tools (like Datadog or Prometheus) are like an **ICU heart monitor**. When a microservice crashes, the alarm beeps loudly, but the monitor has no idea *why* the patient collapsed or *which* specific upstream medication interaction caused the heart attack.
- **AEGIS unites the clinic and the emergency room into a single continuous organism**:
  1. **Pre-Ship Prediction (The Preventive Clinic)**: When an engineer opens a pull request, AEGIS does not just run lint checks. It traverses the microservice dependency graph backwards from the changed service. It computes the **Blast Radius** (how many upstream services call this service), detects **Breaking Contract Diffs** (e.g., removing a field from a shared Protobuf/JSON schema), and checks with **Tarjan’s Algorithm** whether a circular dependency loop has been introduced. These feed into a deterministic mathematical risk formula ($0 \text{ to } 100$). If the score exceeds the safety threshold ($70.0$), the change is blocked.
  2. **Runtime Healing (The Emergency Actuator)**: If an operational fault strikes (such as database connection pool exhaustion or pod crashloops), an AI reasoning agent analyzes the 2-hop topological neighbourhood around the failing service. Because the LLM is **graph-grounded**—meaning it is only allowed to cite nodes and edges that exist in the real graph—it cannot hallucinate non-existent servers. Once the root cause is identified, AEGIS does *not* let the AI execute arbitrary terminal commands. Instead, proposals pass through an **Allowlist Gate** and a **Safety Scoring Gate** (minimum safety score $75.0$). A snapshot of the pre-fix state is captured, a signed command is sent to the target, and a 10-second verification probe checks if latency recovered. If the fix fails, the actuator **immediately rolls back** to the pre-fix snapshot.
  3. **Institutional Memory (The Learning Loop)**: When the incident is resolved, AEGIS writes an `Incident` node and an `Outcome` edge back into the Knowledge Graph. When that same engineer later tests another PR against that service, the historical incident penalty term ($H$) dynamically increases the predicted risk score by $+5$ to $+25$ points. The system has learned.

---

## 2. The Core Problem: Why Modern Software Fails Siloed

Modern distributed systems (microservices) fail primarily because development and operations operate as **disconnected silos**.

```
[ DEVELOPER SILO ]                           [ PRODUCTION SILO ]
Pull Request #142                             Runtime Microservices
(paymentservice code change)                  (54 Services, 142 Edges)
         │                                              │
         ▼                                              ▼
  Unit Tests Pass ✅                            Pod Crashes / Latency Spikes 🚨
  Linters Pass    ✅                            Alarms Fire Everywhere
         │                                              │
         └──────────── THE BLIND SPOT ──────────────────┘
                 No Shared Dependency Context
                 No Feedback From Past Outages
                 Manual Triage: 40–80 min MTTR
```

### 2.1 The Pre-Deployment Blind Spot
1. **Isolated Validation**: Unit and integration tests verify code against mocks or local fixtures. They cannot predict how a change in `paymentservice` propagates across 3 hops to degrade `checkoutservice`, `orderservice`, and `frontend`.
2. **Silent Contract Drift**: A developer may rename or drop an optional field (e.g., `account_id` in `payment.proto`). The service's own tests pass, but downstream client services fail at runtime when deserializing payloads.
3. **Hidden Cycles**: Adding a new client call to an upstream utility service can silently introduce a cyclic dependency graph ($A \rightarrow B \rightarrow C \rightarrow A$), resulting in catastrophic deadlocks under load.

### 2.2 The Post-Deployment Manual Diagnosis Crisis
1. **Alert Fatigue & Blameless Noise**: When a database connection pool exhausts on `postgres-payment`, symptoms cascade upstream. `paymentservice`, `checkoutservice`, and `frontend` all report timeouts simultaneously. Traditional dashboards show dozens of red lights with no indication of where the fire started.
2. **Slow Manual MTTR (Mean Time to Resolution)**: Industry benchmarks from DORA and PagerDuty report typical manual enterprise MTTR between **40 and 80 minutes**. Human on-call engineers must wake up, read disparate logs, query telemetry, hypothesize causes, and manually apply untested fixes.
3. **Dangerous Unchecked Interventions**: In high-stress outages, engineers frequently execute ad-hoc `kubectl` or SQL commands without rollback snapshots, often turning a partial degradation into a total outage.

### 2.3 Why Existing Tools Do Not Close the Loop
- **CI/CD Tools (GitHub Actions, GitLab CI, ArgoCD)**: Only validate code syntax and build artifacts. They have zero awareness of live cluster topology or current database connection pool utilization.
- **APM & Observability (Datadog, Dynatrace, New Relic, Prometheus)**: Monitor metrics and spans after the fact. They cannot analyze an upcoming Git PR before deployment, nor do they feed incident resolutions back into pre-deployment risk gates.
- **Generic AIOps / Copilots**: Generic LLMs hallucinate node names, do not respect architectural invariants, and are too dangerous to grant unrestricted cluster write access.

---

## 3. The Core Solution: One Graph for Predict and Heal

The central architectural thesis of AEGIS is:
> **A single, shared Knowledge Graph must serve as the single source of truth for BOTH pre-deployment change risk evaluation AND post-deployment incident root-cause localization.**

```
                         ┌────────────────────────┐
                         │   AEGIS KNOWLEDGE      │
                         │        GRAPH           │
                         │  (54 Nodes, 142 Edges) │
                         └───────────┬────────────┘
                                     │
            ┌────────────────────────┴────────────────────────┐
            ▼                                                 ▼
   [ PREDICT ENGINE ]                                [ HEAL ACTUATOR ]
• Backward BFS Blast Radius                       • 2-Hop Grounded LLM RCA
• AST Contract Diffing                            • Fallback Deterministic Rules
• Tarjan Cycle Detection                          • Allowlist & Safety Gates (≥75)
• Risk Formula (W_B·B + W_C·C...)                 • Automatic 10s Rollback
            │                                                 │
            └────────────────────────┬────────────────────────┘
                                     │
                                     ▼
                          [ LEARNING FEEDBACK ]
                   Incident Node Written Back to Graph
                   Future Risk Scores Measurably Increase
```

---

## 4. The Closed Autonomous Loop

The AEGIS lifecycle operates as a 6-phase closed loop: **Predict $\rightarrow$ Deploy $\rightarrow$ Monitor $\rightarrow$ Diagnose $\rightarrow$ Heal $\rightarrow$ Learn**.

| Phase | Purpose | Phase 1 Implementation Status | Code Evidence |
| :--- | :--- | :---: | :--- |
| **1. Predict** | Calculates change-risk score before code merges. Evaluates Blast Radius ($B$), Contract Breaking Severity ($C$), Cycle Penalty ($D$), and Historical Incidents ($H$). | **REAL** | [`backend/sim/risk.py:59-130`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/sim/risk.py#L59-L130)<br>[`backend/sim/blast_radius.py:14-46`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/sim/blast_radius.py#L14-L46) |
| **2. Deploy** | Automated merge gating: Blocks PR if Risk $\ge 70$, warns if $40 \le \text{Risk} < 70$, approves if $< 40$. GitHub webhook integration. | **REAL (EMULATED CLUSTER)** | [`backend/api/routes_predict.py:56-110`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/api/routes_predict.py#L56-L110)<br>[`backend/webhooks/processor.py:110-205`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/webhooks/processor.py#L110-L205) |
| **3. Monitor** | Continuous background polling of microservice `/health` endpoints. Detects latency spikes, degraded status, and error rate surges. Enforces SSRF defense. | **REAL** | [`backend/monitor/health_checker.py:102-230`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/monitor/health_checker.py#L102-L230)<br>[`backend/security/ssrf.py:20-65`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/security/ssrf.py#L20-L65) |
| **4. Diagnose** | Graph-grounded Root Cause Analysis (RCA). LiteLLM queries Gemini/Groq/Ollama over a 2-hop graph context. Falls back to deterministic rules if offline. | **REAL** | [`backend/agent/rca.py:70-135`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/agent/rca.py#L70-L135)<br>[`backend/agent/fallback_rules.py:16-160`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/agent/fallback_rules.py#L16-L160) |
| **5. Heal** | Guarded execution of allowlisted actions (`restart`, `scale_pool`, `rollback`). Requires Safety $\ge 75$. Takes snapshot, verifies for 10s, auto-rolls back on failure. | **REAL** | [`backend/executor/orchestrator.py:70-220`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/executor/orchestrator.py#L70-L220)<br>[`backend/executor/allowlist.py:50-130`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/executor/allowlist.py#L50-L130) |
| **6. Learn** | Writes `Incident` nodes and `Decision` records back into graph repository. Future risk assessments for that service query `repo.incidents(days=30)` and increase score. | **REAL** | [`backend/feedback/writer.py:25-85`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/feedback/writer.py#L25-L85)<br>[`backend/sim/risk.py:86-93`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/sim/risk.py#L86-L93) |

---

## 5. Target Users & Stakeholders

| Stakeholder Persona | Daily Pain Point Without AEGIS | How AEGIS Solves It |
| :--- | :--- | :--- |
| **Software Engineer (Developer)** | Merging code into a shared service without knowing if downstream callers rely on renamed schema fields. | Receives an automated GitHub PR comment with risk score, affected callers list, and contract diff breakdown within seconds of opening a PR. |
| **Site Reliability Engineer (SRE)** | Waking up at 2:00 AM to 50 simultaneous alerts across 10 services without knowing which service is the root cause. | Real-time SSE streaming terminal isolates the root cause (e.g., `postgres-payment` connection pool exhaustion) in $< 1 \text{ second}$ and proposes an allowlisted fix. |
| **Platform / DevOps Architect** | Microservice dependencies devolve into a chaotic "spaghetti architecture" with hidden circular calls and unmanaged database contention. | Interactive 2D/3D React Flow canvas visualizes all 54 nodes, monitors live health, and detects cycles using Tarjan's algorithm before PRs merge. |
| **Security & Compliance Auditor** | AI systems performing black-box or non-deterministic changes on production clusters with zero accountability. | Immutable, append-only audit ledger (`audit.jsonl`), per-service locks, HMAC-SHA256 request signing, and complete secret redaction. |

---

## 6. Concrete Real-World Use-Case Scenarios

The following scenarios are fully implemented and verified against the seeded 54-node topology in [`data/topology.yaml`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/data/topology.yaml).

```
   ┌──────────┐
   │ frontend │
   └────┬─────┘
        │ CALLS
        ▼
┌─────────────────┐
│ checkoutservice │
└───────┬─────────┘
        │ CALLS
        ▼
┌─────────────────┐       CALLS        ┌──────────────────┐
│ paymentservice  ├───────────────────▶│ postgres-payment │
└─────────────────┘                    └──────────────────┘
```

### Scenario 1: The Pre-Deployment Gate (PR #142 Breaking Schema Change)
- **Actor**: Backend Payment Engineer.
- **Context**: The developer opens Pull Request #142 proposing a change to `paymentservice`. The commit deletes the required field `account_id` from `payment.proto`.
- **Step-by-Step Execution**:
  1. GitHub Webhook triggers `POST /webhooks/github` with `X-Hub-Signature-256`.
  2. AEGIS acknowledges `200 OK` in $< 3 \text{ ms}$ and enqueues background processing ([`routes_webhooks.py:45-105`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/api/routes_webhooks.py#L45-L105)).
  3. Processor scans *only* changed files (`services/paymentservice/proto/payment.proto`), skipping documentation and assets.
  4. Backward BFS traverses callers: `paymentservice` $\leftarrow$ `checkoutservice` (hop 1) $\leftarrow$ `frontend` (hop 2). Blast score $B = 85.0$.
  5. Contract Differ flags deleted required field: Contract score $C = 100.0$.
  6. Composite risk formula yields **86.4 / 100** ($\ge 70.0 \rightarrow$ **Blocked**).
  7. GitHub Commenter posts a markdown risk report directly onto PR #142 ([`github_commenter.py:120-170`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/webhooks/github_commenter.py#L120-L170)).
- **Result**: The breaking change is blocked *before* merging into `main`.

### Scenario 2: Autonomous Root-Cause Localization (Database Pool Exhaustion)
- **Actor**: Production SRE on on-call shift.
- **Context**: A traffic surge exhausts the database connection pool on `postgres-payment`. `paymentservice` begins throwing timeouts; `checkoutservice` and `frontend` report degraded latency ($> 3000 \text{ ms}$).
- **Step-by-Step Execution**:
  1. Fault injected via `POST /api/chaos/inject` (`pool_exhaustion` on `paymentservice`).
  2. Monitoring worker detects latency threshold breach ($3400 \text{ ms} > 2 \times \text{baseline}$) and creates incident `inc-pool-01`.
  3. `build_context()` gathers 2-hop topological subgraph: `paymentservice`, `postgres-payment`, `checkoutservice`, and `frontend` ([`context.py:41-150`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/agent/context.py#L41-L150)).
  4. LLM reasoning agent receives strict prompt and graph context. It observes that `postgres-payment` has `connections: 100, pool_size: 100, status: "exhausted"`.
  5. RCA outputs: `root_cause_node = "postgres-payment"`, `root_cause_type = "pool_exhausted"`, proposing action `scale_pool` to `150`.
  6. Streaming reasoning events emit over SSE to the Mission Control terminal ([`stream.py:40-120`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/agent/stream.py#L40-L120)).
- **Result**: Root cause accurately attributed to the downstream database in $< 1 \text{ second}$, eliminating alert confusion on upstream services.

### Scenario 3: Guarded Execution with Automatic 10-Second Rollback
- **Actor**: Autonomous Actuator Subsystem.
- **Context**: An erroneous fix proposal is generated (or an operator attempts a faulty pool scale down to `20` connections during an active incident).
- **Step-by-Step Execution**:
  1. Proposal arrives: action `scale_pool`, target `postgres-payment`, `pool_size: 20`.
  2. **Allowlist Gate**: Validates action and parameters ($1 \le \text{pool\_size} \le 1000$). Passed ([`allowlist.py:50-80`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/executor/allowlist.py#L50-L80)).
  3. **Safety Scoring Gate**: Calculates $\text{Safety} = 100 - (\text{blast} + \text{data\_loss} + \text{overhead}) = 90.0 \ge 75.0$. Passed ([`scoring.py:40-110`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/executor/scoring.py#L40-L110)).
  4. **Snapshot**: Captures pre-fix state: `pool_size: 100, config_version: "v1"`.
  5. Actuator applies signed fix with HMAC-SHA256 signature ([`actuator.py:180-225`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/executor/actuator.py#L180-L225)).
  6. **Health Verification**: Background probe checks latency every 2 seconds within a 10-second verification window ([`health.py:115-180`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/executor/health.py#L115-L180)).
  7. Because `pool_size: 20` is worse than `100`, latency remains $> 3000 \text{ ms}$.
  8. Health verification deadline expires: `check_health()` returns `False`.
  9. `rollback()` immediately executes: restores `pool_size: 100` from pre-fix snapshot ([`rollback.py:50-100`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/executor/rollback.py#L50-L100)).
  10. Audit log records decision as `status: "rolled_back"`.
- **Result**: Production is protected from catastrophic remedies; bad changes automatically revert without human intervention.

### Scenario 4: The Closed-Loop Institutional Learning (+5 Score Jump)
- **Actor**: SRE Team Lead and Developer.
- **Context**: PR #142 is evaluated *after* Scenario 2's pool exhaustion incident was resolved and committed to memory.
- **Step-by-Step Execution**:
  1. The incident resolution executed `commit_incident_to_memory("inc-pool-01")` ([`feedback/writer.py:25-85`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/feedback/writer.py#L25-L85)).
  2. Graph repository created an `Incident` node attached to `paymentservice` with timestamp $\le 30 \text{ days}$.
  3. The developer pushes a revision or re-runs risk assessment on `paymentservice`.
  4. Risk engine executes:
     $$\text{incidents} = \text{repo.incidents}("paymentservice", \text{days}=30) \rightarrow \text{count} = 1$$
     $$H = \min(100.0, 1 \times 25.0) = 25.0$$
  5. Weighted contribution: $W_H \times H = 0.20 \times 25.0 = +5.0 \text{ points}$.
  6. Risk score rises from original score by exactly $+5.0$ points.
- **Result**: The system exhibits true institutional memory. Fragile services that suffered recent outages require higher scrutiny before future changes can merge.

---

## 7. Implementation Status: Built vs. Planned

The following table reflects the verified state of the codebase (as of October 2026), updating and superseding historical notes in [`docs/STATUS.md`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/docs/STATUS.md).

| Module / Capability | Status | Implementation Evidence | Description & Capabilities |
| :--- | :---: | :--- | :--- |
| **Graph Interface & NetworkX Backend** | **REAL** | [`backend/graph/repository.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/repository.py)<br>[`backend/graph/networkx_repo.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/networkx_repo.py) | Full in-memory graph repository. Implements 7 contract methods, backward BFS traversal, project isolation, and reset. |
| **Neo4j Persistent Graph Backend** | **REAL** | [`backend/graph/neo4j_repo.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/neo4j_repo.py) | Full Cypher query implementation. Seamless automatic fallback to NetworkX if Neo4j is offline. |
| **Topology Seed (54 Nodes, 142 Edges)** | **REAL** | [`data/topology.yaml`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/data/topology.yaml)<br>[`backend/graph/seed.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/graph/seed.py) | Exact 54 nodes and 142 edges representing e-commerce microservices, Kafka, Redis, and PostgreSQL instances. |
| **Predict Change-Risk Engine** | **REAL** | [`backend/sim/risk.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/sim/risk.py)<br>[`backend/sim/blast_radius.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/sim/blast_radius.py)<br>[`backend/sim/contract_diff.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/sim/contract_diff.py)<br>[`backend/sim/cycles.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/sim/cycles.py) | Real mathematical implementation of $W_B B + W_C C + W_D D + W_H H$. Backward BFS, AST schema diff, Tarjan cycle check. |
| **Live Probing & SSRF Defense** | **REAL** | [`backend/monitor/health_checker.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/monitor/health_checker.py)<br>[`backend/security/ssrf.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/security/ssrf.py) | Real async HTTP probing. Blocks private RFC1918, link-local, loopback, and cloud metadata SSRF vectors. |
| **LLM Root Cause Reasoner (RCA)** | **REAL** | [`backend/agent/rca.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/agent/rca.py)<br>[`backend/agent/context.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/agent/context.py)<br>[`backend/agent/fallback_rules.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/agent/fallback_rules.py) | LiteLLM abstraction calling Gemini/Groq/Ollama. Graph-grounded 2-hop context builder, Pydantic schema validation, and rule fallback. |
| **Diagnosis SSE Stream** | **REAL** | [`backend/agent/stream.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/agent/stream.py)<br>[`backend/api/routes_heal.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/api/routes_heal.py) | Real Server-Sent Events stream emitting `{type: 'thought'\|'cypher'\|'candidates'\|'result'\|'done'}`. |
| **Guarded Actuator & Rollback** | **REAL** | [`backend/executor/allowlist.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/executor/allowlist.py)<br>[`backend/executor/scoring.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/executor/scoring.py)<br>[`backend/executor/actuator.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/executor/actuator.py)<br>[`backend/executor/health.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/executor/health.py)<br>[`backend/executor/rollback.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/executor/rollback.py) | 3 allowlisted actions (`restart`, `scale_pool`, `rollback`). Safety score gate ($\ge 75$), per-service locks, pre-fix snapshots, 10s health verification. |
| **Closed-Loop Feedback & Memory** | **REAL** | [`backend/feedback/writer.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/feedback/writer.py)<br>[`backend/feedback/similarity.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/feedback/similarity.py) | Writes `Incident-[:RESOLVED_BY]->Decision-[:RESULTED_IN]->Outcome` into graph. Cosine incident similarity ranking. Updates future risk scores. |
| **Multi-Tenancy & Project API Keys** | **REAL** | [`backend/auth/dependencies.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/auth/dependencies.py)<br>[`backend/auth/store.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/auth/store.py)<br>[`frontend/src/pages/ProjectsPage.tsx`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/frontend/src/pages/ProjectsPage.tsx) | Complete multi-tenant isolation. SHA-256 hashed API keys required on all mutating routes. Project creation UI with endpoint secret encryption. |
| **GitHub Webhook & PR Commenter** | **REAL** | [`backend/webhooks/verify.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/webhooks/verify.py)<br>[`backend/webhooks/processor.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/webhooks/processor.py)<br>[`backend/webhooks/github_commenter.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/webhooks/github_commenter.py) | Constant-time HMAC-SHA256 signature verification (`hmac.compare_digest`), changed-files scanner, idempotent delivery cache, and PR markdown comment updater. |
| **Service Endpoint Registration** | **REAL** | [`backend/security/endpoints.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/security/endpoints.py)<br>[`backend/security/encryption.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/security/encryption.py) | PBKDF2-HMAC-SHA256 authenticated encryption for endpoint admin secrets. Secrets are never serialized or returned across any API. |
| **Operational Evaluation Suite** | **REAL** | [`scripts/run_eval.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/scripts/run_eval.py)<br>[`docs/EVAL.md`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/docs/EVAL.md) | 5 faults × 10 runs automated benchmark harness. Measures detect, diagnose, heal times, and accuracy against ground truth. Includes `--no-graph-context` ablation. |
| **Security Auditing Tools** | **REAL** | [`scripts/security_audit.py`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/scripts/security_audit.py)<br>[`docs/SECURITY.md`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/docs/SECURITY.md) | OSV database query for Python dependencies, `npm audit` for frontend, and workspace secret scanner (gitleaks equivalent). |
| **Live Kubernetes Cluster Actuation** | **PLANNED (PHASE 2)** | Parked in [`docs/phase2-parked/`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/docs/phase2-parked) | Real `kubectl` exec / deployment restarts against a live K8s or Kind cluster. In Phase 1, actuation is emulated in-memory or executed against `aegis-target`. |
| **Continuous eBPF Tracing** | **PLANNED (PHASE 2)** | Parked in [`docs/phase2-parked/`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/docs/phase2-parked) | Dynamic runtime call extraction using eBPF or OpenTelemetry agents to continuously auto-discover unmapped microservice edges. |

---

## 8. Chronological Build History

The development evolution of AEGIS is inferred directly from Git commit logs, milestone milestones, and working tree records:

```
Oct 20, 2026                 Oct 20, 2026                 Oct 22, 2026                 Oct 22, 2026
Initial Commit               Core Engines Complete        Guarded Actuator (M7)        Enterprise Hardening
7d77f3d                      be77366, ea65d66             0683b1b                      (Current State)
   │                               │                             │                            │
   ▼                               ▼                             ▼                            ▼
• Monorepo setup             • Real PREDICT formula        • backend/executor added     • Multi-tenancy & Projects
• Seed graph (54/142)        • Backward BFS blast          • Allowlist & scoring        • PBKDF2 secret encryption
• React Flow UI baseline     • Health monitor & SSRF       • Pre-fix snapshot           • GitHub webhook & commenter
• Contract schemas           • Docker Compose ingestion    • Auto 10s rollback          • 5-Fault evaluation suite
```

### Verified Git Commit Log Timeline
1. **Commit `7d77f3d` (2026-10-20)**: `initial commit` — Established repository layout, contract specifications ([`docs/02-CONTRACTS.md`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/docs/02-CONTRACTS.md)), and baseline seed topology.
2. **Commit `1f2c03d` – `c2e63a4` (2026-10-20)**: Cloud hosting configuration (Docker, Render, Railway) and comprehensive system README.
3. **Commit `2332b90` – `be77366` (2026-10-20)**: Implemented real PREDICT engine: backward BFS with attenuation, AST schema contract differ, Tarjan cycle detection, and composite risk scoring.
4. **Commit `275d006` – `ea65d66` (2026-10-20)**: Added Docker Compose topology ingestion, periodic health check worker, fault injection endpoints, and SSRF IP-range defense.
5. **Commit `3d27d07` – `abba33e` (2026-10-20)**: Built multi-page enterprise UI with React Flow canvas, Mission Control command bar, and Phase 2 capability navigation.
6. **Commit `cc47839` (2026-10-22)**: Hardened backend configuration via `pydantic-settings`, Neo4j security parameters, and enhanced monitoring rules.
7. **Commit `0683b1b` (2026-10-22)**: Built `backend/executor/` package: action allowlist, safety scoring, actuator per-service locks, pre-fix snapshots, 10s health verification, and automatic rollback. Added 40 new unit tests (109 total passing).
8. **Working Tree Evolution (2026-10-22)**:
   - Added `backend/feedback/`: Incident write-back and embedding similarity ranking.
   - Added `backend/auth/` & `backend/security/`: Multi-tenant project isolation, hashed API keys (`agk_...`), PBKDF2 authenticated encryption for secrets, and project management UI.
   - Added `backend/webhooks/`: GitHub webhook HMAC-SHA256 signature verification (`hmac.compare_digest`), changed-files scanner, and PR markdown commenter.
   - Added `scripts/run_eval.py` & `scripts/security_audit.py`: 5-fault × 10-run evaluation matrix, rule/manual baselines, graph ablation, and dependency security scanner. Test suite expanded to **169 passing tests**.

---

## 9. Verification Notes & Document Discrepancy Ledger

### Commands Executed During Verification
- `git log --format="%h | %cd | %s" --date=short`: Extracted commit history and verified commit hashes.
- `python -m pytest backend/tests/ -q`: Verified **169 tests passed, 5 skipped, 0 failed**.
- `npm run build` in `frontend/`: Verified TypeScript strict compilation and Vite bundle generation (**0 errors**).
- `python scripts/run_eval.py --runs 10`: Executed 50 trials across 5 fault types, measuring real detection, diagnosis, and healing latencies.
- `python scripts/security_audit.py`: Scanned requirements against OSV database and workspace for secret leaks.

### Discrepancy Ledger: Existing Docs vs. Current Code
1. **`docs/STATUS.md` Claims `backend/agent/` and `backend/executor/` are Missing/Misplaced**:
   - *Claim in `STATUS.md:50-53`*: "LLM Graph Reasoner Module (agent/): MISSING", "Autonomous Actuator Module (executor/): PARTIAL / MISPLACED", "Closed-Loop Feedback Module (feedback/): PARTIAL / MISPLACED".
   - *Code Reality*: Both [`backend/agent/`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/agent) and [`backend/executor/`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/executor) and [`backend/feedback/`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/backend/feedback) are fully implemented, independently packaged, and tested by 169 unit tests.
   - *Resolution*: `STATUS.md` was an interim snapshot from Week 3/4. The current codebase has completed M5, M6, M7, and M8.
2. **`docs/STATUS.md` Test Count**:
   - *Claim in `STATUS.md:14`*: "44 passed, 0 failed".
   - *Code Reality*: Active test suite contains **169 passed tests** across 17 test modules.
3. **`docs/06-REAL-VS-SIMULATED.md` vs `docs/REAL_VS_SIMULATED.md`**:
   - *Discrepancy*: `06-REAL-VS-SIMULATED.md` was an initial 12-line placeholder.
   - *Resolution*: Fully superseded by the comprehensive [`docs/REAL_VS_SIMULATED.md`](file:///c:/Users/munee/OneDrive/Desktop/MAJOR%20PROJECT%20BE-IT/aegis-antigravity-pack/docs/REAL_VS_SIMULATED.md) generated during Phase 1 audit.

### Items Marked NOT VERIFIED
- **Historical Git Author Context Before Commit `7d77f3d`**: `NOT VERIFIED` (Git history starts at `7d77f3d`; any earlier prototyping was squash-committed).
- **Physical Kubernetes Node Behavior**: `NOT VERIFIED` (Phase 1 scope intentionally uses emulated telemetry and `aegis-target` container endpoints rather than a multi-node live bare-metal K8s cluster).
