# Why Stateless RAG Fails at 3 AM: Building an SRE Incident Agent with Multi-Hop Memory

Production went down at 3:14 AM. Our payment gateway started throwing `JedisConnectionException: Could not get a resource from the pool`, cascading 502 Bad Gateways across checkout. 

The on-call engineer did what any exhausted engineer does: they pasted the stack trace into a standard LLM chat interface. The model offered polite, textbook advice: *"Restart your pods, check your Redis maxclients setting, or increase your client timeout."*

They restarted the pods. Within 90 seconds, the new pods exhausted the Redis connection pool again. The outage dragged on for another 45 minutes until someone remembered an incident from six weeks prior: an upstream canary deploy on our authentication service had leaked connection leases, silently starving the shared Redis cluster.

That night made something painfully obvious to me: **stateless LLMs and standard vector RAG fail at incident triage**. Standard RAG treats operational history as static chunks of text. It has no concept of causal dependencies, no timeline of deployments, and no mechanism to remember whether an attempted mitigation actually worked or made the outage worse.

Here is how we built **IncidentLens**—an incident triage agent with an active feedback loop powered by [Hindsight](https://github.com/vectorize-io/hindsight) agent memory.

---

## The Core Flaw of Vector RAG in Incident Response

When you index post-mortems into a standard vector database, retrieval relies almost entirely on cosine similarity of dense embeddings. In production incidents, this breaks in three predictable ways:

1. **Exact Error Signatures Get Blurred:** An embedding model blurs the distinction between `JedisConnectionException` and `JedisDataException`, treating them as generic "Redis errors" even though their operational root causes are completely different.
2. **Causal Graph Blindness & Surface Attribution Error:** In a 2-year study of thousands of production post-mortems published by Zalando Engineering, researchers found that even frontier LLMs suffer from a ~10% *Surface Attribution Error*—consistently diagnosing proximate symptoms (e.g. database connection exhaustion) rather than true root causes (e.g. an upstream canary deploy leaking socket leases). If Service A crashes because Service B exhausted a shared pool, semantic similarity alone will never bridge the dependency gap.
3. **The Discussion Noise Paradox:** A study by Roy et al. evaluating LLM RCA across 107,000 production incidents found that naively feeding raw incident discussion comments into an LLM does not yield meaningful diagnostic improvements. Unstructured chat is filled with human speculation, dead ends, and noise.
4. **The Amnesia Loop:** A stateless agent has no memory of outcomes. If it suggests restarting a pod and that restart fails, asking it again produces the exact same recommendation.

To fix this, an SRE agent needs what [Vectorize calls agent memory](https://vectorize.io/what-is-agent-memory): multi-strategy retrieval combined with a closed feedback loop that separates raw noise from typed, evidence-grounded facts.

---

## System Architecture & The Closed Learning Loop

IncidentLens couples ultra-fast LLM inference (via Groq's LPU running `openai/gpt-oss-120b`) with Hindsight's episodic memory engine. Rather than a passive search index, the architecture functions as a stateful feedback loop:

```
[ New P1 Alert & Stack Trace ]
              │
              ▼
[ Hindsight 4-Way Parallel Recall ]
 ├── BM25: Exact error codes & exceptions
 ├── Semantic: Natural language symptom matching
 ├── Graph: Microservice dependency traversal
 └── Temporal: Correlating deploys within a 2-hour window
              │
              ▼
[ Reciprocal Rank Fusion & Cross-Encoder ]
              │
              ▼
[ Triage Proposal: Ranked Fixes + Cited Memory IDs ]
              │
              ▼
[ Engineer Validates Fix: WORKED or FAILED ]
              │
              ▼
[ hs.retain() Stores Outcome as Experience Fact ]
              │
              ▼
[ Background Consolidation & Conflict Resolution via hs.reflect() ]
```

---

## How It Works in Code

Connecting the agent to Hindsight requires three foundational operations: `retain`, `recall`, and `reflect`.

### 1. Ingesting Incidents and Retaining Outcomes

When an engineer tries a mitigation during an outage, the outcome is immediately retained into the memory bank as an **Experience Fact**:

```python
from hindsight_client import Hindsight
from datetime import datetime

client = Hindsight(base_url="http://localhost:8888")

def record_mitigation_outcome(incident_id: str, service: str, action: str, status: str, notes: str):
    """
    Closes the feedback loop by storing human-validated mitigation results.
    """
    content = (
        f"During incident {incident_id} on service '{service}', the mitigation '{action}' "
        f"was attempted. Result: {status.upper()}. Engineer notes: {notes}."
    )
    
    client.retain(
        bank_id="sre-production-bank",
        content=content,
        context="mitigation_feedback_loop",
        timestamp=datetime.now(),
        metadata={
            "incident_id": incident_id,
            "service": service,
            "action": action,
            "status": status.upper(),
            "type": "experience"
        }
    )
```

### 2. Multi-Strategy Recall

When a new incident arrives, we query Hindsight across both world facts (past post-mortems) and experience facts (past mitigation outcomes):

```python
def recall_incident_context(service: str, error_signature: str):
    # Runs Semantic, BM25, Graph, and Temporal search in parallel
    results = client.recall(
        bank_id="sre-production-bank",
        query=f"{service} {error_signature}",
        types=["world", "experience", "observation"],
        budget="high"
    )
    return results.results
```

By specifying `types=["experience", "observation"]`, the agent retrieves not just what happened, but what *failed* when engineers tried to fix it.

### 3. Resolving Cross-Service Policy Conflicts

One of the hardest challenges in distributed systems is that a fix that works on Service A will often break Service B. For example, expanding thread pools on a Python/FastAPI service relieves request backlog, but doing the same on a Node.js cluster exhausts process memory.

We use Hindsight's `reflect()` method to resolve these conflicts:

```python
def resolve_service_conflict(service_a: str, service_b: str, policy: str):
    query = (
        f"How does the mitigation '{policy}' behave across {service_a} versus {service_b}? "
        f"Did it succeed on one service but fail on another? Explain the architectural reason."
    )
    answer = client.reflect(
        bank_id="sre-production-bank",
        query=query,
        context="cross_service_policy_resolution"
    )
    return answer.text
```

The [Hindsight documentation](https://hindsight.vectorize.io/) explains how `reflect()` runs an autonomous evidence-gathering loop over consolidated observations rather than raw text chunks.

---

## Empirical Evaluation: 3-Arm Holdout Generalization Benchmark

To ensure zero circular evaluation or train-test leakage, we benchmarked IncidentLens across **6 unseeded holdout microservice outage scenarios** (`HOLD-101` through `HOLD-601`). These incidents were **never ingested** into Hindsight memory.

We evaluated three distinct architectural configurations:
- **Arm A (Stateless LLM):** Zero memory, pure foundational model inference (`openai/gpt-oss-120b`).
- **Arm B (Naive Vector RAG):** Standard untyped semantic text similarity without feedback weighting.
- **Arm C (IncidentLens Memory Loop):** Hindsight multi-strategy typed memory (World Facts, Experience Facts, Observations) + closed human-in-the-loop feedback loop.

Here are the empirical results from our automated evaluation harness (`server/evaluate_agent.py --holdout`, recorded in `server/eval_results.json`):

| Evaluation Metric | Arm A: Stateless LLM | Arm B: Naive Vector RAG | Arm C: IncidentLens Loop | SRE Operational Impact |
|:---|:---:|:---:|:---:|:---|
| **Precedents Recalled (avg)** | `0.0` | `83.7` | **`86.3`** | Grounded multi-strategy retrieval |
| **Root Cause Accuracy** | `66.7%` | `83.3%` | **`100.0%`** | Accurate failure locus identification |
| **Verified Fix Rate** | `50.0%` | `83.3%` | **`100.0%`** | Actionable remediation identified |
| **Harmful Action Rate (lower=best)** | `50.0%` | `66.7%` | **`0.0%`** | Eliminates deadly trial-and-error |
| **Warning Against Fatal Failures** | `0.0%` | `0.0%` | **`100.0%`** | Enforces acquired negative constraints |
| **Closed Learning Loop (Before/After)** | Unsupported | Unsupported | **Verified (`/api/learning-demo`)** | Immediate negative constraint acquisition |
| **Average Latency (ms)** | `4752ms` | `8342ms` | **`7636ms`** | Real-time interactive SRE war room |

### The Critical Learning Moment
When an engineer marks a mitigation as `FAILED` (e.g., executing a rolling restart during a connection leak), IncidentLens immediately calls `hs.retain()` to persist the outcome as an **Experience Fact**. Upon re-triaging the same or similar incident, the model actively cites the failure and issues a critical safety warning: *"DO NOT restart service pods; past incident experience demonstrated that rebooting drained the connection pool within 90 seconds."* Naive RAG, by contrast, continues to recommend the same disastrous restart because it lacks outcome weighting.

---

## Honest Limitations & Lessons Learned

1. **Background Consolidation Latency:** Hindsight consolidates raw facts into observations asynchronously. In rapid 5-minute incident drills, newly retained experience facts take a short window to emerge as high-level observations. You must query raw experience facts alongside observations during active triage.
2. **Garbage In, Permanent Beliefs Out:** If an engineer incorrectly marks an ineffective fix as `WORKED`, the memory bank adopts that belief. Building a mechanism to deprecate or overwrite stale experience facts is essential for long-term reliability.
3. **Token Budgets vs. Top-K:** Budgeting retrieval by token count rather than top-k results prevented prompt overflow when dealing with massive 200-line stack traces.

---

## Conclusion

Stateless AI assistants give generic advice because they have no lived experience with your infrastructure. By combining multi-strategy retrieval with an active outcome feedback loop, agents can transform from passive search engines into genuine operational memory for engineering teams.

If you are building memory-augmented agents, check out the [Hindsight GitHub repository](https://github.com/vectorize-io/hindsight) and explore how structured memory changes agent reasoning.
