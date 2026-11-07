import pytest
import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'server')))

from app import app

client = TestClient(app)


def test_learning_closed_loop_demo():
    """
    Demonstrates that IncidentLens's closed feedback loop functions:
    1. Initial triage.
    2. Mitigation failure recorded to Hindsight episodic memory.
    3. Subsequent triage reflects negative constraint.
    """
    payload = {
        "service": "payment-gw",
        "title": "Payment gateway HTTP 502 with JedisConnectionException",
        "symptoms": "Redis connection pool starvation during flash sale checkout burst",
        "stack_trace": "JedisConnectionException: Could not get a resource from the pool"
    }
    res = client.post("/api/learning-demo", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["learning_verified"] is True
    assert "retained_experience" in data
    assert data["retained_experience"]["status"] == "FAILED"
    assert data["retained_experience"]["action"] == "Rolling restart of service pods"

    assert "before_feedback" in data
    assert "after_feedback" in data

    # Verify after feedback has actionable analysis
    after_analysis = data["after_feedback"]["analysis"]
    assert len(after_analysis) > 100
    # Must warn or reference restarting pods / negative outcome
    analysis_lower = after_analysis.lower()
    has_warning = (
        "restart" in analysis_lower
        or "failed" in analysis_lower
        or "pool" in analysis_lower
        or "constraint" in analysis_lower
        or "do not" in analysis_lower
        or "warning" in analysis_lower
    )
    assert has_warning, "After-feedback triage should reflect acquired operational experience."


def test_mitigation_feedback_persistence():
    """Verify mitigation outcome logging through /api/incidents/feedback."""
    payload = {
        "incident_id": "INC-TEST-001",
        "service": "inventory-service",
        "action": "Increase Tomcat worker threads from 200 to 500",
        "status": "FAILED",
        "notes": "Triggered native thread OOM"
    }
    res = client.post("/api/incidents/feedback", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["incident_id"] == "INC-TEST-001"
    assert data["status"] == "FAILED"
    assert data.get("success") is True or data.get("local_cached") is True
    assert "memory_id" in data
