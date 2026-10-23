# AI Agent Directive: Target Repository Clone & Runtime Guide

> **IMPORTANT DIRECTIVE FOR AI AGENTS & AUTOMATION RUNNERS**:
> Whenever the main AEGIS system is running (`python -m uvicorn backend.api.main:app` and `npm run dev`), the AI agent **MUST ensure that the target microservice repository is cloned and actively running locally**.
> This powers the real-time health probers, telemetry streaming, and the **live node beats (moving traffic particle dots)** on the AEGIS Mission Control topology graph.

---

## 1. Target Repository Specification

- **Repository URL**: `https://github.com/FawazMulla/spring-petclinic-microservices/`
- **Recommended Clone Directory**: `C:\Users\Fawaz\Desktop\spring-petclinic-microservices` (or adjacent to AEGIS)
- **Architecture**: Distributed Spring Boot 4 Java microservices architecture featuring Spring Cloud Gateway, Netflix Eureka Discovery, Centralized Config Server, and domain microservices.

---

## 2. Step-by-Step Instructions for AI Agent

### Step 1: Clone Target Repository (if not already present)
Check if the repository exists on disk. If not, clone it:
```powershell
if (!(Test-Path "C:\Users\Fawaz\Desktop\spring-petclinic-microservices")) {
    git clone https://github.com/FawazMulla/spring-petclinic-microservices.git "C:\Users\Fawaz\Desktop\spring-petclinic-microservices"
}
```

---

### Step 2: Run Target Microservices
The AI agent must start the target application using **either** of the following two methods:

#### Method A: Unified Multi-Mode Runner (Recommended — Fast & Reliable)
From the AEGIS root repository, launch:
```powershell
python scripts/run_petclinic_live.py
```
- **Auto-detection**: If Docker Desktop daemon is active, it runs official pre-built containers (`springcommunity/spring-petclinic-*`). If Docker is inactive, it immediately starts high-performance native asynchronous microservices serving Spring Boot Actuator `/actuator/health` on the exact service ports.
- **Service Port Allocations**:
  - `api-gateway`: `http://127.0.0.1:8085` (`/actuator/health`) *(port 8085 prevents conflicts with local Jenkins on 8080)*
  - `customers-service`: `http://127.0.0.1:8081` (`/actuator/health`)
  - `visits-service`: `http://127.0.0.1:8082` (`/actuator/health`)
  - `vets-service`: `http://127.0.0.1:8083` (`/actuator/health`)
  - `discovery-server`: `http://127.0.0.1:8761` (`/actuator/health`)
  - `config-server`: `http://127.0.0.1:8888` (`/actuator/health`)
  - `admin-server`: `http://127.0.0.1:9090` (`/actuator/health`)

#### Method B: Pure Docker Compose
If Docker Desktop is running:
```powershell
cd C:\Users\Fawaz\Desktop\spring-petclinic-microservices
docker compose up -d config-server discovery-server customers-service visits-service vets-service api-gateway
```

---

### Step 3: Verify AEGIS Observes the Live Target App

1. **Verify Backend Probing**:
   Trigger an immediate prober check or view monitored status:
   ```powershell
   curl http://localhost:8000/api/monitor/status?project_id=spring-petclinic-microservices
   ```
   All microservices should report `status: "healthy"` and real response times (~10-40ms).

2. **Verify Real-Time Live Node Beats in UI**:
   - Open [http://localhost:5173](http://localhost:5173).
   - In the top-bar project selector, switch to **Spring Petclinic Microservices** (`spring-petclinic-microservices` or `tenant-b-f8f694`).
   - Navigate to the **Topology** page.
   - **Expected Visual Behavior**:
     - All microservice nodes show green `HEALTHY` badges with live rolling latency sparklines.
     - **Live Node Beats (`LiveBeatEdge`)**: Glowing particle dots travel smoothly along the bezier edge paths from `api-gateway` into `customers-service`, `visits-service`, and `vets-service` in real time, visualizing the heartbeat of the microservice network.

---

## 3. Chaos & Outage Simulation Instructions for AI Agent

To test that AEGIS detects real outages and halts the live beats on affected edges:

1. **Simulate Outage on a Microservice**:
   ```powershell
   python scripts/run_petclinic_live.py --fail visits-service
   ```
   - **Observed Result**: Within 2 probe cycles, AEGIS marks `visits-service` as `UNAVAILABLE` (red badge).
   - The glowing particle dots on the `api-gateway -> visits-service` edge immediately cease flowing.

2. **Recover the Microservice**:
   ```powershell
   python scripts/run_petclinic_live.py --recover visits-service
   ```
   - **Observed Result**: AEGIS detects recovery (`status: "healthy"`), emits a `recovered` SSE event, and the glowing live beats resume flowing along the edge.

---

## 4. Architecture Reference

```
                  ┌──────────────────────────────────────────────┐
                  │   Target App: spring-petclinic-microservices │
                  │  (https://github.com/FawazMulla/...)         │
                  └───────────────────────┬──────────────────────┘
                                          │ Real HTTP Actuator Probes
                                          ▼
                  ┌──────────────────────────────────────────────┐
                  │           AEGIS Backend Probers              │
                  │   (backend/monitor/health_checker.py)        │
                  └───────────────────────┬──────────────────────┘
                                          │ SSE Stream (/api/monitor/events)
                                          ▼
                  ┌──────────────────────────────────────────────┐
                  │           AEGIS Mission Control              │
                  │   (TopologyPage.tsx & LiveBeatEdge.tsx)      │
                  │      Glowing particle dots flowing live      │
                  └──────────────────────────────────────────────┘
```
