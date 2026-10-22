# AEGIS Mathematical & Algorithmic Foundations

> **Document Version**: 2.0.0-RELEASE  
> **Audited Date**: October 2026  
> **Source Repository**: `muneeb-sawez/aegis`  
> **Verification Reference**: `backend/sim/`, `backend/executor/`, `backend/feedback/`

---

## 1. Blast Radius: Backward BFS with Exponential Hop Decay

### 1.1 Objective
When a service $s$ undergoes modification, determine the cumulative blast radius score $B \in [0, 100]$ across all upstream callers whose requests traverse $s$.

### 1.2 Mathematical Formulation
In the AEGIS Knowledge Graph, edges are directed from caller to callee:
$$u \xrightarrow{\text{CALLS}} v$$
When service $v$ is modified, the impact propagates in reverse ($v \leftarrow u$).

The set of upstream callers is discovered via Breadth-First Search (BFS) starting at $v$, traversing incoming predecessor edges up to a maximum depth $D_{\max} = 3$:
$$\text{Callers}(v) = \{u \in V \mid \text{dist}_{\text{rev}}(v, u) \le D_{\max}\}$$

For each discovered caller $u$ at topological distance $h = \text{dist}_{\text{rev}}(v, u) \ge 1$, an attenuated impact weight is assigned using decay factor $\gamma = 0.75$:
$$w(u) = \gamma^{h - 1}$$

- **Hop 1 (Direct Callers)**: $w = 0.75^0 = 1.0000$
- **Hop 2 (Secondary Callers)**: $w = 0.75^1 = 0.7500$
- **Hop 3 (Tertiary Callers)**: $w = 0.75^2 = 0.5625$

The raw impact is the sum of all caller weights:
$$I_{\text{raw}} = \sum_{u \in \text{Callers}(v)} w(u)$$

The raw impact is normalized to $[0, 100]$ against a normalization saturation cap $C_{\text{cap}} = 5.0$:
$$B = \min\left(100.0, \, \text{round}\left(\frac{I_{\text{raw}}}{C_{\text{cap}}} \times 100.0, \, 2\right)\right)$$

### 1.3 Implementation Reference
- **Engine**: `backend/sim/blast_radius.py`
- **Graph Traversal**: `backend/graph/networkx_repo.py:164-200`
- **Time Complexity**: $O(V + E)$ where $V \le 54$ and $E \le 142$. On standard CPU hardware, execution completes in $< 5\text{ ms}$.

---

## 2. API Contract Difference Analysis (AST)

### 2.1 Objective
Compare the previous API specification ($S_{\text{old}}$) against the proposed specification ($S_{\text{new}}$) to detect backward-incompatible breaking changes, assigning score $C \in \{0.0, 100.0\}$.

### 2.2 Difference Classification Rules

An API contract modification is partitioned into four categories:

1. **Field Removal**:
   $$\exists f \in S_{\text{old}} \text{ s.t. } f \notin S_{\text{new}} \implies \text{Breaking} \, (C = 100.0)$$
   *Rationale*: Existing client code expecting field $f$ will experience deserialization errors.

2. **Field Type Mutation**:
   $$\exists f \in S_{\text{old}} \cap S_{\text{new}} \text{ s.t. } \text{type}(f_{\text{old}}) \ne \text{type}(f_{\text{new}}) \implies \text{Breaking} \, (C = 100.0)$$
   *Rationale*: Changing a type (e.g., `string` to `integer` or `string` to enum) causes parser exceptions in upstream consumers.

3. **Newly Added Required Parameter**:
   $$\exists f \in S_{\text{new}} \setminus S_{\text{old}} \text{ s.t. } f \in \text{Required}(S_{\text{new}}) \implies \text{Breaking} \, (C = 100.0)$$
   *Rationale*: Existing clients dispatching requests without the new mandatory field receive HTTP 400 Bad Request.

4. **Additive Optional Parameter**:
   $$\exists f \in S_{\text{new}} \setminus S_{\text{old}} \text{ s.t. } f \notin \text{Required}(S_{\text{new}}) \implies \text{Safe} \, (C = 0.0)$$
   *Rationale*: Fully backward-compatible; existing clients can safely ignore optional fields.

### 2.3 Implementation Reference
- **Engine**: `backend/sim/contract_diff.py:30-125`
- **Complexity**: $O(|S_{\text{old}}| + |S_{\text{new}}|)$ using dictionary key lookups.

---

## 3. Cycle Detection: Tarjan's Strongly Connected Components

### 3.1 Objective
Determine whether a proposed change introduces cyclic call loops ($A \to B \to C \to A$) that lead to distributed deadlocks and cascade exhaustion, assigning score $D \in \{0.0, 100.0\}$.

### 3.2 Mathematical Formulation
Given the existing directed dependency graph $G = (V, E)$ and a set of proposed edges $E_{\text{new}}$:
$$G' = (V, E \cup E_{\text{new}})$$

Tarjan's algorithm partitions $V$ into its maximal Strongly Connected Components (SCCs):
$$\mathcal{C} = \{\text{SCC}_1, \text{SCC}_2, \dots, \text{SCC}_k\}$$
where vertices $u, v \in \text{SCC}_i$ if and only if there exists a directed path from $u$ to $v$ and a directed path from $v$ to $u$.

A circular dependency chain exists if and only if at least one component contains two or more vertices:
$$\text{HasCycle} = \exists C_i \in \mathcal{C} \text{ s.t. } |C_i| > 1$$

The cycle score $D$ is binary:
$$D = \begin{cases} 100.0 & \text{if HasCycle is True} \\ 0.0 & \text{if HasCycle is False} \end{cases}$$

### 3.3 Implementation Reference
- **Engine**: `backend/sim/cycles.py:24-60`
- **Complexity**: $O(V + E)$ linear time depth-first search.

---

## 4. Multi-Factor Composite Change-Risk Formula

### 4.1 Objective
Aggregate the four normalized risk components into a single explainable scalar score $R \in [0.0, 100.0]$ and map it to a deterministic deployment gate verdict.

### 4.2 Mathematical Formulation
$$R = \min\left(100.0, \, \max\left(0.0, \, W_B \cdot B + W_C \cdot C + W_D \cdot D + W_H \cdot H\right)\right)$$

Where the weights $W_i$ are constrained by:
$$\sum_{i \in \{B, C, D, H\}} W_i = 1.0$$

#### Default Policy Weights (`backend/sim/config.py`):
| Term | Symbol | Weight | Focus |
| :--- | :---: | :---: | :--- |
| **Blast Radius** | $B$ | $W_B = 0.35$ | Structural breadth of affected upstream services. |
| **Contract Diff** | $C$ | $W_C = 0.25$ | Breaking API schema and interface modifications. |
| **Dependency Cycles**| $D$ | $W_D = 0.20$ | Introduction of circular runtime deadlock paths. |
| **Historical Incidents**| $H$ | $W_H = 0.20$ | Production incident frequency over the trailing 30 days. |

### 4.3 Historical Penalty Calculation
Given $N_{\text{inc}} = |\text{Incidents}(s, \text{days}=30)|$:
$$H = \min\left(100.0, \, N_{\text{inc}} \times 25.0\right)$$
Each historical incident adds $+25.0$ to $H$, which contributes $+5.0$ points to composite risk ($25.0 \times 0.20 = 5.0$).

### 4.4 Gate Verdict Boundaries
$$\text{Verdict}(R) = \begin{cases} 
\textbf{Approved} & \text{if } R < 40.0 \\ 
\textbf{Warn}     & \text{if } 40.0 \le R < 70.0 \\ 
\textbf{Blocked}  & \text{if } R \ge 70.0 
\end{cases}$$

- **Approved**: Safe additive change with low blast radius; auto-deploy permitted.
- **Warn**: Moderate blast radius or architectural changes; requires peer SRE review.
- **Blocked**: Breaking contract change, circular dependency, or high blast radius; automated release blocked.

### 4.5 Implementation Reference
- **Engine**: `backend/sim/risk.py:59-120`

---

## 5. Actuator Safety Scoring & Gating

### 5.1 Objective
Ensure autonomous remediation proposals are mathematically evaluated for blast safety and historical efficacy before execution.

### 5.2 Mathematical Formulation
For any proposed action $a$ on service $s$:
$$\text{Composite}(a) = 0.60 \cdot \text{SafetyScore}(a, s) + 0.40 \cdot \text{RecoveryProb}(a, f)$$

1. **Safety Score**:
   $$\text{SafetyScore}(a, s) = 100.0 - \text{BlastPenalty}(s) - \text{ActionRisk}(a)$$
   - Low blast services ($\le 2$ callers) receive minimal penalty.
   - Non-destructive actions (`scale_pool`) have an action risk of $5.0$.
   - Service restarts have an action risk of $15.0$.

2. **Execution Threshold**:
   $$\text{Proceed} \iff \text{SafetyScore} \ge 75.0 \land \text{Composite} \ge 70.0$$
   Proposals failing this threshold are marked `refused` and require manual human sign-off.

### 5.3 Implementation Reference
- **Engine**: `backend/executor/scoring.py:20-65`
- **Allowlist Filter**: `backend/executor/allowlist.py:76-120`

---

*All formulas are implemented in active Python modules and verified by unit test suites in `backend/tests/`.*
