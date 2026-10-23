"""AEGIS Dynamic PR Generator — Live Examiner Demonstration Engine.

Creates REAL Pull Requests on FawazMulla/spring-petclinic-microservices
by fetching the CURRENT file contents from GitHub, applying a programmatic
mutation (not a hardcoded diff), committing, and opening a PR.

The mutation engine picks from the live file content — so each PR is unique,
and the git diff AEGIS receives is a genuine change the brain has never seen.

Usage:
    # Let the engine auto-select a service and mutation:
    python scripts/raise_pr.py --auto-break

    # Target a specific service:
    python scripts/raise_pr.py --service customers-service

    # Safe/additive change (proves AEGIS approves non-breaking PRs):
    python scripts/raise_pr.py --safe

    # Raise another PR immediately (examiner says "do it again"):
    python scripts/raise_pr.py --auto-break
"""

from __future__ import annotations

import argparse
import base64
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

# ─── Load token from data/github_auth.json ────────────────────────────────────

def load_github_token() -> str:
    """Load the FawazMulla GitHub token from AEGIS auth store."""
    auth_path = Path(__file__).resolve().parent.parent / "data" / "github_auth.json"
    with open(auth_path, "r", encoding="utf-8") as f:
        auth = json.load(f)
    for session in auth.get("sessions", {}).values():
        token = session.get("github_access_token")
        user = session.get("user", {})
        if token and user.get("username") == "FawazMulla":
            return token
    raise RuntimeError("FawazMulla GitHub token not found in data/github_auth.json")


OWNER = "FawazMulla"
REPO = "spring-petclinic-microservices"
BASE_BRANCH = "main"


# ─── GitHub API Helpers ────────────────────────────────────────────────────────

def github_headers(token: str) -> dict:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "AEGIS-PR-Engine/2.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_branch_sha(token: str, branch: str = BASE_BRANCH) -> str:
    """Get the latest commit SHA on a branch."""
    r = httpx.get(
        f"https://api.github.com/repos/{OWNER}/{REPO}/git/ref/heads/{branch}",
        headers=github_headers(token),
    )
    r.raise_for_status()
    return r.json()["object"]["sha"]


def create_branch(token: str, branch_name: str, from_sha: str) -> None:
    """Create a new branch from a given commit SHA."""
    r = httpx.post(
        f"https://api.github.com/repos/{OWNER}/{REPO}/git/refs",
        headers=github_headers(token),
        json={"ref": f"refs/heads/{branch_name}", "sha": from_sha},
    )
    if r.status_code == 422:
        print(f"  ↳ Branch '{branch_name}' already exists — reusing.")
    else:
        r.raise_for_status()


def get_file(token: str, file_path: str, branch: str = BASE_BRANCH) -> tuple[str, str]:
    """Fetch a file's raw content and SHA from GitHub. Returns (content, sha)."""
    r = httpx.get(
        f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{file_path}",
        headers=github_headers(token),
        params={"ref": branch},
    )
    r.raise_for_status()
    data = r.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content, data["sha"]


def commit_file(
    token: str,
    file_path: str,
    new_content: str,
    file_sha: str,
    branch: str,
    commit_message: str,
) -> None:
    """Commit a modified file to a branch."""
    encoded = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
    r = httpx.put(
        f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{file_path}",
        headers=github_headers(token),
        json={
            "message": commit_message,
            "content": encoded,
            "sha": file_sha,
            "branch": branch,
        },
    )
    r.raise_for_status()


def open_pull_request(token: str, branch: str, title: str, body: str) -> dict:
    """Open a Pull Request from branch -> main."""
    r = httpx.post(
        f"https://api.github.com/repos/{OWNER}/{REPO}/pulls",
        headers=github_headers(token),
        json={
            "title": title,
            "body": body,
            "head": branch,
            "base": BASE_BRANCH,
        },
    )
    r.raise_for_status()
    return r.json()


# ─── Catalog of Target Files ───────────────────────────────────────────────────
# Each entry maps a service name to its primary Java source file path.
# This is NOT a hardcoded mutation list — it's only a list of FILES to look at.
# The actual mutation is derived dynamically from the live file content.

SERVICE_FILES = {
    "customers-service": [
        "spring-petclinic-customers-service/src/main/java/org/springframework/samples/petclinic/customers/model/Owner.java",
        "spring-petclinic-customers-service/src/main/java/org/springframework/samples/petclinic/customers/model/Pet.java",
        "spring-petclinic-customers-service/src/main/java/org/springframework/samples/petclinic/customers/web/OwnerResource.java",
    ],
    "visits-service": [
        "spring-petclinic-visits-service/src/main/java/org/springframework/samples/petclinic/visits/model/Visit.java",
        "spring-petclinic-visits-service/src/main/java/org/springframework/samples/petclinic/visits/web/VisitResource.java",
    ],
    "vets-service": [
        "spring-petclinic-vets-service/src/main/java/org/springframework/samples/petclinic/vets/model/Vet.java",
        "spring-petclinic-vets-service/src/main/java/org/springframework/samples/petclinic/vets/web/VetResource.java",
    ],
}


# ─── Dynamic Mutation Engine ───────────────────────────────────────────────────

def _find_removable_field(content: str) -> Optional[tuple[str, str]]:
    """Find a private field in Java source that can be safely removed for demo.

    Returns (field_name, full_line) if found, else None.
    Avoids removing 'id' fields (would break persistence).
    """
    pattern = re.compile(r"^\s*(private\s+(?:String|int|Integer|Long|boolean|Boolean)\s+(\w+)\s*;)", re.MULTILINE)
    matches = [(m.group(1).strip(), m.group(2)) for m in pattern.finditer(content)]
    # Filter out 'id' and very short names (likely internal)
    candidates = [(line, name) for line, name in matches if name.lower() not in ("id", "new", "version")]
    return random.choice(candidates) if candidates else None


def _find_mapping_annotation(content: str) -> Optional[tuple[str, str]]:
    """Find a @GetMapping / @PostMapping annotation to alter its path."""
    pattern = re.compile(r'(@(?:GetMapping|PostMapping|PutMapping|DeleteMapping)\s*\(\s*"?)(/[^"\s)]+)("?\s*\))')
    match = pattern.search(content)
    if match:
        return match.group(0), match.group(2)
    return None


def apply_breaking_mutation(content: str, service: str) -> tuple[str, str, str]:
    """Apply a dynamic breaking mutation to file content.

    Picks randomly between two mutation strategies:
    1. Remove a private field (FIELD_REMOVED — always breaking for consumers).
    2. Rename an endpoint path (ENDPOINT_PATH_CHANGED — breaking for all callers).

    Returns (mutated_content, mutation_description, pr_title).
    """
    strategies = []

    field_info = _find_removable_field(content)
    if field_info:
        strategies.append(("remove_field", field_info))

    mapping_info = _find_mapping_annotation(content)
    if mapping_info:
        strategies.append(("rename_endpoint", mapping_info))

    if not strategies:
        raise RuntimeError(f"No applicable mutation found in {service} source file. Try a different file.")

    strategy, info = random.choice(strategies)

    if strategy == "remove_field":
        full_line, field_name = info
        mutated = content.replace(f"    {full_line}\n", "", 1)
        if mutated == content:
            mutated = content.replace(f"  {full_line}\n", "", 1)
        description = f"Remove field `{field_name}` from {service} API model (FIELD_REMOVED — breaking)"
        title = f"refactor({service}): remove deprecated `{field_name}` field from response model"

    else:  # rename_endpoint
        full_annotation, old_path = info
        new_path = old_path.replace("/", "/v2/", 1) if "/v2/" not in old_path else old_path + "-legacy"
        mutated = content.replace(old_path, new_path, 1)
        description = f"Rename endpoint `{old_path}` → `{new_path}` in {service} (ENDPOINT_PATH_CHANGED — breaking)"
        title = f"refactor({service}): migrate endpoint `{old_path}` to versioned path"

    return mutated, description, title


def apply_safe_mutation(content: str, service: str) -> tuple[str, str, str]:
    """Apply a SAFE (non-breaking, additive) mutation to file content.

    Adds an optional field — never breaks existing consumers.
    Returns (mutated_content, mutation_description, pr_title).
    """
    # Insert a new optional field near the first private field found
    field_pattern = re.compile(r"(^\s*private\s+\w+\s+\w+\s*;)", re.MULTILINE)
    match = field_pattern.search(content)
    if not match:
        raise RuntimeError(f"No field found to add after in {service}")

    ts = int(time.time()) % 10000
    new_field = f"    private String notes{ts};  // optional — added for extensibility\n"
    insert_pos = match.end()
    mutated = content[: insert_pos] + "\n" + new_field + content[insert_pos:]

    description = f"Add optional `notes{ts}` field to {service} model (SAFE — backward compatible)"
    title = f"feat({service}): add optional notes field for extended metadata"
    return mutated, description, title


# ─── Main Engine ──────────────────────────────────────────────────────────────

def raise_pr(service: Optional[str] = None, safe: bool = False) -> dict:
    """Create a real PR on GitHub with a live dynamic mutation.

    Args:
        service: Target microservice. If None, picks randomly from SERVICE_FILES.
        safe:    If True, creates an additive safe change instead of a breaking one.

    Returns:
        GitHub PR response dict containing pr.html_url and pr.number.
    """
    print("=" * 60)
    print("  AEGIS Dynamic PR Engine")
    print("=" * 60)

    token = load_github_token()
    print(f"  [+] GitHub token loaded (FawazMulla)")

    # Select service and file
    if service is None:
        service = random.choice(list(SERVICE_FILES.keys()))
    if service not in SERVICE_FILES:
        raise ValueError(f"Unknown service '{service}'. Options: {list(SERVICE_FILES.keys())}")

    print(f"  [*] Target service: {service}")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    change_type = "safe" if safe else "break"
    branch_name = f"aegis/demo-{change_type}-{service}-{timestamp}"

    # Try files in the service until one works
    file_path = None
    content = None
    file_sha = None

    for candidate_path in SERVICE_FILES[service]:
        try:
            print(f"  [>] Fetching: {candidate_path.split('/')[-1]}")
            content, file_sha = get_file(token, candidate_path)
            file_path = candidate_path
            print(f"  [+] File fetched ({len(content)} chars)")
            break
        except Exception as e:
            print(f"  [!] Could not fetch {candidate_path}: {e}")
            continue

    if not content or not file_path:
        raise RuntimeError(f"Could not fetch any source file for {service}")

    # Apply mutation
    try:
        if safe:
            mutated_content, description, pr_title = apply_safe_mutation(content, service)
        else:
            mutated_content, description, pr_title = apply_breaking_mutation(content, service)
    except RuntimeError as e:
        print(f"  [-] Mutation failed: {e}")
        sys.exit(1)

    print(f"  [*] Mutation: {description}")
    print(f"  [*] PR Title: {pr_title}")

    # Create branch
    print(f"  [*] Creating branch: {branch_name}")
    base_sha = get_branch_sha(token)
    create_branch(token, branch_name, base_sha)

    # Commit mutation
    print("  [*] Committing change...")
    commit_message = f"{pr_title}\n\n{description}\n\n[AEGIS-Demo] Automated change for live breaking-change demonstration."
    commit_file(
        token=token,
        file_path=file_path,
        new_content=mutated_content,
        file_sha=file_sha,
        branch=branch_name,
        commit_message=commit_message,
    )

    # Open PR
    print("  [*] Opening Pull Request...")
    pr_body = (
        f"## AEGIS Live Demonstration PR\n\n"
        f"**Service:** `{service}`  \n"
        f"**Change Type:** {'Breaking' if not safe else 'Safe (Additive)'}  \n"
        f"**Mutation Applied:** {description}  \n\n"
        f"This PR was automatically generated by the AEGIS Dynamic PR Engine "
        f"for live demonstration of intelligent breaking-change detection.\n\n"
        f"> AEGIS will automatically analyze this PR's diff, detect the breaking change "
        f"using Cohere Command A (OCI GenAI), traverse the service dependency graph, "
        f"calculate the composite risk score, and post a detailed assessment here."
    )
    pr = open_pull_request(token, branch_name, pr_title, pr_body)

    print()
    print("=" * 60)
    print(f"  PR #{pr['number']} CREATED SUCCESSFULLY")
    print(f"  {pr['html_url']}")
    print("  AEGIS is now analyzing this PR's diff...")
    print("=" * 60)

    return pr


def main():
    parser = argparse.ArgumentParser(
        description="AEGIS Dynamic PR Engine — creates live breaking-change PRs for demonstration"
    )
    parser.add_argument("--service", help="Target service (customers-service, visits-service, vets-service)")
    parser.add_argument("--auto-break", action="store_true", help="Auto-select service and apply a breaking mutation")
    parser.add_argument("--safe", action="store_true", help="Create a safe/additive PR (proves AEGIS approves non-breaking changes)")

    args = parser.parse_args()

    service = args.service
    if args.auto_break and not service:
        service = None  # Will be auto-selected

    raise_pr(service=service, safe=args.safe)


if __name__ == "__main__":
    main()
