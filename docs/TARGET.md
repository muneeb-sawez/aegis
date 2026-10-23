# AEGIS Target Integration Guide

> [!IMPORTANT]
> **Primary Target System**: For AI agents and developers working with the target microservice architecture **[`spring-petclinic-microservices`](https://github.com/FawazMulla/spring-petclinic-microservices/)**, please consult **[`docs/AI_AGENT_TARGET_REPO_GUIDE.md`](AI_AGENT_TARGET_REPO_GUIDE.md)** for cloning, running, and live node beat visualization instructions.

This document describes how to run target microservice systems, ingest topologies into AEGIS, and register live health endpoints for real-time monitoring, fault injection, and automated healing.

---

## 1. System Overview

`aegis-target` is a real, lightweight three-tier microservice system located at `../aegis-target`:

```
[ Client / AEGIS Monitor ]
           │
           ▼
    gateway (:8001)
           │ (HTTP calls downstream)
           ▼
    payment (:8002)
           │ (HTTP calls downstream)
           ▼
    ledger  (:8003) ──▶ (Simulated Database Connection Pool)
```

### Contracts & Endpoints
Every service exposes identical standardized interfaces:

| Endpoint | Method | Purpose | Authentication |
|---|---|---|---|
| `/health` | `GET` | Reports status (`healthy`, `degraded`, `unhealthy`), latency, active fault, pool utilization, and config version | Public |
| `/work` | `GET` | Executes real end-to-end downstream request chain (`gateway` ➔ `payment` ➔ `ledger`) | Public |
| `/admin/fault` | `POST` | Injects runtime faults (`none`, `timeout`, `slow`, `crash`, `pool_exhausted`) | `X-Signature` HMAC-SHA256 |
| `/admin/fix` | `POST` | Executes actuator remedies (`restart`, `scale_pool`, `rollback`) | `X-Signature` HMAC-SHA256 |

### Security
All `/admin/*` operations require an `X-Signature` header computed as:
```python
X-Signature = hmac.new(ADMIN_SHARED_SECRET.encode("utf-8"), raw_request_body, hashlib.sha256).hexdigest()
```
- Missing signature header returns **401 Unauthorized**.
- Invalid or mismatched signature returns **403 Forbidden**.

---

## 2. Running `aegis-target`

### Option A: With Docker Compose (Recommended)
From the root of `aegis-target`:
```bash
cd ../aegis-target
docker compose up --build -d
```
Verify all three containers are healthy:
```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

### Option B: Native Python (Local Development)
In three separate terminal sessions:
```bash
# Terminal 1: Ledger (:8003)
cd ../aegis-target
uvicorn services.ledger:app --host 0.0.0.0 --port 8003

# Terminal 2: Payment (:8002)
cd ../aegis-target
LEDGER_URL=http://localhost:8003 uvicorn services.payment:app --host 0.0.0.0 --port 8002

# Terminal 3: Gateway (:8001)
cd ../aegis-target
PAYMENT_URL=http://localhost:8002 uvicorn services.gateway:app --host 0.0.0.0 --port 8001
```

---

## 3. Ingesting `docker-compose.yml` into AEGIS

AEGIS can automatically extract the microservice architecture and dependency edges (`CALLS` / `DEPENDS_ON`) directly from `aegis-target/docker-compose.yml`.

### Step 3.1: Read the Target Compose File
Read `../aegis-target/docker-compose.yml`:
```yaml
version: "3.8"
services:
  gateway:
    ...
    depends_on:
      - payment
  payment:
    ...
    depends_on:
      - ledger
  ledger:
    ...
```

### Step 3.2: Submit to AEGIS Ingestion API
Send a `POST` request to `http://localhost:8000/api/ingest/repository`:

```bash
curl -X POST http://localhost:8000/api/ingest/repository \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "local/aegis-target",
    "branch": "master",
    "replace_graph": false,
    "raw_manifest": "version: \"3.8\"\nservices:\n  gateway:\n    ports:\n      - \"8001:8001\"\n    depends_on:\n      - payment\n  payment:\n    ports:\n      - \"8002:8002\"\n    depends_on:\n      - ledger\n  ledger:\n    ports:\n      - \"8003:8003\""
  }'
```

**Expected Response**:
```json
{
  "status": "success",
  "repository": "local/aegis-target",
  "branch": "master",
  "manifest_type": "docker-compose",
  "nodes_imported": 3,
  "edges_imported": 2,
  "nodes": ["gateway", "payment", "ledger"],
  "edges": [
    {"source": "gateway", "target": "payment", "type": "DEPENDS_ON"},
    {"source": "payment", "target": "ledger", "type": "DEPENDS_ON"}
  ],
  "replaced_baseline": false
}
```

The services and dependency topology will immediately appear on the AEGIS 3D/2D Graph Canvas (`/` and `/topology`).

---

## 4. Registering Live `/health` Probe URLs with AEGIS Monitor

Once the services are present in the graph, register their live health URLs with the AEGIS background monitoring worker.

### Via REST API (`POST /api/monitor/configure`)

#### 1. Register Gateway
```bash
curl -X POST http://localhost:8000/api/monitor/configure \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "gateway",
    "health_url": "http://localhost:8001/health",
    "poll_interval_sec": 5.0
  }'
```

#### 2. Register Payment
```bash
curl -X POST http://localhost:8000/api/monitor/configure \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "payment",
    "health_url": "http://localhost:8002/health",
    "poll_interval_sec": 5.0
  }'
```

#### 3. Register Ledger
```bash
curl -X POST http://localhost:8000/api/monitor/configure \
  -H "Content-Type: application/json" \
  -d '{
    "service_id": "ledger",
    "health_url": "http://localhost:8003/health",
    "poll_interval_sec": 5.0
  }'
```

### Via AEGIS Monitor UI
1. Navigate to `http://localhost:5173/monitor` in your browser.
2. Under **Configure Live Probe Endpoint**:
   - Select Service: `gateway` ➔ URL: `http://localhost:8001/health` ➔ Click **Set Probe URL**.
   - Select Service: `payment` ➔ URL: `http://localhost:8002/health` ➔ Click **Set Probe URL**.
   - Select Service: `ledger` ➔ URL: `http://localhost:8003/health` ➔ Click **Set Probe URL**.

The AEGIS monitoring worker will continuously poll each service, report real measured response latencies, and flag health status changes in the UI and graph.

---

## 5. End-to-End Fault & Heal Demonstration

### Scenario: Downstream Payment Timeout propagates to Gateway

1. **Inject Fault into Payment**:
   Generate HMAC signature for `{"fault": "timeout"}` and POST to payment service:
   ```bash
   BODY='{"fault":"timeout"}'
   SIG=$(python -c 'import hmac,hashlib; print(hmac.new(b"secret123", b"{\"fault\":\"timeout\"}", hashlib.sha256).hexdigest())')

   curl -X POST http://localhost:8002/admin/fault \
     -H "Content-Type: application/json" \
     -H "X-Signature: $SIG" \
     -d "$BODY"
   ```

2. **Observe Real Propagation**:
   - Query Gateway Health:
     ```bash
     curl http://localhost:8001/health
     ```
     Gateway detects downstream payment timeout within 2 seconds and reports:
     ```json
     {
       "service": "gateway",
       "status": "degraded",
       "latency_ms": 2005.12,
       "fault": "none",
       "pool_size": 20,
       "pool_in_use": 0,
       "config_version": "v1"
     }
     ```
   - AEGIS Monitor (`GET /api/monitor/status`) transitions `payment` and `gateway` from `healthy` to `degraded`.

3. **Apply Allowlisted Heal Action**:
   Send a signed `restart` fix to Payment:
   ```bash
   BODY='{"action":"restart"}'
   SIG=$(python -c 'import hmac,hashlib; print(hmac.new(b"secret123", b"{\"action\":\"restart\"}", hashlib.sha256).hexdigest())')

   curl -X POST http://localhost:8002/admin/fix \
     -H "Content-Type: application/json" \
     -H "X-Signature: $SIG" \
     -d "$BODY"
   ```

4. **Verify Recovery**:
   Both `payment` and `gateway` immediately return to `status: "healthy"` on subsequent probe cycles.
