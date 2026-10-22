# Changelog

All notable changes to the AEGIS project will be documented in this file.

## [2026-10-22] - Unified Config, Python 3.12 Pinning & Neo4j Backend Integration
### Added
- `backend/config.py`: Unified settings via `pydantic-settings` (`Settings` class) defining `GRAPH_BACKEND`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` (strictly required when `GRAPH_BACKEND=neo4j`), `ADMIN_SHARED_SECRET`, `LLM_PROVIDER`, `LLM_MODEL`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `OLLAMA_BASE_URL`, `GITHUB_TOKEN`, `PORT`, and `HOST`.
- `.env.example`: Updated to match `backend/config.py` with commented descriptions and guidance.
- Parametrized fixture `graph_repo` in `backend/tests/test_graph.py` running tests against both `networkx` and `neo4j` (auto-skipped unless `NEO4J_URI` is configured in environment).
- `test_incident_survives_repo_rebuild_on_neo4j` in `backend/tests/test_graph.py` asserting incident durability across repository instances.
- `backend/tests/test_config_and_neo4j.py`: Unit and integration tests for settings validation, `ADMIN_SHARED_SECRET` protection on `POST /api/reset`, and unreachable Neo4j fallback to NetworkX with `"mode": "ephemeral"` in `GET /health`.
- `frontend/src/config.ts`: Centralized frontend configuration exporting `API_BASE_URL` (reading `VITE_API_BASE`), `DEFAULT_PROBE_URL`, and `apiUrl()`.

### Changed
- Pinned Python 3.12 requirement in `pyproject.toml` (`requires-python = ">=3.12"`), `Dockerfile` (`FROM python:3.12-slim`), and `README.md`.
- `requirements.txt`: Strictly pinned all dependency versions including `pydantic-settings==2.2.1` and `neo4j==5.18.0`.
- `backend/graph/neo4j_repo.py`:
  - Implemented `reset()` to clear existing graph and reseed baseline topology from `data/topology.yaml`.
  - Replaced `apoc.create.uuid()` with Python `uuid.uuid4().hex` passed into Cypher parameters (eliminates APOC requirement).
  - Added timestamp cutoff filtering in `incidents(node, days)`.
  - Added `verify_connectivity()` and `is_empty()` methods.
- `backend/graph/__init__.py`:
  - Singleton initialization now verifies Neo4j connectivity and seeds from `data/topology.yaml` if graph is empty.
  - Automatically falls back to NetworkX with a logged warning if Neo4j is unreachable.
  - Added `get_graph_mode()` returning `"persistent"` or `"ephemeral"`.
- `backend/api/main.py`:
  - `GET /health` now returns `"mode": get_graph_mode()`.
  - Replaced `os.environ.get("PORT")` with `settings.PORT` and `settings.HOST`.
- `backend/api/routes_graph.py`: Protected `POST /api/reset` with `X-Admin-Secret` header validation when `ADMIN_SHARED_SECRET` is configured.
- `backend/ingestion/github_fetcher.py`: Replaced `os.getenv("GITHUB_TOKEN")` with `settings.GITHUB_TOKEN`.
- `frontend/src/pages/MonitorPage.tsx`: Replaced hardcoded default probe URL with `DEFAULT_PROBE_URL` from `../config`.

## [2026-10-22] - Honesty & Real Data Alignment
### Added
- `GET /api/incidents` endpoint in `backend/api/routes_graph.py` backed by `GraphRepository.incidents()`, accepting optional `service_id` and `days` filters.
- Integration test `test_api_incidents_empty_and_after_add` in `backend/tests/test_api_integration.py` verifying empty graph state and incident retrieval after add.
- Visible banner `"Sample data: live OpenTelemetry ingest is planned"` in `frontend/src/pages/ObservabilityPage.tsx`.
- Visible badge `"Demo diagnosis (scripted)"` on the streaming terminal in `frontend/src/pages/ActuatorPage.tsx`.

### Changed
- `backend/graph/repository.py`, `backend/graph/networkx_repo.py`, and `backend/graph/neo4j_repo.py`: updated `incidents(node: str = "", days: int = 30)` to support querying all incidents across the topology when `node` is empty.
- `frontend/src/pages/IncidentLedgerPage.tsx`: replaced hardcoded mock records and fabricated KPIs (`MTTR 7.4s`, `100% healing`) with live data from `GET /api/incidents`. Added empty state `"No incidents yet"` when baseline is clean, and real KPI calculations (`n/a` when no data).
- `frontend/src/pages/ActuatorPage.tsx` and `frontend/src/App.tsx`: removed ungrounded "LLM reasoner" claims from navigation and header subtitles.
- `backend/api/routes_heal.py`: labeled demo diagnosis events as `[Demo diagnosis (scripted)]`.

### Removed
- Deleted orphaned modal components from `frontend/src/components/`:
  - `PredictModal.tsx` (superseded by `PredictPage.tsx`)
  - `MonitorModal.tsx` (superseded by `MonitorPage.tsx`)
  - `IngestionModal.tsx` (superseded by `IngestPage.tsx`)
