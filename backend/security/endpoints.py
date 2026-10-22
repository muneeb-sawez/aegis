"""AEGIS Service Endpoint Registry (Per-Project with Encrypted Secrets & SSRF Guards).

Stores registered service endpoints (name, health_url, optional admin_url, secret).
- Secrets are encrypted with PBKDF2-HMAC-SHA256 authenticated encryption at rest or read from env.
- Secrets are NEVER returned in any public model or API response.
- Every URL is strictly validated through validate_url_ssrf() before registration.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from backend.security.encryption import decrypt_secret, encrypt_secret
from backend.security.ssrf import validate_url_ssrf

ENDPOINTS_FILE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "endpoints.json"


class ServiceEndpointRecord(BaseModel):
    """Internal model for stored endpoint data including encrypted secret."""
    project_id: str = "demo"
    name: str = Field(..., description="Service identifier (e.g. paymentservice)")
    health_url: str = Field(..., description="SSRF-validated HTTP/HTTPS health probe URL")
    admin_url: Optional[str] = Field(None, description="Optional SSRF-validated actuator admin URL")
    encrypted_secret: Optional[str] = Field(None, description="Authenticated encrypted secret")
    has_secret: bool = False
    created_at: str
    updated_at: str


class ServiceEndpointPublic(BaseModel):
    """Public representation. Plaintext secrets are strictly NEVER present."""
    project_id: str
    name: str
    health_url: str
    admin_url: Optional[str] = None
    has_secret: bool = False
    secret_source: str = Field("none", description="'env', 'encrypted_store', or 'none'")
    created_at: str
    updated_at: str


class EndpointRegistry:
    """Thread-safe persistent endpoint registry with per-project isolation."""

    def __init__(self, file_path: Path = ENDPOINTS_FILE_PATH) -> None:
        self.file_path = file_path
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._init_defaults()

    def _init_defaults(self) -> None:
        """Seed default demo project endpoints with SSRF-validated endpoints."""
        now = datetime.now(timezone.utc).isoformat()
        demo_endpoints = {
            "demo": {
                "paymentservice": {
                    "project_id": "demo",
                    "name": "paymentservice",
                    "health_url": "http://127.0.0.1:8000/api/monitor/probe/paymentservice",
                    "admin_url": "http://127.0.0.1:8000/api/actuator/fix/paymentservice",
                    "encrypted_secret": encrypt_secret("demo-hmac-secret-payment"),
                    "has_secret": True,
                    "created_at": now,
                    "updated_at": now,
                },
                "frontend": {
                    "project_id": "demo",
                    "name": "frontend",
                    "health_url": "http://127.0.0.1:8000/api/monitor/probe/frontend",
                    "admin_url": "http://127.0.0.1:8000/api/actuator/fix/frontend",
                    "encrypted_secret": encrypt_secret("demo-hmac-secret-frontend"),
                    "has_secret": True,
                    "created_at": now,
                    "updated_at": now,
                },
                "checkoutservice": {
                    "project_id": "demo",
                    "name": "checkoutservice",
                    "health_url": "http://127.0.0.1:8000/api/monitor/probe/checkoutservice",
                    "admin_url": "http://127.0.0.1:8000/api/actuator/fix/checkoutservice",
                    "encrypted_secret": None,
                    "has_secret": False,
                    "created_at": now,
                    "updated_at": now,
                },
            }
        }
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(demo_endpoints, f, indent=2)

    def load_all(self) -> dict[str, dict[str, ServiceEndpointRecord]]:
        """Load all endpoints grouped by project_id."""
        self._ensure_storage()
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            out: dict[str, dict[str, ServiceEndpointRecord]] = {}
            for pid, svcs in data.items():
                out[pid] = {sname: ServiceEndpointRecord(**sdata) for sname, sdata in svcs.items()}
            return out
        except Exception:
            return {}

    def save_all(self, data: dict[str, dict[str, ServiceEndpointRecord]]) -> None:
        """Atomically persist endpoints to disk."""
        serialized = {
            pid: {sname: rec.model_dump() for sname, rec in svcs.items()}
            for pid, svcs in data.items()
        }
        temp_path = self.file_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(serialized, f, indent=2)
        os.replace(temp_path, self.file_path)

    def register_endpoint(
        self,
        name: str,
        health_url: str,
        admin_url: Optional[str] = None,
        secret: Optional[str] = None,
        project_id: str = "demo",
    ) -> ServiceEndpointRecord:
        """Register or update an endpoint after running all URLs through SSRF check."""
        pid = (project_id or "demo").strip().lower()
        sname = name.strip()
        if not sname:
            raise ValueError("Service name cannot be empty.")

        # 1. Run health_url through SSRF check
        validated_health_url = validate_url_ssrf(health_url)

        # 2. Run optional admin_url through SSRF check
        validated_admin_url = None
        if admin_url and admin_url.strip():
            validated_admin_url = validate_url_ssrf(admin_url.strip())

        # 3. Encrypt secret if supplied
        encrypted_sec = None
        has_sec = False
        if secret and secret.strip():
            encrypted_sec = encrypt_secret(secret.strip())
            has_sec = True

        now = datetime.now(timezone.utc).isoformat()
        all_data = self.load_all()
        if pid not in all_data:
            all_data[pid] = {}

        existing = all_data[pid].get(sname)
        created_at = existing.created_at if existing else now

        # Retain existing encrypted secret if not overridden
        if not secret and existing and existing.encrypted_secret:
            encrypted_sec = existing.encrypted_secret
            has_sec = existing.has_secret

        record = ServiceEndpointRecord(
            project_id=pid,
            name=sname,
            health_url=validated_health_url,
            admin_url=validated_admin_url,
            encrypted_secret=encrypted_sec,
            has_secret=has_sec or bool(self._get_env_secret(pid, sname)),
            created_at=created_at,
            updated_at=now,
        )

        all_data[pid][sname] = record
        self.save_all(all_data)

        # Also synchronize with health checker
        try:
            from backend.monitor.health_checker import get_health_checker
            get_health_checker().configure_endpoint(sname, validated_health_url)
        except Exception:
            pass

        return record

    def _get_env_secret(self, project_id: str, name: str) -> Optional[str]:
        """Check environment variables for service secret overrides."""
        clean_name = name.upper().replace("-", "_").replace(".", "_")
        clean_pid = project_id.upper().replace("-", "_")

        # Check project-specific env var: SERVICE_SECRET_DEMO_PAYMENTSERVICE
        key1 = f"SERVICE_SECRET_{clean_pid}_{clean_name}"
        if key1 in os.environ and os.environ[key1].strip():
            return os.environ[key1].strip()

        # Check service env var: SERVICE_SECRET_PAYMENTSERVICE
        key2 = f"SERVICE_SECRET_{clean_name}"
        if key2 in os.environ and os.environ[key2].strip():
            return os.environ[key2].strip()

        return None

    def get_secret(self, project_id: str, name: str) -> Optional[str]:
        """Retrieve the plaintext secret for execution (env first, then encrypted store).

        NOTE: This is strictly for internal executor/actuator logic and is never exposed in APIs.
        """
        pid = (project_id or "demo").strip().lower()
        sname = name.strip()

        # 1. Environment variable override takes highest priority
        env_secret = self._get_env_secret(pid, sname)
        if env_secret:
            return env_secret

        # 2. Decrypt from encrypted store
        all_data = self.load_all()
        rec = all_data.get(pid, {}).get(sname)
        if rec and rec.encrypted_secret:
            return decrypt_secret(rec.encrypted_secret)

        return None

    def list_endpoints(self, project_id: str = "demo") -> list[ServiceEndpointPublic]:
        """Return public endpoint information for project. Secrets are NEVER returned."""
        pid = (project_id or "demo").strip().lower()
        all_data = self.load_all()
        project_svcs = all_data.get(pid, {})

        results: list[ServiceEndpointPublic] = []
        for sname, rec in project_svcs.items():
            env_sec = bool(self._get_env_secret(pid, sname))
            has_sec = env_sec or bool(rec.encrypted_secret)

            if env_sec:
                sec_source = "env"
            elif rec.encrypted_secret:
                sec_source = "encrypted_store"
            else:
                sec_source = "none"

            results.append(
                ServiceEndpointPublic(
                    project_id=rec.project_id,
                    name=rec.name,
                    health_url=rec.health_url,
                    admin_url=rec.admin_url,
                    has_secret=has_sec,
                    secret_source=sec_source,
                    created_at=rec.created_at,
                    updated_at=rec.updated_at,
                )
            )
        return results

    def get_endpoint(self, project_id: str, name: str) -> Optional[ServiceEndpointPublic]:
        """Return public information for a single service endpoint."""
        pid = (project_id or "demo").strip().lower()
        sname = name.strip()
        all_data = self.load_all()
        rec = all_data.get(pid, {}).get(sname)
        if not rec:
            return None

        env_sec = bool(self._get_env_secret(pid, sname))
        has_sec = env_sec or bool(rec.encrypted_secret)
        sec_source = "env" if env_sec else ("encrypted_store" if rec.encrypted_secret else "none")

        return ServiceEndpointPublic(
            project_id=rec.project_id,
            name=rec.name,
            health_url=rec.health_url,
            admin_url=rec.admin_url,
            has_secret=has_sec,
            secret_source=sec_source,
            created_at=rec.created_at,
            updated_at=rec.updated_at,
        )

    def delete_endpoint(self, project_id: str, name: str) -> bool:
        """Unregister an endpoint."""
        pid = (project_id or "demo").strip().lower()
        sname = name.strip()
        all_data = self.load_all()
        if pid in all_data and sname in all_data[pid]:
            del all_data[pid][sname]
            self.save_all(all_data)
            try:
                from backend.monitor.health_checker import get_health_checker
                get_health_checker().unconfigure_endpoint(sname)
            except Exception:
                pass
            return True
        return False


_registry_instance: Optional[EndpointRegistry] = None


def get_endpoint_registry() -> EndpointRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = EndpointRegistry()
    return _registry_instance
