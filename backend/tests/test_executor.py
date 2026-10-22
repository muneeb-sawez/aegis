"""AEGIS Executor Test Suite (backend/tests/test_executor.py).

Tests are written BEFORE implementation is used in production (AGENTS.md §9).
All tests run without a real LLM, real network, or Neo4j.

Coverage:
  allowlist:  non-allowlisted action refused; invalid scale_pool params refused;
              restart bad params refused; rollback missing revision refused.
  scoring:    safe actions score ≥ 75; unsafe action (manual) refused; composite formula.
  actuator:   per-service lock blocks concurrent fix; HMAC signature computed.
  health:     returns True when latency is below 2× baseline; False when above.
  rollback:   called when health fails; structured result returned.
  audit:      JSONL line written; secrets never logged; update appends new line.
  orchestrator (acceptance tests):
              good fix → 'succeeded';
              unhealthy fix → 'rolled_back';
              non-allowlisted → 'refused';
              two concurrent fixes on same service → second is rejected.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# ALLOWLIST TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestAllowlist:
    """SAFETY CHECK 1-3: allowlist gate must refuse any disallowed action or param."""

    def test_valid_restart_passes(self):
        from backend.executor.allowlist import validate_proposal
        p = validate_proposal(action="restart", target="svc-a", params={}, fault_type="pod_crash")
        assert p.action == "restart"

    def test_valid_scale_pool_passes(self):
        from backend.executor.allowlist import validate_proposal
        p = validate_proposal(action="scale_pool", target="db-1", params={"pool_size": 50})
        assert p.action == "scale_pool"
        assert p.params["pool_size"] == 50

    def test_valid_rollback_passes(self):
        from backend.executor.allowlist import validate_proposal
        p = validate_proposal(action="rollback", target="svc-b", params={"revision": "HEAD~1"})
        assert p.action == "rollback"

    # ── SAFETY CHECK 1 ────────────────────────────────────────────────────────
    def test_non_allowlisted_action_raises(self):
        """SAFETY CHECK 1: Any action not in allowlist must raise AllowlistViolation."""
        from backend.executor.allowlist import validate_proposal, AllowlistViolation
        with pytest.raises(AllowlistViolation, match="not allowlisted"):
            validate_proposal(action="delete_service", target="svc-x")

    def test_kubectl_exec_raises(self):
        """SAFETY CHECK 1: Real Kubernetes actions must be refused."""
        from backend.executor.allowlist import validate_proposal, AllowlistViolation
        with pytest.raises(AllowlistViolation):
            validate_proposal(action="kubectl_exec", target="pod-1")

    def test_empty_action_raises(self):
        from backend.executor.allowlist import validate_proposal, AllowlistViolation
        with pytest.raises(AllowlistViolation):
            validate_proposal(action="", target="svc-a")

    # ── SAFETY CHECK 2 ────────────────────────────────────────────────────────
    def test_empty_target_raises(self):
        """SAFETY CHECK 2: Blank target would apply fix to unknown service."""
        from backend.executor.allowlist import validate_proposal, AllowlistViolation
        with pytest.raises(AllowlistViolation):
            validate_proposal(action="restart", target="   ")

    # ── SAFETY CHECK 3a: scale_pool bounds ───────────────────────────────────
    def test_scale_pool_too_large_raises(self):
        """SAFETY CHECK 3a: pool_size > 100 is refused."""
        from backend.executor.allowlist import validate_proposal, AllowlistViolation
        with pytest.raises(AllowlistViolation, match="out of bounds"):
            validate_proposal(action="scale_pool", target="db-1", params={"pool_size": 200})

    def test_scale_pool_zero_raises(self):
        """SAFETY CHECK 3a: pool_size = 0 is refused."""
        from backend.executor.allowlist import validate_proposal, AllowlistViolation
        with pytest.raises(AllowlistViolation, match="out of bounds"):
            validate_proposal(action="scale_pool", target="db-1", params={"pool_size": 0})

    def test_scale_pool_missing_param_raises(self):
        """SAFETY CHECK 3a: Missing pool_size is refused."""
        from backend.executor.allowlist import validate_proposal, AllowlistViolation
        with pytest.raises(AllowlistViolation, match="pool_size"):
            validate_proposal(action="scale_pool", target="db-1", params={})

    def test_scale_pool_non_int_raises(self):
        """SAFETY CHECK 3a: Non-integer pool_size is refused."""
        from backend.executor.allowlist import validate_proposal, AllowlistViolation
        with pytest.raises(AllowlistViolation):
            validate_proposal(action="scale_pool", target="db-1", params={"pool_size": "lots"})

    # ── SAFETY CHECK 3b: restart extra params ────────────────────────────────
    def test_restart_unexpected_param_raises(self):
        """SAFETY CHECK 3b: Extra restart params (e.g. 'shell_cmd') are refused."""
        from backend.executor.allowlist import validate_proposal, AllowlistViolation
        with pytest.raises(AllowlistViolation, match="unexpected params"):
            validate_proposal(action="restart", target="svc-a", params={"shell_cmd": "rm -rf /"})

    # ── SAFETY CHECK 3c: rollback missing revision ────────────────────────────
    def test_rollback_missing_revision_raises(self):
        """SAFETY CHECK 3c: rollback without revision or target_version is refused."""
        from backend.executor.allowlist import validate_proposal, AllowlistViolation
        with pytest.raises(AllowlistViolation, match="revision"):
            validate_proposal(action="rollback", target="svc-b", params={})


# ─────────────────────────────────────────────────────────────────────────────
# SCORING TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestScoring:
    """SAFETY CHECK 4-5: Safety < 75 must be refused; composite formula must hold."""

    def test_restart_is_safe(self):
        """SAFETY CHECK 5: restart has blast=10,loss=0,overhead=5 → Safety=85 ≥ 75."""
        from backend.executor.scoring import compute_score
        r = compute_score(action="restart", fault_type="pod_crash")
        assert r.safety_score == pytest.approx(85.0)
        assert r.eligible is True
        assert r.refusal_reason == ""

    def test_scale_pool_is_safe(self):
        """SAFETY CHECK 5: scale_pool has blast=5,loss=0,overhead=3 → Safety=92 ≥ 75."""
        from backend.executor.scoring import compute_score
        r = compute_score(action="scale_pool", fault_type="pool_exhaustion")
        assert r.safety_score == pytest.approx(92.0)
        assert r.eligible is True

    def test_rollback_is_safe(self):
        """rollback blast=20,loss=5,overhead=10 → Safety=65. Check if < 75 → refused."""
        from backend.executor.scoring import compute_score, SAFETY_THRESHOLD
        r = compute_score(action="rollback", fault_type="pod_crash")
        expected_safety = 100.0 - (20 + 5 + 10)
        assert r.safety_score == pytest.approx(expected_safety)
        if expected_safety < SAFETY_THRESHOLD:
            assert r.eligible is False
            assert "refused" in r.refusal_reason.lower() or "below threshold" in r.refusal_reason

    def test_composite_formula(self):
        """Score = 0.6 * Safety + 0.4 * Recovery."""
        from backend.executor.scoring import compute_score, SAFETY_WEIGHT, RECOVERY_WEIGHT
        r = compute_score(action="scale_pool", fault_type="pool_exhaustion")
        expected = SAFETY_WEIGHT * r.safety_score + RECOVERY_WEIGHT * r.recovery_score
        assert r.composite_score == pytest.approx(expected, abs=0.01)

    def test_unknown_fault_type_uses_fallback(self):
        """Unknown fault type should use 'unknown' fallback recovery score."""
        from backend.executor.scoring import compute_score
        r = compute_score(action="restart", fault_type="completely_unknown_fault")
        assert r.recovery_score >= 0.0

    def test_unknown_action_refused_conservatively(self):
        """SAFETY CHECK 4: Action not in table must produce eligible=False."""
        from backend.executor.scoring import compute_score
        r = compute_score(action="nonexistent_action", fault_type="pod_crash")
        assert r.eligible is False
        assert r.safety_score == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# ACTUATOR TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestActuator:
    """SAFETY CHECK 6-10: per-service lock, HMAC, snapshot, network failure."""

    def test_snapshot_captures_fields(self):
        """SAFETY CHECK 8: Snapshot must capture config_version and pool_size."""
        from backend.executor.actuator import take_snapshot
        snap = take_snapshot("svc-a", pool_size=50, config_version="v1.2")
        assert snap["service_id"] == "svc-a"
        assert snap["pool_size"] == 50
        assert snap["config_version"] == "v1.2"
        assert "captured_at" in snap

    def test_hmac_signature_computed(self):
        """SAFETY CHECK 7: HMAC signature is deterministic for a given body and secret."""
        from backend.executor.actuator import _sign_payload
        body = b'{"action":"restart"}'
        sig1 = _sign_payload(body, "secret")
        sig2 = _sign_payload(body, "secret")
        assert sig1 == sig2  # deterministic

    def test_hmac_tamper_detected(self):
        """SAFETY CHECK 7: Tampered body produces a different signature."""
        from backend.executor.actuator import _sign_payload
        body_original = b'{"action":"restart"}'
        body_tampered = b'{"action":"delete_all"}'
        sig_original = _sign_payload(body_original, "secret")
        sig_tampered = _sign_payload(body_tampered, "secret")
        assert sig_original != sig_tampered

    @pytest.mark.asyncio
    async def test_per_service_lock_blocks_concurrent_fix(self):
        """SAFETY CHECK 6: A second fix on the same service while first is running must be rejected."""
        from backend.executor.actuator import _get_service_lock, apply_fix

        # Acquire the lock externally to simulate a running fix
        lock = await _get_service_lock("svc-locked")
        snap = {"service_id": "svc-locked", "config_version": "v1", "pool_size": 10, "captured_at": "now"}

        async with lock:
            # Lock is held; now try to apply another fix on the same service
            result = await apply_fix(
                service_id="svc-locked",
                action="restart",
                params={},
                snapshot=snap,
            )
        # The second call must report rejection, not proceed
        assert result["status"] == "rejected"
        assert "in progress" in result["reason"].lower() or "in progress" in result.get("reason", "").lower()

    @pytest.mark.asyncio
    async def test_apply_fix_emulated_success(self):
        """apply_fix in emulated mode (no ACTUATOR_TARGET_BASE_URL) returns 'applied'."""
        from backend.executor.actuator import apply_fix
        snap = {"service_id": "svc-x", "config_version": "v1", "pool_size": 20, "captured_at": "now"}
        env = {"ACTUATOR_TARGET_BASE_URL": "", "ACTUATOR_HMAC_SECRET": "test-secret"}
        with patch.dict(os.environ, env):
            result = await apply_fix("svc-x", "restart", {}, snap)
        assert result["status"] == "applied"
        assert result.get("emulated") is True


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestHealth:
    """SAFETY CHECK 11-12: fail-closed on errors, deadline enforced."""

    @pytest.mark.asyncio
    async def test_healthy_when_latency_below_2x(self):
        """healthy = latency < 2× baseline. 80ms < 2×100ms=200ms → healthy."""
        from backend.executor.health import check_health

        def mock_probe(service_id, baseline):
            return {"latency_ms": 80.0, "has_failures": False, "status": "healthy", "emulated": True}

        with patch("backend.executor.health._probe_emulated", side_effect=mock_probe):
            healthy, log = await check_health(
                service_id="svc-ok",
                baseline_latency_ms=100.0,
                verification_window_sec=3.0,
            )
        assert healthy is True
        assert len(log) >= 1

    @pytest.mark.asyncio
    async def test_unhealthy_when_latency_above_2x(self):
        """250ms > 2×100ms=200ms → unhealthy."""
        from backend.executor.health import check_health

        def mock_probe(service_id, baseline):
            return {"latency_ms": 250.0, "has_failures": False, "status": "degraded", "emulated": True}

        with patch("backend.executor.health._probe_emulated", side_effect=mock_probe):
            healthy, log = await check_health(
                service_id="svc-bad",
                baseline_latency_ms=100.0,
                verification_window_sec=2.0,
            )
        assert healthy is False

    @pytest.mark.asyncio
    async def test_unhealthy_when_has_failures(self):
        """latency fine but has_failures=True → unhealthy."""
        from backend.executor.health import check_health

        def mock_probe(service_id, baseline):
            return {"latency_ms": 50.0, "has_failures": True, "status": "error", "emulated": True}

        with patch("backend.executor.health._probe_emulated", side_effect=mock_probe):
            healthy, _ = await check_health(
                service_id="svc-err",
                baseline_latency_ms=100.0,
                verification_window_sec=2.0,
            )
        assert healthy is False

    @pytest.mark.asyncio
    async def test_expired_deadline_returns_unhealthy(self):
        """SAFETY CHECK 12: Deadline already in the past → immediately unhealthy."""
        from backend.executor.health import check_health

        past = datetime.now(timezone.utc) - timedelta(seconds=10)
        healthy, log = await check_health(
            service_id="svc-expired",
            baseline_latency_ms=100.0,
            deadline=past,
        )
        assert healthy is False
        assert log == []


# ─────────────────────────────────────────────────────────────────────────────
# ROLLBACK TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestRollback:
    """SAFETY CHECK 13-14: structured error on failure; snapshot validation."""

    def test_rollback_emulated_returns_rolled_back(self):
        """SAFETY CHECK 13: Rollback must return a structured result, not raise."""
        from backend.executor.rollback import rollback

        snap = {"service_id": "svc-rb", "config_version": "v1.0", "pool_size": 30, "captured_at": "now"}
        # Mock repo to avoid real graph
        mock_repo = MagicMock()
        mock_repo.get_topology.return_value = MagicMock(nodes=[])
        with patch("backend.executor.rollback._rollback_emulated") as mock_rb:
            mock_rb.return_value = {
                "status": "rolled_back",
                "service_id": "svc-rb",
                "restored_snapshot": snap,
                "rolled_back_at": "2024-01-01T00:00:00Z",
                "emulated": True,
            }
            result = rollback("svc-rb", snap)
        assert result["status"] == "rolled_back"
        assert result["emulated"] is True

    def test_rollback_with_invalid_snapshot_does_not_raise(self):
        """SAFETY CHECK 14: Invalid snapshot is logged but does not crash."""
        from backend.executor.rollback import rollback

        # Missing required keys
        bad_snap = {"service_id": "svc-rb"}
        with patch("backend.executor.rollback._rollback_emulated") as mock_rb:
            mock_rb.return_value = {"status": "rolled_back", "service_id": "svc-rb", "emulated": True}
            result = rollback("svc-rb", bad_snap)
        # Must not raise, must return structured result
        assert "status" in result


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestAudit:
    """SAFETY CHECK 15-17: secrets not logged, append-only, graph-write is best-effort."""

    def test_jsonl_line_written(self, tmp_path):
        """SAFETY CHECK 16: record_decision appends exactly one JSON line."""
        from backend.executor.audit import DecisionRecord, record_decision, _audit_log_path

        audit_file = tmp_path / "audit.jsonl"
        with patch("backend.executor.audit._audit_log_path", return_value=audit_file):
            rec = DecisionRecord(
                incident_id="inc-001",
                service_id="svc-a",
                action="restart",
                fault_type="pod_crash",
                safety_score=85.0,
                recovery_score=80.0,
                composite_score=83.0,
                status="succeeded",
                reason="pod OOM",
            )
            record_decision(rec)

        lines = audit_file.read_text().strip().splitlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["decision_id"] == rec.decision_id
        assert data["action"] == "restart"

    def test_secrets_not_logged(self, tmp_path):
        """SAFETY CHECK 15: Keys named 'api_key', 'password', 'secret' are redacted."""
        from backend.executor.audit import _sanitize

        dirty = {
            "decision_id": "dec-abc",
            "api_key": "sk-super-secret",
            "password": "hunter2",
            "action": "restart",
            "hmac_secret": "mysecret",
            "token": "ghp_12345",
        }
        clean = _sanitize(dirty)
        assert clean["api_key"] == "[REDACTED]"
        assert clean["password"] == "[REDACTED]"
        assert clean["hmac_secret"] == "[REDACTED]"
        assert clean["token"] == "[REDACTED]"
        # Non-secret fields must be untouched
        assert clean["action"] == "restart"
        assert clean["decision_id"] == "dec-abc"

    def test_update_appends_new_line(self, tmp_path):
        """SAFETY CHECK 16: update_decision must append a new line, not overwrite."""
        from backend.executor.audit import DecisionRecord, record_decision, update_decision, _audit_log_path

        audit_file = tmp_path / "audit.jsonl"
        with patch("backend.executor.audit._audit_log_path", return_value=audit_file):
            rec = DecisionRecord(
                incident_id="inc-002",
                service_id="svc-b",
                action="scale_pool",
                fault_type="pool_exhaustion",
                safety_score=92.0,
                recovery_score=90.0,
                composite_score=91.2,
                status="pending",
                reason="pool exhausted",
            )
            record_decision(rec)
            update_decision(rec.decision_id, status="succeeded")

        lines = audit_file.read_text().strip().splitlines()
        # Should be 2 lines: original + update
        assert len(lines) == 2
        update_record = json.loads(lines[1])
        assert update_record.get("_update") is True

    def test_graph_persist_failure_does_not_raise(self):
        """SAFETY CHECK 17: Graph write failure must be swallowed, not crash audit."""
        from backend.executor.audit import DecisionRecord, persist_to_graph

        rec = DecisionRecord(
            incident_id="inc-003",
            service_id="svc-c",
            action="restart",
            fault_type="pod_crash",
            safety_score=85.0,
            recovery_score=80.0,
            composite_score=83.0,
            status="succeeded",
            reason="ok",
        )
        # Patch at the point where it's actually imported inside persist_to_graph
        with patch("backend.graph.get_repository", side_effect=RuntimeError("graph down")):
            # Must not raise
            persist_to_graph(rec)



# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR ACCEPTANCE TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestOrchestratorAcceptance:
    """End-to-end pipeline acceptance tests (all gates wired together)."""

    @pytest.mark.asyncio
    async def test_good_fix_succeeds(self):
        """Acceptance: target heals → decision 'succeeded'."""
        from backend.executor.orchestrator import run_remediation

        # Mock health to return True (service heals)
        with patch("backend.executor.orchestrator.check_health", new_callable=AsyncMock) as mock_health, \
             patch("backend.executor.orchestrator.apply_fix", new_callable=AsyncMock) as mock_fix, \
             patch("backend.executor.orchestrator.persist_to_graph"):
            mock_fix.return_value = {"status": "applied", "emulated": True}
            mock_health.return_value = (True, [{"latency_ms": 80.0, "emulated": True}])

            dec = await run_remediation(
                incident_id="inc-good",
                service_id="svc-good",
                action="scale_pool",
                params={"pool_size": 50},
                fault_type="pool_exhaustion",
                reason="pool saturated",
                reasoning_trace=["DB pool at 100/100"],
                override_mode="auto",
            )
        assert dec.status == "succeeded"

    @pytest.mark.asyncio
    async def test_bad_fix_auto_rollback(self):
        """Acceptance: target does not heal → decision 'rolled_back'."""
        from backend.executor.orchestrator import run_remediation

        with patch("backend.executor.orchestrator.check_health", new_callable=AsyncMock) as mock_health, \
             patch("backend.executor.orchestrator.apply_fix", new_callable=AsyncMock) as mock_fix, \
             patch("backend.executor.orchestrator.rollback") as mock_rb, \
             patch("backend.executor.orchestrator.persist_to_graph"):
            mock_fix.return_value = {"status": "applied", "emulated": True}
            mock_health.return_value = (False, [{"latency_ms": 999.0, "emulated": True}])
            mock_rb.return_value = {"status": "rolled_back", "emulated": True}

            dec = await run_remediation(
                incident_id="inc-bad",
                service_id="svc-bad",
                action="scale_pool",
                params={"pool_size": 10},
                fault_type="pool_exhaustion",
                reason="bad fix",
                reasoning_trace=[],
                override_mode="auto",
            )
        assert dec.status == "rolled_back"
        mock_rb.assert_called_once()

    @pytest.mark.asyncio
    async def test_non_allowlisted_action_refused(self):
        """Acceptance: Non-allowlisted action must be refused before any execution."""
        from backend.executor.orchestrator import run_remediation

        dec = await run_remediation(
            incident_id="inc-bad-action",
            service_id="svc-x",
            action="delete_namespace",
            params={},
            fault_type="unknown",
            reason="someone tried to delete namespace",
            reasoning_trace=[],
            override_mode="auto",
        )
        assert dec.status == "refused"

    @pytest.mark.asyncio
    async def test_approve_mode_creates_pending(self):
        """Acceptance: In approve mode, execution creates a pending Decision only."""
        from backend.executor.orchestrator import run_remediation

        dec = await run_remediation(
            incident_id="inc-approve",
            service_id="svc-approve",
            action="restart",
            params={},
            fault_type="pod_crash",
            reason="pod crashed",
            reasoning_trace=[],
            override_mode="approve",
        )
        assert dec.status == "pending"

    @pytest.mark.asyncio
    async def test_target_unreachable_fails_no_retry(self):
        """Acceptance: Unreachable target → 'failed', no blind retry."""
        from backend.executor.orchestrator import run_remediation

        with patch("backend.executor.orchestrator.apply_fix", new_callable=AsyncMock) as mock_fix, \
             patch("backend.executor.orchestrator.persist_to_graph"):
            mock_fix.return_value = {"status": "unreachable", "error": "connection refused"}

            dec = await run_remediation(
                incident_id="inc-unreachable",
                service_id="svc-gone",
                action="restart",
                params={},
                fault_type="pod_crash",
                reason="service gone",
                reasoning_trace=[],
                override_mode="auto",
            )
        assert dec.status == "failed"
        # apply_fix must have been called exactly once — no retry
        mock_fix.assert_called_once()

    @pytest.mark.asyncio
    async def test_two_concurrent_incidents_on_one_service(self):
        """Acceptance: Two simultaneous fixes on same service — second must be rejected."""
        from backend.executor.actuator import _get_service_lock, apply_fix

        snap = {"service_id": "svc-concurrent", "config_version": "v1", "pool_size": 50, "captured_at": "now"}
        lock = await _get_service_lock("svc-concurrent")

        async def _run_second():
            return await apply_fix("svc-concurrent", "restart", {}, snap)

        # Hold the lock and concurrently attempt a second fix
        async with lock:
            second_result = await _run_second()

        assert second_result["status"] == "rejected"
        assert "in progress" in second_result.get("reason", "").lower()
