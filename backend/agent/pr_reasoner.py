"""AEGIS PR Reasoning Brain — Cohere Command A on OCI Generative AI.

Implements a three-stage sequential LLM prompt pipeline that transforms a raw
GitHub Pull Request git diff into a fully structured, evidence-backed risk assessment.

Stage 1 — Patch Triage:
    Classifies every changed file into CONTRACT | BEHAVIORAL | STRUCTURAL | SAFE | SKIP.

Stage 2 — Semantic Contract Analysis:
    For each CONTRACT/BEHAVIORAL file, extracts exactly what broke (removed fields,
    changed endpoints, altered types) and builds old_schema / new_schema dynamically.

Stage 3 — Blast Path Annotation:
    Annotates the graph-derived upstream callers with specific, per-caller failure modes
    and recommended actions.

The fallback chain ensures the system is never fully blind:
    Cohere OCI → Regex-based AST scanner → Safe (no-break) assumption.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import httpx

from backend.agent.pr_schemas import (
    AnnotatedCallerImpact,
    BreakingChangeEntry,
    ContractAnalysisResult,
    PRReasoningResult,
    TriageEntry,
)
from backend.config import settings

# Import FileDiff directly from its module (NOT via backend.webhooks package)
# to avoid triggering backend/webhooks/__init__.py which imports processor.py
# which would create a circular import chain.
from backend.webhooks.git_diff_analyzer import FileDiff

logger = logging.getLogger("aegis.agent.pr_reasoner")

# ---------------------------------------------------------------------------
# OCI Cohere Client Factory
# ---------------------------------------------------------------------------

_oci_genai_client = None

def _get_oci_client():
    """Build and cache the OCI GenerativeAiInferenceClient."""
    global _oci_genai_client
    if _oci_genai_client is not None:
        return _oci_genai_client

    try:
        import os
        import oci
        from oci.generative_ai_inference import GenerativeAiInferenceClient

        config_path = os.path.expanduser(settings.OCI_CONFIG_FILE or "~/.oci/config")
        config = oci.config.from_file(config_path, settings.OCI_PROFILE or "DEFAULT")
        _oci_genai_client = GenerativeAiInferenceClient(config=config)
        logger.info("OCI_GENAI_CLIENT_INITIALIZED profile=%r", settings.OCI_PROFILE)
        return _oci_genai_client
    except Exception as exc:
        logger.warning("OCI_CLIENT_BUILD_FAILED: %s", exc)
        return None


def _call_cohere_oci(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.0,
) -> Optional[str]:
    """Send a chat request to Cohere Command A on OCI Generative AI.

    Uses OCI's GenerativeAiInferenceClient with CohereChatRequest.
    Temperature=0.0 ensures deterministic, reproducible analysis.
    Returns the raw response text, or None on failure.
    """
    if not settings.OCI_ENABLED or not settings.OCI_COMPARTMENT_ID:
        logger.debug("OCI_NOT_ENABLED — skipping Cohere OCI call")
        return None

    client = _get_oci_client()
    if client is None:
        return None

    try:
        from oci.generative_ai_inference.models import (
            ChatDetails,
            CohereChatRequest,
            OnDemandServingMode,
        )

        cohere_request = CohereChatRequest(
            message=user_prompt,
            preamble_override=system_prompt,
            max_tokens=4000,
            temperature=temperature,
        )

        chat_details = ChatDetails(
            compartment_id=settings.OCI_COMPARTMENT_ID,
            serving_mode=OnDemandServingMode(model_id=settings.OCI_MODEL_ID),
            chat_request=cohere_request,
        )

        logger.info("CALLING_OCI_COHERE model=%r", settings.OCI_MODEL_ID)
        response = client.chat(chat_details)
        chat_resp = getattr(response.data, "chat_response", None)
        text = getattr(chat_resp, "text", "") or ""
        logger.debug("OCI_COHERE_RAW_RESPONSE (first 300 chars): %s", text[:300])
        return text.strip() if text else None
    except Exception as exc:
        logger.warning("OCI_COHERE_CALL_FAILED: %s", exc)
        return None


def _parse_json_response(raw: Optional[str], context: str = "") -> Any:
    """Safely extract and parse a JSON payload from LLM output.

    Handles common LLM formatting issues:
    - Markdown code fences (```json ... ```)
    - Leading/trailing prose text
    - Truncated responses
    """
    if not raw:
        return None
    # Strip markdown fences
    text = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
    # Find the first valid JSON structure
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
    logger.warning("JSON_PARSE_FAILED context=%r raw_snippet=%r", context, raw[:200])
    return None


# ---------------------------------------------------------------------------
# Stage 1 — Patch Triage
# ---------------------------------------------------------------------------

_TRIAGE_SYSTEM = """You are an autonomous SRE and API safety classifier working on a Java Spring Boot
microservices codebase. Your job is to triage changed files in a Pull Request and classify
the risk category of each file strictly based on the evidence in its diff.

Do not make assumptions. Use only the diff content provided.
Return ONLY a valid JSON array. No markdown, no explanation, no extra text.

Risk category definitions:
- CONTRACT: A public REST controller, DTO response/request class, or OpenAPI schema was changed.
  This is the highest risk — callers depend on these contracts.
- BEHAVIORAL: Business logic, service layer, or repository query changed in a way that may
  alter runtime behavior without changing the API surface.
- STRUCTURAL: Infrastructure, configuration (application.yml, pom.xml, Dockerfile), or
  dependency changed.
- SAFE: Test files, documentation, formatting-only changes, comment-only changes.
- SKIP: Binary assets, generated files, lock files, .gitignore."""

_TRIAGE_USER_TEMPLATE = """Below is the raw unified diff for PR #{pr_number} on repository '{repo}'.

Changed files:
{file_diffs_json}

Each entry has: filename, status, patch (unified diff text — may be null for binary files).

For EACH changed file, return one JSON object with these exact keys:
- "filename": string (exact filename from input)
- "risk_category": one of ["CONTRACT", "BEHAVIORAL", "STRUCTURAL", "SAFE", "SKIP"]
- "inferred_service": string (e.g. "customers-service", "vets-service", or "unknown")
- "reason": string (one sentence explaining why you assigned this category)

Return ONLY the JSON array. No other text."""


def _stage1_triage(
    file_diffs: list[FileDiff],
    pr_number: int,
    repo: str,
) -> list[TriageEntry]:
    """Run Stage 1: classify every changed file by risk category."""
    # Build compact input (truncate very large patches to keep prompt size reasonable)
    input_files = []
    for fd in file_diffs:
        patch_preview = fd.patch[:3000] if fd.patch else None
        input_files.append({
            "filename": fd.filename,
            "status": fd.status,
            "patch": patch_preview,
        })

    user_prompt = _TRIAGE_USER_TEMPLATE.format(
        pr_number=pr_number,
        repo=repo,
        file_diffs_json=json.dumps(input_files, indent=2),
    )

    raw = _call_cohere_oci(_TRIAGE_SYSTEM, user_prompt, temperature=0.0)
    data = _parse_json_response(raw, context="stage1_triage")

    if isinstance(data, list):
        entries = []
        for item in data:
            if isinstance(item, dict):
                try:
                    entries.append(TriageEntry(**{k: item.get(k, "") for k in TriageEntry.model_fields}))
                except Exception:
                    pass
        if entries:
            return entries

    # Fallback: basic regex heuristics if LLM unavailable
    logger.info("STAGE1_FALLBACK: using regex heuristics")
    return _fallback_triage(file_diffs)


def _fallback_triage(file_diffs: list[FileDiff]) -> list[TriageEntry]:
    """Regex-based file triage when Cohere is unavailable."""
    CONTRACT_PATTERNS = re.compile(
        r"@(RestController|GetMapping|PostMapping|PutMapping|DeleteMapping|"
        r"RequestMapping|ResponseBody|PathVariable|RequestBody)",
        re.IGNORECASE,
    )
    DTO_PATTERNS = re.compile(
        r"(Request|Response|Dto|DTO|Model|Entity|Resource)\.(java|kt)$",
        re.IGNORECASE,
    )
    SERVICE_PARTS = [
        "customers-service", "visits-service", "vets-service",
        "api-gateway", "config-server", "discovery-server",
        "admin-server", "tracing-server",
    ]

    results = []
    for fd in file_diffs:
        fn = fd.filename
        patch = fd.patch or ""

        # Infer service from path
        inferred = "unknown"
        for svc in SERVICE_PARTS:
            if svc in fn or svc.replace("-", "") in fn.lower():
                inferred = svc
                break

        # Skip non-code files
        if fn.endswith((".md", ".txt", ".png", ".jpg", ".svg", ".gitignore",
                        ".lock", ".sum", "package-lock.json")):
            results.append(TriageEntry(
                filename=fn, risk_category="SKIP",
                inferred_service=inferred, reason="Non-code file",
            ))
            continue

        # Test files
        if "test" in fn.lower() or "Test." in fn or "Spec." in fn:
            results.append(TriageEntry(
                filename=fn, risk_category="SAFE",
                inferred_service=inferred, reason="Test file",
            ))
            continue

        # Controller / REST annotations in diff
        if CONTRACT_PATTERNS.search(patch) or DTO_PATTERNS.search(fn):
            results.append(TriageEntry(
                filename=fn, risk_category="CONTRACT",
                inferred_service=inferred,
                reason="Contains REST controller annotations or DTO class modifications",
            ))
            continue

        # Config files
        if fn.endswith((".yml", ".yaml", ".xml", "Dockerfile", ".properties")):
            results.append(TriageEntry(
                filename=fn, risk_category="STRUCTURAL",
                inferred_service=inferred, reason="Infrastructure/configuration file",
            ))
            continue

        # Default: behavioral
        results.append(TriageEntry(
            filename=fn, risk_category="BEHAVIORAL",
            inferred_service=inferred, reason="Source code change with unknown API impact",
        ))

    return results


# ---------------------------------------------------------------------------
# Stage 2 — Semantic Contract Analysis
# ---------------------------------------------------------------------------

_CONTRACT_SYSTEM = """You are an expert API backward-compatibility auditor. You analyze raw Git diffs of
Java Spring Boot services and determine whether changes break the public API contract that
upstream consumers (callers) depend on.

Breaking changes include but are not limited to:
1. Removal of a public field from a Response DTO or domain model.
2. Renaming a field (callers using the old name will fail to deserialize).
3. Changing the type of a field (e.g., int -> String, Long -> UUID).
4. Removing a REST endpoint entirely (@GetMapping, @PostMapping, @PutMapping, @DeleteMapping).
5. Changing an endpoint's HTTP path (callers using old URL will get 404).
6. Changing an endpoint's HTTP method (GET -> POST breaks all clients).
7. Adding a new required/non-nullable request parameter to an existing endpoint.
8. Changing a method's return type in a way that alters JSON serialization structure.

Safe (non-breaking) changes include:
- Adding a new optional field to a response.
- Adding a brand-new endpoint (additive, no existing caller breaks).
- Internal implementation refactoring with no change to method signatures or field names.
- Fixing a bug without changing the public interface.

Respond ONLY with a valid JSON object matching the schema below. No markdown, no extra text."""

_CONTRACT_USER_TEMPLATE = """File: {filename}
Inferred service: {inferred_service}

Raw unified diff:
{patch_text}

Analyze this diff and return a JSON object with these exact keys:
- "is_breaking": boolean
- "severity": float 0.0-100.0 (100.0 = definite runtime failures for existing consumers, 0.0 = fully safe)
- "breaking_changes": list of objects, each:
    - "type": one of ["FIELD_REMOVED","FIELD_RENAMED","TYPE_CHANGED","ENDPOINT_REMOVED",
               "ENDPOINT_PATH_CHANGED","HTTP_METHOD_CHANGED","REQUIRED_PARAM_ADDED",
               "RETURN_TYPE_CHANGED","SCHEMA_REMOVED"]
    - "element": string (field/endpoint/method name)
    - "old_value": string or null
    - "new_value": string or null
    - "description": string (one sentence — exact consumer impact)
- "safe_changes": list of strings
- "affected_endpoints": list of strings (HTTP paths)
- "old_schema": dict (field_name -> {{"type": "..."}}) from removed/modified '-' diff lines
- "new_schema": dict (field_name -> {{"type": "..."}}) from added/modified '+' diff lines
- "reasoning": string (2-3 sentence chain-of-thought)

Return ONLY the JSON object."""


def _stage2_contract_analysis(
    fd: FileDiff,
    triage: TriageEntry,
) -> Optional[ContractAnalysisResult]:
    """Run Stage 2: deep semantic contract analysis on one CONTRACT/BEHAVIORAL file."""
    if not fd.patch:
        return None

    user_prompt = _CONTRACT_USER_TEMPLATE.format(
        filename=fd.filename,
        inferred_service=triage.inferred_service,
        patch_text=fd.patch[:6000],   # cap at 6k chars (~1500 tokens)
    )

    raw = _call_cohere_oci(_CONTRACT_SYSTEM, user_prompt, temperature=0.0)
    data = _parse_json_response(raw, context=f"stage2:{fd.filename}")

    if isinstance(data, dict):
        try:
            breaking = [
                BreakingChangeEntry(**bc)
                for bc in data.get("breaking_changes", [])
                if isinstance(bc, dict)
            ]
            return ContractAnalysisResult(
                is_breaking=bool(data.get("is_breaking", False)),
                severity=float(data.get("severity", 0.0)),
                breaking_changes=breaking,
                safe_changes=data.get("safe_changes", []),
                affected_endpoints=data.get("affected_endpoints", []),
                old_schema=data.get("old_schema", {}),
                new_schema=data.get("new_schema", {}),
                reasoning=data.get("reasoning", ""),
            )
        except Exception as exc:
            logger.warning("STAGE2_PARSE_ERROR file=%r error=%s", fd.filename, exc)

    # Fallback: regex-based extraction
    logger.info("STAGE2_FALLBACK for file=%r", fd.filename)
    return _fallback_contract_analysis(fd)


def _fallback_contract_analysis(fd: FileDiff) -> ContractAnalysisResult:
    """Regex-based breaking change detector when Cohere is unavailable."""
    patch = fd.patch or ""
    removed_lines = [l[1:].strip() for l in patch.splitlines() if l.startswith("-") and not l.startswith("---")]
    added_lines = [l[1:].strip() for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++")]

    breaking: list[BreakingChangeEntry] = []
    old_schema: dict[str, Any] = {}
    new_schema: dict[str, Any] = {}

    # Detect removed fields: "private String/int/Long/boolean fieldName;"
    field_pattern = re.compile(r"private\s+(\w+)\s+(\w+)\s*;")
    annotation_pattern = re.compile(r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)\s*\("?([^")\s]+)"?\)')

    removed_fields = {m.group(2): m.group(1) for line in removed_lines for m in [field_pattern.search(line)] if m}
    added_fields = {m.group(2): m.group(1) for line in added_lines for m in [field_pattern.search(line)] if m}

    for fname, ftype in removed_fields.items():
        old_schema[fname] = {"type": ftype}
        if fname not in added_fields:
            breaking.append(BreakingChangeEntry(
                type="FIELD_REMOVED", element=fname,
                old_value=ftype, new_value=None,
                description=f"Field '{fname}' (type: {ftype}) was removed from the API contract",
            ))
        elif added_fields[fname] != ftype:
            new_schema[fname] = {"type": added_fields[fname]}
            breaking.append(BreakingChangeEntry(
                type="TYPE_CHANGED", element=fname,
                old_value=ftype, new_value=added_fields[fname],
                description=f"Field '{fname}' changed type from {ftype} to {added_fields[fname]}",
            ))

    for fname, ftype in added_fields.items():
        new_schema[fname] = {"type": ftype}

    # Detect changed endpoint paths
    removed_mappings = {m.group(2): m.group(1) for line in removed_lines for m in [annotation_pattern.search(line)] if m}
    added_mappings = {m.group(2): m.group(1) for line in added_lines for m in [annotation_pattern.search(line)] if m}

    for path, method in removed_mappings.items():
        if path not in added_mappings:
            breaking.append(BreakingChangeEntry(
                type="ENDPOINT_REMOVED", element=path,
                old_value=f"{method}({path})", new_value=None,
                description=f"Endpoint {method}('{path}') was removed; all callers will receive 404",
            ))

    is_breaking = bool(breaking)
    severity = 100.0 if is_breaking else 0.0

    return ContractAnalysisResult(
        is_breaking=is_breaking,
        severity=severity,
        breaking_changes=breaking,
        safe_changes=[],
        affected_endpoints=list(removed_mappings.keys()),
        old_schema=old_schema,
        new_schema=new_schema,
        reasoning="Analyzed via deterministic regex fallback (Cohere OCI unavailable).",
    )


# ---------------------------------------------------------------------------
# Stage 3 — Blast Path Annotation
# ---------------------------------------------------------------------------

_BLAST_SYSTEM = """You are an SRE incident impact analyst specializing in microservice blast radius assessment.
You receive a list of breaking API changes and the list of upstream services that call the changed service.
Your job is to explain, in plain English, exactly HOW each upstream caller will be impacted at runtime.

Be specific. Reference the exact changed field or endpoint. Do not be generic.
Respond ONLY with a valid JSON array. No markdown, no other text."""

_BLAST_USER_TEMPLATE = """The following breaking changes were detected in service '{target_service}':
{breaking_changes_json}

The following upstream services (callers) depend on '{target_service}':
{caller_list_json}
Each entry has: node (service name), hops (1 = direct caller), impact_weight (0.0-1.0)

For EACH caller, return a JSON object with:
- "caller_service": string
- "hops": integer
- "impact_severity": one of ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
- "failure_mode": string (one sentence: exact runtime error or behavior this caller will experience)
- "recommended_action": string (one actionable sentence for the PR author)

Return ONLY the JSON array."""


def _stage3_blast_annotation(
    target_service: str,
    breaking_changes: list[BreakingChangeEntry],
    graph_callers: list[dict],
) -> list[AnnotatedCallerImpact]:
    """Run Stage 3: annotate each graph caller with specific failure modes."""
    if not breaking_changes or not graph_callers:
        return []

    user_prompt = _BLAST_USER_TEMPLATE.format(
        target_service=target_service,
        breaking_changes_json=json.dumps(
            [bc.model_dump() for bc in breaking_changes], indent=2
        ),
        caller_list_json=json.dumps(graph_callers, indent=2),
    )

    raw = _call_cohere_oci(_BLAST_SYSTEM, user_prompt, temperature=0.0)
    data = _parse_json_response(raw, context="stage3_blast")

    if isinstance(data, list):
        results = []
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                results.append(AnnotatedCallerImpact(
                    caller_service=item.get("caller_service", "unknown"),
                    hops=int(item.get("hops", 1)),
                    impact_severity=item.get("impact_severity", "HIGH"),
                    failure_mode=item.get("failure_mode", "Consumer may experience runtime errors."),
                    recommended_action=item.get("recommended_action", "Review consumer code before merging."),
                ))
            except Exception:
                pass
        if results:
            return results

    # Fallback: generic annotation from graph data
    logger.info("STAGE3_FALLBACK: using generic blast annotations")
    return _fallback_blast_annotation(target_service, breaking_changes, graph_callers)


def _fallback_blast_annotation(
    target_service: str,
    breaking_changes: list[BreakingChangeEntry],
    graph_callers: list[dict],
) -> list[AnnotatedCallerImpact]:
    """Generate generic but structurally correct blast annotations without LLM."""
    results = []
    for caller in graph_callers:
        node = caller.get("node", "unknown")
        hops = int(caller.get("hops", 1))
        weight = float(caller.get("impact_weight", 0.5))
        severity = "CRITICAL" if weight >= 0.8 else "HIGH" if weight >= 0.5 else "MEDIUM"

        change_summary = "; ".join(bc.description for bc in breaking_changes[:2])
        results.append(AnnotatedCallerImpact(
            caller_service=node,
            hops=hops,
            impact_severity=severity,
            failure_mode=f"Service '{node}' depends on '{target_service}' and will be affected by: {change_summary}",
            recommended_action=f"Audit '{node}' for usage of changed fields/endpoints before merging this PR.",
        ))
    return results


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------

async def reason_about_pr(
    file_diffs: list[FileDiff],
    pr_number: int,
    repo: str,
    target_service: str,
    graph_callers: list[dict],
    client: Optional[httpx.AsyncClient] = None,
) -> PRReasoningResult:
    """Orchestrate all three reasoning stages for a GitHub Pull Request.

    Args:
        file_diffs:     Raw FileDiff list from git_diff_analyzer.fetch_pr_file_diffs().
        pr_number:      GitHub PR number.
        repo:           Repository full name (owner/repo).
        target_service: The primary microservice being changed (inferred from file paths).
        graph_callers:  Caller list from blast_radius.calculate_blast_radius().
        client:         Optional shared httpx client (unused here, kept for API consistency).

    Returns:
        PRReasoningResult containing old_schema, new_schema, all breaking changes,
        and annotated blast paths — ready for assess_change_risk().
    """
    logger.info(
        "PR_REASONING_START pr=%d repo=%r service=%r files=%d",
        pr_number, repo, target_service, len(file_diffs),
    )
    fallback_used = not (settings.OCI_ENABLED and settings.OCI_COMPARTMENT_ID)

    # -----------------------------------------------------------------------
    # Stage 1 — Triage all changed files
    # -----------------------------------------------------------------------
    triage_entries = _stage1_triage(file_diffs, pr_number, repo)

    # Build filename -> triage lookup for Stage 2
    triage_map = {e.filename: e for e in triage_entries}

    # Filter files that need deep analysis
    deep_analysis_files = [
        fd for fd in file_diffs
        if triage_map.get(fd.filename, TriageEntry(
            filename=fd.filename, risk_category="SKIP"
        )).risk_category in ("CONTRACT", "BEHAVIORAL")
        and fd.patch
    ]

    logger.info(
        "TRIAGE_DONE total=%d deep_analysis=%d",
        len(triage_entries), len(deep_analysis_files),
    )

    # -----------------------------------------------------------------------
    # Stage 2 — Contract analysis on each high-risk file
    # -----------------------------------------------------------------------
    merged_breaking: list[BreakingChangeEntry] = []
    merged_old_schema: dict[str, Any] = {}
    merged_new_schema: dict[str, Any] = {}
    merged_endpoints: list[str] = []
    merged_reasoning_parts: list[str] = []
    is_breaking = False
    max_severity = 0.0

    # Infer target service from triage if not already known
    inferred_svc = target_service
    for entry in triage_entries:
        if entry.inferred_service != "unknown" and entry.risk_category in ("CONTRACT", "BEHAVIORAL"):
            inferred_svc = entry.inferred_service
            break

    for fd in deep_analysis_files:
        triage = triage_map.get(fd.filename, TriageEntry(
            filename=fd.filename, risk_category="BEHAVIORAL",
            inferred_service=inferred_svc,
        ))
        result = _stage2_contract_analysis(fd, triage)
        if result is None:
            continue
        if result.is_breaking:
            is_breaking = True
        max_severity = max(max_severity, result.severity)
        merged_breaking.extend(result.breaking_changes)
        merged_old_schema.update(result.old_schema)
        merged_new_schema.update(result.new_schema)
        merged_endpoints.extend(result.affected_endpoints)
        if result.reasoning:
            merged_reasoning_parts.append(f"[{fd.filename}] {result.reasoning}")

    logger.info(
        "CONTRACT_ANALYSIS_DONE breaking=%s severity=%.1f changes=%d",
        is_breaking, max_severity, len(merged_breaking),
    )

    # -----------------------------------------------------------------------
    # Stage 3 — Blast path annotation
    # -----------------------------------------------------------------------
    annotated_paths: list[AnnotatedCallerImpact] = []
    if is_breaking and graph_callers:
        annotated_paths = _stage3_blast_annotation(
            inferred_svc, merged_breaking, graph_callers
        )

    return PRReasoningResult(
        target_service=inferred_svc,
        triage_summary=triage_entries,
        is_breaking=is_breaking,
        severity=max_severity,
        all_breaking_changes=merged_breaking,
        old_schema=merged_old_schema,
        new_schema=merged_new_schema,
        affected_endpoints=list(set(merged_endpoints)),
        llm_reasoning="\n\n".join(merged_reasoning_parts),
        annotated_blast_paths=annotated_paths,
        fallback_used=fallback_used,
        files_analyzed=len(file_diffs),
        contract_files_found=len(deep_analysis_files),
    )
