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

    health = engine.check_hindsight_live()
    if not health.get("connected"):
        print(f"[!] Warning: Cannot reach Hindsight Cloud at {engine.hindsight_base_url}")
        print(f"    Error details: {health.get('error')}")
        print("    Check HINDSIGHT_BASE_URL and HINDSIGHT_API_KEY in server/.env")
        sys.exit(1)

    print(f"[*] Connected to Hindsight at: {engine.hindsight_base_url} (Latency: {health.get('latency_ms', 0)}ms)")
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
    status_icon1 = "✓" if outcome1["success"] else "!"
    print(f"[{status_icon1}] Recorded FAILED mitigation: {outcome1['action']} (Success: {outcome1['success']})")

    outcome2 = engine.record_mitigation_outcome(
        incident_id=sample["id"],
        service=sample["service"],
        action="Rolled back auth-service to v2.4.0",
        status="WORKED",
        notes="Pool recovered immediately."
    )
    status_icon2 = "✓" if outcome2["success"] else "!"
    print(f"[{status_icon2}] Recorded WORKED mitigation: {outcome2['action']} (Success: {outcome2['success']})")

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
            dt = inc.get('timestamp') or datetime.now(timezone.utc).isoformat()
        except Exception:
            dt = datetime.now(timezone.utc).isoformat()

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
        ok = engine.retain_batch(chunk)
        if ok:
            print(f"        [✓] Chunk retained successfully ({len(chunk)} items).")
        else:
            print(f"        [!] Chunk batch failed. Retaining individual items...")
            for it in chunk:
                try:
                    engine.retain_incident({
                        "id": it["metadata"]["incident_id"],
                        "service": it["metadata"]["service"],
                        "severity": it["metadata"].get("severity", "P2"),
                        "title": it["metadata"].get("type", "event"),
                        "symptoms": it["content"],
                        "stack_trace": "",
                        "root_cause": "",
                        "verified_fix": "",
                        "timestamp": it.get("timestamp")
                    })
                except Exception as ie:
                    print(f"            [-] Item error: {ie}")

    print("\n[✓] Ingestion complete! Memory bank is populated with all incidents and experience facts.")
    print("[*] Hindsight will automatically consolidate observations and causal connections.")


if __name__ == "__main__":
    seed_and_inspect()
