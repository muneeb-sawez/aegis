"""AEGIS Executor — Automatic Rollback (backend/executor/rollback.py).

SAFETY RESPONSIBILITY:
  If health.py declares a service unhealthy by the deadline, this module
  restores the exact snapshot captured before the fix was applied, then marks
  the Decision as 'rolled_back'.

  The rollback path is tested BEFORE the happy path (AGENTS.md §4 rule 4).

Rollback contract:
  - Use the same admin API endpoint (POST /admin/fix with HMAC signature) to
    restore the snapshot values.
  - Never silently swallow rollback failures — return them as a structured error
    and record in audit.
  - Label all emulated operations (honesty rule AGENTS.md §6).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ── Emulated rollback ─────────────────────────────────────────────────────────

def _rollback_emulated(service_id: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    """Emulate rolling back the target service to the snapshot state.

    In Phase 1 this restores telemetry via the in-process graph repository.
    Labels: 'emulated: true' (honesty rule AGENTS.md §6).
    """
    try:
        from backend.graph import get_repository
        repo = get_repository()
        # Restore pool_size from snapshot; config_version is metadata only.
        pool_size = snapshot.get("pool_size")
        if pool_size is not None:
            repo.set_telemetry(service_id, {"pool_size": pool_size, "status": "rolled_back"})
        return {
            "status": "rolled_back",
            "service_id": service_id,
            "restored_snapshot": snapshot,
            "rolled_back_at": datetime.now(timezone.utc).isoformat(),
            "emulated": True,  # honesty label
        }
    except Exception as exc:
        logger.error("ROLLBACK_EMULATED_ERROR service=%r error=%s", service_id, exc)
        return {
            "status": "rollback_failed",
            "service_id": service_id,
            "error": str(exc),
            "emulated": True,
        }


def _rollback_real(
    base_url: str,
    service_id: str,
    snapshot: dict[str, Any],
    secret: str,
    timeout_sec: float,
) -> dict[str, Any]:
    """Send a POST /admin/fix to restore the snapshot on the real target."""
    import hashlib
    import hmac as hmaclib
    import json
    import urllib.request
    import urllib.error
    import os

    action = "rollback"
    params = {
        "config_version": snapshot.get("config_version"),
        "pool_size": snapshot.get("pool_size"),
    }
    url = f"{base_url}/{service_id}/admin/fix"
    body = json.dumps({"action": action, "params": params}).encode()
    sig = hmaclib.new(secret.encode(), body, hashlib.sha256).hexdigest()

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-AEGIS-Signature": sig,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            result = json.loads(resp.read())
            result["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
            result["emulated"] = False
            return result
    except urllib.error.URLError as exc:
        # SAFETY CHECK 13: Rollback failure is a structured error, never silent.
        logger.error("ROLLBACK_REAL_ERROR service=%r error=%s", service_id, exc)
        return {
            "status": "rollback_failed",
            "service_id": service_id,
            "error": str(exc),
            "emulated": False,
        }


# ── Public API ────────────────────────────────────────────────────────────────

def rollback(service_id: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    """Restore the service to its pre-fix snapshot state.

    SAFETY CHECKS:
      13 — Rollback failure is always returned as a structured error (never swallowed).
      14 — Snapshot must contain 'config_version' and 'pool_size'; if missing,
           we log an error and still attempt what we can.

    Args:
        service_id: Service to restore.
        snapshot: Dict captured by actuator.take_snapshot() before the fix.

    Returns:
        Result dict with at minimum {"status": ..., "service_id": ...,
        "rolled_back_at": ..., "emulated": ...}.
    """
    import os

    # SAFETY CHECK 14: Validate snapshot has expected fields.
    if "config_version" not in snapshot or "pool_size" not in snapshot:
        logger.error(
            "ROLLBACK_INVALID_SNAPSHOT service=%r snapshot keys=%s; proceeding with partial data.",
            service_id,
            list(snapshot.keys()),
        )
        # Do not abort — still attempt with whatever we have.

    logger.warning(
        "ROLLBACK_INITIATED service=%r snapshot_version=%r",
        service_id,
        snapshot.get("config_version"),
    )

    base_url = os.environ.get("ACTUATOR_TARGET_BASE_URL", "")
    secret = os.environ.get("ACTUATOR_HMAC_SECRET", "dev-hmac-secret")
    timeout_sec = float(os.environ.get("ACTUATOR_TIMEOUT_SEC", "5.0"))

    if base_url:
        result = _rollback_real(base_url, service_id, snapshot, secret, timeout_sec)
    else:
        result = _rollback_emulated(service_id, snapshot)

    logger.warning(
        "ROLLBACK_RESULT service=%r status=%r",
        service_id,
        result.get("status"),
    )
    return result
