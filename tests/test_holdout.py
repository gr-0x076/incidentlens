import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'server')))

from dataset import INCIDENTS
from holdout import HOLDOUT_INCIDENTS, HOLDOUT_IDS


def test_holdout_train_test_separation():
    """
    Strict proof that held-out incidents are completely disjoint from the training dataset.
    Train-Test leakage must be ZERO.
    """
    training_ids = set(inc["id"] for inc in INCIDENTS)
    holdout_ids = set(HOLDOUT_IDS)

    # Must have 6 held-out incidents
    assert len(holdout_ids) == 6
    assert len(HOLDOUT_INCIDENTS) == 6

    # Intersection must be empty (ZERO leakage)
    intersection = training_ids.intersection(holdout_ids)
    assert len(intersection) == 0, f"Data leakage detected! IDs in both train and holdout: {intersection}"


def test_holdout_schema_completeness():
    """
    Ensure all held-out incidents specify valid test criteria including negative actions.
    """
    required_keys = [
        "id", "service", "severity", "title", "symptoms", 
        "stack_trace", "root_cause", "verified_fix", "negative_actions"
    ]
    for inc in HOLDOUT_INCIDENTS:
        for k in required_keys:
            assert k in inc, f"Missing key {k} in holdout incident {inc.get('id')}"
        assert isinstance(inc["negative_actions"], list), f"negative_actions must be a list in {inc['id']}"
        assert len(inc["negative_actions"]) > 0, f"negative_actions cannot be empty in {inc['id']}"


def test_holdout_diversity():
    """
    Ensure holdout set covers multiple failure categories (database, network/HTTP, kafka, etc.).
    """
    services = set(inc["service"] for inc in HOLDOUT_INCIDENTS)
    assert len(services) >= 4, f"Holdout services must be diverse, got: {services}"

