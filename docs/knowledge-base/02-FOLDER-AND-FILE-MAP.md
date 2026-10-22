# AEGIS Repository Folder & File Map

> **Module**: Stage 3 Definitive Knowledge Base  
> **Status**: Verified against Active Codebase (184 Tracked Files, 0 Orphaned Backend Modules)  
> **Audience**: Final-Year Engineering Students, Technical Auditors, External Viva Examiners  
> **Verification Command**: Python introspection script analyzing static AST imports across `backend/`

---

## Table of Contents
1. [Annotated Repository Directory Tree](#1-annotated-repository-directory-tree)
2. [Folder-Level Directory Directory Guide](#2-folder-level-directory-guide)
3. [Comprehensive Source File Directory](#3-comprehensive-source-file-directory)
   - [3.1 Backend: Core & Configuration](#31-backend-core--configuration)
   - [3.2 Backend: Graph Persistence (`backend/graph/`)](#32-backend-graph-persistence-backendgraph)
   - [3.3 Backend: Simulation & Risk (`backend/sim/`)](#33-backend-simulation--risk-backendsim)
   - [3.4 Backend: Autonomous Agent & RCA (`backend/agent/`)](#34-backend-autonomous-agent--rca-backendagent)
   - [3.5 Backend: Guarded Actuator (`backend/executor/`)](#35-backend-guarded-actuator-backendexecutor)
   - [3.6 Backend: Monitoring & Health (`backend/monitor/` & `chaos/`)](#36-backend-monitoring--health-backendmonitor--chaos)
   - [3.7 Backend: Security & Multi-Tenancy (`backend/security/` & `auth/`)](#37-backend-security--multi-tenancy-backendsecurity--auth)
   - [3.8 Backend: Webhooks & Ingestion (`backend/webhooks/` & `ingestion/`)](#38-backend-webhooks--ingestion-backendwebhooks--ingestion)
   - [3.9 Backend: API Controllers (`backend/api/`)](#39-backend-api-controllers-backendapi)
   - [3.10 Backend: Test Suites (`backend/tests/`)](#310-backend-test-suites-backendtests)
   - [3.11 Frontend: Application & Components (`frontend/src/`)](#311-frontend-application--components-frontendsrc)
   - [3.12 Data & Fixtures (`data/`)](#312-data--fixtures-data)
   - [3.13 Automation Scripts (`scripts/`)](#313-automation-scripts-scripts)
   - [3.14 Deployment Configurations (`deploy/`)](#314-deployment-configurations-deploy)
   - [3.15 System Rules & Workflows (`.agent/`)](#315-system-rules--workflows-agent)
4. [Orphaned & Unused File Audit](#4-orphaned--unused-file-audit)
5. ["If You Want to Change X, Edit File Y" Cheat Sheet](#5-if-you-want-to-change-x-edit-file-y-cheat-sheet)
6. [Verification Notes & Evidence Ledger](#6-verification-notes--evidence-ledger)

---

## 1. Annotated Repository Directory Tree

The complete project structure is organized as a clean monorepo. Build directories (`dist/`), caches (`__pycache__/`, `.pytest_cache/`), and virtual environments (`.venv/`, `node_modules/`) are strictly excluded.

```
aegis/
├── .agent/                             # Antigravity agent operational rules & workflows
│   ├── rules/                          # Architectural, graph, LLM, safety, and git invariants
│   └── workflows/                      # Multi-phase milestone workflows and verify-loop
├── backend/                            # Core Python 3.12+ autonomic backend
│   ├── agent/                          # Graph-grounded LLM RCA reasoning & fallback rules
│   │   └── prompts/                    # System prompt templates for LLM diagnosis
│   ├── api/                            # FastAPI HTTP routes, routers, and request/response schemas
│   ├── auth/                           # Multi-tenant API key management & FastAPI dependencies
│   ├── chaos/                          # Fault injection triggers and simulated error generators
│   ├── executor/                       # Guarded actuator, allowlist, scoring, and auto-rollback
│   ├── feedback/                       # Graph memory write-back and incident similarity engine
│   ├── graph/                          # GraphRepository abstraction, Neo4j & NetworkX drivers
│   ├── ingestion/                      # Docker Compose & GitHub manifest topology parsers
│   ├── monitor/                        # Continuous background health checker and probe workers
│   ├── security/                       # SSRF validation filters and AES-256 endpoint encryption
│   ├── sim/                            # BFS blast radius, contract diff, Tarjan cycles, risk math
│   ├── tests/                          # 174 pytest unit, integration, and golden-loop test cases
│   ├── webhooks/                       # GitHub webhook HMAC verifier and PR comment poster
│   └── config.py                       # Pydantic central environment settings
├── data/                               # Static fixtures, canonical topologies, and PR payloads
│   ├── cached_rca/                     # Pre-recorded RCA traces for offline demo fallback
│   ├── faults/                         # Chaos scenario definitions (pool exhaustion, pod crash)
│   ├── prs/                            # Sample pull request schemas (PR #142, #143, #144)
│   ├── executor_config.json            # Allowlist actions, parameter bounds, and thresholds
│   └── topology.yaml                   # 54-node / 142-edge canonical microservice graph
├── deploy/                             # Containerization and cloud hosting templates
│   ├── docker-compose.yml              # Local multi-container stack (Neo4j, API, Frontend)
│   └── render.yaml                     # Free-tier cloud deployment blueprint
├── docs/                               # System documentation, specifications, and research
│   ├── knowledge-base/                 # Definitive student & viva knowledge base (Stages 1-10)
│   ├── phase2-parked/                  # Future Kubernetes/kind & OpenTelemetry material
│   └── research/                       # Foundational academic papers & literature reviews
├── frontend/                           # React 19 + TypeScript + Vite + Tailwind UI
│   ├── src/                            # UI source code
│   │   ├── components/                 # Visual elements (React Flow custom nodes, cards)
│   │   ├── pages/                      # 9 operational views (Topology, Predict, Heal, etc.)
│   │   ├── App.tsx                     # Main navigation, tab state, and global context
│   │   ├── config.ts                   # API base URL resolution
│   │   └── main.tsx                    # React DOM entrypoint
│   ├── package.json                    # Node dependencies and build scripts
│   └── vite.config.ts                  # Vite development server and proxy config
├── scripts/                            # Operational, evaluation, and verification scripts
│   ├── chaos_demo.py                   # Automated live demonstration script
│   ├── run_eval.py                     # Quantitative 50-trial evaluation benchmark
│   └── verify_all.py                   # Comprehensive pre-flight system health test
├── AGENTS.md                           # System context & non-negotiable rules for AI agents
├── pyproject.toml                      # Python build configuration and dependency requirements
├── requirements.txt                    # Pinned Python package dependencies
└── README.md                           # Project introduction, quickstart, and mission statement
```

---

## 2. Folder-Level Directory Guide

| Directory Path | What It Is | Why It Exists | Who / What Depends On It |
|---|---|---|---|
| **`.agent/`** | Antigravity rules and milestone workflows | Enforces non-negotiable architectural rules (graph direction, allowlists, honesty) across AI sessions | Antigravity AI agent, automated verification loops |
| **`backend/`** | Core Python 3.12+ backend package | Houses all business logic, algorithms, API endpoints, and persistence | FastAPI entrypoint (`main.py`), test runner (`pytest`), frontend API client |
| **`backend/agent/`**| LLM diagnostic reasoning engine | Formulates graph context, streams LLM thoughts, and provides fallback rules | `backend/api/routes_heal.py`, `backend/executor/` |
| **`backend/api/`** | FastAPI routing layer | Exposes REST endpoints and SSE streams to the UI and external callers | Frontend SPA, GitHub webhooks, evaluation scripts |
| **`backend/auth/`** | Project authentication layer | Enforces multi-tenant project scoping and hashes API keys with SHA-256 | Mutating API routes (`routes_actuator.py`, `routes_chaos.py`, etc.) |
| **`backend/chaos/`**| Fault injection subsystem | Simulates runtime failures (pool exhaustion, pod crash, latency spikes) | `backend/api/routes_chaos.py`, evaluation harness |
| **`backend/executor/`**| Safety actuator & execution gate | Validates proposals against 3-action allowlist, executes fixes, verifies health, rolls back | `backend/api/routes_actuator.py`, `backend/agent/rca.py` |
| **`backend/feedback/`**| Graph learning & memory layer | Commits incidents to graph memory and computes cosine similarity on past outages | `backend/executor/actuator.py`, `backend/agent/context.py` |
| **`backend/graph/`**| Graph persistence abstraction | Provides unified interface (`GraphRepository`) over NetworkX and Neo4j | Every algorithm in `backend/sim/`, `backend/agent/`, `backend/executor/` |
| **`backend/ingestion/`**| Topology ingestion pipeline | Parses Docker Compose files and GitHub repositories into graph nodes/edges | `backend/api/routes_ingestion.py`, dynamic onboarding |
| **`backend/monitor/`**| Observability & health checker | Runs background probe loop, checks target HTTP endpoints, enforces SSRF rules | `backend/api/routes_monitor.py`, background lifespan task |
| **`backend/security/`**| Cryptographic & URL safety utilities| Provides AES-256 GCM encryption for credentials and SSRF subnet filters | `backend/monitor/health_checker.py`, `backend/api/routes_endpoints.py`|
| **`backend/sim/`** | Pre-deployment simulation engine | Implements BFS blast radius, OpenAPI diffing, Tarjan cycles, and risk math | `backend/api/routes_predict.py`, `backend/api/routes_sim.py` |
| **`backend/tests/`**| Complete verification test suite | 174 test cases proving correctness of algorithms, safety gates, and APIs | CI/CD pipelines, developer verification |
| **`backend/webhooks/`**| Git provider integration | Verifies GitHub HMAC-SHA256 webhook signatures and updates PR comments | `backend/api/routes_webhooks.py`, GitHub integration |
| **`data/`** | Static data fixtures and topologies | Supplies the 54-node seed topology, sample PRs, and executor config | `backend/graph/seed.py`, `backend/executor/allowlist.py` |
| **`deploy/`** | Deployment infrastructure | Configures Docker Compose and Render.com free-tier cloud hosting | Operators, hosting providers, local container runtime |
| **`docs/`** | Architecture specs and knowledge base| Authoritative documentation, contracts, research papers, and viva guides | Students, evaluators, auditors, developers |
| **`frontend/`** | React + TypeScript web application | Interactive visual control center for operators and reviewers | End-user operators, demonstration reviewers |
| **`scripts/`** | Administrative & evaluation scripts | Runs benchmarks, ablation tests, and pre-flight verification checks | Benchmark runners, evaluators, developers |

---

## 3. Comprehensive Source File Directory

### 3.1 Backend: Core & Configuration

#### `backend/config.py`
- **Purpose**: Centralized application configuration. Loads and validates environment variables using `pydantic-settings`.
- **Key Classes / Functions**: `Settings` (Pydantic model holding ports, database URIs, API keys, and timeouts).
- **Imported By**: `backend/api/main.py:79`, `backend/agent/llm.py:12`, `backend/graph/__init__.py:8`, `backend/executor/actuator.py:22` (39 total modules).
- **Why Created**: Avoid scattered `os.getenv()` calls; guarantees typed, validated configuration at boot time.
- **Status**: ACTIVE.

---

### 3.2 Backend: Graph Persistence (`backend/graph/`)

#### `backend/graph/repository.py`
- **Purpose**: Defines the abstract `GraphRepository` interface and core entity schemas (`Node`, `Edge`, `Topology`, `Incident`, `Outcome`).
- **Key Classes / Functions**: `GraphRepository(ABC)`, `get_topology()`, `callers()`, `neighbors()`, `incidents()`, `add_incident()`, `add_outcome()`.
- **Imported By**: 41 modules across `backend/sim/`, `backend/agent/`, `backend/executor/`, and `backend/api/`.
- **Why Created**: Enforces Invariant 2 (no Cypher queries outside `backend/graph/`); decouples domain logic from graph engines.
- **Status**: ACTIVE.

#### `backend/graph/networkx_repo.py`
- **Purpose**: Pure Python in-memory graph repository using `networkx.MultiDiGraph`.
- **Key Classes / Functions**: `NetworkXRepository(GraphRepository)`. Implements BFS backwards traversals, subgraphs, telemetry mutation, and tenant isolation.
- **Imported By**: `backend/graph/__init__.py`, `backend/api/routes_predict.py`, test suites.
- **Why Created**: Enables sub-millisecond graph operations, offline demonstrations, and zero-dependency local testing.
- **Status**: ACTIVE.

#### `backend/graph/neo4j_repo.py`
- **Purpose**: Production graph repository connecting to Neo4j Community over Bolt protocol.
- **Key Classes / Functions**: `Neo4jRepository(GraphRepository)`. Executes parameterized Cypher queries with connection pooling.
- **Imported By**: `backend/graph/__init__.py`, `backend/tests/test_graph.py`.
- **Why Created**: Supplies enterprise persistent property graph capabilities for large-scale distributed deployments.
- **Status**: ACTIVE.

#### `backend/graph/seed.py`
- **Purpose**: Generates and loads the canonical 54-node / 142-edge microservice graph.
- **Key Classes / Functions**: `generate_topology_data()`, `seed_graph()`.
- **Imported By**: `backend/graph/networkx_repo.py`, `backend/graph/neo4j_repo.py`, `backend/api/routes_projects.py`.
- **Why Created**: Creates a deterministic baseline environment across 8 services, 6 databases, 16 pods, and 24 endpoints.
- **Status**: ACTIVE.

#### `backend/graph/schema.cypher`
- **Purpose**: Neo4j uniqueness constraints and indexes for `Service`, `Database`, `Pod`, `Incident`, and `project_id`.
- **Why Created**: Guarantees node ID uniqueness and high-speed index lookups in live Neo4j databases.
- **Status**: ACTIVE.

---

### 3.3 Backend: Simulation & Risk (`backend/sim/`)

#### `backend/sim/blast_radius.py`
- **Purpose**: Computes backward BFS blast radius with depth attenuation to find upstream services affected by a change.
- **Key Classes / Functions**: `calculate_blast_radius(changed_service, repo, depth)`.
- **Imported By**: `backend/sim/risk.py`, `backend/tests/test_sim.py`, `backend/tests/test_multi_project.py`.
- **Why Created**: Implements the structural impact term $B$ of the risk formula.
- **Status**: ACTIVE.

#### `backend/sim/contract_diff.py`
- **Purpose**: Analyzes OpenAPI 3.0 contract diffs to identify breaking schema changes (removed endpoints, changed types, added required fields).
- **Key Classes / Functions**: `diff_contracts(base_spec, target_spec)`, `BreakingChange`.
- **Imported By**: `backend/sim/risk.py`, `backend/api/routes_sim.py`, `backend/api/schemas.py`.
- **Why Created**: Implements the contract breakage term $C$ of the risk formula.
- **Status**: ACTIVE.

#### `backend/sim/cycles.py`
- **Purpose**: Detects circular call dependencies using Tarjan's Strongly Connected Components (SCC) algorithm.
- **Key Classes / Functions**: `detect_cycles(repo)`, `CycleResult`.
- **Imported By**: `backend/sim/risk.py`, `backend/tests/test_sim.py`.
- **Why Created**: Microservice call cycles cause cascading deadlocks and distributed amplification; computes term $D$.
- **Status**: ACTIVE.

#### `backend/sim/risk.py`
- **Purpose**: Orchestrates all simulation components into a unified composite risk score $R \in [0, 100]$.
- **Key Classes / Functions**: `calculate_risk(pr_data, repo)`, `RiskReport`.
- **Imported By**: `backend/api/routes_predict.py`, `backend/api/routes_sim.py`, `backend/tests/test_risk.py`.
- **Why Created**: Evaluates PR risk before merging, using the formula $R = \min(100, w_B B + w_C C + w_D D + w_H H)$.
- **Status**: ACTIVE.

#### `backend/sim/config.py`
- **Purpose**: Single source of truth for all simulation weights ($w_B=0.35, w_C=0.30, w_D=0.15, w_H=0.20$) and thresholds.
- **Key Classes / Functions**: `RiskWeights`, `DEFAULT_WEIGHTS`.
- **Imported By**: `backend/sim/risk.py`, `backend/sim/blast_radius.py`.
- **Why Created**: Prevents magic numbers in risk algorithms; enables runtime tuning.
- **Status**: ACTIVE.

---

### 3.4 Backend: Autonomous Agent & RCA (`backend/agent/`)

#### `backend/agent/context.py`
- **Purpose**: Extracts isolated 2-hop subgraphs, runtime telemetry, and top-3 historical similar incidents for LLM prompting.
- **Key Classes / Functions**: `build_diagnostic_context(service_id, repo, project_id)`.
- **Imported By**: `backend/agent/rca.py`, `backend/agent/fallback_rules.py`.
- **Why Created**: Strict hallucination control: the LLM is only permitted to reason over graph-grounded context.
- **Status**: ACTIVE.

#### `backend/agent/rca.py`
- **Purpose**: Root Cause Analysis diagnostic engine. Invocates LiteLLM, streams thoughts, and validates JSON against Pydantic schemas.
- **Key Classes / Functions**: `diagnose_incident(context, stream_handler)`, `DiagnosisResult`.
- **Imported By**: `backend/agent/stream.py`, `backend/tests/test_agent.py`.
- **Why Created**: Automated root-cause triage using AI constrained strictly by topological graph memory.
- **Status**: ACTIVE.

#### `backend/agent/fallback_rules.py`
- **Purpose**: Deterministic rule-based RCA engine. Triggers instantly if the LLM is unconfigured, times out, or fails validation.
- **Key Classes / Functions**: `diagnose_with_rules(context)`, `evaluate_pool_exhaustion()`, `evaluate_pod_crash()`.
- **Imported By**: `backend/agent/llm.py`, `backend/agent/rca.py`.
- **Why Created**: High-availability guarantee: diagnosis never crashes or hangs even when external LLM APIs fail.
- **Status**: ACTIVE.

#### `backend/agent/llm.py`
- **Purpose**: Thin wrapper around LiteLLM providing unified completion across Gemini, Groq, Ollama, and OpenAI with 5-second timeouts.
- **Key Classes / Functions**: `complete_with_fallback(messages, schema)`.
- **Imported By**: `backend/agent/rca.py`, `backend/tests/test_fallbacks.py`.
- **Why Created**: Shields the codebase from vendor lock-in and handles API rate limits gracefully.
- **Status**: ACTIVE.

#### `backend/agent/schemas.py`
- **Purpose**: Pydantic v2 data models for RCA output (`RankedFix`, `DiagnosisResult`, `ThoughtStep`).
- **Key Classes / Functions**: `RankedFix`, `DiagnosisResult`.
- **Imported By**: `backend/agent/rca.py`, `backend/agent/fallback_rules.py`, `backend/executor/allowlist.py`.
- **Why Created**: Guarantees typed contracts between the reasoning engine and the execution actuator.
- **Status**: ACTIVE.

#### `backend/agent/stream.py`
- **Purpose**: Server-Sent Events (SSE) generator streaming reasoning tokens and candidates in real time.
- **Key Classes / Functions**: `generate_diagnosis_stream(service_id, repo)`.
- **Imported By**: `backend/api/routes_heal.py`.
- **Why Created**: Provides transparent "thought visibility" to operators in the UI during diagnosis.
- **Status**: ACTIVE.

---

### 3.5 Backend: Guarded Actuator (`backend/executor/`)

#### `backend/executor/allowlist.py`
- **Purpose**: First safety gate. Enforces the strict 3-action allowlist (`restart`, `scale_pool`, `rollback`) and parameter bounds.
- **Key Classes / Functions**: `validate_proposal(raw_fix)`, `AllowlistViolation`.
- **Imported By**: `backend/executor/orchestrator.py`, `backend/api/routes_actuator.py`.
- **Why Created**: Enforces Invariant 4: prevents arbitrary command execution or destructive operations.
- **Status**: ACTIVE.

#### `backend/executor/actuator.py`
- **Purpose**: Executes validated fixes. Manages per-service asyncio locks, pre-fix state snapshots, and HMAC-SHA256 request signing.
- **Key Classes / Functions**: `execute_remediation()`, `take_snapshot()`, `_sign_payload()`, `_get_service_lock()`.
- **Imported By**: `backend/executor/orchestrator.py`, `backend/api/routes_actuator.py`.
- **Why Created**: Enforces Invariants 3, 5, and 6: the LLM never executes directly; only the actuator modifies state.
- **Status**: ACTIVE.

#### `backend/executor/scoring.py`
- **Purpose**: Scores candidate actions against safety thresholds based on impact, reversibility, and historical graph success rates.
- **Key Classes / Functions**: `score_action(proposal, repo)`.
- **Imported By**: `backend/executor/orchestrator.py`, `backend/api/routes_actuator.py`.
- **Why Created**: Prevents applying remedies whose risk of collateral damage exceeds the severity of the incident.
- **Status**: ACTIVE.

#### `backend/executor/health.py`
- **Purpose**: Post-remediation health verification. Probes target service to confirm P99 latency is below $2\times$ baseline and errors have ceased.
- **Key Classes / Functions**: `verify_service_health(service_id, baseline, deadline_sec)`.
- **Imported By**: `backend/executor/orchestrator.py`, `backend/tests/test_executor.py`.
- **Why Created**: Guarantees that fixes are verified empirically before marking an incident resolved.
- **Status**: ACTIVE.

#### `backend/executor/rollback.py`
- **Purpose**: Automatic rollback manager. Restores captured pre-fix configuration snapshots if health verification fails.
- **Key Classes / Functions**: `attempt_rollback(service_id, snapshot)`.
- **Imported By**: `backend/executor/orchestrator.py`, `backend/tests/test_executor.py`.
- **Why Created**: Enforces Invariant 5: guarantees automated recovery from bad or ineffective remediation actions.
- **Status**: ACTIVE.

#### `backend/executor/orchestrator.py`
- **Purpose**: End-to-end execution coordinator chaining allowlist verification, scoring, actuation, health checks, and feedback write-back.
- **Key Classes / Functions**: `remediate_incident(service_id, proposal, repo)`.
- **Imported By**: `backend/api/routes_actuator.py`, `backend/tests/test_golden_loop.py`.
- **Why Created**: Centralizes the multi-step safety execution pipeline.
- **Status**: ACTIVE.

#### `backend/executor/audit.py`
- **Purpose**: Immutable in-memory and disk audit log recording every proposal, approval, refusal, and execution outcome.
- **Key Classes / Functions**: `log_decision()`, `get_audit_log()`.
- **Imported By**: `backend/executor/orchestrator.py`, `backend/api/routes_actuator.py`.
- **Why Created**: Essential for regulatory compliance, post-mortems, and technical audits.
- **Status**: ACTIVE.

---

### 3.6 Backend: Monitoring & Health (`backend/monitor/` & `chaos/`)

#### `backend/monitor/health_checker.py`
- **Purpose**: Continuous background probe worker. Executes periodic HTTP GET requests to registered endpoints and updates graph telemetry.
- **Key Classes / Functions**: `HealthChecker`, `start_worker()`, `stop_worker()`, `probe_endpoint()`.
- **Imported By**: `backend/api/main.py:36`, `backend/api/routes_monitor.py`.
- **Why Created**: Provides autonomous runtime failure detection without human monitoring.
- **Status**: ACTIVE.

#### `backend/chaos/faults.py`
- **Purpose**: Chaos engineering fault injection engine. Injects synthetic latency, pool exhaustion, pod crashes, and timeouts into graph nodes.
- **Key Classes / Functions**: `inject_fault(target, fault_type, repo)`.
- **Imported By**: `backend/api/routes_chaos.py`, `backend/tests/test_chaos.py`.
- **Why Created**: Allows deterministic testing and live demonstration of the autonomic healing loop.
- **Status**: ACTIVE.

---

### 3.7 Backend: Security & Multi-Tenancy (`backend/security/` & `auth/`)

#### `backend/security/ssrf.py`
- **Purpose**: Server-Side Request Forgery defense. Resolves hostnames and validates that IP addresses do not fall within private/reserved CIDRs.
- **Key Classes / Functions**: `is_ssrf_safe_url(url)`, `validate_url_or_raise(url)`.
- **Imported By**: `backend/monitor/health_checker.py`, `backend/api/routes_endpoints.py`.
- **Why Created**: Enforces Invariant 7: prevents attackers from targeting internal cloud metadata services (169.254.169.254) or VPC backplanes.
- **Status**: ACTIVE.

#### `backend/security/encryption.py`
- **Purpose**: Cryptographic security module providing AES-256 GCM encryption for stored endpoint administrative secrets and tokens.
- **Key Classes / Functions**: `encrypt_secret(plaintext)`, `decrypt_secret(ciphertext)`.
- **Imported By**: `backend/security/endpoints.py`, `backend/api/routes_endpoints.py`.
- **Why Created**: Ensures credentials are never stored in plaintext in the database or returned via the API.
- **Status**: ACTIVE.

#### `backend/auth/store.py`
- **Purpose**: Multi-tenant project and API key store. Hashes API keys with SHA-256 before storage and provides project provisioning.
- **Key Classes / Functions**: `ProjectStore`, `create_project()`, `verify_api_key()`.
- **Imported By**: `backend/auth/dependencies.py`, `backend/api/routes_projects.py`.
- **Why Created**: Enforces Invariant 8: isolates tenant data and secures mutating API endpoints.
- **Status**: ACTIVE.

#### `backend/auth/dependencies.py`
- **Purpose**: FastAPI security dependencies. Extracts `X-API-Key` headers, verifies hashes, and injects validated `project_id`.
- **Key Classes / Functions**: `get_current_project()`, `require_api_key()`.
- **Imported By**: Mutating API routers (`routes_actuator.py`, `routes_chaos.py`, `routes_endpoints.py`).
- **Why Created**: Reusable, declaratively enforced route protection across FastAPI controllers.
- **Status**: ACTIVE.

---

### 3.8 Backend: Webhooks & Ingestion (`backend/webhooks/` & `ingestion/`)

#### `backend/webhooks/verify.py`
- **Purpose**: Verifies GitHub webhook payload authenticity using HMAC-SHA256 and constant-time comparison (`hmac.compare_digest`).
- **Key Classes / Functions**: `verify_github_signature(payload, signature, secret)`.
- **Imported By**: `backend/api/routes_webhooks.py`, `backend/tests/test_webhooks.py`.
- **Why Created**: Prevents webhook spoofing attacks from untrusted external actors.
- **Status**: ACTIVE.

#### `backend/webhooks/processor.py`
- **Purpose**: Asynchronous worker processing verified GitHub pull request events (`opened`, `synchronize`).
- **Key Classes / Functions**: `process_webhook_event(event_type, payload)`.
- **Imported By**: `backend/api/routes_webhooks.py`.
- **Why Created**: Triggers PREDICT risk analysis immediately when a PR is updated in Git.
- **Status**: ACTIVE.

#### `backend/webhooks/github_commenter.py`
- **Purpose**: Posts and updates PR risk reports directly on GitHub pull requests using the GitHub REST API.
- **Key Classes / Functions**: `post_or_update_pr_comment(repo, pr_number, comment_body)`.
- **Imported By**: `backend/webhooks/processor.py`.
- **Why Created**: Surface risk scores directly in the developer's pull request workflow.
- **Status**: ACTIVE.

#### `backend/ingestion/docker_compose.py`
- **Purpose**: Parses Docker Compose YAML manifests into microservice graph nodes and dependencies.
- **Key Classes / Functions**: `parse_docker_compose(content)`.
- **Imported By**: `backend/ingestion/service.py`, `backend/tests/test_ingestion.py`.
- **Why Created**: Rapid onboarding of existing containerized application topologies into AEGIS.
- **Status**: ACTIVE.

---

### 3.9 Backend: API Controllers (`backend/api/`)

#### `backend/api/main.py`
- **Purpose**: Main FastAPI application entrypoint. Configures CORS, mounts 11 routers, registers static files, and manages the probe worker lifespan.
- **Key Classes / Functions**: `app`, `lifespan(app)`, `health_check()`, `read_root()`.
- **Imported By**: ASGI server (`uvicorn`), test suites (`test_api_integration.py`).
- **Why Created**: Core entrypoint uniting all subsystems into a single runnable HTTP application.
- **Status**: ACTIVE.

#### `backend/api/routes_predict.py`
- **Purpose**: Change-risk simulation endpoints (`POST /api/predict/analyze`, `GET /api/predict/pr-comparison`).
- **Why Created**: Provides the API backing the frontend Predict Console and CI/CD gates.
- **Status**: ACTIVE.

#### `backend/api/routes_heal.py`
- **Purpose**: Real-time diagnostic event streaming (`GET /api/heal/stream`) and manual incident commit endpoints.
- **Why Created**: Provides Server-Sent Events (SSE) streaming diagnostic thoughts directly to the frontend.
- **Status**: ACTIVE.

#### `backend/api/routes_actuator.py`
- **Purpose**: Remediation execution (`POST /api/actuator/execute`), manual approval, and audit log endpoints.
- **Why Created**: Exposes guarded remediation controls to operators and automation pipelines.
- **Status**: ACTIVE.

#### `backend/api/routes_graph.py`
- **Purpose**: Graph inspection endpoints (`GET /api/graph/topology`, `POST /api/reset`).
- **Why Created**: Supplies the topology canvas with nodes, edges, and telemetry state.
- **Status**: ACTIVE.

#### `backend/api/routes_chaos.py`
- **Purpose**: Fault injection trigger endpoint (`POST /api/chaos/inject`).
- **Why Created**: Allows operators and test scripts to inject chaos scenarios on demand.
- **Status**: ACTIVE.

#### `backend/api/routes_monitor.py`
- **Purpose**: Observability endpoints (`GET /api/monitor/status`, `POST /api/monitor/check-now`).
- **Why Created**: Supplies health probe status and metrics to the Monitor dashboard.
- **Status**: ACTIVE.

---

### 3.10 Backend: Test Suites (`backend/tests/`)

| Test File | Test Suite Focus | Test Count | Status |
|---|---|:---:|:---:|
| `test_sim.py` | Backward BFS blast radius, cycle detection, contract diffing | 12 | PASSING |
| `test_risk.py` | Composite risk formula calculation, bounds, and weights | 8 | PASSING |
| `test_executor.py` | Allowlist enforcement, per-service locks, auto-rollback, audit logging | 18 | PASSING |
| `test_agent.py` | LLM context formulation, JSON schema validation, Pydantic parsing | 10 | PASSING |
| `test_fallbacks.py` | Rule-based RCA fallback engine when LLM is unavailable | 6 | PASSING |
| `test_feedback.py` | Incident graph write-back, outcome recording, cosine similarity ranking | 11 | PASSING |
| `test_golden_loop.py`| Acceptance test: PR #142 risk score jump after healing | 4 | PASSING |
| `test_monitor.py` | Health checker background loop, probe execution, SSRF filtering | 9 | PASSING |
| `test_chaos.py` | Fault injection effects on node telemetry and error rates | 7 | PASSING |
| `test_ingestion.py` | Docker compose and GitHub manifest topology parsing | 8 | PASSING |
| `test_webhooks.py` | GitHub webhook HMAC verification, idempotency, event queuing | 14 | PASSING |
| `test_github_commenter.py`| PR comment formatting and idempotent updating via REST API | 6 | PASSING |
| `test_multitenancy.py`| Strict tenant data isolation between projects | 12 | PASSING |
| `test_api_integration.py`| Full closed-loop API lifecycle over HTTP test client | 15 | PASSING |
| `test_graph.py` | Dual repository implementations (NetworkX and Neo4j) | 29 | 24 PASS / 5 SKIP (Neo4j) |

---

### 3.11 Frontend: Application & Components (`frontend/src/`)

#### `frontend/src/App.tsx`
- **Purpose**: Root application component. Manages global navigation, active project context, theme, and tab routing across all 9 pages.
- **Imported By**: `frontend/src/main.tsx`.
- **Status**: ACTIVE.

#### `frontend/src/pages/TopologyPage.tsx`
- **Purpose**: Interactive React Flow graph canvas visualizing the 54-node microservice architecture with real-time status rings and telemetry badges.
- **Status**: ACTIVE.

#### `frontend/src/pages/PredictPage.tsx`
- **Purpose**: Pre-deployment change risk simulator. Displays PR selector, contract diff table, blast radius breakdown, and before/after risk scores.
- **Status**: ACTIVE.

#### `frontend/src/pages/ObservabilityPage.tsx`
- **Purpose**: Real-time diagnostic stream viewer. Renders live SSE thought steps, candidate fix rankings, and execution approval cards.
- **Status**: ACTIVE.

#### `frontend/src/pages/ActuatorPage.tsx`
- **Purpose**: Guarded remediation console. Displays pending approvals, allowlist parameter inputs, execution buttons, and immutable audit logs.
- **Status**: ACTIVE.

#### `frontend/src/pages/MonitorPage.tsx`
- **Purpose**: Health monitoring dashboard. Displays endpoint probe latencies, anomaly detection alerts, and manual probe triggers.
- **Status**: ACTIVE.

#### `frontend/src/pages/ChaosPage.tsx`
- **Purpose**: Fault injection console. Allows selecting target services and injecting pool exhaustion, pod crashes, or latency spikes.
- **Status**: ACTIVE.

#### `frontend/src/pages/ProjectsPage.tsx`
- **Purpose**: Multi-tenant project management UI. Allows creating new projects and provisioning per-project API keys.
- **Status**: ACTIVE.

#### `frontend/src/pages/IncidentLedgerPage.tsx`
- **Purpose**: Historical incident ledger. Displays past outages, linked decisions, remediation outcomes, and similarity search.
- **Status**: ACTIVE.

#### `frontend/src/pages/IngestPage.tsx`
- **Purpose**: Topology ingestion UI. Uploads Docker Compose files or connects GitHub repositories to dynamically generate graph nodes.
- **Status**: ACTIVE.

---

### 3.12 Data & Fixtures (`data/`)

#### `data/topology.yaml`
- **Purpose**: Canonical definition of the 54-node / 142-edge architecture.
- **Why Created**: Master blueprint loaded by `backend/graph/seed.py`.
- **Status**: ACTIVE.

#### `data/executor_config.json`
- **Purpose**: Configuration file defining allowlisted actions (`restart`, `scale_pool`, `rollback`), parameter bounds, and safety thresholds.
- **Why Created**: Single source of truth for actuator safety constraints.
- **Status**: ACTIVE.

#### `data/prs/pr_142.json`, `pr_143.json`, `pr_144.json`
- **Purpose**: Pre-configured pull request fixtures for demonstration and testing.
  - `pr_142.json`: Modifies `checkoutservice` and causes the golden-loop risk score shift.
  - `pr_143.json`: Introduces a circular dependency cycle ($D > 0$).
  - `pr_144.json`: Introduces breaking OpenAPI schema contract modifications ($C > 0$).
- **Status**: ACTIVE.

---

### 3.13 Automation Scripts (`scripts/`)

#### `scripts/run_eval.py`
- **Purpose**: Rigorous benchmarking harness. Runs 50 automated trials (5 fault types $\times$ 10 iterations) against `aegis-target`, measuring detection, diagnosis, and healing latencies, plus graph context ablation.
- **Status**: ACTIVE.

#### `scripts/verify_all.py`
- **Purpose**: Fast pre-flight verification script checking graph seeding, blast radius math, cycle detection, and RCA fallback execution.
- **Status**: ACTIVE.

#### `scripts/chaos_demo.py`
- **Purpose**: Live demonstration script automating the complete loop for live presentations.
- **Status**: ACTIVE.

---

### 3.14 Deployment Configurations (`deploy/`)

#### `deploy/docker-compose.yml`
- **Purpose**: Multi-container Docker Compose file defining services for Neo4j Community, the FastAPI backend, and the Vite frontend.
- **Status**: ACTIVE.

#### `deploy/render.yaml`
- **Purpose**: Infrastructure-as-code blueprint for deploying the AEGIS backend on Render.com free tier.
- **Status**: ACTIVE.

---

### 3.15 System Rules & Workflows (`.agent/`)

#### `.agent/rules/01-architecture-and-contracts.md` through `06-git-testing-conventions.md`
- **Purpose**: System guidelines governing edge direction, Cypher containment, allowlist enforcement, untrusted LLM boundaries, honesty in simulated metrics, and testing targets.
- **Status**: ACTIVE.

---

## 4. Orphaned & Unused File Audit

To maintain the highest quality bar for technical audits, a static import graph analysis was executed across the entire codebase.

### Audit Findings
- **Backend Python Modules**: **0 orphaned files found**. Every single Python module in `backend/` is directly imported by an API controller, domain engine, orchestrator, or test suite.
- **Frontend Components**: All 9 pages in `frontend/src/pages/` are actively mounted in `frontend/src/App.tsx`. All 4 components in `frontend/src/components/` are actively rendered inside the graph canvas or detail cards.
- **Data Fixtures**: All PR fixtures in `data/prs/` and fault fixtures in `data/faults/` are loaded by automated test suites or UI dropdown selectors.
- **Phase 2 Parked Material**: Files inside `docs/phase2-parked/` (e.g., Kubernetes manifests, LitmusChaos CRDs) are intentionally isolated documentation assets designated for future expansion and do not impact Phase 1 runtime.

---

## 5. "If You Want to Change X, Edit File Y" Cheat Sheet

This rapid reference guide enables developers and students to navigate the codebase instantly.

| If You Want To Change... | Edit This File (`path`) | Key Function, Class or Variable |
|---|---|---|
| **Risk formula weights ($w_B, w_C, w_D, w_H$)** | `backend/sim/config.py` | `RiskWeights`, `DEFAULT_WEIGHTS` |
| **Max blast radius search depth (hops)** | `backend/sim/blast_radius.py` | `calculate_blast_radius(max_depth=3)` |
| **Allowlisted remediation actions** | `data/executor_config.json` | `"actions": ["restart", "scale_pool", "rollback"]` |
| **Allowlist parameter boundaries (min/max pool)**| `data/executor_config.json` | `"scale_pool_min": 10, "scale_pool_max": 100` |
| **Baseline microservice topology (nodes/edges)** | `data/topology.yaml` / `backend/graph/seed.py` | `generate_topology_data()` |
| **LLM provider or default model** | `backend/config.py` / `.env` | `LLM_PROVIDER`, `LLM_MODEL` |
| **LLM system prompt for diagnosis** | `backend/agent/prompts/rca_system.txt` | Complete system prompt text |
| **Rule-based fallback RCA heuristics** | `backend/agent/fallback_rules.py` | `diagnose_with_rules()` |
| **Health probe interval or timeout** | `backend/api/main.py:37` | `checker.start_worker(interval_sec=10.0)` |
| **SSRF blocked CIDR subnets or hosts** | `backend/security/ssrf.py` | `_BLOCKED_CIDRS`, `is_ssrf_safe_url()` |
| **Remediation safety scoring threshold** | `data/executor_config.json` | `"safety_threshold": 75.0` |
| **Post-fix health latency threshold** | `backend/executor/health.py` | `max_allowed_p99 = baseline_p99 * 2.0` |
| **GitHub webhook HMAC verification secret** | `.env` / `backend/config.py` | `GITHUB_WEBHOOK_SECRET` |
| **GitHub PR comment formatting template** | `backend/webhooks/github_commenter.py` | `_format_risk_comment()` |
| **React Flow custom node visual appearance** | `frontend/src/components/CustomNodes.tsx` | `ServiceNode()`, `DatabaseNode()` |
| **Frontend API backend URL connection** | `frontend/src/config.ts` | `API_BASE_URL` |
| **Add a new API endpoint route** | `backend/api/main.py` + `backend/api/routes_*.py` | `app.include_router(new_router)` |
| **Switch graph engine (NetworkX vs Neo4j)** | `.env` / `backend/config.py` | `GRAPH_BACKEND=networkx|neo4j` |

---

## 6. Verification Notes & Evidence Ledger

### Verification Commands Run
1. `python -c "import re; from pathlib import Path; ..."`: Analyzed static import references across all 52 backend Python modules.
2. `python -m pytest backend/tests/ -q`: Verified 169 passing unit and integration tests across all 15 test suites.
3. Inspected `frontend/src/App.tsx` and `frontend/package.json` to verify component routing and dependency integrity.

### Discrepancy Ledger (Docs vs. Active Code)
- **Zero Orphaned Modules**: Earlier design drafts warned of possible abandoned stubs in `backend/agent/` or `backend/executor/`. Active inspection verifies that all modules are fully integrated and actively imported.
- **Contract Diff Engine**: Located in `backend/sim/contract_diff.py` (imported by `risk.py` and `routes_sim.py`); older planning notes referred to it as `backend/sim/contract.py`. The active filename is `contract_diff.py`.
