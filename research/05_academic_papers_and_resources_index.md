# IncidentLens — Academic Research Papers, Datasets & Tools Index

This document catalogs the 76 sources, academic papers, industrial benchmarks, commercial platforms, and open-source tools identified during our deep competitive research.

---

## 📚 1. Core Academic Research Papers (AIOps, RCA & Memory)

| Paper Title | Venue / Year | Key Contribution & Relevance to IncidentLens | Link |
|:---|:---:|:---|:---:|
| **STRATUS: A Multi-agent System for Autonomous Reliability Engineering** | NeurIPS 2025 | Multi-agent autonomous reliability engineering framework; closest current academic peer. | [arXiv:2502.00055](https://arxiv.org/abs/2502.00055) |
| **OpsAgent: A Self-Evolving Multi-Agent System for Microservice Incident Management** | ASE Industry 2026 | Deployed at Lenovo. Uses multi-agent reflection to distill incident knowledge into per-agent vector memory. | [arXiv:2510.24145](https://arxiv.org/abs/2510.24145) |
| **KRCA: An End-to-End Root Cause Analysis System for Hyper-Scale Microservices** | arXiv 2026 | Deployed at Kuaishou (200K+ microservices). Implements 3-tier memory (Working, Factual, Experiential). | [arXiv:2606.29193](https://arxiv.org/abs/2606.29193) |
| **GALA+: Graph-Augmented LLM Agent for Microservice Root Cause Analysis** | arXiv 2026 | Uses service dependency graphs to bound exploration and trace cascading fault propagation. | [arXiv:2608.08968](https://arxiv.org/abs/2608.08968) |
| **Exploring LLM-based Agents for Root Cause Analysis (Roy et al.)** | arXiv 2024 | Evaluated 107K incidents. Found that adding raw Slack chat does NOT improve RCA without typed fact extraction. | [arXiv:2403.04123](https://arxiv.org/abs/2403.04123) |
| **TimeRAG: Retrieval-Augmented Generation over Time-Series Incidents** | arXiv 2026 | Evaluated RAG over 3,249 historical incidents. Proved that RAG accuracy strictly depends on corpus diversity. | [arXiv:2601.04709](https://arxiv.org/abs/2601.04709) |
| **Triangle: Multi-Agent Incident Triage with Semantic Distillation** | ASE 2025 (Microsoft) | Microsoft Research paper on semantic distillation for heterogeneous cloud incidents (97% accuracy). | [arXiv:2505.14820](https://arxiv.org/abs/2505.14820) |
| **ChaosEater: Fully Automating Chaos Engineering with LLMs** | ASE 2025 | Automated chaos injection and failure verification using LLM planning agents. | [arXiv:2501.02531](https://arxiv.org/abs/2501.02531) |
| **A Survey of AIOps in the Era of Large Language Models** | ACM Computing Surveys 2025 | Comprehensive review of LLM applications in anomaly detection, RCA, and auto-remediation. | [arXiv:2404.09837](https://arxiv.org/abs/2404.09837) |
| **Automatic Root Cause Analysis via LLMs for Cloud Incidents** | EuroSys 2024 | Foundational EuroSys paper on in-context learning for cloud incident diagnostics. | [arXiv:2305.15778](https://arxiv.org/abs/2305.15778) |
| **SoftNER: Mining Knowledge Graphs From Cloud Incidents** | arXiv 2021 | Mining entity-relationship graphs from incident reports and post-mortems. | [arXiv:2101.05961](https://arxiv.org/abs/2101.05961) |
| **Nissist: An Incident Mitigation Copilot based on Troubleshooting Guides** | arXiv 2024 | Automated mitigation extraction from operational runbooks and markdown guides. | [arXiv:2402.17531](https://arxiv.org/abs/2402.17531) |
| **RC-LLM: Residual-Connection-based LLM RCA** | arXiv 2026 | Multimodal RCA combining metrics, logs, and traces (reached 48.25% on CCF AIOps 2025). | [arXiv:2602.04512](https://arxiv.org/abs/2602.04512) |

---

## 🏆 2. Industrial Benchmarks & Datasets

| Benchmark / Dataset | Description | Source |
|:---|:---|:---:|
| **OpenRCA (Microsoft)** | Standard benchmark: 335 enterprise failures, 68GB+ telemetry. Frontier LLMs solve only 11.3%. | [GitHub](https://github.com/microsoft/OpenRCA) |
| **OpenRCA 2.0 (arXiv 2026)** | Step-wise causal annotations benchmark showing LLMs recover full root causes in only 20.7% of cases. | [Paper](https://arxiv.org/abs/2606.12891) |
| **RCAEval** | Standard multi-modal microservice evaluation suite for RCA algorithms. | [GitHub](https://github.com/phamquiluan/RCAEval) |
| **SRE Bench** | Standardized benchmark testing agentic SRE performance on real incidents. | [sreben.ch](https://sreben.ch/) |
| **OpsEval** | Task-oriented AIOps benchmark for LLMs. | [arXiv:2310.07637](https://arxiv.org/abs/2310.07637) |
| **Azure Public Dataset** | Real cloud operations telemetry and failure traces from Microsoft Azure. | [GitHub](https://github.com/Azure/AzurePublicDataset) |
| **LogHub** | Curated collection of 14+ open log datasets (HDFS, BGL, Android, Windows, Spark). | [GitHub](https://github.com/logpai/loghub) |
| **Alibaba Cluster Trace** | Production microservice and container trace datasets from Alibaba data centers. | [GitHub](https://github.com/alibaba/clusterdata) |

---

## 🛠️ 3. Commercial & Industrial Platforms

| Platform | Core Value Proposition | Link |
|:---|:---|:---:|
| **Datadog Bits Memories** | Automatically saves operational context from postmortems, Slack, and runbooks (DASH 2026). | [datadoghq.com](https://www.datadoghq.com/blog/dash-2026-new-feature-roundup-keynote/) |
| **Azure SRE Agent (Microsoft)** | Institutional memory agent retaining investigation context across teams. | [azure.microsoft.com](https://learn.microsoft.com/en-us/azure/sre-agent/overview) |
| **incident.io AI SRE** | Correlates ongoing alerts with historical incidents and code changes in Slack. | [incident.io](https://incident.io/solution/ai-sre) |
| **Sherlocks AI** | Slack-native AI SRE maintaining a 1-year operational Awareness Graph. | [sherlocks.ai](https://www.sherlocks.ai/) |
| **Resolve AI** | Autonomous SRE platform founded by OpenTelemetry co-creators ($125M Series A). | [resolve.ai](https://resolve.ai) |
| **Causely** | Live causal topology model for blast-radius calculation. | [causely.ai](https://causely.ai) |
| **HolmesGPT (CNCF Sandbox)** | Open-source Kubernetes incident triage agent by Robusta.dev and Microsoft. | [GitHub](https://github.com/HolmesGPT/holmesgpt) |
| **Rootly & FireHydrant** | Incident management workflow and retrospective drafting platforms. | [rootly.com](https://rootly.com) / [firehydrant.com](https://firehydrant.com) |
| **PagerDuty AIOps** | Alert grouping, event correlation, and AI-assisted post-incident reviews. | [pagerduty.com](https://www.pagerduty.com/platform/aiops/) |

---

## 📖 4. Industrial SRE Case Studies

- **Zalando Engineering (September 2025):** *"Dead Ends or Data Goldmines: AI-Powered Postmortem Analysis"*. Two-year production study revealing the **10% Surface Attribution Error** and how automated IaC guardrails prevented 25% of subsequent datastore outages. [Blog Post](https://engineering.zalando.com/posts/2025/09/dead-ends-or-data-goldmines-ai-powered-postmortem-analysis.html).
- **Google SRE Resources (2025):** *"AI Engineering for Reliable Operations"*. Parsing unstructured incident timelines into time-ordered human response trajectories (10% MTTM reduction with Incident Hypothesis). [Google SRE](https://sre.google/resources/practices-and-processes/ai-engineering-reliable-operations/).
- **ClickHouse Engineering (2026):** *"What We Learned Building AI SRE Agents for Production On-Call"*. Evaluating on-call agents against live production databases. [Article](https://clickhouse.com/resources/engineering/ai-sre-agents).

---

## 🔗 5. Foundational Frameworks We Use

- **Hindsight (Vectorize):** [GitHub](https://github.com/vectorize-io/hindsight) | [Documentation](https://hindsight.vectorize.io/) | [Concept Guide](https://vectorize.io/what-is-agent-memory)
- **Groq Cloud:** [Console](https://console.groq.com) | [Supported Models](https://console.groq.com/docs/models)
- **Band AI Desktop:** [Platform](https://www.band.ai) | [Docs](https://docs.band.ai)
