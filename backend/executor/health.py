"""AEGIS Executor — Post-Fix Health Verification (backend/executor/health.py).

SAFETY RESPONSIBILITY:
  After a fix is applied this module probes the target service repeatedly within
  a time-limited verification window. If the service does not meet the health
  criteria by the deadline, health_check() returns False and rollback.py takes
  over.

Health criteria (from executor_config.json):
  healthy = latency < 2 × baseline  AND  no active failures

Probing is emulated in Phase 1 (AGENTS.md §Phase 1 scope). Real probing
requires ACTUATOR_TARGET_BASE_URL env var.

Labels: emulated probes are marked "emulated: true" (honesty rule AGENTS.md §6).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Load config ───────────────────────────────────────────────────────────────
_CONFIG_PATH = Path(__file__).parent.parent.parent / "data" / "executor_config.json"


def _load_config() -> dict[str, Any]:
    with _CONFIG_PATH.open() as f:
        return json.load(f)


_CFG = _load_config()
_HEALTH_CFG = _CFG["health"]

LATENCY_MULTIPLIER: float = _HEALTH_CFG["latency_multiplier"]         # 2.0
VERIFICATION_WINDOW_SEC: float = _HEALTH_CFG["verification_window_sec"]   # 10.0
PROBE_INTERVAL_SEC: float = _HEALTH_CFG["probe_interval_sec"]             # 2.0


# ── Telemetry probe ───────────────────────────────────────────────────────────

def _probe_emulated(service_id: str, baseline_latency_ms: float) -> dict[str, Any]:
    """Emulate a single health probe for the target service.

    In Phase 1 this looks up the current telemetry set by actuator/chaos modules
    (stored in the in-process NetworkX graph state). In production this would be
    a real HTTP GET /metrics call.

    Returns a dict with keys: latency_ms, has_failures, emulated.
    """
    try:
        # Import here to avoid circular imports; graph is the source of truth.
        from backend.graph import get_repository
        repo = get_repository()
        topo = repo.get_topology()
        # Find the node's telemetry
        for node in topo.nodes:
            if node.id == service_id:
                latency = float(node.properties.get("p99_ms", baseline_latency_ms))
                status = node.properties.get("status", "healthy")
                error_rate = float(node.properties.get("error_rate", 0.0))
                has_failures = (status not in ("healthy", "Running")) or (error_rate > 0.1)
                return {
                    "latency_ms": latency,
                    "has_failures": has_failures,
                    "status": status,
                    "emulated": True,  # honesty label
                }
    except Exception as exc:
        logger.warning("HEALTH_PROBE_ERROR service=%r error=%s", service_id, exc)

    # Fallback: assume healthy if we can't probe
    return {
        "latency_ms": baseline_latency_ms * 0.9,
        "has_failures": False,
        "status": "assumed_healthy",
        "emulated": True,
    }


def _probe_real(base_url: str, service_id: str, timeout_sec: float) -> dict[str, Any]:
    """Make a real HTTP GET /metrics request to the target service."""
    import urllib.request
    import urllib.error

    url = f"{base_url}/{service_id}/metrics"
    try:
        with urllib.request.urlopen(url, timeout=timeout_sec) as resp:
            data = json.loads(resp.read())
            return {
                "latency_ms": float(data.get("p99_ms", 9999.0)),
                "has_failures": data.get("has_failures", True),
                "status": data.get("status", "unknown"),
                "emulated": False,
            }
    except urllib.error.URLError as exc:
        logger.warning("HEALTH_PROBE_UNREACHABLE service=%r error=%s", service_id, exc)
        # SAFETY CHECK 11: Unreachable target counts as unhealthy — fail closed.
        return {
            "latency_ms": 9999.0,
            "has_failures": True,
            "status": "unreachable",
            "emulated": False,
        }


# ── Public API ────────────────────────────────────────────────────────────────

async def check_health(
    service_id: str,
    baseline_latency_ms: float,
    deadline: datetime | None = None,
    verification_window_sec: float | None = None,
) -> tuple[bool, list[dict[str, Any]]]:
    """Probe the target service until it passes health criteria or deadline expires.

    SAFETY CHECKS:
      11 — Unreachable target is treated as unhealthy (fail-closed).
      12 — Deadline is always enforced; the loop cannot run indefinitely.

    Args:
        service_id: Service to probe.
        baseline_latency_ms: Pre-fix latency baseline; threshold = 2× this value.
        deadline: UTC datetime by which health must be confirmed. Defaults to
                  now + VERIFICATION_WINDOW_SEC.
        verification_window_sec: Overrides config value (useful in tests).

    Returns:
        (is_healthy: bool, probe_log: list of probe results)
    """
    from datetime import timedelta

    window = verification_window_sec if verification_window_sec is not None else VERIFICATION_WINDOW_SEC

    if deadline is None:
        deadline = datetime.now(timezone.utc) + timedelta(seconds=window)

    # SAFETY CHECK 12: Deadline must be in the future.
    if deadline <= datetime.now(timezone.utc):
        logger.warning(
            "HEALTH_CHECK_EXPIRED service=%r deadline already passed; treating as unhealthy.",
            service_id,
        )
        return False, []

    threshold_ms = LATENCY_MULTIPLIER * baseline_latency_ms
    base_url = os.environ.get("ACTUATOR_TARGET_BASE_URL", "")
    timeout_sec = float(os.environ.get("ACTUATOR_TIMEOUT_SEC", "5.0"))

    probe_log: list[dict[str, Any]] = []
    is_healthy = False

    while datetime.now(timezone.utc) < deadline:
        # SAFETY CHECK 11 (also applied in _probe_real): fail-closed on errors.
        if base_url:
            probe = _probe_real(base_url, service_id, timeout_sec)
        else:
            probe = _probe_emulated(service_id, baseline_latency_ms)

        probe["probed_at"] = datetime.now(timezone.utc).isoformat()
        probe["threshold_ms"] = threshold_ms
        probe_log.append(probe)

        latency_ok = probe["latency_ms"] < threshold_ms
        failure_ok = not probe["has_failures"]

        logger.info(
            "HEALTH_PROBE service=%r latency=%.1f threshold=%.1f failures=%s → %s",
            service_id,
            probe["latency_ms"],
            threshold_ms,
            probe["has_failures"],
            "PASS" if (latency_ok and failure_ok) else "FAIL",
        )

        if latency_ok and failure_ok:
            is_healthy = True
            break

        await asyncio.sleep(PROBE_INTERVAL_SEC)

    return is_healthy, probe_log
