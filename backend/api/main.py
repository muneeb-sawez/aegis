"""AEGIS Core API Service (M0).

Mounts:
- Graph & Topology Routes (/api/graph/topology, /api/reset)
- Simulation Routes (/api/simulate-pr)
- Chaos Routes (/api/chaos/inject)
- Healing & Actuator Routes (/api/heal/stream, /api/actuator/execute, /api/memory/commit)
- Ingestion Routes (/api/ingest/repository, /api/graph/external-service)
- Monitor Routes (/api/monitor/status, /api/monitor/check-now, /api/monitor/fault, /api/monitor/configure)
- PREDICT Routes (/api/predict/analyze)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes_chaos import router as chaos_router
from backend.api.routes_graph import router as graph_router
from backend.api.routes_heal import router as heal_router
from backend.api.routes_ingestion import router as ingestion_router
from backend.api.routes_monitor import router as monitor_router
from backend.api.routes_predict import router as predict_router
from backend.api.routes_sim import router as sim_router

app = FastAPI(
    title="AEGIS — Autonomous Engineering Graph & Intelligence System",
    description="Graph-grounded pre-deployment change risk simulation (PREDICT) and post-deployment service health monitoring (MONITOR).",
    version="0.2.0",
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all domain routers
app.include_router(graph_router)
app.include_router(sim_router)
app.include_router(chaos_router)
app.include_router(heal_router)
app.include_router(ingestion_router)
app.include_router(monitor_router)
app.include_router(predict_router)


@app.get("/")
def read_root():
    return {
        "system": "AEGIS",
        "motto": "See every risk before it ships. Heal every failure after it lands.",
        "phase": 1,
        "capabilities": ["PREDICT", "MONITOR", "INGESTION"],
        "status": "operational",
        "docs_url": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.main:app", host="0.0.0.0", port=8000, reload=True)
