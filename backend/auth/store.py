"""AEGIS Multi-Tenant Project & API Key Storage (Hashed in Storage).

Stores per-project API keys securely as SHA-256 hex digests in data/projects.json.
Raw keys are NEVER stored on disk and are only returned once at creation time.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

PROJECTS_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "projects.json"
DEFAULT_DEMO_API_KEY = "aegis-demo-api-key"


class ProjectRecord(BaseModel):
    """Internal model for project metadata and stored key hash."""
    project_id: str
    name: str
    description: str = ""
    key_hash: str = Field(..., description="SHA-256 hex digest of the per-project API key")
    created_at: str
    repo_full_name: Optional[str] = None
    repo_branch: str = "main"
    manifest_path: Optional[str] = None


class ProjectPublic(BaseModel):
    """Public representation of project without sensitive hash."""
    project_id: str
    name: str
    description: str = ""
    created_at: str
    key_status: str = "SHA-256 Hashed"
    node_count: int = 0
    edge_count: int = 0
    repo_full_name: Optional[str] = None
    repo_branch: str = "main"
    manifest_path: Optional[str] = None


class ProjectCreationResponse(BaseModel):
    """Returned once when creating a project containing the one-time raw API key."""
    project_id: str
    name: str
    description: str = ""
    api_key: str = Field(..., description="Plaintext API key. Only returned once; store securely!")
    created_at: str
    message: str = "Project created successfully. Save your API key now; it is hashed in storage and cannot be recovered."


def hash_api_key(raw_key: str) -> str:
    """Compute SHA-256 hex digest of a raw API key."""
    return hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()


def generate_raw_api_key(prefix: str = "aegis_key_") -> str:
    """Generate a secure cryptographic API key."""
    return f"{prefix}{secrets.token_hex(20)}"


class ProjectStore:
    """Manages persistent project storage and key hash verification."""

    def __init__(self, storage_path: Path = PROJECTS_DATA_PATH) -> None:
        self.storage_path = storage_path
        self._ensure_storage_exists()

    def _ensure_storage_exists(self) -> None:
        """Initialize data/projects.json with default 'demo' project if absent."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._init_defaults()
        else:
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict) or "demo" not in data:
                    self._init_defaults(existing=data if isinstance(data, dict) else {})
            except Exception:
                self._init_defaults()

    def _init_defaults(self, existing: Optional[dict] = None) -> None:
        """Seed the default 'demo' project with hashed key."""
        projects = existing or {}
        if "demo" not in projects:
            demo_hash = hash_api_key(DEFAULT_DEMO_API_KEY)
            projects["demo"] = {
                "project_id": "demo",
                "name": "Default Demo Fleet",
                "description": "Pre-seeded 54-node microservice baseline topology",
                "key_hash": demo_hash,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(projects, f, indent=2)

    def load_all(self) -> dict[str, ProjectRecord]:
        """Load all project records from disk."""
        self._ensure_storage_exists()
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {pid: ProjectRecord(**pdata) for pid, pdata in data.items()}
        except Exception:
            return {}

    def save_all(self, projects: dict[str, ProjectRecord]) -> None:
        """Persist all project records to disk."""
        data = {pid: record.model_dump() for pid, record in projects.items()}
        temp_path = self.storage_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, self.storage_path)

    def create_project(
        self,
        project_id: str,
        name: str,
        description: str = "",
        custom_key: Optional[str] = None,
    ) -> tuple[ProjectRecord, str]:
        """Create a new project, hash its API key, and return the record and one-time raw key."""
        pid = project_id.strip().lower()
        if not pid:
            raise ValueError("project_id cannot be empty")

        projects = self.load_all()
        if pid in projects:
            raise ValueError(f"Project '{pid}' already exists")

        raw_key = custom_key.strip() if custom_key else generate_raw_api_key()
        key_hash = hash_api_key(raw_key)

        record = ProjectRecord(
            project_id=pid,
            name=name.strip() or pid,
            description=description.strip(),
            key_hash=key_hash,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        projects[pid] = record
        self.save_all(projects)
        return record, raw_key

    def get_project(self, project_id: str) -> Optional[ProjectRecord]:
        """Lookup a project record by ID."""
        projects = self.load_all()
        return projects.get(project_id.strip().lower())

    def validate_key(self, raw_key: str, project_id: Optional[str] = None) -> Optional[ProjectRecord]:
        """Verify raw_key against stored SHA-256 hash using timing-safe comparison."""
        if not raw_key or not raw_key.strip():
            return None

        candidate_hash = hash_api_key(raw_key)
        projects = self.load_all()

        if project_id:
            pid = project_id.strip().lower()
            record = projects.get(pid)
            if record and hmac.compare_digest(record.key_hash, candidate_hash):
                return record
            return None

        # If no specific project_id requested, check if key matches any project
        for record in projects.values():
            if hmac.compare_digest(record.key_hash, candidate_hash):
                return record

        return None

    def bind_repository(
        self,
        project_id: str,
        repo_full_name: str,
        branch: str = "main",
        manifest_path: Optional[str] = None,
    ) -> ProjectRecord:
        """Bind a GitHub repository to a project tenant."""
        pid = project_id.strip().lower()
        projects = self.load_all()
        if pid not in projects:
            raise ValueError(f"Project '{pid}' does not exist")

        record = projects[pid]
        record.repo_full_name = repo_full_name.strip()
        record.repo_branch = branch.strip() or "main"
        if manifest_path:
            record.manifest_path = manifest_path.strip()

        projects[pid] = record
        self.save_all(projects)
        return record

    def get_project_by_repo(self, repo_full_name: str) -> Optional[ProjectRecord]:
        """Find the AEGIS project registered for a given GitHub 'owner/repo'."""
        clean = repo_full_name.strip().lower()
        projects = self.load_all()
        for record in projects.values():
            if record.repo_full_name and record.repo_full_name.strip().lower() == clean:
                return record
        return None


# Global singleton instance
_project_store: Optional[ProjectStore] = None


def get_project_store() -> ProjectStore:
    global _project_store
    if _project_store is None:
        _project_store = ProjectStore()
    return _project_store
