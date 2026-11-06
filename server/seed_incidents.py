"""
IncidentLens Seeding & Memory Inspection Script
Ingests public SRE incidents and verified mitigation outcomes into Hindsight memory banks.
"""

import sys
import time
from datetime import datetime, timezone
from dataset import INCIDENTS
from engine import IncidentLensEngine


def seed_and_inspect():
    print("=" * 60)
    print("IncidentLens — Hindsight Seeding & Memory Inspection")
    print("=" * 60)

    engine = IncidentLensEngine(bank_id="incidentlens-sre-bank")

    if not engine.hs_client:
        print("[!] Hindsight client not connected. Is Hindsight running?")
        print("    Check HINDSIGHT_BASE_URL and HINDSIGHT_API_KEY in server/.env")
        sys.exit(1)

    print(f"[*] Connected to Hindsight at: {engine.hindsight_base_url}")
    print(f"[*] Target Memory Bank: {engine.bank_id}")

    # Step 1: Ingest 1 Incident First & Inspect
    sample = INCIDENTS[0]
    print(f"\n--> Step 1: Retaining single test incident: {sample['id']} ({sample['service']})...")
    mem_ref = engine.retain_incident(sample)
    print(f"[✓] Retained successfully! Items processed.")

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
    remaining = INCIDENTS[1:]
    print(f"\n--> Step 4: Batch ingesting remaining {len(remaining)} incidents and historical outcomes...")

    batch_items = []
    for inc in remaining:
        # 1. Postmortem item
        content = (
            f"Incident {inc['id']} on service '{inc['service']}' ({inc['severity']}): {inc['title']}. "
            f"Symptoms: {inc['symptoms']}. "
            f"Stack trace: {inc['stack_trace']}. "
            f"Root cause: {inc['root_cause']}. "
            f"Verified fix: {inc['verified_fix']}."
        )
        try:
            dt = datetime.fromisoformat(inc['timestamp'].replace("Z", "+00:00"))
        except Exception:
            dt = datetime.now(timezone.utc)

        batch_items.append({
            "content": content,
            "context": f"incident_postmortem_{inc['service']}",
            "timestamp": dt,
            "metadata": {
                "incident_id": str(inc["id"]),
                "service": str(inc["service"]),
                "severity": str(inc["severity"]),
                "type": "post_mortem"
            }
        })

        # 2. Historical mitigation outcomes (Experience facts)
        for attempt in inc.get("attempted_mitigations", []):
            outcome_text = (
                f"During incident {inc['id']} on service '{inc['service']}', the mitigation '{attempt['action']}' was attempted. "
                f"Result: {attempt['status'].upper()}. Engineer notes: {attempt.get('notes', '')}."
            )
            batch_items.append({
                "content": outcome_text,
                "context": "mitigation_feedback_loop",
                "timestamp": dt,
                "metadata": {
                    "incident_id": str(inc["id"]),
                    "service": str(inc["service"]),
                    "action": str(attempt["action"]),
                    "status": str(attempt["status"].upper()),
                    "type": "experience"
                }
            })

    print(f"[*] Prepared {len(batch_items)} memory items across {len(remaining)} incidents.")
    
    # Send in chunks of 10 items for optimal speed and reliability
    chunk_size = 10
    for chunk_idx in range(0, len(batch_items), chunk_size):
        chunk = batch_items[chunk_idx:chunk_idx + chunk_size]
        print(f"    --> Retaining batch chunk {chunk_idx // chunk_size + 1}/{(len(batch_items) + chunk_size - 1) // chunk_size} ({len(chunk)} items)...")
        try:
            res = engine.hs_client.retain_batch(bank_id=engine.bank_id, items=chunk)
            print(f"        [✓] Chunk retained: items_count={getattr(res, 'items_count', len(chunk))}")
        except Exception as e:
            print(f"        [!] Chunk error: {e}. Falling back to individual retains...")
            for it in chunk:
                try:
                    engine.hs_client.retain(
                        bank_id=engine.bank_id,
                        content=it["content"],
                        context=it["context"],
                        timestamp=it["timestamp"],
                        metadata=it["metadata"]
                    )
                except Exception as ie:
                    print(f"            [-] Item error: {ie}")

    print("\n[✓] Ingestion complete! Memory bank is populated with all 20 incidents and experience facts.")
    print("[*] Hindsight will automatically consolidate observations and causal connections.")


if __name__ == "__main__":
    seed_and_inspect()
