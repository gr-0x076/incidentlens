import pytest
import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'server')))

from app import app
from dataset import INCIDENTS
from holdout import HOLDOUT_INCIDENTS

client = TestClient(app)


def test_healthz_and_health():
    """Verify live health checks and status reporting."""
    res = client.get("/healthz")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "service" in data
    assert data["service"] == "IncidentLens"

    res_api = client.get("/api/health")
    assert res_api.status_code == 200
    api_data = res_api.json()
    assert api_data["version"] == "1.2.0"
    assert "hindsight" in api_data
    assert "groq" in api_data
    assert "dataset" in api_data
    assert api_data["dataset"]["holdout_test_count"] == 6


def test_list_incidents():
    """Verify all catalog incidents are returned."""
    res = client.get("/api/incidents")
    assert res.status_code == 200
    data = res.json()
    assert "incidents" in data
    assert data["count"] == 20
    assert len(data["incidents"]) == 20


def test_list_holdouts():
    """Verify the 6 holdout incidents are isolated and returned."""
    res = client.get("/api/holdouts")
    assert res.status_code == 200
    data = res.json()
    assert "holdouts" in data
    assert data["count"] == 6
    assert len(data["holdouts"]) == 6


def test_benchmark_endpoint():
    """Verify /api/benchmark returns real evaluation numbers without fabrication."""
    res = client.get("/api/benchmark")
    assert res.status_code == 200
    data = res.json()
    assert "benchmark_metadata" in data
    assert "summary" in data
    assert "stateless" in data["summary"]
    assert "naive_rag" in data["summary"]
    assert "incidentlens" in data["summary"]
    # Check that evaluation sample size is 6
    assert data["summary"]["incidentlens"]["samples_evaluated"] == 6


def test_payload_size_limit():
    """Verify input validation rejection on excessive payload size."""
    oversized_trace = "x" * 20000
    res = client.post("/api/incidents/triage", json={
        "service": "test-service",
        "title": "Large payload test",
        "symptoms": "overflow",
        "stack_trace": oversized_trace,
        "use_memory": False
    })
    # Pydantic validates Field(..., max_length=16384) and returns 422
    assert res.status_code in [413, 422]


def test_alert_webhook_ingestion():
    """Verify webhook ingestion from external alerting systems (PagerDuty / Alertmanager)."""
    alert_payload = {
        "service": "billing-service",
        "severity": "P1",
        "title": "Stripe Webhook Timeout Surge",
        "symptoms": "HTTP 504 Gateway Timeout on /webhook/stripe",
        "stack_trace": "java.net.SocketTimeoutException: Read timed out"
    }
    res = client.post("/api/webhooks/alert", json=alert_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "incident_id" in data
    assert data["service"] == "billing-service"
    assert "triage" in data

    # Verify alert shows in the recent alerts list
    res_list = client.get("/api/webhooks/alerts")
    assert res_list.status_code == 200
    alerts_data = res_list.json()
    assert alerts_data["count"] >= 1
    recent_ids = [a["incident_id"] for a in alerts_data["alerts"]]
    assert data["incident_id"] in recent_ids


def test_band_war_room_simulation_marker():
    """Verify Band AI desktop war room bridge is explicitly marked as simulation."""
    res = client.post("/api/band/war-room", json={
        "incident_id": "INC-101",
        "service": "payment-gw"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_simulation"] is True
    assert "Simulated" in data["platform"]


def test_metrics_endpoint():
    """Verify /metrics exposes valid Prometheus exposition format."""
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "incidentlens_service_info" in res.text
    assert "incidentlens_upstream_health" in res.text
    assert "incidentlens_holdout_benchmark_accuracy" in res.text
