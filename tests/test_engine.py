import pytest
import sys
import os

# Add server to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'server')))

from dataset import INCIDENTS
from engine import IncidentLensEngine


def test_dataset_integrity():
    assert len(INCIDENTS) == 20
    required_keys = ["id", "service", "severity", "title", "symptoms", "stack_trace", "root_cause", "verified_fix"]
    for inc in INCIDENTS:
        for k in required_keys:
            assert k in inc, f"Missing {k} in {inc.get('id')}"


def test_engine_init():
    engine = IncidentLensEngine(bank_id="test-bank")
    assert engine.bank_id == "test-bank"
    assert engine.groq_model in ["llama-3.3-70b-versatile", "openai/gpt-oss-120b"]


def test_triage_stateless_execution():
    engine = IncidentLensEngine(bank_id="test-bank")
    sample = INCIDENTS[0]
    res = engine.triage_incident(
        title=sample["title"],
        service=sample["service"],
        symptoms=sample["symptoms"],
        stack_trace=sample["stack_trace"],
        use_memory=False
    )
    assert res["service"] == sample["service"]
    assert res["use_memory"] is False
    assert "analysis" in res
    assert len(res["analysis"]) > 50


def test_honest_offline_feedback_reporting():
    # When Hindsight is pointed to a dead port, record_mitigation_outcome must report success=False
    engine = IncidentLensEngine(bank_id="test-bank")
    engine.hindsight_base_url = "http://localhost:9999" # Deliberately dead port
    outcome = engine.record_mitigation_outcome(
        incident_id="INC-TEST",
        service="test-service",
        action="restarted pods",
        status="FAILED"
    )
    assert outcome["success"] is False
    assert outcome["error"] is not None
