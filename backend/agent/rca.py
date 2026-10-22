"""AEGIS Root Cause Analysis (RCA) Diagnostic Engine (M6).

Orchestrates LLM diagnostic reasoning over graph context:
1. Calls LLM with strict system prompt and graph context JSON.
2. Validates output schema against Pydantic v2 RCAResult.
3. Strictly rejects node IDs not present in the graph context.
4. Retries once including the validation error feedback upon failure.
5. Falls back to deterministic rules if validation fails again.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re
from typing import Any

from backend.agent.schemas import RCAResult
from backend.agent.llm import call_llm
from backend.agent.fallback_rules import run_fallback_rules

logger = logging.getLogger("aegis.agent.rca")

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
RCA_SYSTEM_PROMPT_PATH = PROMPTS_DIR / "rca_system.txt"


def load_system_prompt() -> str:
    """Load the RCA system prompt from disk."""
    if RCA_SYSTEM_PROMPT_PATH.exists():
        return RCA_SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    return (
        "You are the AEGIS Root Cause Analysis (RCA) diagnostic engine. "
        "Reason ONLY over the supplied JSON. Cite node IDs verbatim. Never invent services. "
        "Output valid JSON conforming to the RCAResult schema."
    )


def extract_context_node_ids(context: dict[str, Any]) -> set[str]:
    """Extract all valid node IDs explicitly present in the context dictionary."""
    valid_ids: set[str] = set()

    fn = context.get("failing_node")
    if fn:
        valid_ids.add(fn)

    neighbourhood = context.get("neighbourhood_2hop", {})
    for node in neighbourhood.get("nodes", []):
        nid = node.get("id")
        if nid:
            valid_ids.add(nid)

    for edge in neighbourhood.get("edges", []):
        if edge.get("source"):
            valid_ids.add(edge["source"])
        if edge.get("target"):
            valid_ids.add(edge["target"])

    for ds in neighbourhood.get("datastores", []):
        if ds:
            valid_ids.add(ds)

    for c in neighbourhood.get("callers", []):
        if c:
            valid_ids.add(c)

    for c in neighbourhood.get("callees", []):
        if c:
            valid_ids.add(c)

    for k in context.get("telemetry", {}).keys():
        if k:
            valid_ids.add(k)

    return valid_ids


def clean_llm_json(raw_text: str) -> str:
    """Strip markdown code block fences and trailing text to isolate JSON string."""
    text = raw_text.strip()
    # Match ```json ... ``` or ``` ... ```
    fence_pattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
    match = re.search(fence_pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


def validate_rca_result(raw_text: str, valid_node_ids: set[str]) -> RCAResult:
    """Parse and strictly validate raw LLM JSON against schema and graph context.

    Raises:
        ValueError if JSON is malformed, schema validation fails, or node IDs are hallucinated.
    """
    cleaned = clean_llm_json(raw_text)
    result = RCAResult.model_validate_json(cleaned)

    # Validate root_cause_node against graph context
    if result.root_cause_node not in valid_node_ids:
        raise ValueError(
            f"Validation Error: Hallucinated root_cause_node '{result.root_cause_node}' is not in context nodes: {sorted(valid_node_ids)}"
        )

    # Validate propagation_path nodes
    for node in result.propagation_path:
        if node not in valid_node_ids:
            raise ValueError(
                f"Validation Error: Hallucinated node '{node}' in propagation_path is not in context nodes: {sorted(valid_node_ids)}"
            )

    # Validate ranked_fixes target nodes
    for fix in result.ranked_fixes:
        if fix.target not in valid_node_ids:
            raise ValueError(
                f"Validation Error: Hallucinated fix target '{fix.target}' is not in context nodes: {sorted(valid_node_ids)}"
            )

    return result


def diagnose_incident(
    context: dict[str, Any],
    timeout: float = 10.0,
    model_override: str | None = None,
) -> RCAResult:
    """Diagnose an incident from graph context with retry and fallback guarantees.

    Args:
        context: Context dictionary produced by build_context().
        timeout: Timeout per LLM call in seconds.
        model_override: Optional model identifier.

    Returns:
        Guaranteed valid RCAResult.
    """
    valid_node_ids = extract_context_node_ids(context)
    system_prompt = load_system_prompt()
    user_prompt = json.dumps(context, default=str)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Attempt 1: Initial LLM invocation
    raw_response = call_llm(messages, context, timeout=timeout, model_override=model_override)
    first_error_msg: str = ""
    try:
        return validate_rca_result(raw_response, valid_node_ids)
    except Exception as first_error:
        first_error_msg = str(first_error)
        logger.warning(
            f"Initial RCA response failed validation ({first_error_msg}). Retrying once with error feedback."
        )

    # Attempt 2: Retry with validation error feedback included in context
    retry_prompt = (
        f"Validation Error: {first_error_msg}\n"
        "Your previous response violated output requirements or hallucinated nodes not in context.\n"
        f"Allowed node IDs are strictly: {sorted(valid_node_ids)}.\n"
        "Please fix the error and output strictly valid JSON conforming to the schema."
    )
    retry_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
        {"role": "assistant", "content": raw_response},
        {"role": "user", "content": retry_prompt},
    ]

    retry_response = call_llm(retry_messages, context, timeout=timeout, model_override=model_override)
    try:
        return validate_rca_result(retry_response, valid_node_ids)
    except Exception as retry_error:
        logger.warning(
            f"Retry RCA response also failed validation ({retry_error}). Falling back to deterministic rules."
        )

    # Attempt 3: Guaranteed fallback rules engine
    return run_fallback_rules(context)
