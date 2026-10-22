# AEGIS Complete File Inventory

This inventory contains every file in the repository (excluding `.venv`, `node_modules`, `.git`, `__pycache__`, `.pytest_cache`, and build output directories), detailing its relative path, functional classification, file size, and purpose.

**Total Tracked Files**: 184  

| Path | Type | Size (Bytes) | One-Line Functional Purpose |
| :--- | :--- | :---: | :--- |
| `.agent/rules/01-architecture-and-contracts.md` | Workflow / Antigravity Rule | 1,135 | Documentation: Architecture & contract rules |
| `.agent/rules/02-graph-rules.md` | Workflow / Antigravity Rule | 1,044 | Documentation: Graph rules |
| `.agent/rules/03-actuator-safety.md` | Workflow / Antigravity Rule | 1,231 | Documentation: Actuator & agent-tool safety (highest-scrutiny code) |
| `.agent/rules/04-llm-agent-rules.md` | Workflow / Antigravity Rule | 1,281 | Documentation: LLM / RCA agent rules |
| `.agent/rules/05-honesty-real-vs-simulated.md` | Workflow / Antigravity Rule | 972 | Documentation: Honesty rules |
| `.agent/rules/06-git-testing-conventions.md` | Workflow / Antigravity Rule | 1,088 | Documentation: Conventions |
| `.agent/workflows/verify-loop.md` | Workflow / Antigravity Rule | 1,128 | Documentation: /verify-loop — run the whole loop, even if crude |
| `.agent/workflows/week-01.md` | Workflow / Antigravity Rule | 1,573 | Documentation: Week 1 — Foundations and contracts |
| `.agent/workflows/week-02.md` | Workflow / Antigravity Rule | 1,206 | Documentation: Week 2 — Graph and canvas |
| `.agent/workflows/week-03.md` | Workflow / Antigravity Rule | 1,260 | Documentation: Week 3 — Simulation v1 (backend + PR UI) |
| `.agent/workflows/week-04.md` | Workflow / Antigravity Rule | 1,214 | Documentation: Week 4 — CI gate, drift view and ingestion-lite |
| `.agent/workflows/week-05.md` | Workflow / Antigravity Rule | 1,348 | Documentation: Week 5 — Chaos and telemetry emulator |
| `.agent/workflows/week-06.md` | Workflow / Antigravity Rule | 1,274 | Documentation: Week 6 — RCA agent v1 (streaming) |
| `.agent/workflows/week-07.md` | Workflow / Antigravity Rule | 1,309 | Documentation: Week 7 — Guarded actuator and candidate scoring |
| `.agent/workflows/week-08.md` | Workflow / Antigravity Rule | 1,179 | Documentation: Week 8 — Closed loop (the learning claim) |
| `.agent/workflows/week-09.md` | Workflow / Antigravity Rule | 1,117 | Documentation: Week 9 — Hardening, cases and deployment |
| `.agent/workflows/week-10.md` | Workflow / Antigravity Rule | 807 | Documentation: Week 10 — Polish, rehearsal and Review 2 |
| `.env.example` | Configuration File | 973 | Environment variable template specifying required secrets, ports, graph backends, and LLM keys. |
| `.gitignore` | Asset / Config | 183 | Specifies files and patterns intentionally excluded from Git revision control. |
| `AEGIS_MASTER_SYSTEM_DOCUMENTATION_REPORT.md` | Asset / Config | 28,242 | Documentation: AEGIS: Autonomous Enterprise Graph-Grounded Immune System |
| `AGENTS.md` | Asset / Config | 5,654 | Core project context, phase 1 scope, free-tier tech stack, and non-negotiable rules for agents. |
| `backend/agent/__init__.py` | Backend LLM Agent / RCA | 763 | AEGIS Agent Module: Graph-Grounded RCA & Autonomous Reasoning. |
| `backend/agent/context.py` | Backend LLM Agent / RCA | 13,138 | AEGIS Agent Context Builder (M6). Assembles graph-grounded diagnostic context for the LLM reasoning agent. |
| `backend/agent/fallback_rules.py` | Backend LLM Agent / RCA | 8,648 | AEGIS Agent Fallback Rules (M6). Deterministic root cause analysis rules when the LLM is unreachable, |
| `backend/agent/llm.py` | Backend LLM Agent / RCA | 3,439 | AEGIS LiteLLM Wrapper (M6). Abstracts LLM invocations with strict timeouts and automatic fallback chaining: |
| `backend/agent/prompts/rca_system.txt` | Backend LLM Agent / RCA | 1,895 | You are the AEGIS Root Cause Analysis (RCA) diagnostic engine. |
| `backend/agent/rca.py` | Backend LLM Agent / RCA | 6,289 | AEGIS Root Cause Analysis (RCA) Diagnostic Engine (M6). Orchestrates LLM diagnostic reasoning over graph context: |
| `backend/agent/schemas.py` | Backend LLM Agent / RCA | 1,932 | AEGIS Agent Schemas (Pydantic v2). Defines the structured output contracts for graph-grounded root cause analysis (RCA) |
| `backend/agent/stream.py` | Backend LLM Agent / RCA | 7,650 | AEGIS Diagnosis SSE Stream Generator & Execution Logger (M6). Streams real-time agent reasoning events over SSE: |
| `backend/api/main.py` | Backend REST Route / Schema | 4,007 | AEGIS Core API Service (M0). Mounts: |
| `backend/api/routes_actuator.py` | Backend REST Route / Schema | 5,789 | AEGIS Executor API Routes (backend/api/routes_actuator.py). Routes: |
| `backend/api/routes_chaos.py` | Backend REST Route / Schema | 4,359 | AEGIS Chaos & Fault Injection Endpoints (docs/02-CONTRACTS.md §4). |
| `backend/api/routes_endpoints.py` | Backend REST Route / Schema | 5,976 | AEGIS Service Endpoints Registration & Management Routes. Per-project service endpoint registration: |
| `backend/api/routes_graph.py` | Backend REST Route / Schema | 2,146 | AEGIS Graph & Topology Endpoints (docs/02-CONTRACTS.md §4). |
| `backend/api/routes_heal.py` | Backend REST Route / Schema | 11,064 | AEGIS Healing, Diagnosis SSE Stream & Actuator Endpoints (docs/02-CONTRACTS.md §4 & §5). |
| `backend/api/routes_ingestion.py` | Backend REST Route / Schema | 2,224 | AEGIS Ingestion API Endpoints (Directive §3.B). |
| `backend/api/routes_monitor.py` | Backend REST Route / Schema | 5,505 | Server-Sent Events (SSE) stream emitting {type: 'probe'\|'anomaly'\|'recovered', ts, payload}. |
| `backend/api/routes_predict.py` | Backend REST Route / Schema | 10,004 | AEGIS PREDICT Change-Risk Analysis API Endpoints (Directive §3.A). |
| `backend/api/routes_projects.py` | Backend REST Route / Schema | 4,205 | AEGIS Project Management & API Key Management Endpoints. Allows creating new projects, provisioning per-project API keys (hashe... |
| `backend/api/routes_sim.py` | Backend REST Route / Schema | 2,828 | AEGIS Pre-Ship Simulation Endpoints (docs/02-CONTRACTS.md §4). |
| `backend/api/routes_webhooks.py` | Backend REST Route / Schema | 6,048 | AEGIS GitHub Webhook Endpoints. Mounts: |
| `backend/api/schemas.py` | Backend REST Route / Schema | 3,116 | AEGIS API Schemas & Data Contracts (docs/02-CONTRACTS.md §4 & §5). |
| `backend/auth/__init__.py` | Backend Auth & Multi-Tenancy | 427 | AEGIS Authentication & Per-Project API Key Package. |
| `backend/auth/dependencies.py` | Backend Auth & Multi-Tenancy | 3,658 | FastAPI Authentication Dependencies for Per-Project API Keys. Enforces valid API key verification on all mutating routes. |
| `backend/auth/store.py` | Backend Auth & Multi-Tenancy | 6,571 | AEGIS Multi-Tenant Project & API Key Storage (Hashed in Storage). Stores per-project API keys securely as SHA-256 hex digests i... |
| `backend/config.py` | Python Source | 4,169 | AEGIS Central Configuration Module. Loads and validates all environment variables using pydantic-settings. |
| `backend/executor/__init__.py` | Backend Guarded Actuator | 19 | # Executor package |
| `backend/executor/actuator.py` | Backend Guarded Actuator | 9,340 | AEGIS Executor — Guarded Actuator (backend/executor/actuator.py). SAFETY RESPONSIBILITY: |
| `backend/executor/allowlist.py` | Backend Guarded Actuator | 8,097 | AEGIS Executor — Action Allowlist (backend/executor/allowlist.py). SAFETY RESPONSIBILITY: This is the first gate every proposed... |
| `backend/executor/audit.py` | Backend Guarded Actuator | 9,440 | AEGIS Executor — Immutable Audit Log (backend/executor/audit.py). SAFETY RESPONSIBILITY: |
| `backend/executor/health.py` | Backend Guarded Actuator | 7,272 | AEGIS Executor — Post-Fix Health Verification (backend/executor/health.py). SAFETY RESPONSIBILITY: |
| `backend/executor/orchestrator.py` | Backend Guarded Actuator | 10,881 | AEGIS Executor — Execution Orchestrator (backend/executor/orchestrator.py). Coordinates the full remediation pipeline in the co... |
| `backend/executor/rollback.py` | Backend Guarded Actuator | 5,687 | AEGIS Executor — Automatic Rollback (backend/executor/rollback.py). SAFETY RESPONSIBILITY: |
| `backend/executor/scoring.py` | Backend Guarded Actuator | 7,349 | AEGIS Executor — Safety & Recovery Scoring (backend/executor/scoring.py). SAFETY RESPONSIBILITY: This is the second gate. Even ... |
| `backend/feedback/__init__.py` | Backend Feedback & Learning | 40 | # Feedback package — M8 learning loop |
| `backend/feedback/similarity.py` | Backend Feedback & Learning | 6,467 | AEGIS Incident Similarity Engine (backend/feedback/similarity.py) — M8. Embeds incident descriptions using sentence-transformer... |
| `backend/feedback/writer.py` | Backend Feedback & Learning | 5,114 | AEGIS Feedback Writer (backend/feedback/writer.py) — M8 Learning Loop. GOAL: After every terminal Decision, persist structured ... |
| `backend/graph/__init__.py` | Backend Graph Layer | 1,969 | AEGIS Graph Package (M1). Provides the factory method get_repository() to retrieve either |
| `backend/graph/neo4j_repo.py` | Backend Graph Layer | 16,214 | AEGIS Neo4j Graph Repository Implementation (M1). Implements GraphRepository using the official neo4j driver with multi-tenant ... |
| `backend/graph/networkx_repo.py` | Backend Graph Layer | 14,609 | AEGIS NetworkX Graph Repository Implementation (M1). Provides an in-memory, zero-external-dependency implementation of GraphRep... |
| `backend/graph/repository.py` | Backend Graph Layer | 4,813 | AEGIS Graph Repository Interface (docs/02-CONTRACTS.md §3). Encapsulates all graph operations. No Cypher or direct graph storag... |
| `backend/graph/schema.cypher` | Backend Graph Layer | 1,245 | // AEGIS Neo4j Schema & Constraints (docs/02-CONTRACTS.md §1) |
| `backend/graph/seed.py` | Backend Graph Layer | 15,764 | AEGIS Topology Generator and Seed Loader (M2). Generates and validates the canonical 54-node / 142-edge microservice graph |
| `backend/ingestion/docker_compose.py` | Backend Topology Ingestion | 4,456 | AEGIS Docker Compose Manifest Parser (Directive §3.B). Parses docker-compose.yml files into normalized graph nodes and edges. |
| `backend/ingestion/github_fetcher.py` | Backend Topology Ingestion | 3,221 | AEGIS GitHub Repository Fetcher (Directive §3.B). Fetches manifest files via GitHub REST API without requiring git clone. |
| `backend/ingestion/models.py` | Backend Topology Ingestion | 1,723 | AEGIS Repository Ingestion Models (docs/02-CONTRACTS.md & Directive §3.B). |
| `backend/ingestion/sample_repos.py` | Backend Topology Ingestion | 6,115 | AEGIS Bundled Sample Repositories for Offline & Demonstration Testing. Provides verified, realistic multi-tier microservice arc... |
| `backend/ingestion/service.py` | Backend Topology Ingestion | 7,292 | AEGIS Ingestion Service (Directive §3.B). Orchestrates repository fetching, manifest parsing, idempotent graph updating, |
| `backend/logs/audit.jsonl` | Asset / Config | 169,602 | {"decision_id": "dec-9a918ce0", "incident_id": "inc-good", "service_id": "svc-good", "action": "scale_pool", "params": {"pool_s... |
| `backend/monitor/health_checker.py` | Backend Live Monitoring | 31,787 | AEGIS Service Health Monitoring, Rolling Window Telemetry & Anomaly Engine. Features: |
| `backend/security/__init__.py` | Backend Security & Encryption | 238 | AEGIS Security & Cryptography Package. |
| `backend/security/encryption.py` | Backend Security & Encryption | 4,123 | AEGIS Authenticated Encryption for Endpoint Secrets at Rest. Implements PBKDF2-HMAC-SHA256 authenticated keystream encryption u... |
| `backend/security/endpoints.py` | Backend Security & Encryption | 11,884 | AEGIS Service Endpoint Registry (Per-Project with Encrypted Secrets & SSRF Guards). Stores registered service endpoints (name, ... |
| `backend/security/ssrf.py` | Backend Security & Encryption | 4,458 | AEGIS SSRF (Server-Side Request Forgery) Defense Engine. Enforces strict URL validation on every outbound destination (health_u... |
| `backend/sim/blast_radius.py` | Backend Risk Simulation | 1,454 | AEGIS Blast Radius Engine (M4). Traverses BACKWARDS along CALLS edges to determine all upstream callers |
| `backend/sim/config.py` | Backend Risk Simulation | 1,574 | AEGIS Simulation & Risk Configuration (M4). Centralizes all weights, thresholds, and parameters. |
| `backend/sim/contract_diff.py` | Backend Risk Simulation | 4,699 | AEGIS Contract Diff Engine (M4). Compares old vs new API/schema JSON to detect breaking changes. |
| `backend/sim/cycles.py` | Backend Risk Simulation | 2,040 | AEGIS Cycle Detection Engine using Tarjan SCC (M4). Analyzes whether a proposed change introduces dependency cycles. |
| `backend/sim/risk.py` | Backend Risk Simulation | 6,054 | AEGIS Change-Risk Prediction Engine (M4). Computes deterministic, evidence-backed risk score for any proposed pull request: |
| `backend/tests/conftest.py` | Backend Test | 483 | AEGIS Pytest Configuration & Fixtures. Provides clean repository isolation (autouse fixture) so each test executes |
| `backend/tests/test_agent.py` | Backend Test | 6,666 | Tests for AEGIS Agent schemas and context builder. Covers: |
| `backend/tests/test_api_integration.py` | Backend Test | 6,498 | AEGIS End-to-End API Integration & Closed-Loop Lifecycle Test. Tests the complete operational lifecycle across all API endpoints: |
| `backend/tests/test_api_keys.py` | Backend Test | 6,141 | Tests for AEGIS Per-Project API Keys & Authentication. Verifies: |
| `backend/tests/test_audit_fixes.py` | Backend Test | 3,408 | Regression tests for the 8 core audit defects across PREDICT, MONITOR, and Ingestion. |
| `backend/tests/test_config_and_neo4j.py` | Backend Test | 3,480 | Tests for AEGIS unified configuration, Neo4j repository, and fallback behavior. |
| `backend/tests/test_detection_rules.py` | Backend Test | 11,047 | Unit and integration tests for AEGIS deterministic detection rules, de-duplication, and SSE events. |
| `backend/tests/test_executor.py` | Backend Test | 28,784 | AEGIS Executor Test Suite (backend/tests/test_executor.py). Tests are written BEFORE implementation is used in production (AGEN... |
| `backend/tests/test_fallbacks.py` | Backend Test | 4,010 | Tests for AEGIS Fallback Resilience. Verifies: |
| `backend/tests/test_feedback.py` | Backend Test | 22,444 | AEGIS Feedback & Learning Loop Tests (backend/tests/test_feedback.py) — M8. Tests (written before production use): |
| `backend/tests/test_github_commenter.py` | Backend Test | 5,829 | Tests for backend/webhooks/github_commenter.py Verifies: |
| `backend/tests/test_graph.py` | Backend Test | 6,228 | AEGIS Graph Layer Tests (M1 & M2). Verifies: |
| `backend/tests/test_ingestion.py` | Backend Test | 7,530 | AEGIS Ingestion Tests (Directive §3.B). Verifies: |
| `backend/tests/test_monitor.py` | Backend Test | 8,619 | AEGIS Health Monitoring & Simulated Telemetry Comprehensive Test Suite. Verifies Directive §3.C acceptance criteria: |
| `backend/tests/test_multi_project.py` | Backend Test | 14,167 | AEGIS Multi-Project Isolation Tests (Task 7a). Verifies: |
| `backend/tests/test_predict.py` | Backend Test | 8,348 | AEGIS PREDICT Change-Risk & Impact Analysis Tests (Directive §3.A). Verifies: |
| `backend/tests/test_rca.py` | Backend Test | 10,180 | Tests for AEGIS Agent LLM wrapper, RCA diagnosis, and fallback rules. All tests use a MOCK LLM to ensure: |
| `backend/tests/test_service_endpoints.py` | Backend Test | 8,913 | Tests for AEGIS Per-Project Service Endpoint Registration, SSRF Defense, and Secret Encryption. Verifies: |
| `backend/tests/test_sim.py` | Backend Test | 4,532 | AEGIS Simulation & Risk Scoring Tests (M4). Verifies: |
| `backend/tests/test_stream_route.py` | Backend Test | 4,762 | Tests for the real SSE diagnosis route GET /api/heal/stream. Covers: |
| `backend/tests/test_webhooks.py` | Backend Test | 12,548 | Tests for AEGIS GitHub Webhook Ingestion, HMAC Verification & Idempotency. Verifies: |
| `backend/tests/verify_all.py` | Backend Test | 13,387 | AEGIS Final Integration & Regression Verification Script. Executes and verifies: |
| `backend/webhooks/__init__.py` | Backend GitHub Webhooks | 483 | AEGIS GitHub Webhook Integration Package. |
| `backend/webhooks/github_commenter.py` | Backend GitHub Webhooks | 6,250 | AEGIS GitHub Commenter Module. Handles posting and updating PR comments via the GitHub REST API. |
| `backend/webhooks/processor.py` | Backend GitHub Webhooks | 10,291 | AEGIS Webhook Event Processor & Changed Files Scanner. Enqueues asynchronous jobs from GitHub webhooks: |
| `backend/webhooks/store.py` | Backend GitHub Webhooks | 3,421 | AEGIS Webhook Delivery Store & Idempotency Ledger. Tracks processed X-GitHub-Delivery IDs to prevent duplicate work |
| `backend/webhooks/verify.py` | Backend GitHub Webhooks | 1,286 | GitHub Webhook HMAC Signature Verification. Verifies X-Hub-Signature-256 header using timing-safe hmac.compare_digest. |
| `data/.master.key` | Topology / Seed / Data Asset | 32 | N{lfSz\E];<Nl%A t |
| `data/agent_runs.jsonl` | Topology / Seed / Data Asset | 591,027 | {"timestamp": "2026-10-22T11:02:45.930443+00:00", "incident_id": "inc-0001", "provider": "gemini", "model": "gemini/gemini-1.5-... |
| `data/endpoints.json` | Topology / Seed / Data Asset | 10,410 | { |
| `data/executor_config.json` | Topology / Seed / Data Asset | 2,046 | { |
| `data/projects.json` | Topology / Seed / Data Asset | 6,390 | { |
| `data/prs/pr_142_breaking.json` | Topology / Seed / Data Asset | 774 | { |
| `data/prs/pr_cyclic.json` | Topology / Seed / Data Asset | 629 | { |
| `data/prs/pr_gateway.json` | Topology / Seed / Data Asset | 523 | { |
| `data/prs/pr_leaf.json` | Topology / Seed / Data Asset | 580 | { |
| `data/prs/pr_moderate.json` | Topology / Seed / Data Asset | 523 | { |
| `data/prs/pr_safe.json` | Topology / Seed / Data Asset | 643 | { |
| `data/topology.yaml` | Topology / Seed / Data Asset | 40,019 | nodes: |
| `data/webhook_deliveries.json` | Topology / Seed / Data Asset | 15,914 | { |
| `Dockerfile` | Deployment / Container Spec | 826 | Multi-stage Dockerfile packaging FastAPI backend and compiled React SPA for deployment. |
| `docs/00-BASELINE-ASSESSMENT.md` | Project Documentation | 4,121 | Documentation: AEGIS — System Baseline Assessment & Status Ledger |
| `docs/00-START-HERE.md` | Project Documentation | 2,042 | Documentation: Start here — using this pack with Antigravity |
| `docs/01-TEAM-AND-PROCESS.md` | Project Documentation | 1,801 | Documentation: Team, ownership and process (assumes 4 people) |
| `docs/02-CONTRACTS.md` | Project Documentation | 2,793 | Documentation: Integration contracts (FROZEN after Week 1) |
| `docs/03-MODULES.md` | Project Documentation | 2,606 | Documentation: Modules M0–M10 (scope and "done when") |
| `docs/04-ALGORITHMS.md` | Project Documentation | 3,874 | Documentation: Algorithms and formulas (Phase 1) |
| `docs/05-FAILURE-CASES.md` | Project Documentation | 1,480 | Documentation: Case matrix — what can go wrong and what we do |
| `docs/06-REAL-VS-SIMULATED.md` | Project Documentation | 792 | Documentation: Real vs simulated in Phase 1 (say this openly) |
| `docs/07-DECISIONS.md` | Project Documentation | 1,673 | Documentation: Decisions log |
| `docs/08-TESTING.md` | Project Documentation | 955 | Documentation: Testing strategy |
| `docs/09-INGESTION-LITE-REFERENCE.md` | Project Documentation | 2,017 | Documentation: Ingestion-lite reference (M3, Weeks 4 & 9) — IN SCOPE for Phase 1 |
| `docs/CHANGELOG.md` | Project Documentation | 4,476 | Documentation: Changelog |
| `docs/DEMO-SCRIPT.md` | Project Documentation | 8,867 | Documentation: AEGIS — Four-Day Review Demonstration Script & Technical Guide |
| `docs/DEPLOYMENT.md` | Project Documentation | 2,234 | Documentation: AEGIS — 100% Free Live Cloud Hosting Guide |
| `docs/EVAL.md` | Project Documentation | 3,322 | Documentation: AEGIS Evaluation & Benchmark Report |
| `docs/EVAL_ABLATION.md` | Project Documentation | 4,267 | Documentation: AEGIS Evaluation & Benchmark Report |
| `docs/phase2-parked/build-guide-reference.md` | Project Documentation | 2,717 | Documentation: Build Guide reference (condensed) — for Phase 2 |
| `docs/phase2-parked/README.md` | Project Documentation | 943 | Documentation: Phase 2 (Weeks 11–20) — PARKED. Do NOT implement in Phase 1. |
| `docs/REAL_VS_SIMULATED.md` | Project Documentation | 4,978 | Documentation: AEGIS: Real vs. Simulated Capabilities (Phase 1) |
| `docs/research/01-OPEN-SOURCE-INTELLIGENCE.md` | Project Documentation | 5,649 | Documentation: AEGIS — Open-Source Intelligence & Research Comparison Matrix |
| `docs/SECURITY.md` | Project Documentation | 2,612 | Documentation: AEGIS Security Audit & Vulnerability Assessment Report |
| `docs/STATUS.md` | Project Documentation | 21,398 | Documentation: AEGIS System Audit & Honest Status Report |
| `docs/TARGET.md` | Project Documentation | 7,324 | Documentation: AEGIS Target Integration Guide |
| `frontend/.gitignore` | Asset / Config | 253 | # Logs |
| `frontend/.oxlintrc.json` | Configuration File | 245 | { |
| `frontend/index.html` | Asset / Config | 977 | <!doctype html> |
| `frontend/package-lock.json` | Configuration File | 51,487 | { |
| `frontend/package.json` | Configuration File | 591 | { |
| `frontend/public/favicon.svg` | Asset / Config | 9,522 | <svg xmlns="http://www.w3.org/2000/svg" width="48" height="46" fill="none" viewBox="0 0 48 46"><path fill="#863bff" d="M25.946 ... |
| `frontend/public/icons.svg` | Asset / Config | 5,031 | <svg xmlns="http://www.w3.org/2000/svg"> |
| `frontend/README.md` | Asset / Config | 1,278 | Documentation: React + TypeScript + Vite |
| `frontend/src/App.css` | Frontend Core (TS/CSS) | 2,891 | .counter { |
| `frontend/src/App.tsx` | Frontend Core (TS/CSS) | 18,092 | import { useState, useEffect } from 'react'; |
| `frontend/src/assets/hero.png` | Frontend Core (TS/CSS) | 13,057 | PNG |
| `frontend/src/assets/react.svg` | Frontend Core (TS/CSS) | 4,126 | <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" aria-hidden="true" role="img" class="iconify... |
| `frontend/src/assets/vite.svg` | Frontend Core (TS/CSS) | 8,709 | <svg xmlns="http://www.w3.org/2000/svg" width="77" height="47" fill="none" aria-labelledby="vite-logo-title" viewBox="0 0 77 47... |
| `frontend/src/components/BlastRadiusPanel.tsx` | Frontend Component (React/TSX) | 16,701 | import React, { useState } from 'react'; |
| `frontend/src/components/BottomLayerCards.tsx` | Frontend Component (React/TSX) | 9,484 | import React from 'react'; |
| `frontend/src/components/CustomNodes.tsx` | Frontend Component (React/TSX) | 11,061 | import { memo } from 'react'; |
| `frontend/src/components/LatencySparkline.tsx` | Frontend Component (React/TSX) | 3,953 | import React from 'react'; |
| `frontend/src/config.ts` | Frontend Core (TS/CSS) | 2,483 | /** |
| `frontend/src/index.css` | Frontend Core (TS/CSS) | 3,364 | /* AEGIS Mission Control Design System (Dark Glassmorphism) */ |
| `frontend/src/main.tsx` | Frontend Core (TS/CSS) | 230 | import { StrictMode } from 'react' |
| `frontend/src/pages/ActuatorPage.tsx` | Frontend Page (React/TSX) | 28,759 | import React, { useState, useEffect } from 'react'; |
| `frontend/src/pages/ChaosPage.tsx` | Frontend Page (React/TSX) | 18,565 | import React, { useState, useEffect } from 'react'; |
| `frontend/src/pages/IncidentLedgerPage.tsx` | Frontend Page (React/TSX) | 34,600 | import React, { useState, useEffect } from 'react'; |
| `frontend/src/pages/IngestPage.tsx` | Frontend Page (React/TSX) | 21,517 | import React, { useState, useEffect } from 'react'; |
| `frontend/src/pages/MonitorPage.tsx` | Frontend Page (React/TSX) | 25,485 | import React, { useState, useEffect } from 'react'; |
| `frontend/src/pages/ObservabilityPage.tsx` | Frontend Page (React/TSX) | 12,591 | import React, { useState } from 'react'; |
| `frontend/src/pages/PredictPage.tsx` | Frontend Page (React/TSX) | 21,000 | import React, { useState, useEffect } from 'react'; |
| `frontend/src/pages/ProjectsPage.tsx` | Frontend Page (React/TSX) | 60,856 | import React, { useState, useEffect, useCallback } from 'react'; |
| `frontend/src/pages/TopologyPage.tsx` | Frontend Page (React/TSX) | 33,276 | import React, { useState, useEffect, useCallback } from 'react'; |
| `frontend/tsconfig.app.json` | Configuration File | 655 | { |
| `frontend/tsconfig.json` | Configuration File | 119 | { |
| `frontend/tsconfig.node.json` | Configuration File | 558 | { |
| `frontend/vite.config.ts` | Asset / Config | 324 | import { defineConfig } from 'vite' |
| `pyproject.toml` | Configuration File | 805 | Python project configuration, pytest options, and package build settings. |
| `README.md` | Asset / Config | 14,600 | Main repository README detailing system overview, quickstart, architecture, and live demo steps. |
| `render.yaml` | Configuration File | 425 | Infrastructure-as-code specification for deploying AEGIS API service on Render free tier. |
| `requirements.txt` | Asset / Config | 207 | Pinned production Python dependencies (FastAPI, Pydantic, NetworkX, LiteLLM, Neo4j, httpx). |
| `scripts/eval_rca.py` | Script / CLI Tool | 3,521 | Evaluate RCA accuracy for each fault type. For each fault type (pool_exhaustion, pod_crash, latency_spike) the script: |
| `scripts/make_inventory.py` | Script / CLI Tool | 6,155 | Generates docs/knowledge-base/_inventory.md containing all 183 tracked files. |
| `scripts/run_eval.py` | Script / CLI Tool | 17,584 | AEGIS Comprehensive Operational Evaluation Runner. Evaluates AEGIS across 5 fault types x N runs: |
| `scripts/security_audit.py` | Script / CLI Tool | 10,089 | AEGIS Security Audit Tool (pip-audit, npm-audit, and gitleaks equivalent). Performs: |
