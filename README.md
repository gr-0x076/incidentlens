# IncidentLens — SRE Post-Mortem Memory Agent

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Hindsight-v1.2%20Memory-purple?style=for-the-badge" alt="Hindsight v1.2">
  <img src="https://img.shields.io/badge/Groq%20LPU-GPT--OSS--120B-orange?style=for-the-badge" alt="Groq LPU">
  <img src="https://img.shields.io/badge/FastAPI-Production-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Band%20AI-War%20Room%20Mesh-indigo?style=for-the-badge" alt="Band AI">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License MIT">
</p>

---

## The 3:14 AM Problem

It is 3:14 AM on a Saturday. Your payment gateway starts throwing `JedisConnectionException: Could not get a resource from the pool`, cascading HTTP 502 Bad Gateways across checkout.

Your exhausted on-call engineer copies the stack trace into a standard LLM chat assistant. The model offers polite, generic textbook advice:  
> *"Restart your payment gateway pods, check your Redis maxclients setting, or increase your pool timeout."*

They restart the pods. Within 90 seconds, the new pods crash again.

**Why?** Because 6 weeks ago, someone already tried restarting those exact pods for the exact same error—and it failed because an upstream authentication canary was leaking connection leases. 

Stateless LLMs and standard vector RAG fail at incident triage because:
1. **They have amnesia:** They don't know your architecture, your recent deploys, or what happened 6 weeks ago.
2. **They have zero feedback loop:** If an engineer follows their suggestion and it makes the outage worse, asking the model again yields the exact same recommendation.
3. **They suffer from Surface Attribution Error:** In a 2-year study of thousands of production post-mortems published by Zalando Engineering, researchers found that LLMs misdiagnose proximate symptoms (e.g. database pool exhaustion) as root causes, completely missing cross-service upstream leaks.

**IncidentLens** fixes this by giving SRE incident agents **episodic operational memory** powered by [Hindsight](https://github.com/vectorize-io/hindsight).

---

## How It Works

```mermaid
flowchart TD
    subgraph AlertPhase ["1. Real-Time Outage Ingestion"]
        Alert["🚨 Production Alert / P1 Incident<br/>(Service: payment-gw, Stack Trace, Recent Deploys)"] --> Engine["IncidentLens Core Engine"]
    end

    subgraph RecallPhase ["2. Hindsight 4-Way Parallel Retrieval"]
        Engine --> HRecall["Hindsight Multi-Strategy Recall"]
        HRecall --> B1["<b>BM25</b><br/>Exact error codes & exception signatures"]
        HRecall --> B2["<b>Semantic</b><br/>Natural language symptom matching"]
        HRecall --> B3["<b>Graph</b><br/>Microservice dependency tree traversal"]
        HRecall --> B4["<b>Temporal</b><br/>Recent canary/deploy windows (< 2 hrs)"]
        B1 & B2 & B3 & B4 --> Fusion["Reciprocal Rank Fusion & Reranker"]
    end

    subgraph GroundingPhase ["3. Actionable Triage Proposal"]
        Fusion --> Proposal["<b>Triage Proposal with Cited Precedents</b><br/>• Verified Remediation: Roll back auth-service canary<br/>• ⚠️ WARNING: DO NOT restart pods (failed in INC-101)"]
    end

    subgraph FeedbackPhase ["4. Closed Learning Loop (Human-in-the-Loop)"]
        Proposal --> Engineer["Engineer Executes & Validates"]
        Engineer -->|"Fix Succeeded"| RetainW["hs.retain(outcome='WORKED')<br/>Saved as Experience Fact"]
        Engineer -->|"Fix Failed"| RetainF["hs.retain(outcome='FAILED')<br/>Saved as Warning Fact"]
        RetainW & RetainF --> Bank[("Hindsight Episodic Memory Bank")]
        Bank -->|"Autonomous Reflection"| Reflect["hs.reflect()<br/>Resolves Cross-Service Policy Conflicts"]
        Reflect -.->|"Informs Next Incident"| Engine
    end
```

---

## Visual Product Tour

### 1. SRE Executive Console & Active Triage
The console organizes live telemetry, multi-strategy precedent retrieval, and actionable runbooks in an enterprise-grade dark interface:

<p align="center">
  <img src="docs/images/dashboard.png" width="100%" alt="IncidentLens Dashboard" />
</p>

### 2. Live Investigation & Precedent Citations
Recalls 100+ cited memory nodes, separates verified fixes from deadly pitfalls, and provides exact shell commands:

<p align="center">
  <img src="docs/images/triage_result.png" width="100%" alt="IncidentLens Triage Result" />
</p>

### 3. Head-to-Head: Stateless Baseline vs. IncidentLens Memory Loop
Side-by-side empirical comparison showing how memory eliminates repeat mistakes during active P1 outages:

<p align="center">
  <img src="docs/images/compare_modal.png" width="100%" alt="Stateless vs Memory Comparison Modal" />
</p>


## Cross-Service Policy Reflection (`reflect()`)

One of the most dangerous traps in distributed architectures is applying a fix that works on Service A to Service B, triggering an immediate crash. 

IncidentLens uses Hindsight's `reflect()` agentic loop to analyze cross-service divergence before mitigations are applied:

```mermaid
flowchart LR
    A["Mitigation Action:<br/><b>Increase worker thread pool</b>"] --> B{"Hindsight reflect() Loop"}
    B -->|"Python / FastAPI<br/>(inventory-service)"| C["<b>Succeeds</b><br/>Relieves async I/O worker starvation<br/>Memory overhead minimal"]
    B -->|"Java / Spring Boot<br/>(payment-gw)"| D["<b>CRASHES (OutOfMemoryError)</b><br/>Native OS thread exhaustion<br/>Cascades into JVM death"]
```

---

## Empirical Benchmark Results (3-Arm Holdout Generalization)

To ensure zero circular evaluation or train-test leakage, IncidentLens is benchmarked against **6 held-out microservice incidents** (`HOLD-101` through `HOLD-601`) that are **never seeded** into Hindsight memory.

We evaluated 3 distinct architectural arms:
- **Arm A (Stateless LLM):** Zero memory, pure foundational model inference.
- **Arm B (Naive Vector RAG):** Standard un-typed semantic similarity without feedback weighting.
- **Arm C (IncidentLens Memory Loop):** Hindsight multi-strategy typed memory + human-in-the-loop closed feedback loop.

| Evaluation Metric | Arm A: Stateless LLM | Arm B: Naive Vector RAG | Arm C: IncidentLens Loop | SRE Impact |
|:---|:---:|:---:|:---:|:---|
| **Precedents Recalled (avg)** | `0.0` | `83.7` | **`86.3`** | Grounded multi-strategy retrieval |
| **Root Cause Accuracy** | `66.7%` | `83.3%` | **`100.0%`** | Accurate failure locus identification |
| **Verified Fix Rate** | `50.0%` | `83.3%` | **`100.0%`** | Actionable remediation identified |
| **Harmful Action Rate (lower=best)** | `50.0%` | `66.7%` | **`0.0%`** | Eliminates deadly trial-and-error |
| **Warning Against Fatal Failures** | `0.0%` | `0.0%` | **`100.0%`** | Enforces acquired negative constraints |
| **Closed Learning Loop (Before/After)** | Unsupported | Unsupported | **Verified (`/api/learning-demo`)** | Immediate negative constraint acquisition |
| **Average Latency (ms)** | `4752ms` | `8342ms` | **`7636ms`** | Real-time interactive SRE war room |

> [!NOTE]
> All benchmark results are reproducible with `python server/evaluate_agent.py --holdout` and served live via `GET /api/benchmark`.  
> For full disclosure on synthetic scope, boundary conditions, and failure abstention, see [LIMITATIONS.md](LIMITATIONS.md).

---

## 🧪 Automated Verification & Test Suite

IncidentLens includes an end-to-end automated test suite verifying holdout separation, API contracts, webhook alert ingestion, and the closed learning loop:

```bash
# Run complete test suite (17 tests)
python -m pytest tests/ -v
```

Tests include:
- `tests/test_holdout.py`: Mathematical proof of zero train-test leakage (`set(TRAIN) ∩ set(HOLDOUT) == ∅`).
- `tests/test_api.py`: Payload size limits (422/413), health checks (`/healthz`, `/api/health`), and external alert webhooks (`/api/webhooks/alert`).
- `tests/test_learning.py`: Automated before $\rightarrow$ operator feedback $\rightarrow$ after triage diff verification.
- `tests/test_engine.py`: Resilient fallback and offline error reporting.

---

## ⚡ Quick Start (3 Steps)

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/gr-0x076/incidentlens.git
cd incidentlens
pip install -r server/requirements.txt
```

### 2. Configure Environment Variables
Copy the example environment file and add your credentials:
```bash
cp server/.env.example server/.env
```

Edit `server/.env`:
```env
HINDSIGHT_BASE_URL=https://api.hindsight.vectorize.io
HINDSIGHT_API_KEY=your_hindsight_api_key
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
```

### 3. Start the Server
```bash
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
```
Open [`http://localhost:8000`](http://localhost:8000) in your browser.

---

## 🤝 Multi-Agent War Room (Band Desktop Integration)

IncidentLens integrates with **Band Desktop** and **Band CLI** to spin up multi-agent collaborative incident response sessions:

```powershell
# Windows PowerShell
.\band\incident_war_room.ps1 -IncidentId INC-101 -Service payment-gw
```

```bash
# Linux / macOS Bash
./band/incident_war_room.sh INC-101 payment-gw
```

This bridges the SRE on-call engineer, the IncidentLens memory bot, and infrastructure monitoring peers into a synchronized channel.

---

## Repository Structure

```
incidentlens/
├── band/                               # Band AI Desktop multi-agent integration
│   ├── incident_war_room.ps1           # Windows PowerShell session coordinator
│   └── incident_war_room.sh            # Linux/macOS session coordinator
├── content/                            # Launch package & technical publication
│   ├── article_draft.md                # Technical deep-dive article draft
│   ├── video_script.md                 # 3-minute video recording walkthrough & titles
│   ├── linkedin_post.txt               # High-signal LinkedIn post
│   └── reddit_post.txt                 # Technical community discussion post
├── docs/
│   └── images/                         # Project UI screenshots & visual assets
│       ├── dashboard.png               # Executive console screenshot
│       ├── triage_result.png           # Live investigation & precedents
│       └── compare_modal.png           # Head-to-head empirical comparison modal
├── server/                             # Production FastAPI application & Engine
│   ├── app.py                          # REST API, alert webhooks & static routing
│   ├── engine.py                       # IncidentLens agent logic & Hindsight REST client
│   ├── dataset.py                      # 20 curated microservice post-mortems
│   ├── holdout.py                      # 6 un-seeded holdout scenarios for generalization test
│   ├── seed_incidents.py               # Memory ingestion script (retains world & experience facts)
│   ├── evaluate_agent.py               # 3-Arm empirical holdout benchmark harness
│   ├── eval_results.json               # Recorded benchmark metrics (single source of truth)
│   ├── requirements.txt                # Python dependencies
│   ├── .env.example                    # Environment template
│   └── static/
│       └── index.html                  # Modern enterprise incident console (Tailwind & Marked.js)
├── tests/                              # Automated Pytest suite (17 test cases)
│   ├── test_api.py                     # API contracts, health checks, webhook tests
│   ├── test_engine.py                  # Core engine init, stateless triage, offline resilience
│   ├── test_holdout.py                 # Zero train-test leakage mathematical validation
│   └── test_learning.py                # Closed feedback loop & negative constraint diff tests
├── Dockerfile                          # Production containerization specification
├── render.yaml                         # 1-Click Cloud deployment infrastructure blueprint
├── LIMITATIONS.md                      # Honest engineering disclosure of scope and edge cases
├── cleanup_before_submission.ps1       # Pre-submission repository sanitizer (Windows)
├── cleanup_before_submission.sh        # Pre-submission repository sanitizer (Linux/macOS)
├── .gitignore                          # Git configuration
└── README.md                           # Documentation & architecture guide
```

---

## Key Technical References

1. **Vectorize Hindsight Framework:** [https://github.com/vectorize-io/hindsight](https://github.com/vectorize-io/hindsight)
2. **What is Agent Memory?:** [https://vectorize.io/what-is-agent-memory](https://vectorize.io/what-is-agent-memory)
3. **Zalando Engineering Study on Surface Attribution Error in Post-Mortems:** Empirical analysis of LLM diagnostic misattribution in distributed systems.
4. **Chen et al. (2024):** *Root Cause Analysis in Microservices using Large Language Models*, IEEE Transactions on Software Engineering / arXiv:2401.03472.
5. **USENIX SREcon / ATC:** *Post-Mortem Analysis and Operational Knowledge Graphs in Distributed Systems.*
6. **Band AI Collaboration Protocol:** [https://www.band.ai](https://www.band.ai)

---

## License
MIT License. Open source and free for engineering teams.
