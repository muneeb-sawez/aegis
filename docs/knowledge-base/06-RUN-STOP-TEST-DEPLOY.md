# AEGIS Operations, Testing, Deployment & Security Manual

> **Module**: Stage 7 Definitive Knowledge Base  
> **Status**: Verified against Active Codebase (PowerShell & Bash Execution, Pip-Audit, Multi-Stage Dockerfile)  
> **Audience**: Final-Year Engineering Students, Technical Auditors, External Viva Examiners  
> **Verification Command**: `python -m pytest backend/tests/ -q` (169 passed, 5 skipped)

---

## Table of Contents
1. [Prerequisites & System Requirements](#1-prerequisites--system-requirements)
2. [Complete Environment Variables Ledger](#2-complete-environment-variables-ledger)
3. [Local Development: Install, Run & Stop (Windows & macOS/Linux)](#3-local-development-install-run--stop-windows--macoslinux)
   - [3.1 Dependency Installation](#31-dependency-installation)
   - [3.2 Running the Application (Unified vs. Separate)](#32-running-the-application-unified-vs-separate)
   - [3.3 Running Verification & Benchmark Suites](#33-running-verification--benchmark-suites)
   - [3.4 How to Stop Processes & Free Stuck Ports](#34-how-to-stop-processes--free-stuck-ports)
   - [3.5 How to Reset Demo State](#35-how-to-reset-demo-state)
4. [Common Operational Errors & Verified Fixes](#4-common-operational-errors--verified-fixes)
5. [Production & Cloud Deployment Architecture](#5-production--cloud-deployment-architecture)
   - [5.1 Multi-Stage Docker Container (`Dockerfile`)](#51-multi-stage-docker-container-dockerfile)
   - [5.2 Free-Tier Cloud Hosting (Render.com)](#52-free-tier-cloud-hosting-rendercom)
   - [5.3 Free-Tier Pitfalls: Sleep Cycles & State Persistence](#53-free-tier-pitfalls-sleep-cycles--state-persistence)
   - [5.4 Live Pre-Demo Checklist](#54-live-pre-demo-checklist)
6. [Rigorous Security Review & Real Gaps Audit](#6-rigorous-security-review--real-gaps-audit)
7. [Verification Notes & Evidence Ledger](#7-verification-notes--evidence-ledger)

---

## 1. Prerequisites & System Requirements

Before running or deploying AEGIS, ensure the underlying operating system meets these verified toolchain versions:

| Toolchain / Runtime | Required Version | Active Environment Version | Verification Command | Purpose |
|---|---|---|---|---|
| **Python** | `>= 3.12.0` | `3.14.0` / `3.12.3` | `python --version` | Asynchronous backend, algorithms, and graph repo |
| **Node.js** | `>= 18.0.0` (LTS 20 recommended) | `v20.x` / `v22.x` | `node --version` | Compiling React 19 frontend and Vite bundler |
| **npm** | `>= 9.0.0` | `10.x` | `npm --version` | Node package installation and build scripting |
| **Git** | `>= 2.30.0` | `2.4x` | `git --version` | Version control, webhook payload simulation |
| **Docker** *(Optional)* | `>= 24.0.0` | Container runtime | `docker --version` | Single-container multi-stage build or Neo4j |

---

## 2. Complete Environment Variables Ledger

All application settings are parsed, validated, and type-checked at boot by `backend/config.py:12-78` using `pydantic-settings`. Values can be set in a local `.env` file or exported into the process environment.

| Variable Name | Type | Required? | Default Value | Example Value (Masked) | Functional Role in System |
|---|:---:|:---:|:---:|---|---|
| `GRAPH_BACKEND` | `str` | No | `"networkx"` | `networkx` or `neo4j` | Selects in-memory NetworkX vs. persistent Neo4j engine |
| `NEO4J_URI` | `str` | Conditional | `"bolt://localhost:7687"` | `bolt://localhost:7687` | Bolt connection string for Neo4j database |
| `NEO4J_USER` | `str` | Conditional | `"neo4j"` | `neo4j` | Neo4j database user account |
| `NEO4J_PASSWORD` | `str` | **YES** (if neo4j) | `None` | `********` | Neo4j password; validation raises error if empty in neo4j mode |
| `ADMIN_SHARED_SECRET`| `str` | No | `None` | `adm_sec_********` | Optional authorization secret protecting `/api/reset` |
| `LLM_PROVIDER` | `str` | No | `"gemini"` | `gemini` \| `groq` \| `ollama` | Selects LiteLLM backend for diagnostic root-cause analysis |
| `LLM_MODEL` | `str` | No | `"gemini/gemini-1.5-flash"`| `groq/llama-3.1-70b` | Exact LiteLLM model identifier string |
| `GEMINI_API_KEY` | `str` | Conditional | `None` | `AIzaSy********` | Required if `LLM_PROVIDER="gemini"` |
| `GROQ_API_KEY` | `str` | Conditional | `None` | `gsk_********` | Required if `LLM_PROVIDER="groq"` |
| `OLLAMA_BASE_URL` | `str` | No | `"http://localhost:11434"`| `http://localhost:11434`| HTTP endpoint for local Ollama container or daemon |
| `DEMO_MODE` | `bool` | No | `False` | `true` or `false` | When true, streams pre-recorded traces instead of querying LLM |
| `EXECUTION_MODE` | `str` | No | `"approve"` | `"approve"` or `"auto"` | `"approve"` queues fix for human; `"auto"` runs immediately |
| `ACTUATOR_TARGET_BASE_URL` | `str` | No | `""` | `http://localhost:8080` | Base URL for target cluster. If empty, runs in **emulated mode** |
| `ACTUATOR_HMAC_SECRET` | `str` | No | `"dev-hmac-secret"` | `hmac_key_********` | Secret key used to sign outbound actuator requests |
| `GITHUB_TOKEN` | `str` | No | `None` | `ghp_********` | Personal Access Token for GitHub repository ingestion & comments |
| `GITHUB_WEBHOOK_SECRET`| `str` | No | `"test-webhook-secret"` | `whsec_********` | Secret for validating incoming GitHub webhook HMAC signatures |
| `BASELINE_WINDOW` | `int` | No | `5` | `5` | Rolling window size of healthy probes to compute baseline |
| `LATENCY_MULTIPLIER` | `float`| No | `3.0` | `3.0` | Multiplier over baseline P99 latency triggering an anomaly alert |
| `CONSECUTIVE_FAILURES`| `int` | No | `2` | `2` | Number of consecutive probe drops required to trigger outage alert |
| `ERROR_RATE_THRESHOLD`| `float`| No | `0.5` | `0.5` | Error rate ratio ($50\%$) triggering anomaly alert |
| `COOLDOWN_SECONDS` | `float`| No | `60.0` | `60.0` | Deduplication cooldown preventing alert spam on the same service |
| `MONITOR_INTERVAL_SEC`| `float`| No | `3.0` | `3.0` | Frequency (seconds) of background health probe worker |
| `MONITOR_TIMEOUT_SEC` | `float`| No | `2.0` | `2.0` | Probe HTTP timeout; **must be strictly shorter than interval** |
| `PORT` | `int` | No | `8000` | `8000` | Port on which the FastAPI application listens |
| `HOST` | `str` | No | `"0.0.0.0"` | `"0.0.0.0"` | Network interface binding |

---

## 3. Local Development: Install, Run & Stop (Windows & macOS/Linux)

### 3.1 Dependency Installation

#### Windows (PowerShell)
```powershell
# 1. Clone repository
git clone https://github.com/muneeb-sawez/aegis.git
cd aegis

# 2. Set up Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install backend dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Install frontend dependencies
cd frontend
npm install
cd ..
```

#### macOS / Linux (Bash)
```bash
# 1. Clone repository
git clone https://github.com/muneeb-sawez/aegis.git
cd aegis

# 2. Set up Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install backend dependencies
python3 -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Install frontend dependencies
cd frontend
npm install
cd ..
```

---

### 3.2 Running the Application (Unified vs. Separate)

#### Option A: Separate Development Mode (Hot Reloading)
This is the recommended workflow for developing or inspecting code.

##### Terminal 1: Backend API (Port 8000)
- **Windows PowerShell**:
  ```powershell
  .\.venv\Scripts\Activate.ps1
  python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
  ```
- **macOS / Linux**:
  ```bash
  source .venv/bin/activate
  python3 -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
  ```

##### Terminal 2: Frontend Vite Dev Server (Port 5173)
- **All Platforms**:
  ```bash
  cd frontend
  npm run dev
  ```
*Access UI at `http://localhost:5173`.*

#### Option B: Unified Production Build (Single Process on Port 8000)
Compile the React frontend into static assets served directly by FastAPI.

```bash
# 1. Compile React application
cd frontend
npm run build
cd ..

# 2. Launch FastAPI server (serves frontend at http://localhost:8000/)
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
```
*Access UI at `http://localhost:8000`.*

---

### 3.3 Running Verification & Benchmark Suites

#### 1. Full Pytest Suite (Unit, Integration & Golden Loop)
```bash
# Run all 174 test cases
python -m pytest backend/tests/ -q
```
*Expected: `169 passed, 5 skipped` in ~27 seconds.*

#### 2. Golden Loop Acceptance Test Specifically
```bash
python -m pytest backend/tests/test_golden_loop.py -v
```
*Asserts that PR #142 risk score shifts deterministically by $+5.0$ after an incident.*

#### 3. Full Benchmark & Ablation Harness (`scripts/run_eval.py`)
```bash
# Runs 50 trials (5 fault types x 10 runs) plus graph ablation test
python scripts/run_eval.py
```
*Measures automated detection, diagnosis, and healing times, printing results directly to console.*

#### 4. Pre-Flight System Sanity Test (`scripts/verify_all.py`)
```bash
python scripts/verify_all.py
```
*Validates graph seeding, blast radius calculations, contract diffing, and fallback rules.*

---

### 3.4 How to Stop Processes & Free Stuck Ports

Occasionally, background node or uvicorn processes remain bound to ports `8000` or `5173`. Use these commands to inspect and cleanly terminate them.

#### Windows PowerShell
```powershell
# Check what process is listening on Port 8000
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object OwningProcess, State

# Terminate process holding Port 8000
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force

# Terminate process holding Port 5173 (Vite)
Stop-Process -Id (Get-NetTCPConnection -LocalPort 5173).OwningProcess -Force
```

#### macOS / Linux
```bash
# Check what process is listening on Port 8000
lsof -i :8000

# Terminate process holding Port 8000
lsof -ti :8000 | xargs kill -9

# Terminate process holding Port 5173 (Vite)
lsof -ti :5173 | xargs kill -9
```

---

### 3.5 How to Reset Demo State
To restore the topology, clear historical incidents, and reset node telemetry back to the clean 54-node baseline:

#### Via HTTP cURL
```bash
curl -X POST http://localhost:8000/api/reset \
  -H "X-API-Key: aegis-demo-api-key"
```

#### Via Python CLI
```bash
python -c "
from backend.graph import get_repository
repo = get_repository()
repo.reset('demo')
print('Graph reset successfully to 54-node baseline.')
"
```

---

## 4. Common Operational Errors & Verified Fixes

| Observed Error Message | Root Cause | Verified Resolution |
|---|---|---|
| `ValueError: MONITOR_TIMEOUT_SEC must be strictly shorter than MONITOR_INTERVAL_SEC` | Misconfigured timeout in `.env`. `backend/config.py:75` requires probe timeout $<$ interval to prevent thread starvation. | Set `MONITOR_TIMEOUT_SEC=2.0` and `MONITOR_INTERVAL_SEC=3.0` in `.env`. |
| `ValueError: NEO4J_PASSWORD is required when GRAPH_BACKEND is 'neo4j'` | `GRAPH_BACKEND=neo4j` set without providing password. | Supply `NEO4J_PASSWORD` in `.env` or set `GRAPH_BACKEND=networkx`. |
| `PytestUnknownMarkWarning: Unknown pytest.mark.asyncio` | `pytest-asyncio` plugin not installed in active environment. | Run `pip install pytest-asyncio>=0.23.0`. |
| `Unauthorized: Per-project API key required for mutating routes` | Calling mutating routes (`/api/chaos/inject`, `/api/actuator/execute`) without authentication. | Provide `X-API-Key: aegis-demo-api-key` in request headers. |
| `SSRF / Validation Failed: Target host is blocked for security purposes` | Attempting to register probe URL resolving to loopback (`127.0.0.1`), cloud metadata (`169.254.169.254`), or RFC 1918 subnets. | Provide an external public URL or configure test mock endpoint. |
| `Address already in use (Errno 98 / 10048)` | Previous Uvicorn or Vite process did not release port. | Execute the port-killing commands in Section 3.4. |

---

## 5. Production & Cloud Deployment Architecture

AEGIS is designed to be hosted 100% free of charge without credit cards on modern developer platforms.

### 5.1 Multi-Stage Docker Container (`Dockerfile`)
The repository includes a production-grade multi-stage `Dockerfile` in the root:

```dockerfile
# Stage 1: Build React 19 Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python 3.12 Backend & Server
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Copy compiled SPA from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

ENV PORT=8000
ENV GRAPH_BACKEND=networkx
EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

### 5.2 Free-Tier Cloud Hosting (Render.com)
As documented in `docs/DEPLOYMENT.md`, Render allows hosting both backend and frontend together as a single free Web Service:
1. Connect GitHub repo `muneeb-sawez/aegis` to Render.
2. Select **Runtime: Python 3**.
3. **Build Command**:
   ```bash
   pip install -r requirements.txt && cd frontend && npm install && npm run build
   ```
4. **Start Command**:
   ```bash
   python -m uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT
   ```
5. Instance Type: **Free** (512 MB RAM).

### 5.3 Free-Tier Pitfalls: Sleep Cycles & State Persistence

Technical auditors and examiners may inquire about cloud behavior. Be prepared to explain:
1. **Container Sleep on Inactivity**: Free instances on Render/Fly.io spin down after 15 minutes of zero HTTP traffic. The first request after sleep experiences a **cold-start delay of 30–50 seconds**.
2. **Ephemeral Disk & In-Memory State**: When running `GRAPH_BACKEND=networkx` on free tier, any restart or redeploy resets the Knowledge Graph back to the seed baseline.
3. **Mitigation**: For a viva examination, operators must wake the instance 5 minutes before the presentation by pinging `GET /health` or run the demonstration locally via Option B.

### 5.4 Live Pre-Demo Checklist
- [ ] Verify Python virtual environment is active (`which python` or `$env:VIRTUAL_ENV`).
- [ ] Run `python -m pytest backend/tests/test_golden_loop.py -q` (must return exit code 0).
- [ ] Free ports 8000 and 5173 to ensure no zombie processes interfere.
- [ ] Check `.env` contains valid `GEMINI_API_KEY` or `GROQ_API_KEY` (or confirm fallback rules are enabled).
- [ ] Run `curl -s http://localhost:8000/health` and verify `status: "healthy"`.
- [ ] Ensure browser is open to `http://localhost:5173/#topology` or `http://localhost:8000/`.

---

## 6. Rigorous Security Review & Real Gaps Audit

A formal security scan combining `pip-audit`, `npm audit`, and `gitleaks` patterns was executed (`docs/SECURITY.md`). Here is the objective assessment of system defenses versus real gaps:

### 6.1 Architectural Security Strengths Enforced
1. **SSRF Barrier (`backend/security/ssrf.py:28-60`)**: Enforces strict DNS resolution checks blocking loopback (`127.0.0.1`), RFC 1918 private subnets, link-local addresses, and AWS/GCP metadata endpoints (`169.254.169.254`).
2. **Encrypted Secret Storage (`backend/security/encryption.py:18`)**: Stored endpoint credentials and tokens are encrypted at rest using AES-256 GCM authenticated encryption. Plaintext secrets are **never serialized across REST responses**.
3. **SHA-256 API Key Storage (`backend/auth/store.py:53`)**: Per-project API keys are hashed with SHA-256 before saving to `data/projects.json`. Raw tokens are returned only once at creation time.
4. **Guarded Allowlist Actuation (`backend/executor/allowlist.py:35`)**: The LLM has zero execution authority; only 3 allowlisted operations (`restart`, `scale_pool`, `rollback`) with bounded numerical arguments can pass the actuator.

### 6.2 Real Security Gaps & Technical Debt (Auditor Disclosure)
In accordance with engineering honesty, the following limitations must be acknowledged before an auditor:
- **Wildcard CORS Configuration (`backend/api/main.py:53`)**: `allow_origins=["*"]` is currently enabled to simplify local cross-port development between Vite (5173) and FastAPI (8000). In production, this must be restricted to specific domain origins.
- **Absence of Rate Limiting**: The API lacks IP-based rate limiting (such as `slowapi` or Redis token buckets). Unauthenticated endpoints like `/api/simulate-pr` could be subjected to denial-of-service query floods.
- **Dependency Advisories**: `pip-audit` identified 8 advisories in development packages (`pytest 8.1.1` and `anyio 4.3.0`). While non-critical for local demo execution, upgrading to `anyio >= 4.4` and `pytest >= 8.3` is scheduled for production hardening.

---

## 7. Verification Notes & Evidence Ledger

### Verification Commands Run
1. `python -m pytest backend/tests/ -q`: Verified 169 passing unit and integration tests.
2. Verified `Dockerfile` multi-stage build syntax in repository root.
3. Introspected `backend/config.py:12-80` to verify all 24 environment variable definitions and model validators.
4. Executed PowerShell port termination commands to verify process killing mechanics.

### Discrepancy Ledger (Docs vs. Active Code)
- **Deployment Folder**: Early documentation referenced `deploy/render.yaml` and `deploy/docker-compose.yml`. In the active repository, deployment is handled by the multi-stage `Dockerfile` in the repository root and manual Render setup documented in `docs/DEPLOYMENT.md`. There is no separate `deploy/` directory in Git.
- **Active Security Report**: Audited against `docs/SECURITY.md`, documenting real findings from `pip-audit` and `gitleaks` scans.
