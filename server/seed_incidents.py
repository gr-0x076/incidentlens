"""
IncidentLens Seeding & Memory Inspection Script
Ingests public SRE incidents into Hindsight and tests single-incident fact extraction before batching.
"""

import sys
import time
from dataset import INCIDENTS
from engine import IncidentLensEngine


def seed_and_inspect():
    print("=" * 60)
    print("IncidentLens — Hindsight Seeding & Memory Inspection")
    print("=" * 60)

    engine = IncidentLensEngine(bank_id="incidentlens-sre-bank")

    if not engine.hs_client:
        print("[!] Hindsight client not connected. Is Hindsight running?")
        print("    Run local Docker: docker run -p 8888:8888 ghcr.io/vectorize-io/hindsight:latest")
        print("    Or set HINDSIGHT_BASE_URL and HINDSIGHT_API_KEY in .env")
        sys.exit(1)

    print(f"[*] Connected to Hindsight at: {engine.hindsight_base_url}")
    print(f"[*] Memory Bank: {engine.bank_id}")

    # Step 1: Ingest 1 Incident First & Inspect (Safety requirement)
    sample = INCIDENTS[0]
    print(f"\n--> Step 1: Retaining single test incident: {sample['id']} ({sample['service']})...")
    mem_ref = engine.retain_incident(sample)
    print(f"[✓] Retained successfully! Reference: {mem_ref}")

    print("\n--> Step 2: Testing Recall on the test incident...")
    recalled = engine.recall_incident_context("JedisConnectionException payment-gw", service="payment-gw")
    print(f"[✓] Recall returned {len(recalled)} memories:")
    for i, m in enumerate(recalled[:3]):
        print(f"    [{i+1}] ({m['type']}): {m['text'][:120]}...")

    # Step 3: Test Closed-Loop Feedback Retention
    print("\n--> Step 3: Testing Closed Feedback Loop (Recording WORKED/FAILED outcomes)...")
    outcome1 = engine.record_mitigation_outcome(
        incident_id=sample["id"],
        service=sample["service"],
        action="Restarted payment-gw pods",
        status="FAILED",
        notes="Pods drained connection pool within 90 seconds."
    )
    print(f"[✓] Recorded FAILED mitigation: {outcome1['action']}")

    outcome2 = engine.record_mitigation_outcome(
        incident_id=sample["id"],
        service=sample["service"],
        action="Rolled back auth-service to v2.4.0",
        status="WORKED",
        notes="Pool recovered immediately."
    )
    print(f"[✓] Recorded WORKED mitigation: {outcome2['action']}")

    # Step 4: Batch Ingest Remaining Incidents
    print(f"\n--> Step 4: Batch ingesting remaining {len(INCIDENTS)-1} incidents...")
    for inc in INCIDENTS[1:]:
        engine.retain_incident(inc)
        # Also retain historical mitigation attempts as experience facts
        for attempt in inc.get("attempted_mitigations", []):
            engine.record_mitigation_outcome(
                incident_id=inc["id"],
                service=inc["service"],
                action=attempt["action"],
                status=attempt["status"],
                notes=attempt.get("notes", "")
            )
        print(f"    [+] Ingested {inc['id']} ({inc['service']}) with {len(inc.get('attempted_mitigations', []))} outcomes")

    print("\n[✓] Ingestion complete! Memory bank is populated with 20 incidents and experience facts.")
    print("[*] Note: Hindsight background consolidation will automatically deduplicate and build Observations.")


if __name__ == "__main__":
    seed_and_inspect()
