"""AEGIS API Schemas & Data Contracts (docs/02-CONTRACTS.md §4 & §5)."""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

from backend.graph.repository import Edge, Node
from backend.sim.contract_diff import ContractDiffResult
from backend.sim.cycles import CycleCheckResult
from backend.sim.risk import RiskBreakdown


# 1. Graph / Topology
class TopologyResponse(BaseModel):
    nodes: list[Node]
    edges: list[Edge]
    total_nodes: int
    total_edges: int


# 2. Simulate PR
class SimulatePRRequest(BaseModel):
    pr_id: Optional[str] = None
    title: Optional[str] = "Proposed Pull Request"
    target_service: str
    project_id: str = "demo"
    author: Optional[str] = "developer@company.com"
    description: Optional[str] = ""
    old_schema: Optional[dict[str, Any]] = None
    new_schema: Optional[dict[str, Any]] = None
    proposed_edges: Optional[list[dict[str, Any]]] = None


class SimulatePRResponse(BaseModel):
    pr_id: str
    target_service: str
    project_id: str = "demo"
    risk_score: float
    verdict: Literal["Approved", "Warn", "Blocked"]
    breakdown: RiskBreakdown
    blast_details: list[dict[str, Any]]
    contract_diff: ContractDiffResult
    cycle_check: CycleCheckResult
    incident_count_30d: int
    recommendation: str
    explanation: list[str]


# 3. Chaos / Fault Injection
class InjectFaultRequest(BaseModel):
    fault_id: str  # pool_exhaustion, pod_crash, cpu_saturation, latency_spike
    target_service: Optional[str] = "paymentservice"
    project_id: str = "demo"
    intensity: Optional[float] = 1.0


class InjectFaultResponse(BaseModel):
    fault_id: str
    target_service: str
    status: str
    message: str
    altered_nodes: list[str]
    applied_telemetry: dict[str, Any]


# 4. SSE Event Envelope (docs/02-CONTRACTS.md §5)
class SSEEventEnvelope(BaseModel):
    type: Literal["thought", "query", "cypher", "result", "candidates", "done", "error"]
    ts: str
    payload: dict[str, Any]


# 5. Actuator Execution (docs/02-CONTRACTS.md §4 & .agent/rules/03-actuator-safety.md)
class ActuatorExecuteRequest(BaseModel):
    action: Literal["restart_pod", "scale_pool", "rollback_release"]
    target: str
    project_id: str = "demo"
    params: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""


class ActuatorExecuteResponse(BaseModel):
    execution_id: str
    action: str
    target: str
    status: Literal["executed", "rolled_back", "rejected"]
    safety_score: float
    message: str
    health_verified: bool


# 6. Memory Commit
class MemoryCommitRequest(BaseModel):
    service_id: str
    incident_description: str
    action_taken: str
    outcome: str = "success"
    safety_score: float = 90.0
    project_id: str = "demo"


class MemoryCommitResponse(BaseModel):
    incident_id: str
    decision_id: str
    service_id: str
    status: str
    message: str
    project_id: str = "demo"


# 7. Reset
class ResetResponse(BaseModel):
    status: str
    message: str
    node_count: int
    edge_count: int
    project_id: str = "demo"

