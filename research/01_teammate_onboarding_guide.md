# Welcome to IncidentLens — Teammate Onboarding & Master Brief

Welcome to the team! This document gives you full context on everything we have researched, planned, and built so far, so you can jump in immediately without missing a beat.

---

## 🎯 1. The Context: Hack With Bangalore 4.0

* **Event:** Hack With Bangalore 4.0 (Organized by Devnovate & Hack With India, in partnership with **Microsoft**, **Vectorize**, and **Band AI**).
* **Format Evolution:** The event was postponed from its original October date. It is now a **Two-Stage Competition**:
  1. **Stage 1 (Current Phase):** Virtual project building & content submission due **Saturday, November 7, 2026 at 11:59 PM IST**.
  2. **Stage 2 (Offline Grand Finale):** Shortlisted teams present live on-site at the **Microsoft Office, Bengaluru**.
* **Mandatory Action For You RIGHT NOW:**
  - 👉 Fill out the [Mandatory Profile Review Form](https://forms.gle/BGcky3M6Nw1pBEPw6). 
  - Every single team member must submit this form individually. Teams with missing profile submissions are disqualified from shortlisting!

---

## 🧠 2. The Project: IncidentLens

### The Problem
When production crashes at 3:14 AM with a cascading failure (e.g., `JedisConnectionException` on payment-gw), on-call engineers paste stack traces into standard LLM chatbots. The model gives generic advice: *"Restart your pods."*
The engineer restarts the pods—and within 90 seconds, the new pods exhaust the connection pool again. The outage drags on because the real root cause was an upstream canary deploy on the authentication service leaking connections six weeks ago.
Standard RAG has total amnesia. It has no causal graph, no timeline, and no concept of whether a past mitigation worked or failed.

### Our Solution
**IncidentLens** is a memory-powered SRE triage copilot built on [Hindsight](https://github.com/vectorize-io/hindsight) (by Vectorize) and [Groq](https://groq.com) LLaMA 3.3 70B:
1. **Multi-Strategy Parallel Recall:** Uses BM25 (exact stack traces), Semantic search (symptoms), Causal Graph (microservice dependencies), and Temporal filtering (deployments in the last 2 hours).
2. **The Closed Feedback Loop (Our Core Innovation):** When an engineer executes a mitigation, they mark it as `WORKED` or `FAILED`. The agent retains this outcome as an **Experience Fact**. Next time, verified fixes rank higher and known failed mitigations are actively warned against.
3. **Cross-Service Policy Conflict Resolution:** Uses Hindsight's `reflect()` operation to resolve conflicting runbooks (e.g., why thread-pool scaling works on Python/FastAPI but deadlocks Java/Spring).

---

## ⚖️ 3. The Official Judging Rubric (Why We Win)

| Criterion | Weight | How IncidentLens Targets It |
|:---|:---:|:---|
| **Innovation** | **30%** | The closed feedback loop (`retain` of human-validated outcomes) and cross-service conflict resolution via `reflect()`. |
| **Use of Hindsight Memory** | **25%** | Exercises all 4 retrieval strategies (BM25 + Semantic + Graph + Temporal) and contrasts Stateless vs. Memory mode. |
| **Technical Implementation** | **20%** | Realistic 20-incident microservices corpus across 5 services based on real post-mortems (Cloudflare, Monzo, GitLab, Stripe). |
| **User Experience (UX)** | **15%** | Dark-mode SRE terminal UI at `http://localhost:8000` with live memory evidence drawer and 1-click outcome feedback. |
| **Real-World Impact** | **10%** | Solves 3 AM P1 outage fatigue. Competes in a high-value category ($50–$150/engineer/mo). |

---

## 💻 4. How to Run the Project Locally in 2 Minutes

### 1. Prerequisites
- Python 3.10+
- Docker (optional, if running Hindsight locally)

### 2. Setup
```bash
git clone <repo-url>
cd incidentlens/server

# Install dependencies
pip install -r requirements.txt

# Configure .env
cp .env.example .env
```

Add your keys to `server/.env`:
```ini
HINDSIGHT_BASE_URL=https://api.hindsight.vectorize.io # Or http://localhost:8888
HINDSIGHT_API_KEY=your_key_here                       # Get $50 free credit with code MEMHACK99
GROQ_API_KEY=your_groq_key_here                      # Free tier from console.groq.com
GROQ_MODEL=llama-3.3-70b-versatile
```

### 3. Run the Backend & Triage Dashboard
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
Open **`http://localhost:8000`** in your browser. You can immediately select incidents, toggle memory on/off, click `Triage Incident`, and test the closed feedback loop!

### 4. Run the Evaluation Benchmark
```bash
python evaluate_agent.py
```

---

## 🛡️ 5. Critical Competition Rules & Disqualification Traps

1. 🔴 **THE ABSOLUTE BAN ON "HACKATHON":**
   - The official Content Guide commands: **DO NOT MENTION THE WORD "HACKATHON" ANYWHERE IN THE ARTICLE, LINKEDIN POST, REDDIT POST, VIDEO TITLE, OR README.** 
   - Violators will be immediately disqualified! All public material must be framed as a genuine engineering case study / open-source tool.
2. 🔴 **Individual Content Requirement:**
   - The guide requires an **Article per team member** (800–1,500 words on Dev.to or Medium) and a **LinkedIn post per team member**, plus **1 team video** (YouTube, 2–5 min).
   - Drafts are already pre-written in `content/`!
3. 🔴 **Band AI Desktop Requirement:**
   - We must demonstrate usage of Band AI. We have already integrated Band CLI v0.4.17 in `band/incident_war_room.sh`.

---

## 📂 6. Repository Layout & What's in Here

```
incidentlens/
├── server/
│   ├── app.py                     # FastAPI server + serves static UI at /
│   ├── engine.py                  # IncidentLensEngine (Hindsight retain/recall/reflect + Groq)
│   ├── dataset.py                 # 20 realistic incidents modeled on public SRE post-mortems
│   ├── seed_incidents.py          # Ingestion script with single-incident safety check
│   ├── evaluate_agent.py          # Automated benchmark (Stateless vs. IncidentLens)
│   ├── requirements.txt           # Python dependencies
│   ├── .env.example               # Environment variables template
│   └── static/                    # Dark-mode SRE terminal UI
│       └── index.html
├── band/
│   └── incident_war_room.sh       # Band AI collaboration room creator
├── content/
│   ├── article_draft.md           # 1,200-word Dev.to/Medium technical article (ZERO "hackathon" mentions)
│   ├── linkedin_post.txt          # Andrej Karpathy-style LinkedIn post (773 chars)
│   ├── video_script.md            # 3-min YouTube demo video script with cues & titles
│   └── reddit_post.txt            # Link post copy for r/aiagents & r/llmdevs
├── research/                      # Complete intelligence archive (YOU ARE HERE)
│   ├── 01_teammate_onboarding_guide.md
│   ├── 02_competitive_landscape_deep_dive.md
│   ├── 03_master_technical_blueprint.md
│   ├── 04_hackathon_round1_plan.md
│   ├── 05_academic_papers_and_resources_index.md
│   ├── IncidentLens-Exhaustive-Competitive-Research-Landscape-Report.pdf
│   ├── raw_problem_statement.txt
│   └── raw_content_guide.txt
├── cleanup_before_submission.sh   # Run this before final submission to clean out research/
└── README.md                      # Clean, professional engineering README
```

---

## 🧹 7. Submission Cleanup Workflow

To keep our research, competitive analysis, and internal notes organized while building, everything lives in `research/`.

Before we submit our GitHub repository URL to the judges:
```bash
./cleanup_before_submission.sh
```
This script cleanly archives/removes the `research/` folder and commits the pure, production-grade project so the judges only see the clean codebase, evaluation harness, UI, and documentation!

---

## 🚀 8. Immediate Next Actions

1. [ ] Fill out the [Mandatory Profile Review Form](https://forms.gle/BGcky3M6Nw1pBEPw6).
2. [ ] Pull the repo, install requirements, and run `uvicorn app:app --port 8000` to test the UI.
3. [ ] Review `research/02_competitive_landscape_deep_dive.md` and `content/article_draft.md`.
4. [ ] Sync on who records the demo video and who reviews the article draft!
