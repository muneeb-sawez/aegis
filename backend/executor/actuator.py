"""AEGIS Executor — Guarded Actuator (backend/executor/actuator.py).

SAFETY RESPONSIBILITY:
  - Snapshots target state BEFORE any change so rollback.py can restore it.
  - Signs every outbound request with HMAC-SHA256; the target verifies this.
  - A per-service asyncio.Lock ensures exactly one fix runs on a service at a time
    (acceptance test: two simultaneous incidents → only one fix proceeds).
  - The LLM can only PROPOSE — this module executes, and only after allowlist +
    scoring gates have passed.

All network calls are emulated in Phase 1 (AGENTS.md §Phase 1 scope).
Real HTTP is used only when ACTUATOR_TARGET_BASE_URL env var is set.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ── Per-service locks ─────────────────────────────────────────────────────────
# SAFETY CHECK 6: Global registry of asyncio Locks keyed by service/node ID.
# Two fixes on the same service will not run concurrently.
_SERVICE_LOCKS: dict[str, asyncio.Lock] = {}
_LOCKS_MUTEX = asyncio.Lock()          # protects the registry itself


async def _get_service_lock(service_id: str) -> asyncio.Lock:
    """Return (or create) the per-service lock. Thread-safe via _LOCKS_MUTEX."""
    async with _LOCKS_MUTEX:
        if service_id not in _SERVICE_LOCKS:
            _SERVICE_LOCKS[service_id] = asyncio.Lock()
        return _SERVICE_LOCKS[service_id]


# ── HMAC helper ───────────────────────────────────────────────────────────────
def _sign_payload(payload: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for a request body.

    SAFETY CHECK 7: Every outbound request is signed. The target service must
    validate this signature before executing the action. A tampered request
    (different body or wrong secret) will have a mismatched signature and be
    rejected by the target — tested in test_executor.py.
    """
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


# ── Snapshot ──────────────────────────────────────────────────────────────────

def take_snapshot(service_id: str, pool_size: int, config_version: str) -> dict[str, Any]:
    """Record pre-fix state so rollback can restore it exactly.

    SAFETY CHECK 8: A snapshot is always taken BEFORE any mutation. If the fix
    is applied and health degrades, rollback.py restores from this snapshot.
    """
    snapshot = {
        "service_id": service_id,
        "config_version": config_version,
        "pool_size": pool_size,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("SNAPSHOT captured service=%r snapshot=%s", service_id, snapshot)
    return snapshot


# ── Emulated target call ──────────────────────────────────────────────────────

def _call_target_emulated(
    service_id: str,
    action: str,
    params: dict[str, Any],
    signature: str,
) -> dict[str, Any]:
    """Emulate the POST /admin/fix call to the target service.

    In Phase 1 this is a pure in-process emulation (AGENTS.md §Phase 1).
    The response mimics the real contract so the rest of the pipeline is real.

    Labels: emulator / simulated (honesty rule AGENTS.md §6).
    """
    # SAFETY CHECK 9: Even in emulation we validate that a signature was provided.
    if not signature:
        return {
            "status": "rejected",
            "reason": "Missing HMAC signature. [simulated]",
            "emulated": True,
        }

    logger.info(
        "ACTUATOR_CALL (emulated) service=%r action=%r params=%s sig=%.8s...",
        service_id,
        action,
        params,
        signature,
    )

    # Restore node telemetry to healthy in graph repository (emulated fix outcome)
    try:
        from backend.graph import get_repository
        repo = get_repository()
        repo.set_telemetry(service_id, {"status": "healthy", "p99_ms": 45.0, "error_rate": 0.0, "connections": 10})
        if "postgres" in service_id or "pod" in service_id:
            svc_name = service_id.replace("postgres-", "").replace("-pod-1", "")
            if svc_name == "payment":
                svc_name = "paymentservice"
            repo.set_telemetry(svc_name, {"status": "healthy", "p99_ms": 45.0, "error_rate": 0.0})
    except Exception:
        pass

    # Simulate a successful execution response
    return {
        "status": "applied",
        "action": action,
        "target": service_id,
        "params_applied": params,
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "emulated": True,  # honesty label
    }


def _call_target_real(
    base_url: str,
    service_id: str,
    action: str,
    params: dict[str, Any],
    secret: str,
    timeout_sec: float,
) -> dict[str, Any]:
    """Make a real HTTPS POST /admin/fix request to the target service.

    Used only when ACTUATOR_TARGET_BASE_URL is set (Phase 2+).
    Kept minimal here to avoid Phase 2 scope creep.
    """
    import urllib.request
    import urllib.error

    url = f"{base_url}/{service_id}/admin/fix"
    body = json.dumps({"action": action, "params": params}).encode()
    sig = _sign_payload(body, secret)

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
            return json.loads(resp.read())
    except urllib.error.URLError as exc:
        # SAFETY CHECK 10: On network failure, return a structured error so
        # the caller records it as 'failed' without blind retry.
        logger.error("ACTUATOR_UNREACHABLE service=%r url=%r error=%s", service_id, url, exc)
        return {"status": "unreachable", "error": str(exc)}


# ── Main public API ───────────────────────────────────────────────────────────

async def apply_fix(
    service_id: str,
    action: str,
    params: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Apply a validated, scored fix to the target service.

    SAFETY CHECKS ENFORCED HERE:
      6 — Per-service lock prevents two simultaneous fixes on one service.
      7 — HMAC signature is computed and attached to every outbound request.
      8 — Snapshot is referenced (must have been taken before calling this fn).
      9 — Signature presence validated even in emulation.
     10 — Network failure returns 'unreachable'; no blind retry.

    Args:
        service_id: Target service node ID.
        action: Allowlisted + scored action string.
        params: Action parameters (already validated by allowlist.py).
        snapshot: Pre-fix state snapshot (from take_snapshot()).

    Returns:
        Result dict with at minimum {"status": ..., "applied_at": ..., "emulated": ...}.
    """
    # SAFETY CHECK 6: Acquire per-service lock.
    lock = await _get_service_lock(service_id)
    if lock.locked():
        logger.warning(
            "ACTUATOR_LOCK_BUSY service=%r — another fix is in progress; refusing.",
            service_id,
        )
        return {
            "status": "rejected",
            "reason": f"Service '{service_id}' has a fix already in progress. "
                      "Two concurrent fixes on one service are not allowed.",
        }

    async with lock:
        # Determine execution mode: real vs emulated
        base_url = os.environ.get("ACTUATOR_TARGET_BASE_URL", "")
        secret = os.environ.get("ACTUATOR_HMAC_SECRET", "dev-hmac-secret")

        body = json.dumps({"action": action, "params": params}).encode()

        # SAFETY CHECK 7: Sign the request body with HMAC-SHA256.
        sig = _sign_payload(body, secret)

        if base_url:
            timeout = float(os.environ.get("ACTUATOR_TIMEOUT_SEC", "5.0"))
            result = _call_target_real(base_url, service_id, action, params, secret, timeout)
        else:
            result = _call_target_emulated(service_id, action, params, sig)

        # Augment result with request metadata for audit trail
        result["request"] = {
            "action": action,
            "target": service_id,
            "params": params,
            "snapshot_version": snapshot.get("config_version"),
        }
        result["signature_prefix"] = sig[:8] + "..."   # never log full sig
        result["ts"] = datetime.now(timezone.utc).isoformat()

        logger.info(
            "ACTUATOR_RESULT service=%r action=%r status=%r",
            service_id,
            action,
            result.get("status"),
        )
        return result
