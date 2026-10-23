# AEGIS — Technology Stack Document

**Autonomous Engineering Graph & Intelligence System**\
> *"See every risk before it ships. Heal every failure after it lands."*

| | |
|:---|:---|
| **Document Type** | Technology Stack & Tooling Reference |
| **Architecture Style** | Event-Driven Microservices + Knowledge Graph |
| **Project Stage** | Review 2 — Interactive Prototype |
| **Primary Substrate** | Neo4j Knowledge Graph + LLM RCA Agent |

---

## 1. Technology Stack Overview

The AEGIS technology stack is architected around a **seven-layer model** that cleanly separates concerns from data ingestion through to end-user presentation. Each layer is purpose-selected to serve the dual-commitment architecture: *pre-deployment risk prediction* and *post-deployment autonomous self-healing*, both grounded on a single, shared Neo4j Knowledge Graph.

Technology selections follow three guiding principles:

1. **Graph-native tooling** for structural reasoning
2. **Battle-tested open-source** infrastructure where possible
3. **Clean separation** between the reasoning layer (which thinks) and the execution layer (which acts), ensuring safety-by-design

### Architecture Layer Stack

```
┌──────────────────────┬────────────────────────────────────────────────────────────────┐
│  ⑦  PRESENTATION     │  React 18 · TypeScript · Tailwind CSS · shadcn/ui             │
│                      │  Cytoscape.js · Framer Motion · Recharts                      │
├──────────────────────┼────────────────────────────────────────────────────────────────┤
│  ⑥  API GATEWAY      │  FastAPI · REST API · WebSocket · Pydantic v2                 │
├──────────────────────┼────────────────────────────────────────────────────────────────┤
│  ⑤  REASONING & AI   │  LangChain · OpenAI / Gemini API · Neo4j Cypher Tool          │
│                      │  ReAct Agent · Vector Store (ChromaDB)                        │
├──────────────────────┼────────────────────────────────────────────────────────────────┤
│  ④  PREDICTIVE       │  BFS/DFS Traversal · Risk Scoring · Simulation Sandbox        │
│     ENGINE           │  APOC Graph Algorithms                                        │
├──────────────────────┼────────────────────────────────────────────────────────────────┤
│  ③  KNOWLEDGE GRAPH  │  Neo4j 5.x · Cypher · APOC · GDS Library                     │
│                      │  Neo4j Python Driver · PostgreSQL                             │
├──────────────────────┼────────────────────────────────────────────────────────────────┤
│  ②  COLLECTOR LAYER  │  OpenTelemetry · Prometheus · Grafana · Jaeger · Kafka        │
├──────────────────────┼────────────────────────────────────────────────────────────────┤
│  ①  DATA SOURCES     │  Git / GitHub · Kubernetes · PostgreSQL · Docker              │
│                      │  REST/gRPC APIs                                               │
└──────────────────────┴────────────────────────────────────────────────────────────────┘
```

---

## 2. Frontend — Presentation Layer

The AEGIS Mission Control dashboard is a high-fidelity, real-time interface designed for SRE operators and engineering leadership. It renders the live Knowledge Graph topology, streams AI reasoning traces, and provides interactive simulation controls for both pre-deployment risk analysis and post-deployment healing.

| Technology | Version | Category | Role in AEGIS |
|:---|:---|:---|:---|
| **React** | 18.x (latest stable) | UI Framework | Component-based rendering engine for the Mission Control dashboard, providing efficient virtual DOM diffing for real-time graph state updates. |
| **TypeScript** | 5.x (strict mode) | Language | Type safety across all layers. Enforces typed interfaces for graph node/edge models, incident schemas, and WebSocket message contracts. |
| **Vite** | Latest stable | Bundler | Fast HMR during development, optimised production builds, native ESM support, path aliases (`@/*`). |
| **Tailwind CSS** | v3.x / v4.x | Styling | Utility-first CSS framework. Custom design tokens for AEGIS's dark mission-control theme, status colours (critical, warning, healthy), and responsive breakpoints. |
| **React Flow / Cytoscape** | Latest stable | Graph Rendering | Primary graph visualisation engine. Renders the dynamic microservice architecture knowledge graph with interactive zoom, pan, click-to-inspect flyouts, and animated edge particles for live traffic flow (with verified baseline demo fallback). |
| **Framer Motion** | Latest | Animation | Orchestrates UI micro-animations: pulse rings on fault-injected nodes, blast-radius expansion animations, healing progress transitions, and timeline scrubber interactions. |
| **Recharts** | v2.x | Data Viz | SVG-based charts for latency sparklines, risk score gauges, incident frequency histograms, and MTTR comparison bar charts. |
| **Lucide React** | Latest | Icons | Consistent, semantic stroke icon set used across all dashboard panels (shields, alerts, graphs, settings). |
| **Zustand** | Latest stable | State Mgmt | Lightweight client state management. Separate stores for graph state, simulation results, incident feed, and WebSocket connection status. |
| **Sonner** | Latest | Toasts | Low-friction toast notifications for real-time alerts: fault detection, healing completion, risk gate verdicts. |

> **Design System Convention:** All UI components are built using shadcn/ui primitives composed with Tailwind CSS utility classes. No external UI frameworks (Material UI, Bootstrap, Chakra) are permitted — ensuring a consistent, lightweight, and fully-customisable design system aligned with the AEGIS dark mission-control aesthetic.

---

## 3. Backend — API & Orchestration Layer

The AEGIS backend serves as the orchestration hub connecting the Knowledge Graph, the LLM reasoning agent, the simulation engine, and the guarded execution layer. It exposes both REST endpoints for dashboard consumption and WebSocket channels for real-time streaming of AI reasoning traces and incident telemetry.

| Technology | Version | Category | Role in AEGIS |
|:---|:---|:---|:---|
| **Python** | 3.11+ | Language | Primary backend language. Chosen for its rich AI/ML ecosystem, LangChain compatibility, and Neo4j driver maturity. |
| **FastAPI** | 0.100+ | Web Framework | Async-first web framework powering all REST and WebSocket endpoints. Auto-generates OpenAPI specs. Native Pydantic v2 integration for request/response validation. |
| **Pydantic v2** | 2.x | Validation | Runtime data validation for all API contracts, graph query parameters, incident schemas, and LLM tool-call argument parsing. |
| **Uvicorn** | Latest | ASGI Server | High-performance async server running FastAPI in production. Supports WebSocket connections for real-time dashboard feeds. |
| **Celery** (optional) | 5.x | Task Queue | Background task orchestration for long-running operations: repository scanning, graph population batch jobs, and scheduled drift detection. |
| **Redis** | 7.x | Cache / Broker | Caching layer for frequently-queried graph subsets, session state, and Celery message broker. Rate limiting for API endpoints. |

### REST API Surface

| Endpoint | Method | Purpose |
|:---|:---|:---|
| `/api/repo/scan` | `POST` | Asynchronous repository scan & Microservice/Module Derivation trigger |
| `/api/repo/scan/{scan_id}/status` | `GET` | Polling endpoint for live scanning phase progress & counters |
| `/api/v1/graph/topology` | `GET` | Dynamic scanned graph or baseline demo topology payload |
| `/api/v1/simulate/pre-ship` | `POST` | Run blast-radius simulation for a given PR diff |
| `/api/v1/simulate/inject-fault` | `POST` | Trigger chaos injection in the sandbox |
| `/api/v1/incidents` | `GET` | Paginated incident history with reasoning traces |
| `/ws/feed` | `WebSocket` | Real-time stream of AI reasoning, telemetry, and healing events |

### API Design Principles

- **Schema-First:** All endpoints defined via Pydantic models; OpenAPI spec auto-generated.
- **Typed Contracts:** Shared TypeScript types generated from OpenAPI for frontend consumption.
- **Versioned:** All routes prefixed with `/api/v1/` for future backward compatibility.
- **Async-Native:** All I/O-bound operations (graph queries, LLM calls) use `async/await`.

---

## 4. Knowledge Graph — Core Data Substrate

The Neo4j Knowledge Graph is the **architectural centrepiece** of AEGIS. It serves as the single source of truth for structural entities (services, APIs, databases, pods), runtime entities (incidents, decisions, actions), and the typed relationships between them. Both the pre-deployment simulator and the post-deployment healing agent query the same graph — this shared substrate is the system's primary novelty.

| Technology | Version | Category | Role in AEGIS |
|:---|:---|:---|:---|
| **Neo4j** | 5.x (Community / Enterprise) | Graph Database | Stores all structural and runtime entities. Provides native graph traversal for blast-radius computation, dependency analysis, and incident-similarity searches. |
| **Cypher** | Neo4j Native | Query Language | Declarative graph query language for all AEGIS operations: topology retrieval, BFS blast-radius traversal, 2-hop RCA neighbourhood queries, and incident memory writes. |
| **APOC** | 5.x | Plugin Library | Extended procedures: `apoc.path.expandConfig` for configurable traversals, `apoc.algo.dijkstra` for weighted shortest-path analysis, data import/export utilities. |
| **Neo4j GDS** | 2.x | Graph Algorithms | Graph Data Science library for advanced analytics: PageRank (service criticality ranking), community detection (failure blast domains), betweenness centrality (bottleneck identification). |
| **neo4j Python Driver** | 5.x | Connector | Official async-capable Python driver for all backend-to-Neo4j communication. Connection pooling, transaction management, and result streaming. |
| **PostgreSQL** | 15+ | Relational DB | Structured storage for audit logs, user sessions, API keys, and time-series incident metadata that benefits from relational indexing rather than graph traversal. |

### Graph Schema Summary (Dynamic Microservice & Architecture Graph)

```cypher
// ─── Node Labels ─────────────────────────────────────────────────
(:Service)        // Core microservices (8 nodes)
(:Database)       // Data stores: PostgreSQL, Redis, MongoDB, Kafka (6 nodes)
(:APIEndpoint)    // REST/gRPC endpoint definitions (20+ nodes)
(:Pod)            // Kubernetes container replicas (20+ nodes)
(:Incident)       // Runtime incident records (dynamic, grows over time)
(:Decision)       // Remediation decisions with reasoning traces

// ─── Relationship Types ─────────────────────────────────────────
[:CALLS]          // Service-to-service dependency  {latency_p99, protocol}
[:DEPENDS_ON]     // Service-to-database dependency
[:EXPOSES]        // Service-to-API endpoint mapping
[:INSTANCE_OF]    // Pod-to-service instance binding
[:OCCURRED_IN]    // Incident-to-service (runtime memory)
[:RESOLVED_BY]    // Incident-to-decision outcome link
```

---

## 5. AI & Reasoning — Autonomous Intelligence Layer

The reasoning layer is where AEGIS distinguishes itself from conventional AIOps tools. Rather than applying fixed rules to logs and metrics, AEGIS deploys an LLM-powered **ReAct agent** that grounds every diagnostic hypothesis in *live graph queries* — querying service dependencies, historical incidents, and blast-radius topology before forming conclusions.

| Technology | Version | Category | Role in AEGIS |
|:---|:---|:---|:---|
| **LangChain** | 0.2+ / Latest | Agent Framework | Orchestrates the ReAct agent loop: Thought → Action (Cypher query / telemetry fetch) → Observation → repeat until diagnosis. Manages tool-calling, chain-of-thought prompting, and output parsing. |
| **OpenAI API** | GPT-4 / GPT-4o | LLM Provider | Primary LLM backbone for reasoning, diagnosis narration, remediation candidate evaluation, and natural-language explanation generation. |
| **Google Gemini API** | Gemini 1.5 Pro+ | LLM Provider | Alternative / secondary LLM provider. Multi-model support enables comparative evaluation and failover resilience. |
| **Neo4j Cypher Tool** | Custom | Agent Tool | Custom LangChain tool that allows the agent to compose and execute Cypher queries against the Knowledge Graph during reasoning — the core mechanism for *graph-grounded RCA*. |
| **Telemetry Query Tool** | Custom | Agent Tool | Agent tool to fetch live Prometheus metrics (latency, error rates, CPU/memory) for services identified during graph traversal. |
| **ChromaDB** | Latest | Vector Store | Stores embeddings of past incident descriptions for incident-similarity retrieval. The agent queries this to find historically similar failures and their successful remediations. |

> **Graph-Grounded Reasoning (Core Novelty):** Unlike conventional AIOps that scan raw logs with pattern matching, the AEGIS agent's first action on any anomaly is a Cypher query:
> ```cypher
> MATCH (s:Service {name: $alerting_service})-[:CALLS|DEPENDS_ON*1..2]-(neighbor)
> RETURN neighbor
> ```
> This structural grounding eliminates hallucinated diagnoses and ensures every hypothesis is anchored to real dependency topology.

### Agent Tool-Calling Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  AEGIS ReAct Agent Loop                                                 │
│                                                                         │
│  THOUGHT:  "PaymentService latency spiked. Let me check its            │
│             downstream dependencies and recent incident history."       │
│                                                                         │
│  ACTION:   neo4j_cypher_tool(                                           │
│              "MATCH (p:Service {name:'PaymentService'})-[:DEPENDS_ON]   │
│               ->(db) RETURN db.name, db.type, db.connection_pool"       │
│            )                                                            │
│                                                                         │
│  OBSERVE:  PostgreSQL Payments DB — pool: 20/20 (EXHAUSTED)            │
│                                                                         │
│  THOUGHT:  "DB connection pool is fully exhausted. Checking if          │
│             similar incident occurred before..."                        │
│                                                                         │
│  ACTION:   vector_similarity_tool("PostgreSQL pool exhaustion")         │
│                                                                         │
│  OBSERVE:  INC-087: Same root cause, resolved by scaling pool           │
│            to 50 + rolling restart. Success rate: 100%.                 │
│                                                                         │
│  DIAGNOSIS: Root Cause = DB Pool Exhaustion (confidence: 94%)           │
│  REMEDY:    Scale pool to 50 + pod rolling restart                      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Observability & Telemetry Stack

The telemetry layer instruments the sandbox testbed environment with production-grade observability, providing the raw signal that feeds both anomaly detection and the AI reasoning agent's diagnostic queries. All three pillars of observability — **metrics, logs, and traces** — are captured via OpenTelemetry and routed to purpose-built backends.

| Technology | Version | Category | Role in AEGIS |
|:---|:---|:---|:---|
| **OpenTelemetry** | Latest stable | Instrumentation | Unified instrumentation SDK for all sandbox microservices. Auto-instruments HTTP/gRPC calls, database queries, and Kafka message flow. Generates traces, metrics, and structured logs in a vendor-neutral format. |
| **Prometheus** | 2.x | Metrics Store | Pull-based time-series metrics collection. Stores service latency (P50/P95/P99), error rates, CPU/memory utilisation, connection pool gauges, and custom AEGIS health counters. |
| **Grafana** | 10.x | Dashboards | Metrics visualisation and alerting. Pre-built dashboards for sandbox service health, Kubernetes resource utilisation, and AEGIS performance benchmarks (TTD, TTH, MTTR). |
| **Jaeger** | Latest | Tracing | Distributed tracing backend. Captures end-to-end request traces across the microservice mesh, enabling the AI agent to correlate latency spikes to specific service hops. |
| **Loki** (optional) | Latest | Log Aggregation | Centralised log aggregation for all sandbox services. Structured JSON logs indexed by service, severity, and trace ID for cross-referencing with distributed traces. |

### Three Pillars of Observability

| Pillar | Backend | Signal Type | AEGIS Usage |
|:---|:---|:---|:---|
| **Metrics** | Prometheus | Quantitative time-series | Latency percentiles, error rates, saturation gauges, request throughput |
| **Traces** | Jaeger | Distributed request traces | Span-level timing across service boundaries for RCA correlation |
| **Logs** | Loki | Structured event logs | Contextual event logs correlated by trace ID for root-cause drill-down |

### AEGIS-Specific Custom Metrics

| Metric | Type | Description |
|:---|:---|:---|
| `aegis_ttd_seconds` | Histogram | Time-to-Detect — seconds from anomaly onset to alert raised |
| `aegis_ttdiag_seconds` | Histogram | Time-to-Diagnose — seconds from alert to root-cause identification |
| `aegis_tth_seconds` | Histogram | Time-to-Heal — seconds from diagnosis to verified recovery |
| `aegis_diagnosis_accuracy` | Gauge | Boolean match of agent diagnosis vs. injected ground-truth fault |

---

## 7. Infrastructure & DevOps

AEGIS is deployed and evaluated on a fully containerised, locally reproducible Kubernetes sandbox. This ensures the entire predict-diagnose-heal-learn loop can be demonstrated safely, repeatably, and without requiring access to production cloud infrastructure.

| Technology | Version | Category | Role in AEGIS |
|:---|:---|:---|:---|
| **Docker** | 24.x+ | Containerisation | All microservices, databases, and AEGIS components are containerised with multi-stage Dockerfiles. Ensures reproducible builds across development and demonstration environments. |
| **Kubernetes** | 1.28+ | Orchestration | Container orchestration platform. Manages pod scheduling, service discovery, health probes, and rolling updates for the sandbox testbed. |
| **Kind / Minikube** | Latest | Local K8s | Local Kubernetes cluster for sandbox evaluation. Kind (Kubernetes-in-Docker) preferred for CI reproducibility; Minikube for developer ergonomics. |
| **Helm** | 3.x | Package Manager | Kubernetes package manager for deploying the sandbox testbed, Neo4j, Prometheus, Grafana, and Kafka via versioned Helm charts. |
| **Docker Compose** | v2 | Local Dev | Development-mode orchestration for running the full AEGIS stack locally without Kubernetes (Neo4j, FastAPI, Redis, frontend dev server). |
| **Chaos Mesh / Litmus** | Latest | Chaos Engineering | Controlled fault injection framework. Injects pod crashes, CPU saturation, network latency, and database timeouts to test AEGIS's autonomous healing capabilities. |
| **GitHub Actions** | N/A | CI/CD | Continuous integration pipeline: linting, type-checking, unit tests, Docker image builds, and automated AEGIS evaluation benchmark runs. |
| **Apache Kafka** | 3.x | Messaging | Event streaming bus for asynchronous communication between sandbox microservices (order events, payment confirmations, inventory updates) — modelled as a node in the Knowledge Graph. |

---

## 8. Testing & Quality Assurance

### Unit Testing

| Tool | Role |
|:---|:---|
| **Vitest** | Frontend component unit tests with Testing Library |
| **Pytest** | Backend unit tests for FastAPI endpoints, graph query builders, and agent tool functions |

### Integration Testing

| Tool | Role |
|:---|:---|
| **Testcontainers** | Spin up ephemeral Neo4j and PostgreSQL containers for integration tests |
| **httpx** | Async HTTP client for end-to-end API integration testing |

### Chaos & Evaluation Testing

| Tool | Role |
|:---|:---|
| **Chaos Mesh** | Automated fault injection benchmarks on Kubernetes |
| **Custom Evaluation Harness** | AEGIS-specific evaluation runner measuring TTD, TTH, and diagnosis accuracy against ground-truth faults |

---

## 9. Complete Technology Dependency Map

The table below provides a consolidated, categorised view of every technology in the AEGIS stack, including its selection rationale and the specific AEGIS layer it serves.

| Layer | Technology | Category | Selection Rationale |
|:---|:---|:---|:---|
| **Presentation** | React 18 | UI Framework | Industry standard; concurrent rendering for real-time graph updates |
| | TypeScript | Language | End-to-end type safety; shared types between frontend and backend |
| | Tailwind CSS | Styling | Utility-first; rapid iteration on dark mission-control theme |
| | shadcn/ui | Components | Headless, accessible; full design ownership without framework lock-in |
| | Cytoscape.js | Graph Viz | Purpose-built for network graph rendering; plugin ecosystem for layouts |
| | Framer Motion | Animation | Production-grade animation library; orchestrates healing transitions |
| | Zustand | State | Minimal boilerplate; per-domain stores; excellent TypeScript support |
| **Backend** | Python 3.11+ | Language | AI/ML ecosystem maturity; LangChain + Neo4j driver availability |
| | FastAPI | Framework | Async-first; auto-generated OpenAPI; native Pydantic validation |
| | Redis | Cache | Sub-millisecond caching; Celery broker; rate limiting |
| **Knowledge Graph** | Neo4j 5.x | Graph DB | Native graph storage; Cypher query language; APOC + GDS ecosystem |
| | APOC + GDS | Plugins | Extended traversals, graph algorithms (PageRank, centrality) |
| | PostgreSQL | Relational DB | Audit logs, structured metadata; complements graph for tabular data |
| **AI / Reasoning** | LangChain | Agent Framework | ReAct agent loop; tool-calling; prompt management; output parsing |
| | OpenAI / Gemini | LLM Provider | State-of-the-art reasoning; tool-calling support; multi-model flexibility |
| | ChromaDB | Vector Store | Incident-similarity search via embeddings; lightweight and self-hosted |
| **Observability** | OpenTelemetry | Instrumentation | Vendor-neutral; auto-instruments all service communication |
| | Prometheus | Metrics | Industry standard time-series; PromQL for agent metric queries |
| | Grafana | Dashboards | Pre-built ecosystem; Prometheus + Jaeger data source integration |
| | Jaeger | Tracing | Distributed tracing; OpenTelemetry-native; trace-to-log correlation |
| **Infrastructure** | Docker | Containers | Reproducible builds; multi-stage images; CI/CD compatibility |
| | Kubernetes | Orchestration | Production-parity sandbox; target deployment platform for Review 3 |
| | Kind / Minikube | Local K8s | Zero-cost local cluster for development and demonstration |
| | Chaos Mesh | Chaos Eng. | Kubernetes-native fault injection; controlled evaluation benchmarks |

---

## 10. Integration & Data Flow Architecture

### Mode 1: "See Every Risk Before It Ships"

```
GitHub PR Webhook
      │
      ▼
  FastAPI  ──parse diff──▶  Simulation Engine  ──BFS traversal──▶  Neo4j
      │                                                              │
      │                       ◄── blast radius + risk score ─────────┘
      ▼
  CI/CD Shield Gate  ──verdict──▶  GitHub Status Check
      │
      ▼
  WebSocket  ──stream──▶  React Dashboard  (Cytoscape.js renders impact)
```

### Mode 2: "Heal Every Failure After It Lands"

```
OpenTelemetry / Prometheus  ──anomaly signal──▶  FastAPI
      │
      ▼
  LangChain ReAct Agent
      │
      ├──tool call──▶  Neo4j Cypher Tool     (2-hop dependency query)
      ├──tool call──▶  Prometheus Tool        (live metric fetch)
      ├──tool call──▶  Vector Store Tool      (similar incident lookup)
      │
      ▼
  Diagnosis + Ranked Remediation Candidates
      │
      ▼
  Guarded Execution Layer  ──apply fix──▶  Kubernetes API
      │                                         │
      │     ◄── health probe verification ──────┘
      │     ◄── Dead-Man's Switch (auto-rollback if unhealthy)
      │
      ▼
  Feedback Writer  ──write──▶  Neo4j  (new :Incident + :Decision nodes)
      │
      ▼
  Future risk predictions now incorporate this incident ✓
```

---

## 11. Version Policy & Compatibility Matrix

> **Version Policy:** AEGIS pins **major** versions of all core dependencies and floats patch versions for security updates. All version constraints are locked via `package-lock.json` (frontend) and `poetry.lock` / `requirements.txt` (backend) to ensure reproducible builds across all environments.

| Dependency | Minimum Version | Version Policy | Compatibility Notes |
|:---|:---|:---|:---|
| Node.js | 18 LTS+ | Pin major, float minor | Required for Vite dev server and build toolchain |
| Python | 3.11+ | Pin minor | Required for `asyncio` improvements and LangChain compatibility |
| Neo4j | 5.0+ | Pin major | Cypher syntax and APOC compatibility tied to Neo4j 5.x series |
| Docker | 24.0+ | Pin major | Multi-stage build support and BuildKit features required |
| Kubernetes | 1.28+ | Pin minor | API version compatibility for Chaos Mesh CRDs and Helm charts |

---

*AEGIS — Autonomous Engineering Graph & Intelligence System • Technology Stack Document • Major Project Review 2*
