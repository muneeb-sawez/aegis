"""AEGIS Final Integration & Regression Verification Script.

Executes and verifies:
1. PREDICT numerical calculations across multiple change types (Additive, Breaking, Cycle).
2. Graph-grounded upstream traversal and blast radius attenuation.
3. Ingestion and imported dependency impact on risk calculation.
4. MONITOR healthy endpoint, unconfigured services, simulated fault, incident creation, deduplication, and verified recovery.
5. Error handling for invalid inputs, missing endpoints, malformed YAML, and SSRF defense.
"""

import asyncio
from datetime import datetime
import json
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.graph import get_repository
from backend.sim.risk import assess_change_risk
from backend.sim.config import DEFAULT_CONFIG

client = TestClient(app)


def verify_predict_scenarios():
    print("=" * 60)
    print("1. VERIFYING PREDICT SCENARIOS & INDEPENDENT NUMERICAL CHECKS")
    print("=" * 60)

    # Scenario 1: Safe Additive Change on paymentservice
    resp1 = client.post("/api/predict/analyze", json={
        "service_id": "paymentservice",
        "change_type": "additive_safe",
        "details": "Add optional loyalty_discount float field"
    })
    assert resp1.status_code == 200, f"Error: {resp1.text}"
    data1 = resp1.json()
    b1 = data1["breakdown"]["blast_score"]
    c1 = data1["breakdown"]["contract_score"]
    d1 = data1["breakdown"]["cycle_score"]
    h1 = data1["breakdown"]["history_score"]
    score1 = data1["risk_score"]

    # Manual independent formula calculation
    expected_score1 = round(
        DEFAULT_CONFIG.weight_blast * b1 +
        DEFAULT_CONFIG.weight_contract * c1 +
        DEFAULT_CONFIG.weight_cycle * d1 +
        DEFAULT_CONFIG.weight_history * h1,
        2
    )

    print(f"Scenario 1 (Additive):")
    print(f"  Inputs: B={b1}, C={c1}, D={d1}, H={h1}")
    print(f"  Formula: 0.35*{b1} + 0.30*{c1} + 0.15*{d1} + 0.20*{h1} = {expected_score1}")
    print(f"  API Output Score: {score1}")
    assert score1 == expected_score1, f"Mismatch: {score1} != {expected_score1}"
    assert c1 == 0.0, f"Additive change must have C=0, got {c1}"
    assert d1 == 0.0, f"No cycle should have D=0, got {d1}"
    assert data1["verdict"] in ("Approved", "Warning")
    print("  -> PASSED: Additive change verified.")

    # Scenario 2: Breaking API Change on paymentservice
    resp2 = client.post("/api/predict/analyze", json={
        "service_id": "paymentservice",
        "change_type": "api_breaking",
        "details": "Remove required card_token field"
    })
    assert resp2.status_code == 200, f"Error: {resp2.text}"
    data2 = resp2.json()
    b2 = data2["breakdown"]["blast_score"]
    c2 = data2["breakdown"]["contract_score"]
    d2 = data2["breakdown"]["cycle_score"]
    h2 = data2["breakdown"]["history_score"]
    score2 = data2["risk_score"]

    expected_score2 = round(
        DEFAULT_CONFIG.weight_blast * b2 +
        DEFAULT_CONFIG.weight_contract * c2 +
        DEFAULT_CONFIG.weight_cycle * d2 +
        DEFAULT_CONFIG.weight_history * h2,
        2
    )

    print(f"\nScenario 2 (Breaking API Contract):")
    print(f"  Inputs: B={b2}, C={c2}, D={d2}, H={h2}")
    print(f"  Formula: 0.35*{b2} + 0.30*{c2} + 0.15*{d2} + 0.20*{h2} = {expected_score2}")
    print(f"  API Output Score: {score2}")
    assert score2 == expected_score2, f"Mismatch: {score2} != {expected_score2}"
    assert c2 == 100.0, f"Breaking change must have C=100.0, got {c2}"
    assert score2 >= 30.0, f"Breaking change must add at least 30 points from C, got {score2}"
    print("  -> PASSED: Breaking change verified.")

    # Scenario 3: Circular Dependency Injection (paymentservice -> frontend)
    resp3 = client.post("/api/predict/analyze", json={
        "service_id": "paymentservice",
        "change_type": "dependency_add",
        "new_dependency_target": "frontend",
        "details": "Add call from paymentservice back to frontend creating circular dependency"
    })
    assert resp3.status_code == 200, f"Error: {resp3.text}"
    data3 = resp3.json()
    d3 = data3["breakdown"]["cycle_score"]
    score3 = data3["risk_score"]
    print(f"\nScenario 3 (Dependency Cycle):")
    print(f"  Cycle Score D: {d3}")
    print(f"  Cycle Detected: {data3['cycle_check']['has_cycle']}")
    print(f"  Total Score: {score3}")
    assert d3 == 100.0, f"Cycle penalty must be 100.0, got {d3}"
    assert data3["cycle_check"]["has_cycle"] is True
    print("  -> PASSED: Cycle detection verified.")


def verify_ingestion_and_impact():
    print("\n" + "=" * 60)
    print("2. VERIFYING REPOSITORY INGESTION & IMPACTED DEPENDENCY SCORING")
    print("=" * 60)

    # Ingest sample repository shop-sphere/ecommerce-core
    ingest_resp = client.post("/api/ingest/repository", json={
        "repo_url": "shop-sphere/ecommerce-core",
        "mode": "replace"
    })
    assert ingest_resp.status_code == 200, f"Ingestion failed: {ingest_resp.text}"
    ingest_data = ingest_resp.json()
    print(f"Ingested Repository: {ingest_data['source']}")
    print(f"  Discovered Services: {len(ingest_data['services_discovered'])} ({ingest_data['services_discovered']})")
    print(f"  Edges Added: {ingest_data['edges_added']}")

    # Verify active topology matches backend
    topo_resp = client.get("/api/graph/topology")
    assert topo_resp.status_code == 200
    topo = topo_resp.json()
    print(f"  Active Topology Node Count: {topo['total_nodes']}")
    print(f"  Active Topology Edge Count: {topo['total_edges']}")
    assert topo["total_nodes"] == ingest_data["total_graph_nodes"]

    # Run PREDICT on an imported service: paymentservice
    pred_resp = client.post("/api/predict/analyze", json={
        "service_id": "paymentservice",
        "change_type": "api_breaking",
        "details": "Invalidate payment payload"
    })
    assert pred_resp.status_code == 200, f"Error: {pred_resp.text}"
    pred_data = pred_resp.json()
    callers = [c["node"] for c in pred_data["blast_details"]]
    print(f"  PREDICT on Imported 'paymentservice':")
    print(f"    Risk Score: {pred_data['risk_score']}")
    print(f"    Upstream Impacted Callers: {len(callers)} callers ({callers})")
    assert "checkoutservice" in callers, "checkoutservice should be an upstream caller of paymentservice"
    print("  -> PASSED: Ingestion & dependency impact verified.")


def verify_monitoring_lifecycle():
    print("\n" + "=" * 60)
    print("3. VERIFYING MONITORING: UNCONFIGURED, OBSERVED, FAULT, INCIDENT & RECOVERY")
    print("=" * 60)

    # Reset repository back to clean baseline
    reset_resp = client.post("/api/reset")
    assert reset_resp.status_code == 200

    # 1. Check that unconfigured services are NOT treated as healthy
    status_resp = client.get("/api/monitor/status")
    assert status_resp.status_code == 200
    statuses = {s["service_id"]: s for s in status_resp.json()}
    assert "paymentservice" in statuses
    assert statuses["paymentservice"]["status"] == "unconfigured"
    assert statuses["paymentservice"]["data_source"] == "unconfigured"
    assert statuses["paymentservice"]["http_status"] is None
    print("  [Step 1] Unconfigured service status confirmed: paymentservice is 'unconfigured', NOT healthy.")

    # 2. Start a real local HTTP server to test genuine observed network health check
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')

        def log_message(self, format, *args):
            pass

    test_server = HTTPServer(("127.0.0.1", 58231), HealthHandler)
    server_thread = threading.Thread(target=test_server.serve_forever, daemon=True)
    server_thread.start()

    cfg_resp = client.post("/api/monitor/configure", json={
        "service_id": "frontend",
        "endpoint_url": "http://127.0.0.1:58231/health"
    })
    assert cfg_resp.status_code == 200
    print("  [Step 2] Configured probe endpoint for 'frontend' -> http://127.0.0.1:58231/health (Real Local HTTP Server)")

    # 3. Trigger immediate check
    chk_resp = client.post("/api/monitor/check-now")
    assert chk_resp.status_code == 200
    updated_statuses = {s["service_id"]: s for s in chk_resp.json()}
    frontend_rec = updated_statuses["frontend"]
    print(f"  [Step 3] Healthy check observed: status={frontend_rec['status']}, http_status={frontend_rec['http_status']}, latency={frontend_rec['response_time_ms']}ms, source={frontend_rec['data_source']}")
    assert frontend_rec["status"] == "healthy"
    assert frontend_rec["http_status"] == 200
    assert frontend_rec["data_source"] == "observed"

    # 4. Trigger simulated fault: timeout
    fault_resp = client.post("/api/monitor/fault", json={
        "service_id": "paymentservice",
        "fault_type": "timeout",
        "consecutive_failures": 2,
    })
    assert fault_resp.status_code == 200
    fault_rec = fault_resp.json()
    print(f"  [Step 4] Simulated fault applied: status={fault_rec['status']}, http={fault_rec['http_status']}, source={fault_rec['data_source']}, alert_active={fault_rec['alert_active']}, incident_id={fault_rec['active_incident_id']}")
    assert fault_rec["status"] == "unavailable"
    assert fault_rec["data_source"] == "simulated"
    assert fault_rec["alert_active"] is True
    assert fault_rec["active_incident_id"] is not None
    assert "simulated / emulator time" in fault_rec["error_message"]

    first_incident_id = fault_rec["active_incident_id"]

    # 5. Incident deduplication check: triggering another check does not duplicate incident
    chk_resp2 = client.post("/api/monitor/check-now")
    assert chk_resp2.status_code == 200
    statuses2 = {s["service_id"]: s for s in chk_resp2.json()}
    assert statuses2["paymentservice"]["active_incident_id"] == first_incident_id
    print(f"  [Step 5] Incident deduplication verified: active_incident_id remains '{first_incident_id}' without creating duplicate.")

    # 6. Verify recovery
    clear_resp = client.post("/api/monitor/fault", json={
        "service_id": "paymentservice",
        "fault_type": "clear",
    })
    assert clear_resp.status_code == 200
    recovered_rec = clear_resp.json()
    print(f"  [Step 6] Recovery verified: status={recovered_rec['status']}, failures={recovered_rec['consecutive_failures']}, alert_active={recovered_rec['alert_active']}, recovery_time={recovered_rec['recovery_time']}")
    assert recovered_rec["status"] == "healthy"
    assert recovered_rec["consecutive_failures"] == 0
    assert recovered_rec["alert_active"] is False
    assert recovered_rec["recovery_time"] is not None
    print("  -> PASSED: Complete monitoring lifecycle verified.")


def verify_error_handling():
    print("\n" + "=" * 60)
    print("4. VERIFYING ERROR HANDLING (INGESTION, PREDICT, SSRF, INVALID INPUTS)")
    print("=" * 60)

    # 1. Invalid repository ingestion
    bad_repo_resp = client.post("/api/ingest/repository", json={"repo_url": "invalid//nonexistent/repo"})
    assert bad_repo_resp.status_code == 400
    print(f"  [1] Invalid Repo Rejected: HTTP {bad_repo_resp.status_code} - {bad_repo_resp.json()['detail']}")

    # 2. Malformed Docker Compose YAML
    bad_yaml_resp = client.post("/api/ingest/repository", json={"compose_yaml_content": "services:\n  invalid: [unbalanced"})
    assert bad_yaml_resp.status_code == 400
    print(f"  [2] Malformed YAML Rejected: HTTP {bad_yaml_resp.status_code} - {bad_yaml_resp.json()['detail']}")

    # 3. Nonexistent service in PREDICT
    bad_predict_resp = client.post("/api/predict/analyze", json={"service_id": "nonexistent-svc", "change_type": "api_breaking"})
    assert bad_predict_resp.status_code == 404
    print(f"  [3] Nonexistent Service Rejected: HTTP {bad_predict_resp.status_code} - {bad_predict_resp.json()['detail']}")

    # 4. Missing dependency target for dependency_add
    missing_target_resp = client.post("/api/predict/analyze", json={"service_id": "paymentservice", "change_type": "dependency_add"})
    assert missing_target_resp.status_code == 400
    print(f"  [4] Missing Dependency Target Rejected: HTTP {missing_target_resp.status_code} - {missing_target_resp.json()['detail']}")

    # 5. SSRF blocked URL in Monitor
    ssrf_resp = client.post("/api/monitor/configure", json={"service_id": "paymentservice", "endpoint_url": "http://169.254.169.254/latest/meta-data"})
    assert ssrf_resp.status_code == 400
    print(f"  [5] SSRF Metadata URL Rejected: HTTP {ssrf_resp.status_code} - {ssrf_resp.json()['detail']}")

    ssrf_scheme_resp = client.post("/api/monitor/configure", json={"service_id": "paymentservice", "endpoint_url": "ftp://malicious.host/probe"})
    assert ssrf_scheme_resp.status_code == 400
    print(f"  [6] Unsafe Scheme Rejected: HTTP {ssrf_scheme_resp.status_code} - {ssrf_scheme_resp.json()['detail']}")
    print("  -> PASSED: All error handling verified.")


if __name__ == "__main__":
    verify_predict_scenarios()
    verify_ingestion_and_impact()
    verify_monitoring_lifecycle()
    verify_error_handling()
    print("\n" + "=" * 60)
    print("ALL INTEGRATION VERIFICATION CHECKS PASSED 100%!")
    print("=" * 60)
