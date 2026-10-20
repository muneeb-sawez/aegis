---
description: AEGIS Phase 1 — Week 7: Guarded actuator and candidate scoring
---
# Week 7 — Guarded actuator and candidate scoring

**Before starting:** read `AGENTS.md`, `.agent/rules/`, and the docs referenced below. Ask the human for their role (A/B/C/D) and only work on that role's tasks. Restate tasks, files, and exit test; get approval; implement test-first; run tests; report output.

**Goal:** a fix is applied safely or rolled back automatically.

## Tasks
- **M7 (C):** allowlist of 3 actions (`restart_pod`, `scale_pool`, `rollback_release`) each with a param validator and simulated effect on telemetry. **Write and pass the rollback test first.**
- **M7 (C):** candidate scoring `F = 0.6·Safety + 0.4·Recovery`; execute only if Safety ≥ 75; Recovery from a transparent lookup table by fault type.
- **M7 (C):** health probe after 2 s; dead-man switch restores the pre-action snapshot if p99 is not < 2× baseline in the window.
- **M5 (B):** add a "bad fix" fault mode that makes things worse.
- **M9 (D):** ranked fix cards, execution progress bar, dead-man indicator, healed badge.
- **Safety review (B reviews C):** try to make the actuator run something outside the allowlist; it must refuse.

## Exit test
Good fix heals · bad fix rolls back · non-allowlisted action refused.
