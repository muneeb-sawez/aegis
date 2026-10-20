# Decisions log

## Resolved conflicts between source documents
| Conflict | Decision | Why |
|---|---|---|
| Review 2 says 5-day build; Build Guide says 20 weeks | **Phase 1 = Weeks 1–10, Phase 2 = Weeks 11–20** | 5 days can't deliver real algorithms + LLM + polished UI |
| Go/Spring Boot/Python vs Python only | **Python only (FastAPI)** | Three languages triple integration cost |
| Kafka node vs real Kafka | Kafka is a **demo-topology node only** | Part of the story, not plumbing |
| Risk formula A (blast, history, change size, criticality) vs B (blast, contract, cycle, history) | **Formula B** in Phase 1; change-size added in Phase 2 | B matches the demo (breaking contract = high risk) |
| Build Guide formula `0.35B+0.25H+0.20change+0.20crit` | Superseded for Phase 1 by formula B | see above |
| Review 2 metrics | Label **simulated** now, measure in Phase 2 | Panel will ask how computed |
| Neo4j vs NetworkX | Neo4j behind `GraphRepository`, NetworkX fallback | App runs even if Docker fails |
| Cytoscape.js (Build Guide) vs React Flow (plan) | **React Flow** for the demo | Recommended; confirm |
| Blast radius up to 4 hops (Build Guide Cypher) vs 3 hops + 0.75 attenuation (plan) | **3 hops + 0.75 attenuation** in Phase 1 | Plan is the Phase 1 authority |

## Assumptions to confirm (edit when answered)
1. 10 + 10 week split — _unconfirmed_.
2. Team of 4 — _unconfirmed_.
3. Free LLM available (Gemini / Groq / Ollama) — _unconfirmed_.
4. React Flow vs Cytoscape — React Flow assumed.

## Open decision (Week 3)
Risk calibration option for PR #142 (see `04-ALGORITHMS.md` §6). Chosen option: _TBD_.

## Log
_(date — decision — who)_
