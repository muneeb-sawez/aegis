"""AEGIS GitHub Commenter Module.

Handles posting and updating PR comments via the GitHub REST API.
Identifies existing AEGIS assessment comments using a hidden HTML marker
and performs a PATCH update instead of creating duplicate comments.
"""

from typing import Optional
import httpx
from backend.config import settings

AEGIS_COMMENT_MARKER = "<!-- aegis-risk-report -->"


def format_risk_comment(
    pr_number: int,
    target_service: str,
    risk_score: float,
    blast_radius: list[str],
    breaking_changes: Optional[list[str]] = None,
    annotated_blast_paths: Optional[list[dict]] = None,
    llm_reasoning: Optional[str] = None,
    triage_summary: Optional[list[dict]] = None,
    fallback_used: bool = True,
    project_id: str = "demo",
) -> str:
    """Render a rich, intelligent Markdown risk report for a pull request.

    Includes LLM-extracted breaking change details, annotated blast paths,
    and a chain-of-thought reasoning block from Cohere Command A.
    """
    if risk_score >= 80:
        risk_badge = "🔴 **CRITICAL RISK — BLOCKED**"
    elif risk_score >= 70:
        risk_badge = "🔴 **HIGH RISK — BLOCKED**"
    elif risk_score >= 50:
        risk_badge = "🟡 **ELEVATED RISK — WARN**"
    else:
        risk_badge = "🟢 **LOW RISK — APPROVED**"

    breaking = breaking_changes or []
    breaking_summary = (
        f"🚨 **{len(breaking)} breaking change(s) detected**"
        if breaking
        else "✅ No breaking changes detected"
    )

    blast_str = ", ".join(f"`{s}`" for s in blast_radius) if blast_radius else "*None (leaf service)*"

    lines = [
        AEGIS_COMMENT_MARKER,
        f"## 🛡️ AEGIS Change Risk Assessment — PR #{pr_number}",
        "",
        f"**Project**: `{project_id}` | **Status**: {risk_badge}",
        "",
        "| Attribute | Value |",
        "| :--- | :--- |",
        f"| **Target Service** | `{target_service}` |",
        f"| **Predicted Risk Score** | **{risk_score:.1f} / 100** |",
        f"| **Blast Radius ({len(blast_radius)} service(s))** | {blast_str} |",
        f"| **Contract Compatibility** | {breaking_summary} |",
        f"| **Analysis Engine** | {'🤖 Cohere Command A (OCI)' if not fallback_used else '⚙️ Deterministic Fallback'} |",
    ]

    # Breaking changes section
    if breaking:
        lines += ["", "### 🚨 Detected Breaking Changes"]
        for change in breaking:
            lines.append(f"- ⚠️ {change}")

    # Annotated blast path table (from Stage 3 LLM output)
    if annotated_blast_paths:
        lines += ["", "### 💥 Upstream Caller Impact Analysis"]
        lines += [
            "| Caller Service | Hops | Severity | Failure Mode |",
            "| :--- | :---: | :---: | :--- |",
        ]
        severity_icons = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}
        for path in annotated_blast_paths:
            svc = path.get("caller_service", "?")
            hops = path.get("hops", "?")
            sev = path.get("impact_severity", "HIGH")
            icon = severity_icons.get(sev, "🟡")
            failure = path.get("failure_mode", "Impact unknown")
            lines.append(f"| `{svc}` | {hops} | {icon} {sev} | {failure} |")

    # LLM chain-of-thought reasoning block
    if llm_reasoning:
        lines += ["", "### 🤖 AI Reasoning (Cohere Command A)"]
        for part in llm_reasoning.split("\n\n"):
            if part.strip():
                lines.append(f"> {part.strip()}")

    # Triage summary (which files were analyzed)
    if triage_summary:
        contract_files = [
            t for t in triage_summary
            if t.get("risk_category") in ("CONTRACT", "BEHAVIORAL")
        ]
        if contract_files:
            lines += ["", "### 🔍 Files Analyzed"]
            for t in contract_files[:5]:  # show up to 5
                cat = t.get("risk_category", "?")
                fn = t.get("filename", "?").split("/")[-1]
                svc = t.get("inferred_service", "unknown")
                lines.append(f"- `{fn}` — **{cat}** (service: `{svc}`)")

    lines += [
        "",
        "> ℹ️ *Risk score computed by AEGIS: 0.35·Blast + 0.30·Contract + 0.15·Cycle + 0.20·History*",
        f"<!-- updated_at: pr_{pr_number} -->",
    ]

    return "\n".join(lines)


async def get_existing_comment_id(
    owner: str,
    repo: str,
    pr_number: int,
    token: Optional[str] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> Optional[int]:
    """Search existing PR/issue comments for the AEGIS risk report marker."""
    auth_token = token or settings.GITHUB_TOKEN
    if not auth_token:
        return None

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {auth_token}",
        "User-Agent": "AEGIS-Risk-Bot/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=10.0)
        should_close = True

    try:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 200:
            comments = resp.json()
            if isinstance(comments, list):
                for c in comments:
                    if isinstance(c, dict) and AEGIS_COMMENT_MARKER in c.get("body", ""):
                        return c.get("id")
        return None
    finally:
        if should_close:
            await client.aclose()


async def post_or_update_pr_comment(
    owner: str,
    repo: str,
    pr_number: int,
    comment_body: str,
    token: Optional[str] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> dict:
    """Post a new comment or update existing one on a GitHub Pull Request."""
    auth_token = token or settings.GITHUB_TOKEN
    if not auth_token:
        return {
            "status": "skipped",
            "action": "skipped_no_token",
            "message": "GITHUB_TOKEN not configured; skipped GitHub REST comment.",
        }

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {auth_token}",
        "User-Agent": "AEGIS-Risk-Bot/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=10.0)
        should_close = True

    try:
        # Check if a comment already exists
        existing_id = await get_existing_comment_id(owner, repo, pr_number, token=auth_token, client=client)

        if existing_id:
            # PATCH existing comment
            patch_url = f"https://api.github.com/repos/{owner}/{repo}/issues/comments/{existing_id}"
            resp = await client.patch(patch_url, headers=headers, json={"body": comment_body})
            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    "status": "updated",
                    "action": "patched",
                    "comment_id": existing_id,
                    "html_url": data.get("html_url", ""),
                }
            return {
                "status": "error",
                "action": "patch_failed",
                "status_code": resp.status_code,
                "error": resp.text,
            }
        else:
            # POST new comment
            post_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
            resp = await client.post(post_url, headers=headers, json={"body": comment_body})
            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    "status": "created",
                    "action": "posted",
                    "comment_id": data.get("id"),
                    "html_url": data.get("html_url", ""),
                }
            return {
                "status": "error",
                "action": "post_failed",
                "status_code": resp.status_code,
                "error": resp.text,
            }
    finally:
        if should_close:
            await client.aclose()
