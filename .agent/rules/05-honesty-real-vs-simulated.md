---
trigger: always_on
description: Honesty rules for metrics, labels and demo numbers
---
# Honesty rules
- Telemetry, pods, latency, error rates, the "merge", PRs (sample JSON), fix execution and MTTR are **simulated** in Phase 1. Label them "simulated" / "emulator time" in code comments, API fields and UI.
- Real in Phase 1: the graph DB and queries, BFS blast radius, Tarjan cycle detection, the risk formula, LLM reasoning over graph context, safety scoring/allowlist/rollback logic, incident write-back and the resulting score change.
- **Never hard-code 86 or 91.** Choose sensible inputs and let the code produce the number. If honest numbers differ (e.g. 72 → 77), use them; the +5 learning jump must still hold.
- Do not show "MTTR 7.4 s", ">92% accuracy" or "35 min saved" as results. Show measured values from our own runs only, marked as emulator measurements.
- If a count/number differs from the claimed 54/142, fix the seed — don't fake the display.
