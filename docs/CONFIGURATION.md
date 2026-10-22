# AEGIS Runtime Configuration Guide

> **Document Version**: 2.0.0-RELEASE  
> **Audited Date**: October 2026  
> **Source Repository**: `muneeb-sawez/aegis`

---

## 1. Environment Variable Reference

AEGIS is configured via environment variables or a `.env` file located in the workspace root. Copy `.env.example` to `.env` to begin:

```bash
cp .env.example .env
```

| Variable Name | Default Value | Accepted Values | Description |
| :--- | :--- | :--- | :--- |
| `GRAPH_BACKEND` | `networkx` | `networkx`, `neo4j` | Active graph database implementation. `networkx` runs in-memory with zero dependencies; `neo4j` connects to an active Neo4j Community/Enterprise instance. |
| `LLM_PROVIDER` | `gemini` | `gemini`, `groq`, `ollama`, `mock` | Primary LLM diagnostic reasoning engine invoked by LiteLLM. |
| `LLM_MODEL` | `gemini/gemini-1.5-flash` | Any LiteLLM string | Specific model identifier used for root cause analysis prompts. |
| `GEMINI_API_KEY` | *(None)* | `AIza...` | API key for Google Gemini (Free Tier supported). Optional if using `mock` or `ollama`. |
| `GROQ_API_KEY` | *(None)* | `gsk_...` | API key for Groq Cloud. Optional. |
| `OLLAMA_BASE_URL`| `http://localhost:11434` | URL string | Base URL for local offline Ollama inference. |
| `NEO4J_URI` | `bolt://localhost:7687` | Bolt/Neo4j URI | Connection URI for the Neo4j instance when `GRAPH_BACKEND=neo4j`. |
| `NEO4J_USER` | `neo4j` | String | Username for Neo4j authentication. |
| `NEO4J_PASSWORD` | `password` | String | Password for Neo4j authentication. |
| `DEMO_MODE` | `false` | `true`, `false` | When `true`, diagnostic reasoning uses local deterministic stubs without making outbound LLM API network calls. |
| `AEGIS_MASTER_KEY`| *(Generated)* | 64-char Hex | Cryptographic secret used by PBKDF2 to encrypt service endpoint admin secrets at rest. |
| `GITHUB_WEBHOOK_SECRET` | *(None)* | Secret String | Shared secret used to verify incoming GitHub webhook signatures (`X-Hub-Signature-256`). |
| `PORT` | `8000` | Port Number | Port bound by the Uvicorn web server. |

---

## 2. Fallback Hierarchies

### 2.1 Graph Storage Fallback
If `GRAPH_BACKEND=neo4j` is configured but the Neo4j container is unreachable or offline:
- The system logs a warning during startup: `NEO4J_UNAVAILABLE: Falling back to NetworkX in-memory repository`.
- Operations continue seamlessly using the 54-node in-memory seed graph.

### 2.2 LLM Reasoning Fallback
If the configured LLM provider returns a network error, HTTP 429 quota limit, or times out (> 10s):
- `backend/agent/rca.py` catches the exception and routes the context to `backend/agent/fallback_rules.py`.
- Deterministic heuristic rules evaluate the anomaly metrics directly (e.g., connection pool exhaustion $\to$ `scale_pool`), returning a guaranteed valid `RCAResult` in $< 15\text{ ms}$.

---

## 3. Secret Management & Security Guidelines

1. **Never Commit `.env`**: `.gitignore` strictly excludes `.env`, `data/.master.key`, and runtime databases.
2. **Encrypted Store**: Service admin secrets registered via `POST /api/endpoints` are encrypted using authenticated AES-256 GCM encryption before being persisted to `data/endpoints.json`.
3. **Public API Masking**: In all API responses and client-facing models (`ServiceEndpointPublic`), plaintext secrets are masked and omitted (`has_secret: true`, `secret_source: "encrypted_store"`).

---

*For deployment templates on Render and Docker Compose, refer to `render.yaml` and `deploy/docker-compose.yml`.*
