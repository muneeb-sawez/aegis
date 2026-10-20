# Modules M0–M10 (scope and "done when")

| # | Module (owner) | Phase 1 scope | Done when |
|---|---|---|---|
| M0 | Platform & CI (D) | Repo, Docker Compose, CI, env config, deploy | `docker compose up` starts API + Neo4j + UI on a clean laptop |
| M1 | Graph layer (A) | Schema, repository interface, Neo4j + NetworkX impls | Same test suite passes on both backends |
| M2 | Topology seed (A) | `topology.yaml` → 54 nodes / 142 edges | Counts match exactly; loader idempotent |
| M3 | Ingestion-lite (A) | Parse Online Boutique k8s manifests into CALLS edges | Edge precision/recall vs hand-written ground truth |
| M4 | Simulation (B) | BFS blast radius, contract diff, Tarjan cycle check, risk score, merge gate | Unit tests on 6 hand-checked cases |
| M5 | Chaos & telemetry (B) | Fault catalogue, emulated telemetry, anomaly trigger | Injecting a fault changes telemetry and fires exactly one event |
| M6 | RCA agent (C) | Graph-context builder, grounded prompt, streaming, rule fallback | 3 fault types diagnosed correctly ≥ 8/10 runs each |
| M7 | Guarded actuator (C) | Allowlist, candidate scoring, health probe, dead-man rollback | A deliberately bad fix auto-rolls back in a test |
| M8 | Feedback writer (C) | Incident/Decision nodes; H term updates | Re-running PR #142 gives a higher score |
| M9 | Dashboard (D) | Canvas, two tabs, gauge, terminal, timeline, KPI bar | A stranger can follow one incident alert → outcome unaided |
| M10 | Demo & docs (D) | 4-minute script, backup video, report sections | Two full rehearsals, no live fix needed |

## Priority (cut line)
- **Must:** M0, M1, M2, M4, M5, M6 (with fallback), M7, M8, canvas + both tabs.
- **Should:** M3 ingestion-lite, timeline scrubber, auto-postmortem.
- **Could:** second graph view (Boutique), latency heat view, polish animations.

## UI (M9) summary
React Flow canvas (dark theme) with custom `ServiceNode`, `DatabaseNode`, `PodNode`; auto layout via dagre/elkjs.
- **Tab 1 — Pre-ship simulation:** PR dropdown, "Run Pre-Ship Simulation", radial risk gauge, blast-radius halos (amber/red by `impact_weight`), GitHub-style status card (Approved/Warn/Blocked), contract diff viewer.
- **Tab 2 — Mission control:** "Inject Failure" control, traffic dots on edges turning crimson, KPI bar (live emulated telemetry), typewriter terminal (renders `thought` vs `cypher` differently), ranked fix cards, execution progress bar, dead-man indicator, "healed" badge, timeline scrubber (Baseline → Fault → Healing → Learned) from a saved event log, incident node animating onto the canvas, auto-postmortem card.
