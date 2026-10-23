"""AEGIS PR Reasoning Schemas.

Pydantic models for the three-stage Cohere Command A reasoning pipeline.
These define the contract between the LLM output and the risk formula inputs.
"""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Stage 1 — Patch Triage
# ---------------------------------------------------------------------------

RiskCategory = Literal["CONTRACT", "BEHAVIORAL", "STRUCTURAL", "SAFE", "SKIP"]


class TriageEntry(BaseModel):
    """Per-file classification output from Stage 1 Triage Prompt."""

    filename: str
    risk_category: RiskCategory
    inferred_service: str = "unknown"
    reason: str = ""


# ---------------------------------------------------------------------------
# Stage 2 — Semantic Contract Analysis
# ---------------------------------------------------------------------------

BreakingChangeType = Literal[
    "FIELD_REMOVED",
    "FIELD_RENAMED",
    "TYPE_CHANGED",
    "ENDPOINT_REMOVED",
    "ENDPOINT_PATH_CHANGED",
    "HTTP_METHOD_CHANGED",
    "REQUIRED_PARAM_ADDED",
    "RETURN_TYPE_CHANGED",
    "SCHEMA_REMOVED",
]


class BreakingChangeEntry(BaseModel):
    """Single breaking change extracted by Stage 2 Semantic Analysis."""

    type: BreakingChangeType
    element: str                  # field name, endpoint path, or method name
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    description: str              # human-readable impact sentence


class ContractAnalysisResult(BaseModel):
    """Stage 2 output: full semantic contract analysis for one changed file."""

    is_breaking: bool
    severity: float = Field(ge=0.0, le=100.0)
    breaking_changes: list[BreakingChangeEntry] = Field(default_factory=list)
    safe_changes: list[str] = Field(default_factory=list)
    affected_endpoints: list[str] = Field(default_factory=list)
    old_schema: dict[str, Any] = Field(default_factory=dict)
    new_schema: dict[str, Any] = Field(default_factory=dict)
    reasoning: str = ""


# ---------------------------------------------------------------------------
# Stage 3 — Blast Path Annotation
# ---------------------------------------------------------------------------

ImpactSeverity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]


class AnnotatedCallerImpact(BaseModel):
    """Per-caller annotated impact from Stage 3 Blast Path Prompt."""

    caller_service: str
    hops: int
    impact_severity: ImpactSeverity
    failure_mode: str             # concrete runtime failure description
    recommended_action: str


# ---------------------------------------------------------------------------
# Final Aggregated Result
# ---------------------------------------------------------------------------


class PRReasoningResult(BaseModel):
    """Aggregated output of all three reasoning stages for one PR."""

    target_service: str
    # Stage 1
    triage_summary: list[TriageEntry] = Field(default_factory=list)
    # Stage 2 (merged across all CONTRACT/BEHAVIORAL files)
    is_breaking: bool = False
    severity: float = 0.0
    all_breaking_changes: list[BreakingChangeEntry] = Field(default_factory=list)
    old_schema: dict[str, Any] = Field(default_factory=dict)
    new_schema: dict[str, Any] = Field(default_factory=dict)
    affected_endpoints: list[str] = Field(default_factory=list)
    llm_reasoning: str = ""
    # Stage 3
    annotated_blast_paths: list[AnnotatedCallerImpact] = Field(default_factory=list)
    # Meta
    fallback_used: bool = False
    files_analyzed: int = 0
    contract_files_found: int = 0
