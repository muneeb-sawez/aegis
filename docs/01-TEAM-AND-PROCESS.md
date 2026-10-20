# Team, ownership and process (assumes 4 people)

| Role | Owns modules | Backup |
|---|---|---|
| **A — Graph & Data** | M1 Graph layer, M2 Topology seed, M3 Ingestion-lite | B |
| **B — Simulation & Scoring** | M4 Simulation engine, M5 Chaos/telemetry emulator | A |
| **C — Agent & Execution** | M6 RCA agent, M7 Guarded actuator, M8 Feedback writer | D |
| **D — Platform & UI** | M0 Platform/CI, M9 Dashboard, M10 Demo & docs | C |

**Review rules:** B reviews M7 (allowlist + rollback); A reviews the LLM prompt guardrails (M6). Nobody reviews their own safety code.
**File ownership:** only A edits `schema.cypher` and `data/topology.yaml`; others raise an issue.

## Weekly cadence
- **Mon 30 min** planning (pick cards, confirm owners) · **Wed 15 min** blocker check · **Fri 45 min** integration demo of the *whole loop* · **Fri evening** tag `v0.W` + update changelog.
- If the loop is broken on Friday, fixing it outranks new features.

## Git rules
`main` always runnable · short feature branches · PR needs 1 review · CI = ruff + pytest + frontend build.

## Where
One GitHub org, two repos: `aegis` (monorepo, the product) and `aegis-testbed` (Online Boutique fork, used from Week 4–6). Local laptops; GitHub Codespaces as fallback. Pin Python 3.11 and Node versions in `.tool-versions`/README.

## Free toolkit
GitHub Free + Actions + Projects · Neo4j Community (Docker) / AuraDB Free · NetworkX · FastAPI/Pydantic/pytest · React+TS+Vite+Tailwind+React Flow · Gemini/Groq free + Ollama · LiteLLM · Render/Fly/Railway + Vercel/Netlify · Mermaid/draw.io · Figma free · OBS for backup demo video · Discord/WhatsApp + Google Meet.
Free LLM limits change without notice — re-check in Week 1 and assume fallback to Ollama (needs ~8 GB free RAM for small models).
