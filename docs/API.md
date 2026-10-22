# AEGIS REST & Event API Reference

> **Document Version**: 2.0.0-RELEASE  
> **Audited Date**: October 2026  
> **Base URL**: `http://localhost:8000` (Local) / `/api` (Production Proxy)  
> **OpenAPI Schema**: Accessible interactively at `http://localhost:8000/docs`

---

## 1. Authentication & Security Headers

All mutating endpoints (`POST`, `PUT`, `DELETE`) require project authentication via an API Key or Bearer Token:

| Header Name | Format | Description |
| :--- | :--- | :--- |
| `X-API-Key` | `agk_<random_hex>` | Project-scoped API key. Verified against SHA-256 hash in storage. |
| `Authorization` | `Bearer agk_<random_hex>` | Standard Bearer token header equivalent to `X-API-Key`. |
| `X-Hub-Signature-256` | `sha256=<hexdigest>` | HMAC-SHA256 signature for GitHub webhook delivery verification. |

Public read-only endpoints (`GET /health`, `GET /api/graph/topology`, `GET /docs`) do not require authentication.

---

## 2. API Endpoint Directory

### 2.1 System & Health Probes

| Method | Path | Summary | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/health` | Application status, version, and active graph backend | No |
| `GET` | `/` | Serves compiled React frontend (`frontend/dist/index.html`) | No |

### 2.2 Knowledge Graph & Topology

| Method | Path | Summary | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/graph/topology` | Retrieve full 54-node / 142-edge graph for a project | No |
| `POST` | `/api/graph/reset` | Reset project topology back to baseline seed state | Yes |
| `GET` | `/api/graph/services` | List all registered microservice nodes and layers | No |
| `POST` | `/api/graph/external-service` | Register an external SaaS or third-party dependency | Yes |

### 2.3 Pre-Merge Change-Risk Simulation (`PREDICT`)

| Method | Path | Summary | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/sim/evaluate` | Evaluate PR change risk ($B, C, D, H$), score & verdict | No |
| `GET` | `/api/sim/prs` | List pre-bundled test pull request scenarios | No |
| `POST` | `/api/predict/analyze` | Alternative prediction endpoint with detailed breakdown | No |
| `GET` | `/api/predict/services` | List targetable services for risk simulation | No |

### 2.4 Service Health Probing & Chaos (`MONITOR`)

| Method | Path | Summary | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/monitor/status` | List monitored endpoints, active anomalies & statuses | No |
| `POST` | `/api/monitor/check-now` | Trigger immediate out-of-band health probe check | Yes |
| `POST` | `/api/monitor/fault` | Trigger simulated probe fault on a target service | Yes |
| `POST` | `/api/monitor/configure` | Dynamically register a new service URL for health probing | Yes |
| `POST` | `/api/chaos/inject` | Inject synthetic telemetry fault (`pool_exhaustion`, etc.) | Yes |

### 2.5 Autonomous Healing & Diagnosis (`HEAL`)

| Method | Path | Summary | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/heal/stream` | Stream real-time diagnostic reasoning thoughts over SSE | No |
| `GET` | `/api/heal/events` | Polling fallback for diagnostic thought events | No |
| `POST` | `/api/heal/execute` | Execute an allowlisted remediation proposal | Yes |
| `GET` | `/api/heal/config` | Inspect active LLM provider, model, and demo mode | No |
| `GET` | `/api/actuator/actions` | List frozen allowlisted actions (`restart`, `scale_pool`, `rollback`) | No |

### 2.6 Incident Memory & Learning (`LEARN`)

| Method | Path | Summary | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/memory/commit` | Persist an Incident and Decision record to the graph | Yes |
| `GET` | `/api/memory/incidents` | List historical incidents and outcomes for a project | No |

### 2.7 Project & Endpoint Security Administration

| Method | Path | Summary | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/projects` | List registered tenant projects | No |
| `POST` | `/api/projects` | Provision a new project and generate its API key | Yes |
| `GET` | `/api/endpoints` | List registered service endpoints (secrets masked) | Yes |
| `POST` | `/api/endpoints` | Register a new endpoint with encrypted secret | Yes |

### 2.8 GitHub Webhooks

| Method | Path | Summary | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/webhooks/github` | Receive GitHub PR webhook, evaluate risk, post comment | HMAC Signature |

---

## 3. Server-Sent Events (SSE) Protocol

Diagnostic reasoning is streamed from `GET /api/heal/stream` using the standard `text/event-stream` MIME type. Each event follows the frozen envelope structure:

```json
{
  "type": "thought | cypher | candidates | result | done",
  "ts": "2026-10-22T21:00:00.000Z",
  "payload": { ... }
}
```

### Event Types:
1. `thought`: Natural-language reasoning step emitted by the diagnostic engine.
2. `cypher`: Query pattern executed against the Knowledge Graph.
3. `candidates`: Ranked list of suspicious services with anomaly confidence scores.
4. `result`: Validated `RCAResult` containing `root_cause_node`, `fault_type`, and `ranked_fixes`.
5. `done`: Signal indicating diagnosis stream termination.

---

## 4. Standard Error Response Format

All API errors return a standard RFC 7807-compatible JSON payload:

```json
{
  "detail": "Action 'drop_table' is not allowlisted. Allowed actions: ['restart', 'scale_pool', 'rollback']."
}
```

- **HTTP 400**: Schema validation error, out-of-bounds parameter, or allowlist violation.
- **HTTP 401 / 403**: Missing or invalid API key (`X-API-Key`).
- **HTTP 404**: Target service or incident ID not found in the Knowledge Graph.
- **HTTP 422**: Pydantic input body validation failure.
- **HTTP 500**: Unhandled internal server exception.

---

*For interactive parameter testing and schema models, visit `/docs` on the active backend server.*
