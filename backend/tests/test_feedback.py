"""AEGIS Feedback & Learning Loop Tests (backend/tests/test_feedback.py) — M8.

Tests (written before production use):
  1. Outcome nodes written to graph with correct RESULTED_IN edge.
  2. Success-rate table: computed correctly from outcomes.
  3. Fallback to static lookup when < 3 samples.
  4. Scoring uses empirical rate when >= 3 samples.
  5. Similarity ranking on a toy set (keyword fallback, no real model needed).
  6. Similar incidents included in build_context output.
  7. Same PR score changes after an incident (golden loop — H term, not broken).
  8. Human-readable explanation mentions incident count after write.
  9. Non-terminal statuses (pending) do not create Outcome nodes.
 10. Graph write failure in persist_to_graph does not crash audit pipeline.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from backend.graph.networkx_repo import NetworkXGraphRepository
from backend.graph.repository import Outcome


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_repo() -> NetworkXGraphRepository:
    return NetworkXGraphRepository()


def _add_n_outcomes(repo, fault_type: str, action: str, n: int, succeeded: int):
    """Add n Outcome nodes: 'succeeded' count succeeded, rest 'rolled_back'."""
    for i in range(n):
        status = "succeeded" if i < succeeded else "rolled_back"
        repo.add_outcome(
            decision_id=f"dec-{i:04d}",
            incident_id=f"inc-{i:04d}",
            service_id="paymentservice",
            fault_type=fault_type,
            action=action,
            status=status,
            safety_score=85.0,
            composite_score=88.0,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Outcome nodes written with RESULTED_IN edge
# ─────────────────────────────────────────────────────────────────────────────

class TestOutcomeGraph:
    def test_add_outcome_returns_outcome_object(self):
        repo = _make_repo()
        out = repo.add_outcome(
            decision_id="dec-0001",
            incident_id="inc-0001",
            service_id="paymentservice",
            fault_type="pool_exhaustion",
            action="scale_pool",
            status="succeeded",
            safety_score=92.0,
            composite_score=91.2,
        )
        assert isinstance(out, Outcome)
        assert out.status == "succeeded"
        assert out.fault_type == "pool_exhaustion"
        assert out.action == "scale_pool"
        assert out.id.startswith("out-")

    def test_resulted_in_edge_written(self):
        """Decision -[:RESULTED_IN]-> Outcome edge must exist in the graph."""
        repo = _make_repo()
        # Add a proper decision node first via add_incident
        inc = repo.add_incident(
            service_id="paymentservice",
            description="pool exhaustion",
            decision_data={"action": "scale_pool", "safety_score": 92.0, "outcome": "success"},
        )
        dec_id = inc.decision_id

        out = repo.add_outcome(
            decision_id=dec_id,
            incident_id=inc.id,
            service_id="paymentservice",
            fault_type="pool_exhaustion",
            action="scale_pool",
            status="succeeded",
            safety_score=92.0,
            composite_score=91.2,
        )

        # Verify RESULTED_IN edge in the underlying graph
        assert repo._graph.has_node(out.id)
        # Check edge type between dec_id and out.id
        edge_types = [
            attrs.get("type")
            for _, _, attrs in repo._graph.edges(dec_id, data=True)
        ]
        assert "RESULTED_IN" in edge_types

    def test_outcomes_cleared_on_reset(self):
        repo = _make_repo()
        _add_n_outcomes(repo, "pod_crash", "restart", n=2, succeeded=2)
        assert len(repo._outcomes) == 2
        repo.reset()
        assert len(repo._outcomes) == 0

    def test_non_terminal_status_not_written_by_writer(self):
        """Pending/executing statuses must NOT create Outcome nodes."""
        from backend.feedback.writer import write_outcome

        repo = _make_repo()
        result = write_outcome(
            decision_id="dec-pend",
            incident_id="inc-pend",
            service_id="paymentservice",
            fault_type="pod_crash",
            action="restart",
            status="pending",  # non-terminal
            safety_score=85.0,
            composite_score=83.0,
            repo=repo,
        )
        assert result is None
        assert len(repo._outcomes) == 0

    def test_terminal_status_creates_outcome(self):
        """succeeded, rolled_back, failed, refused must all create Outcome nodes."""
        from backend.feedback.writer import write_outcome, TERMINAL_STATUSES

        for status in TERMINAL_STATUSES:
            repo = _make_repo()
            result = write_outcome(
                decision_id="dec-t",
                incident_id="inc-t",
                service_id="paymentservice",
                fault_type="pod_crash",
                action="restart",
                status=status,
                safety_score=85.0,
                composite_score=83.0,
                repo=repo,
            )
            assert result is not None, f"Expected Outcome for status={status!r}"
            assert len(repo._outcomes) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 2 & 3. Success-rate table: empirical vs fallback
# ─────────────────────────────────────────────────────────────────────────────

class TestSuccessRateTable:
    def test_rate_zero_samples_not_reliable(self):
        """No outcomes → reliable=False, rate=0."""
        from backend.feedback.writer import compute_success_rate_table
        repo = _make_repo()
        result = compute_success_rate_table("pool_exhaustion", "scale_pool", repo=repo)
        assert result["reliable"] is False
        assert result["sample_count"] == 0

    def test_rate_two_samples_not_reliable(self):
        """2 outcomes < 3 → reliable=False even if all succeeded."""
        from backend.feedback.writer import compute_success_rate_table
        repo = _make_repo()
        _add_n_outcomes(repo, "pool_exhaustion", "scale_pool", n=2, succeeded=2)
        result = compute_success_rate_table("pool_exhaustion", "scale_pool", repo=repo)
        assert result["reliable"] is False
        assert result["sample_count"] == 2

    def test_rate_three_samples_reliable(self):
        """3 outcomes >= 3 → reliable=True."""
        from backend.feedback.writer import compute_success_rate_table
        repo = _make_repo()
        _add_n_outcomes(repo, "pool_exhaustion", "scale_pool", n=3, succeeded=3)
        result = compute_success_rate_table("pool_exhaustion", "scale_pool", repo=repo)
        assert result["reliable"] is True
        assert result["sample_count"] == 3
        assert result["rate"] == pytest.approx(1.0)

    def test_rate_mixed_outcomes(self):
        """3 outcomes, 2 succeeded → rate = 2/3."""
        from backend.feedback.writer import compute_success_rate_table
        repo = _make_repo()
        _add_n_outcomes(repo, "pod_crash", "restart", n=3, succeeded=2)
        result = compute_success_rate_table("pod_crash", "restart", repo=repo)
        assert result["reliable"] is True
        assert result["rate"] == pytest.approx(2 / 3, abs=0.01)

    def test_rate_ignores_other_fault_types(self):
        """Outcomes for different fault_type must not pollute the count."""
        from backend.feedback.writer import compute_success_rate_table
        repo = _make_repo()
        _add_n_outcomes(repo, "latency_spike", "restart", n=5, succeeded=5)
        result = compute_success_rate_table("pool_exhaustion", "scale_pool", repo=repo)
        assert result["reliable"] is False
        assert result["sample_count"] == 0

    def test_rate_ignores_other_actions(self):
        """Outcomes for different action must not pollute the count."""
        from backend.feedback.writer import compute_success_rate_table
        repo = _make_repo()
        _add_n_outcomes(repo, "pool_exhaustion", "rollback", n=5, succeeded=5)
        result = compute_success_rate_table("pool_exhaustion", "scale_pool", repo=repo)
        assert result["reliable"] is False


# ─────────────────────────────────────────────────────────────────────────────
# 4. scoring.py uses empirical rate when >= 3 samples
# ─────────────────────────────────────────────────────────────────────────────

class TestScoringEmpiricalRecovery:
    def test_scoring_uses_static_when_no_samples(self):
        """With no outcomes, recovery_source must be 'static_table'."""
        from backend.executor.scoring import compute_score
        repo = _make_repo()
        # get_repository is imported inside compute_success_rate_table, so patch there
        with patch("backend.graph.get_repository", return_value=repo):
            result = compute_score("scale_pool", "pool_exhaustion")
        assert "static_table" in result.recovery_source

    def test_scoring_uses_empirical_when_enough_samples(self):
        """With 3+ outcomes, recovery_source must say 'empirical'."""
        from backend.executor.scoring import compute_score
        repo = _make_repo()
        _add_n_outcomes(repo, "pool_exhaustion", "scale_pool", n=5, succeeded=4)  # 80% rate
        with patch("backend.graph.get_repository", return_value=repo):
            result = compute_score("scale_pool", "pool_exhaustion")
        assert "empirical" in result.recovery_source
        # 4/5 = 80% → recovery_score = 80.0
        assert result.recovery_score == pytest.approx(80.0, abs=1.0)

    def test_composite_score_reflects_empirical_rate(self):
        """Composite = 0.6*Safety + 0.4*Recovery with empirical Recovery."""
        from backend.executor.scoring import compute_score, SAFETY_WEIGHT, RECOVERY_WEIGHT
        repo = _make_repo()
        _add_n_outcomes(repo, "pool_exhaustion", "scale_pool", n=3, succeeded=3)  # 100% rate
        with patch("backend.graph.get_repository", return_value=repo):
            result = compute_score("scale_pool", "pool_exhaustion")
        expected_composite = SAFETY_WEIGHT * result.safety_score + RECOVERY_WEIGHT * result.recovery_score
        assert result.composite_score == pytest.approx(expected_composite, abs=0.1)



# ─────────────────────────────────────────────────────────────────────────────
# 5. Similarity ranking on a toy set
# ─────────────────────────────────────────────────────────────────────────────

class TestSimilarity:
    """Use keyword fallback (no model download needed in tests)."""

    def _incidents(self):
        return [
            {"id": "inc-001", "service_id": "svc-a", "description": "DB connection pool exhaustion under load"},
            {"id": "inc-002", "service_id": "svc-b", "description": "Pod OOM killed due to memory leak"},
            {"id": "inc-003", "service_id": "svc-c", "description": "Connection pool saturated high traffic"},
            {"id": "inc-004", "service_id": "svc-d", "description": "CPU spike above 90% on worker node"},
        ]

    def test_top_results_returned(self):
        from backend.feedback.similarity import find_similar_incidents
        results = find_similar_incidents(
            query_description="DB connection pool exhaustion",
            all_incidents=self._incidents(),
            top_k=2,
        )
        assert len(results) <= 2
        assert all("similarity_score" in r for r in results)

    def test_most_similar_ranked_first(self):
        """'DB connection pool exhaustion' should rank pool-related incidents higher."""
        from backend.feedback.similarity import find_similar_incidents, _get_model
        # Force keyword fallback by mocking model as unavailable
        with patch("backend.feedback.similarity._get_model", return_value=None):
            results = find_similar_incidents(
                query_description="DB connection pool exhaustion",
                all_incidents=self._incidents(),
                top_k=3,
            )
        assert len(results) >= 1
        # inc-001 and inc-003 share more tokens with query than inc-002 or inc-004
        top_id = results[0]["id"]
        assert top_id in ("inc-001", "inc-003"), f"Expected pool-related incident first, got {top_id}"

    def test_excluded_id_not_in_results(self):
        """Current incident must be excluded from similarity results."""
        from backend.feedback.similarity import find_similar_incidents
        with patch("backend.feedback.similarity._get_model", return_value=None):
            results = find_similar_incidents(
                query_description="DB connection pool exhaustion",
                all_incidents=self._incidents(),
                top_k=4,
                exclude_id="inc-001",
            )
        ids = [r["id"] for r in results]
        assert "inc-001" not in ids

    def test_empty_candidates_returns_empty(self):
        from backend.feedback.similarity import find_similar_incidents
        results = find_similar_incidents(
            query_description="some fault",
            all_incidents=[],
            top_k=3,
        )
        assert results == []

    def test_scores_sorted_descending(self):
        from backend.feedback.similarity import find_similar_incidents
        with patch("backend.feedback.similarity._get_model", return_value=None):
            results = find_similar_incidents(
                query_description="pool exhaustion database",
                all_incidents=self._incidents(),
                top_k=3,
            )
        scores = [r["similarity_score"] for r in results]
        assert scores == sorted(scores, reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Similar incidents appear in build_context
# ─────────────────────────────────────────────────────────────────────────────

class TestContextSimilarity:
    def test_similar_incidents_in_context(self):
        """build_context must include 'similar_incidents' key."""
        from backend.agent.context import build_context
        repo = _make_repo()
        # Seed two past incidents so similarity has something to search
        repo.add_incident("paymentservice", "DB pool exhaustion")
        repo.add_incident("paymentservice", "DB connection saturated")

        ctx = build_context("paymentservice", repo=repo)
        assert "similar_incidents" in ctx
        assert isinstance(ctx["similar_incidents"], list)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Golden loop: same PR score increases after incident (H term preserved)
# ─────────────────────────────────────────────────────────────────────────────

class TestGoldenLoopPreserved:
    def test_h_term_increases_after_outcome(self):
        """H = min(100, incidents_last_30_days * 25).

        After writing an Outcome via feedback/writer, the incident count
        seen by risk.py must be 1 and H must be 25.0.
        """
        from backend.sim.risk import PRPayload, assess_change_risk
        from backend.feedback.writer import write_outcome

        repo = _make_repo()

        pr = PRPayload(
            id="pr-142",
            title="Test PR",
            target_service="paymentservice",
        )

        pre = assess_change_risk(pr, repo)
        assert pre.breakdown.history_score == 0.0, "Should start at zero"

        # Inject an incident + outcome through the standard path
        inc = repo.add_incident(
            service_id="paymentservice",
            description="pool exhaustion during test",
            decision_data={"action": "scale_pool", "safety_score": 92.0, "outcome": "success"},
        )
        write_outcome(
            decision_id=inc.decision_id,
            incident_id=inc.id,
            service_id="paymentservice",
            fault_type="pool_exhaustion",
            action="scale_pool",
            status="succeeded",
            safety_score=92.0,
            composite_score=91.2,
            repo=repo,
        )

        post = assess_change_risk(pr, repo)
        assert post.breakdown.history_score == 25.0, (
            f"Expected H=25.0 (1 incident × 25), got {post.breakdown.history_score}"
        )
        delta = round(post.risk_score - pre.risk_score, 1)
        assert delta == pytest.approx(5.0, abs=0.1), (
            f"Expected +5.0 risk delta (0.20 × 25), got {delta}"
        )

    def test_explanation_mentions_incident_after_write(self):
        """Human-readable explanation must mention the incident count after write."""
        from backend.sim.risk import PRPayload, assess_change_risk

        repo = _make_repo()
        repo.add_incident("paymentservice", "pool exhaustion post-deploy")

        pr = PRPayload(id="pr-test", title="Post-incident PR", target_service="paymentservice")
        result = assess_change_risk(pr, repo)

        incident_explanations = [e for e in result.explanation if "Incident History" in e]
        assert len(incident_explanations) == 1
        assert "1 incident" in incident_explanations[0]
        assert "+25" in incident_explanations[0] or "25.0" in incident_explanations[0]


# ─────────────────────────────────────────────────────────────────────────────
# 8. persist_to_graph failure does not crash audit
# ─────────────────────────────────────────────────────────────────────────────

class TestAuditGraphFailureSafe:
    def test_persist_graph_error_does_not_raise(self):
        """SAFETY CHECK 17: graph write failure is swallowed, not raised."""
        from backend.executor.audit import DecisionRecord, persist_to_graph

        rec = DecisionRecord(
            incident_id="inc-fail",
            service_id="svc-x",
            action="restart",
            fault_type="pod_crash",
            safety_score=85.0,
            recovery_score=80.0,
            composite_score=83.0,
            status="succeeded",
            reason="test",
        )
        with patch("backend.graph.get_repository", side_effect=RuntimeError("graph down")):
            # Must not raise
            persist_to_graph(rec)


# ─────────────────────────────────────────────────────────────────────────────
# 9. Feedback & PR Comparison API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestFeedbackAPI:
    def test_pr_comparison_endpoint(self):
        """GET /api/predict/pr-comparison returns baseline, current, delta, and explanation."""
        from fastapi.testclient import TestClient
        from backend.api.main import app

        client = TestClient(app)
        res = client.get("/api/predict/pr-comparison?pr_id=PR-142")
        assert res.status_code == 200
        data = res.json()

        assert data["pr_id"] == "PR-142"
        assert data["target_service"] == "paymentservice"
        assert "baseline_score" in data
        assert "current_score" in data
        assert "delta_score" in data
        assert "explanation" in data
        assert len(data["explanation"]) > 20

    def test_outcomes_and_success_rate_api(self):
        """GET /api/outcomes and GET /api/feedback/success-rates return valid structures."""
        from fastapi.testclient import TestClient
        from backend.api.main import app

        client = TestClient(app)
        res_out = client.get("/api/outcomes")
        assert res_out.status_code == 200
        assert isinstance(res_out.json(), list)

        res_rate = client.get("/api/feedback/success-rates?fault_type=pool_exhaustion&action=scale_pool")
        assert res_rate.status_code == 200
        rate_data = res_rate.json()
        assert "rate" in rate_data
        assert "sample_count" in rate_data
        assert "reliable" in rate_data

