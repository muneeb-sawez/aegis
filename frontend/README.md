# AEGIS Frontend — Mission Control Dashboard

Modern React 18, TypeScript, and Vite single-page application for the AEGIS reliability intelligence system.

---

## 🚀 Quickstart

### 1. Install Dependencies
```bash
npm install
```
*(Make sure to run `npm install`, NOT `npm run install`)*

### 2. Run Development Server
```bash
npm run dev
```
- **Local URL**: [http://localhost:5173](http://localhost:5173)
- API requests made to `/api/*` are automatically proxied to the backend at `http://localhost:8000` via [vite.config.ts](file:///c:/Users/Fawaz/Desktop/M-ageis/aegis/frontend/vite.config.ts).

### 3. Production Build
```bash
npm run build
```
Build output is saved to `dist/`, which is automatically mounted and served by the FastAPI backend in unified production mode.

---

## 🛠️ Tech Stack & Views

- **Framework**: React 18 + Vite + TypeScript
- **Styling**: Tailwind CSS
- **Interactive Graph Visualization**: `@xyflow/react` (React Flow)
- **State & Streaming**: Server-Sent Events (SSE) for real-time diagnostic reasoning streams

### Available Dashboard Views
- **Topology**: Interactive 2D microservice dependency graph with health badges and node telemetry.
- **Predict (`PREDICT`)**: Pre-merge pull request risk scoring, blast radius simulation, and AST contract diffing.
- **Monitor (`MONITOR`)**: Active HTTP probe status, latency percentiles, and error rate monitoring.
- **Chaos (`CHAOS`)**: Controlled fault injection (latency spike, connection pool saturation, process crashes).
- **Actuator (`HEAL`)**: Guarded remediation proposals, pre-action snapshots, and 10-second rollback watchdog.
- **Projects**: Multi-project management and GitHub repository ingestion.
