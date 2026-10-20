# Algorithms and formulas (Phase 1)

All weights/thresholds live in `backend/sim/config.py`.

## 1. Blast radius (M4)
- Start at the changed service; call `repo.callers(service, depth=3)` (walks **backwards** over `CALLS`, caller of caller…).
- Depth attenuation **0.75 per hop**: `impact_weight = 0.75^(hops-1)` (hop 1 = 1.0). *(Assumption — record the exact form in `07-DECISIONS.md`.)*
- Returns per-service `{service, hops, impact_weight}`; UI halos use amber/red by `impact_weight`.
- Optional: ignore edges with `confidence < 0.5`.
- Normalise to a 0–100 term **B**.

## 2. Contract diff (M4) → term C
Compare old vs new schema JSON. **Breaking** if a field is removed, renamed, or its type changes. Added optional fields are safe. Breaking ⇒ C = 100 (safe ⇒ 0; weight severity if you add levels).

## 3. Cycle check (M4) → term D
Add the PR's proposed new edges to a **copy** of the graph; run Tarjan SCC (`networkx.strongly_connected_components`). Any SCC of size > 1 introduced by the PR ⇒ D = 100, else 0.

## 4. History (M8 writes, M4 reads) → term H
`H = min(100, 25 × incidents_in_30_days)` using `repo.incidents(node, days=30)` on the affected service(s). One incident ⇒ H +25 ⇒ total risk **+5** (0.20 × 25).

## 5. Risk score (Phase 1 uses "formula B")
```
Risk = 0.35·B + 0.30·C + 0.15·D + 0.20·H        (each term 0–100)
```
(change-size and criticality terms are Phase 2 unless used for calibration — see §6.)

## 6. Calibration decision (Week 3 — needs a human decision)
Target: PR #142 (changes PaymentService response schema, removes a field) ≈ **86** on a fresh graph, **produced by code**. Naive inputs give B≈80, C=100, D=0, H=0 ⇒ **58**, so the *inputs* need rethinking, not the formula. Options (pick one, document it, never hard-code the output):
1. Raise the weight on contract severity.
2. Count datastore dependents (Postgres, Redis) in B.
3. Add the Build Guide's *criticality* term.
If the honest number is different (e.g. 72 → 77) use it; the +5 jump still works. **Agent: propose options with computed numbers and ask the human to choose.**

## 7. Merge gate
`score ≥ 70` ⇒ **Block** · `40–69` ⇒ **Warn** · `< 40` ⇒ **Approve**. Output category breakdown: breaking contract, cycle, history, blast.

## 8. Six hand-checked test cases (write on paper first, Week 1)
Safe PR · Moderate PR · Breaking PR #142 · Cyclic PR · PR on a leaf service · PR on the gateway — each with expected blast radius and score **computed by hand** before coding.

## 9. Anomaly detector (M5)
Threshold only, no ML: **p99 > 3× baseline for 3 consecutive ticks** ⇒ raise exactly **one** anomaly event. Telemetry emulator adds small random noise via `set_telemetry()` so data looks alive.

## 10. Fault catalogue (M5)
DB pool exhaustion · pod crash · CPU saturation · latency injection (+ a **bad-fix** mode that makes things worse, for rollback tests). Each fault JSON lists which nodes' telemetry change and how.

## 11. Candidate scoring and rollback (M7)
`F = 0.6·Safety + 0.4·Recovery`. Execute only if **Safety ≥ 75**. Recovery probability = transparent lookup table by fault type (later: similarity to past incidents). Health probe after **2 s**; if p99 isn't back **< 2× baseline** within the window, restore the pre-action snapshot.

## 12. RCA agent output schema (M6)
```json
{ "hypothesis": "...", "confidence": 0.0-1.0,
  "propagation_path": ["node_id", "..."],
  "remediations": [ { "action": "restart_pod|scale_pool|rollback_release", "params": {}, "rationale": "..." } ] }
```
All node IDs must exist in the supplied context.

## 13. Closed-loop write-back (M8)
`commit_incident()` writes `(:Incident)-[:OCCURRED_IN]->(:Service)`, a `(:Decision)` with outcome (`RESOLVED_BY`). After commit, re-running PR #142 must score higher; `POST /api/reset` restores the original score.
