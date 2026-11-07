# IncidentLens — Known Limitations, Assumptions & Production Boundary Conditions

This document provides a transparent, engineering-first audit of IncidentLens's current architecture, dataset scope, failure modes, and production prerequisites.

---

## 1. Dataset Scope & Synthetic Evaluation

- **Curated Post-Mortem Catalog (N=20):**  
  The historical knowledge bank is seeded with 20 curated microservice outage post-mortems across 5 recurring distributed system failure clusters:
  1. Redis connection pool starvation and timeout cascades (`payment-gw`)
  2. PostgreSQL deadlock chains under concurrent un-ordered batch operations (`inventory-service`)
  3. Upstream partner HTTP rate limiting and backpressure failures (`auth-service`, `billing-service`)
  4. Kafka consumer partition rebalance storms (`order-service`, `analytics-worker`)
  5. JVM Metaspace ClassLoader leaks and heap exhaustion (`notification-service`)

- **Generalization Holdout Benchmark (N=6):**  
  Evaluation of generalization is conducted on 6 distinct held-out scenarios (`HOLD-101` through `HOLD-601`). These incidents are **never seeded** into Hindsight episodic memory to ensure zero train-test data leakage.
- **Realistic but Synthetic Scenarios:**  
  While all scenarios are modeled directly after published real-world SRE post-mortems (Netflix, Uber, GitHub, Stripe), they are synthetically structured into reproducible JSON post-mortems to allow deterministic, automated CI/CD evaluation without exposing proprietary telemetry.

---

## 2. Integration Modes & Simulated Capabilities

- **Band AI Desktop War Room Bridge (Simulation Preview):**  
  The Band AI War Room endpoint (`/api/band/war-room`) generates real collaborative war room state (session tokens, participant roles, telemetry sync schemas, and runbook handoffs). In this version, it operates as a **simulated integration preview** for demonstration and UI testing, rather than executing live background RPC daemons against a local desktop client.
- **Dual-Mode Inference & Graceful Degradation:**  
  IncidentLens is designed for high availability:
  - **Live Mode:** Powered by Groq LPU (`llama-3.3-70b-versatile` / `openai/gpt-oss-120b`) + Hindsight Cloud.
  - **Cognitive Synthesis Fallback:** If upstream LLM quotas are exhausted or network timeouts occur, the engine falls back to deterministic SRE heuristic synthesis. Triage proposals remain operational, grounded, and structurally valid, but lack the conversational depth of a 70B parameter model.

---

## 3. Failure Modes & Boundary Conditions

- **Novel Failure Domains (Abstention vs. Hallucination):**  
  When an incident features an error signature with zero relevant precedents in the memory bank (e.g., `HOLD-601` Amazon S3 `503 SlowDown` throttling during unpartitioned batch export), IncidentLens calculates an error domain overlap score. When overlap is negligible, it flags `grounded: False` and explicitly warns that no high-confidence historical precedent exists, rather than forcing a hallucinated recommendation from an unrelated database or Kafka outage.
- **Operator Feedback Drift:**  
  IncidentLens internalizes negative operational constraints when an engineer flags a mitigation as `FAILED`. If an operator erroneously marks a correct fix as `FAILED`, the agent will temporarily incorporate this negative constraint. In production, this requires an administrative curation workflow or confidence decay weighting over time.
- **Latency Under Cold-Start Recall:**  
  Hindsight semantic and episodic recall over cloud endpoints typically takes between 600ms and 1800ms. End-to-end triage latency averages ~7-9 seconds when combined with a full 70B parameter inference stream.

---

## 4. Production Deployment Prerequisites

To deploy IncidentLens in enterprise environments with live production traffic, the following controls should be implemented:

1. **Webhook Signature Verification:**  
   Configure HMAC SHA-256 signature verification (`X-Hub-Signature-256` or `X-PagerDuty-Signature`) on `/api/webhooks/alert` to prevent unauthenticated alert injection.
2. **Multi-Tenant Bank Partitioning:**  
   Configure separate `bank_id` instances per engineering domain (e.g., `sre-payments-prod`, `sre-infrastructure-prod`) to prevent cross-team policy crosstalk.
3. **Secret Management:**  
   Store `HINDSIGHT_API_KEY` and `GROQ_API_KEY` in HashiCorp Vault, AWS Secrets Manager, or Doppler with automated rotation.
4. **Audit Trail & Rollback:**  
   Log all autonomous policy reflection proposals to an immutable append-only audit log before applying automated remediation scripts.

