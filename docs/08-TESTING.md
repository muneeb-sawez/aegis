# Testing strategy
- **Unit (pytest):** blast radius (direction test!), contract diff, Tarjan, risk formula, candidate scoring, allowlist, rollback. Coverage **≥ 70 %** on `sim/` and `executor/`.
- **Repository parity:** one suite parametrized over Neo4j + NetworkX.
- **Contract tests:** schemathesis or plain pytest against the OpenAPI.
- **LLM tests:** 3 fault types × 10 repeated runs; record accuracy, latency, tokens, cost. Target ≥ 8/10 per type; lower ⇒ prompt-fix day.
- **Safety tests:** non-allowlisted action refused; bad fix rolls back; prompt-injection in incident name does not break the allowlist.
- **Context size test:** RCA context JSON < ~3,000 tokens.
- **UI:** Playwright smoke test of the full demo path (optional, in CI).
- **Weekly metrics sheet:** tests passing, open bugs, cards done vs planned, rehearsal time.
- **Degraded-mode runs (Week 9):** Wi-Fi off (local), LLM key disabled (fallback), Neo4j stopped (NetworkX).
