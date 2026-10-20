# Real vs simulated in Phase 1 (say this openly)

| Real | Simulated (becomes real in Phase 2) |
|---|---|
| Graph database and queries | Pods, latency, error rates (emulated telemetry) |
| BFS blast radius, Tarjan cycles, risk formula | The "merge" and the PR (sample JSON, not live GitHub) |
| LLM reasoning over graph context | Fix execution (changes emulated state, not a cluster) |
| Safety scoring, allowlist, rollback logic | MTTR figures (measured on the emulator) |
| Incident write-back and score change | Detection thresholds tuned by hand |

Quote timings as "emulator time". Drop the "35 min saved" claim unless a source is cited; use "versus manual baseline, measured in Phase 2". Review-2 metrics (MTTR 7.4 s, accuracy > 92 %) are labelled *simulated* until measured for real.
