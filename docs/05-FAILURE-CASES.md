# Case matrix — what can go wrong and what we do

| Case | Plan |
|---|---|
| Neo4j won't start / Docker too heavy | `GRAPH_BACKEND=networkx`; same API. Aura Free as cloud alternative |
| LLM rate-limited / key expired | LiteLLM → Ollama → `fallback_rules.py` → cached run |
| LLM returns invalid JSON or hallucinated node | Pydantic validation; reject IDs not in context; retry once; fall back |
| LLM diagnosis wrong | Show confidence; allowlist + simulation still limit damage; log as failed diagnosis and count in accuracy |
| SSE blocked by network/proxy | Frontend auto-switches to polling `GET /api/heal/events` |
| Demo-day Wi-Fi fails | Local `docker compose` copy + backup video |
| Render cold start (30–60 s) | Warm-up script 5 min before; local copy ready |
| Fix makes things worse | Dead-man rollback restores snapshot; shown deliberately as a bonus scene |
| Team member ill / exam week | Backup owner per module |
| Behind schedule | Cut: timeline scrubber → Online Boutique view → cyclic-PR UI → CPU fault → fancy animation |
| Graph numbers differ from 54/142 | Fix the seed, not the slide |
| Panel asks "is this real?" | Show `06-REAL-VS-SIMULATED.md` slide |
| Merge conflicts in schema | Only A edits `schema.cypher`/`topology.yaml` |

## Free-tier notes
Free LLM limits change without notice; Ollama needs ~8 GB RAM; free hosting sleeps when idle (demo concern only). Small paid LLM key / always-on instance are optional, never required.
