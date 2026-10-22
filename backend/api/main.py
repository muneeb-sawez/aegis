"""AEGIS Core API Service (M0).

Mounts:
- Graph & Topology Routes (/api/graph/topology, /api/reset)
- Simulation Routes (/api/simulate-pr)
- Chaos Routes (/api/chaos/inject)
- Healing & Diagnosis SSE (/api/heal/stream, /api/memory/commit)
- Executor Routes (/api/actuator/execute, /api/actuator/approve, /api/decisions)
- Ingestion Routes (/api/ingest/repository, /api/graph/external-service)
- Monitor Routes (/api/monitor/status, /api/monitor/check-now, /api/monitor/fault, /api/monitor/configure)
- PREDICT Routes (/api/predict/analyze)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes_actuator import router as actuator_router
from backend.api.routes_chaos import router as chaos_router
from backend.api.routes_graph import router as graph_router
from backend.api.routes_heal import router as heal_router
from backend.api.routes_ingestion import router as ingestion_router
from backend.api.routes_monitor import router as monitor_router
from backend.api.routes_predict import router as predict_router
from backend.api.routes_projects import router as projects_router
from backend.api.routes_endpoints import router as endpoints_router
from backend.api.routes_webhooks import router as webhooks_router
from backend.api.routes_github_auth import router as github_auth_router
from backend.api.routes_sim import router as sim_router

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start continuous background monitoring worker (Directive §3.C)
    from backend.monitor.health_checker import get_health_checker

    checker = get_health_checker()
    await checker.start_worker(interval_sec=10.0)
    yield
    # Shutdown: Stop worker cleanly
    checker.stop_worker()


app = FastAPI(
    title="AEGIS — Autonomous Engineering Graph & Intelligence System",
    description="Graph-grounded pre-deployment change risk simulation (PREDICT) and post-deployment service health monitoring (MONITOR).",
    version="0.2.0",
    lifespan=lifespan,
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
from fastapi.staticfiles import StaticFiles

app.include_router(graph_router)
app.include_router(sim_router)
app.include_router(chaos_router)
app.include_router(heal_router)
app.include_router(actuator_router)   # Executor: /api/actuator/execute, /approve, /api/decisions
app.include_router(ingestion_router)
app.include_router(monitor_router)
app.include_router(predict_router)
app.include_router(projects_router)
app.include_router(endpoints_router)
app.include_router(webhooks_router)
app.include_router(github_auth_router)


from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.graph import get_graph_mode

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AEGIS",
        "version": "0.2.0",
        "mode": get_graph_mode(),
    }


dist_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")
assets_dir = os.path.join(dist_dir, "assets")

if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/")
def read_root(request: Request):
    accept = request.headers.get("accept", "")
    index_file = os.path.join(dist_dir, "index.html")
    if "text/html" in accept and os.path.exists(index_file):
        return FileResponse(index_file)

    return {
        "system": "AEGIS",
        "motto": "See every risk before it ships. Heal every failure after it lands.",
        "phase": 1,
        "capabilities": ["PREDICT", "MONITOR", "INGESTION", "EXECUTOR"],
        "status": "operational",
        "docs_url": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.main:app", host=settings.HOST, port=settings.PORT, reload=True)

