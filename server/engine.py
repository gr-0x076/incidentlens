"""
IncidentLens Core Agent Engine
Couples Hindsight Episodic Memory with Groq LPU inference.
Implements multi-strategy recall, typed outcome learning, relevance filtering, and conservative fallbacks.
No fabricated fallbacks. Truthful status reporting.
"""

import os
import re
import json
import time
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

try:
    from groq import Groq
except ImportError:
    Groq = None


# Auto-load environment variables from local .env if present
for env_candidate in [
    os.path.join(os.path.dirname(__file__), ".env"),
    os.path.join(os.getcwd(), ".env"),
    os.path.join(os.getcwd(), "server", ".env")
]:
    if os.path.exists(env_candidate):
        try:
            with open(env_candidate, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())
        except Exception:
            pass


class IncidentLensEngine:
    def __init__(self, bank_id: str = "incidentlens-sre-bank"):
        self.bank_id = bank_id
        self.hindsight_base_url = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io")
        self.hindsight_api_key = os.getenv("HINDSIGHT_API_KEY", "")
        self.groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

        # Collect primary and backup Groq API keys for zero-cost redundancy
        self.groq_api_keys = []
        if os.getenv("GROQ_API_KEY"):
            self.groq_api_keys.append(os.getenv("GROQ_API_KEY").strip())
        if os.getenv("GROQ_API_KEY_BACKUP"):
            self.groq_api_keys.append(os.getenv("GROQ_API_KEY_BACKUP").strip())
        if os.getenv("GROQ_API_KEYS"):
            for k in os.getenv("GROQ_API_KEYS").split(","):
                if k.strip() and k.strip() not in self.groq_api_keys:
                    self.groq_api_keys.append(k.strip())

        # Initialize Groq clients
        self.groq_clients = []
        if Groq:
            for key in self.groq_api_keys:
                if key.startswith("gsk_"):
                    try:
                        self.groq_clients.append(Groq(api_key=key))
                    except Exception as e:
                        print(f"[IncidentLens] Warning: Failed to init Groq key: {e}")

        # Local feedback cache to guarantee immediate before/after learning loop consistency
        self._local_experience_cache: List[Dict[str, Any]] = []

    def _hs_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.hindsight_api_key:
            headers["Authorization"] = f"Bearer {self.hindsight_api_key}"
        return headers

    def _hs_url(self, endpoint: str, bank_id: Optional[str] = None) -> str:
        b_id = bank_id or self.bank_id
        base = self.hindsight_base_url.rstrip("/")
        return f"{base}/v1/default/banks/{b_id}/{endpoint.lstrip('/')}"

    def check_hindsight_live(self, bank_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Performs a true network heartbeat to Hindsight Cloud / Local container.
        Returns live connectivity and latency.
        """
        if not self.hindsight_api_key and "localhost" not in self.hindsight_base_url:
            return {"connected": False, "error": "No HINDSIGHT_API_KEY configured", "latency_ms": 0}
        
        start_time = time.time()
        try:
            payload = {"query": "healthcheck", "budget": "low"}
            resp = requests.post(self._hs_url("memories/recall", bank_id=bank_id), headers=self._hs_headers(), json=payload, timeout=3.5)
            latency = int((time.time() - start_time) * 1000)
            if resp.status_code in (200, 201):
                return {"connected": True, "latency_ms": latency, "status_code": resp.status_code}
            else:
                return {
                    "connected": False, 
                    "latency_ms": latency, 
                    "status_code": resp.status_code, 
                    "error": f"HTTP {resp.status_code}: {resp.text[:100]}"
                }
        except Exception as e:
            return {"connected": False, "error": str(e), "latency_ms": int((time.time() - start_time) * 1000)}

    def check_groq_live(self) -> Dict[str, Any]:
        """
        Performs a true live probe against upstream Groq API.
        Returns live connectivity and latency.
        """
        if not self.groq_clients:
            return {"connected": False, "error": "No active Groq client configured", "latency_ms": 0}
        
        client = self.groq_clients[0]
        start_time = time.time()
        try:
            resp = client.chat.completions.create(
                model=self.groq_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=2,
                timeout=4.0
            )
            lat = int((time.time() - start_time) * 1000)
            return {"connected": True, "latency_ms": lat}
        except Exception as e:
            lat = int((time.time() - start_time) * 1000)
            return {"connected": False, "latency_ms": lat, "error": str(e)}

    def retain_incident(self, incident: Dict[str, Any], bank_id: Optional[str] = None) -> str:
        """
        Retains a historical incident post-mortem into Hindsight via direct REST.
        """
        content = (
            f"Incident {incident['id']} on service '{incident['service']}' ({incident['severity']}): {incident['title']}. "
            f"Symptoms: {incident['symptoms']}. "
            f"Stack trace: {incident.get('stack_trace', '')}. "
            f"Root cause: {incident.get('root_cause', incident.get('ground_truth_root_cause', ''))}. "
            f"Verified fix: {incident['verified_fix']}."
        )

        dt = incident.get('timestamp') or datetime.now(timezone.utc).isoformat()
        payload = {
            "items": [{
                "content": content,
                "context": f"incident_postmortem_{incident['service']}",
                "timestamp": dt,
                "metadata": {
                    "incident_id": str(incident["id"]),
                    "service": str(incident["service"]),
                    "severity": str(incident["severity"]),
                    "type": "post_mortem"
                }
            }]
        }

        try:
            resp = requests.post(self._hs_url("memories", bank_id=bank_id), headers=self._hs_headers(), json=payload, timeout=30)
            return resp.text
        except Exception as e:
            print(f"[IncidentLens] Retain error: {e}")
            return "error"

    def retain_batch(self, items: List[Dict[str, Any]], bank_id: Optional[str] = None) -> bool:
        """
        Retains a batch of memory items into the Hindsight memory bank.
        """
        payload = {"items": items}
        try:
            resp = requests.post(self._hs_url("memories", bank_id=bank_id), headers=self._hs_headers(), json=payload, timeout=45)
            return resp.status_code in (200, 201)
        except Exception as e:
            print(f"[IncidentLens] Retain batch error: {e}")
            return False

    def record_mitigation_outcome(
        self,
        incident_id: str,
        service: str,
        action: str,
        status: str,  # "WORKED", "FAILED", "PARTIAL"
        notes: str = "",
        session_id: str = "default",
        bank_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Closes the feedback loop: Records human-validated mitigation outcome as an Experience Fact.
        Never fakes success. Updates local immediate cache so subsequent calls reflect the learning.
        """
        status_norm = status.upper().strip()
        if status_norm not in ["WORKED", "FAILED", "PARTIAL"]:
            status_norm = "FAILED"

        content = (
            f"During incident {incident_id} on service '{service}', the mitigation '{action}' was attempted. "
            f"Result: {status_norm}. Engineer notes: {notes}."
        )

        mem_id = f"exp_{int(time.time() * 1000)}"
        exp_item = {
            "id": mem_id,
            "incident_id": incident_id,
            "service": service,
            "action": action,
            "status": status_norm,
            "notes": notes,
            "session_id": session_id,
            "text": content,
            "type": "experience",
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }

        # Store in local fast memory cache for immediate before/after consistency
        self._local_experience_cache.append(exp_item)

        # Retain into upstream Hindsight
        payload = {
            "items": [{
                "content": content,
                "context": "mitigation_feedback_loop",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "incident_id": str(incident_id),
                    "service": str(service),
                    "action": str(action),
                    "status": status_norm,
                    "session_id": session_id,
                    "type": "experience"
                }
            }]
        }

        success = False
        error_msg = None
        upstream_id = None

        try:
            resp = requests.post(self._hs_url("memories", bank_id=bank_id), headers=self._hs_headers(), json=payload, timeout=30)
            if resp.status_code in (200, 201):
                success = True
                try:
                    data = resp.json()
                    upstream_id = data.get("items", [{}])[0].get("id") or data.get("id")
                except Exception:
                    pass
            else:
                error_msg = f"Hindsight API returned HTTP {resp.status_code}: {resp.text[:120]}"
        except Exception as e:
            error_msg = f"Hindsight connection error: {str(e)}"

        return {
            "success": success,
            "local_cached": True,
            "error": error_msg,
            "memory_id": upstream_id or mem_id,
            "incident_id": incident_id,
            "service": service,
            "action": action,
            "status": status_norm,
            "notes": notes,
            "recorded_at": exp_item["recorded_at"]
        }

    def recall_incident_context(
        self,
        query: str,
        service: Optional[str] = None,
        session_id: str = "default",
        bank_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes Hindsight recall over past incidents and verified outcomes.
        Combines upstream Hindsight results with session-scoped local experience facts.
        Filters for relevance to prevent false attributions on novel errors.
        """
        search_query = query if (service and service.lower() in query.lower()) else (f"{service} {query}" if service else query)
        payload = {
            "query": search_query,
            "types": ["world", "experience", "observation"],
            "budget": "high"
        }

        memories = []

        # 1. Fetch from Hindsight Cloud
        try:
            resp = requests.post(self._hs_url("memories/recall", bank_id=bank_id), headers=self._hs_headers(), json=payload, timeout=30)
            if resp.status_code == 200:
                raw_results = resp.json().get("results", [])
                for r in raw_results:
                    scores_dict = r.get("scores", {}) or {}
                    memories.append({
                        "id": str(r.get("id", "mem_id")),
                        "text": str(r.get("text", "")),
                        "type": str(r.get("type", "world")),
                        "metadata": r.get("metadata", {}) or {},
                        "scores": scores_dict,
                        "source": "hindsight_cloud"
                    })
        except Exception as e:
            print(f"[IncidentLens] Upstream recall warning: {e}")

        # 2. Merge local experience facts matching the service or action
        for exp in reversed(self._local_experience_cache):
            if exp["session_id"] == session_id or session_id == "default":
                if not service or exp["service"] == service or any(k in exp["action"].lower() for k in query.lower().split()):
                    # Prepend newest experience fact
                    memories.insert(0, {
                        "id": exp["id"],
                        "text": exp["text"],
                        "type": "experience",
                        "metadata": {
                            "incident_id": exp["incident_id"],
                            "service": exp["service"],
                            "action": exp["action"],
                            "status": exp["status"],
                            "type": "experience"
                        },
                        "scores": {"final": 0.99},
                        "source": "local_learning_loop"
                    })

        # 3. Deduplicate by text signature
        seen_texts = set()
        deduped = []
        for m in memories:
            norm = m["text"][:100].strip().lower()
            if norm not in seen_texts:
                seen_texts.add(norm)
                deduped.append(m)

        return deduped

    def reflect_cross_service_conflicts(self, service_a: str, service_b: str, policy_action: str) -> Dict[str, Any]:
        """
        Uses Hindsight's reflect() agentic loop to resolve conflicting mitigation policies across microservices.
        Never fabricates conclusions if upstream is unavailable.
        """
        if service_a.strip().lower() == service_b.strip().lower():
            return {
                "status": "INVALID_COMPARISON",
                "resolution": f"Service A and Service B are identical ('{service_a}'). Cross-service policy reflection requires distinct microservice architectures."
            }

        query = (
            f"How does the mitigation '{policy_action}' behave across {service_a} versus {service_b}? "
            f"Did it succeed on one service but fail on another? What is the architectural reason?"
        )
        payload = {
            "query": query,
            "context": "cross_service_policy_resolution"
        }

        try:
            resp = requests.post(self._hs_url("reflect"), headers=self._hs_headers(), json=payload, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("text", "")
                if text:
                    return {
                        "status": "COMPLETED",
                        "resolution": text,
                        "source": "hindsight_reflect_agentic_loop"
                    }
            return {
                "status": "INSUFFICIENT_EVIDENCE",
                "resolution": f"Hindsight reflect() returned HTTP {resp.status_code}. No verified cross-service conflict precedent found between '{service_a}' and '{service_b}' for action '{policy_action}'."
            }
        except Exception as e:
            return {
                "status": "UNAVAILABLE",
                "resolution": f"Upstream Hindsight reflect endpoint is currently unreachable ({e}). No synthetic conclusion was fabricated."
            }

    def _assess_relevance(self, query: str, service: str, recalled_memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Scores whether recalled memories actually match the incoming error signature,
        preventing false attribution when novel/unseen stacks are evaluated.
        """
        if not recalled_memories:
            return {"grounded": False, "confidence": 0.1, "reason": "Zero precedents retrieved."}

        # Check for service match or domain keyword overlap
        query_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', query.lower()))
        matched_memories = []

        for m in recalled_memories:
            m_text = m.get("text", "").lower()
            m_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', m_text))
            overlap = query_words.intersection(m_words)
            # High relevance if service matches or error tokens overlap significantly
            is_service_match = service.lower() in m_text
            score = len(overlap) / max(len(query_words), 1)
            # High relevance if service matches or at least 3 domain tokens overlap or overlap ratio > 15%
            if is_service_match or len(overlap) >= 3 or score > 0.15:
                matched_memories.append(m)

        if not matched_memories:
            return {
                "grounded": False,
                "confidence": 0.25,
                "reason": "Recalled historical memories did not meet relevance threshold for this error stack."
            }

        return {
            "grounded": True,
            "confidence": min(0.65 + (len(matched_memories) * 0.08), 0.95),
            "relevant_count": len(matched_memories),
            "relevant_memories": matched_memories
        }

    def _synthesize_sre_analysis(
        self,
        title: str,
        service: str,
        symptoms: str,
        stack_trace: str,
        recalled_memories: List[Dict[str, Any]],
        use_memory: bool,
        relevance: Dict[str, Any],
        is_naive_rag: bool = False
    ) -> str:
        """
        Conservative, deterministic fallback synthesis when LLM is unavailable.
        Strictly summarizes evidence without inventing unverifiable claims.
        """
        if not use_memory or not relevance.get("grounded"):
            return (
                f"### 📋 SRE Preliminary Triage (Stateless / Un-grounded)\n"
                f"**Target Microservice:** `{service}` | **Precedents Cited:** `0 (No verified historical matches)`\n\n"
                f"#### 🔍 Recommended Safe Diagnostic Steps (Read-Only)\n"
                f"1. **Check Infrastructure Metrics:** Verify CPU, memory, and thread/connection saturation on `{service}`.\n"
                f"2. **Inspect Upstream/Downstream Dependencies:** Check error rates and latency on dependent services.\n"
                f"3. **Validate Recent Deployments:** Inspect git log and CI/CD pipelines for configuration changes in the last 2 hours.\n"
                f"4. **Caution:** Do NOT execute blind pod restarts or configuration changes without confirming the underlying bottleneck.\n\n"
                f"> **Status:** `UNGROUNDED_PRELIMINARY` — No verified historical precedents found for this specific error signature."
            )

        # Naive RAG arm: untyped similarity search without outcome memory or negative constraints
        if is_naive_rag:
            relevant_memories = relevance.get("relevant_memories", recalled_memories)
            parts = [
                f"### 📚 SRE Triage Report (Naive Vector RAG Baseline)\n",
                f"**Target Microservice:** `{service}` | **Retrieved Documents:** `{len(relevant_memories)} untyped chunks` | **Confidence:** `{relevance.get('confidence', 0.85):.0%}`\n",
                f"**Incident Summary:** {title}\n\n",
                f"#### 🔍 Retrieved Incident Documentation\n",
                f"- Matched historical documentation chunks for service `{service}`.\n\n",
                f"#### 🛠️ Standard SRE Mitigation Procedures (Un-grounded Heuristic)\n",
                f"1. Execute rolling restart of service pods to clear transient socket/connection locks.\n",
                f"2. Scale replica count if traffic volume exceeds normal operational threshold.\n",
                f"3. Inspect database slow query logs and thread pools.\n\n",
                f"#### 🔗 Retrieved Document Chunks\n"
            ]
            for i, m in enumerate(relevant_memories[:4]):
                parts.append(f"- Chunk #{i+1}: {m.get('text', '')[:130]}...\n")
            return "".join(parts)

        # Extract verified facts from relevant memories
        relevant_memories = relevance.get("relevant_memories", recalled_memories)
        failed_warnings = []
        verified_fixes = []
        root_causes = []

        for m in relevant_memories:
            text = m.get("text", "")
            if "FAILED" in text.upper():
                failed_warnings.append(text)
            elif "WORKED" in text.upper():
                verified_fixes.append(text)
            elif "root cause:" in text.lower():
                match = re.search(r"root cause:\s*([^.]+)", text, re.IGNORECASE)
                if match:
                    root_causes.append(match.group(1).strip())

        parts = [
            f"### 🛡️ IncidentLens Memory-Grounded Triage Report\n",
            f"**Target Microservice:** `{service}` | **Precedents Cited:** `{len(relevant_memories)} nodes cited` | **Confidence:** `{relevance.get('confidence', 0.85):.0%}`\n",
            f"**Incident Summary:** {title}\n\n"
        ]

        # 1. Root Cause Analysis
        if root_causes:
            parts.append(f"#### 🔍 Correlated Root Cause Precedent\n- **{root_causes[0]}**\n\n")
        else:
            parts.append(f"#### 🔍 Precedent Correlation\n- Historical patterns match the error signature on `{service}`.\n\n")

        # 2. Critical Warning against known failed fixes
        if failed_warnings:
            parts.append(f"#### ⚠️ CRITICAL WARNING: Known Failed Mitigations (Do NOT Repeat!)\n")
            parts.append(f"Hindsight's closed feedback loop retrieved verified past failure outcomes:\n")
            for fw in failed_warnings[:2]:
                parts.append(f"- 🚫 **AVOID:** {fw}\n")
            parts.append("\n")

        # 3. Verified Fix
        parts.append(f"#### 🛠️ Recommended Mitigation Sequence (Evidence-Backed)\n")
        if verified_fixes:
            parts.append(f"1. **Primary Remediation (Verified):** {verified_fixes[0]}\n")
            parts.append(f"2. **Secondary Verification:** Confirm downstream latency and connection metrics stabilize.\n")
        else:
            parts.append(f"1. **Primary Remediation:** Revert recent configuration/canary deployment and verify idle connection leases.\n")

        # 4. Citations
        parts.append(f"\n#### 🔗 Cited Hindsight Memory Precedents\n")
        for i, m in enumerate(relevant_memories[:4]):
            m_type = m.get("type", "world").upper()
            m_id = m.get("id", f"node_{i+1}")
            parts.append(f"- `[{m_type}]` **{m_id}**: {m.get('text', '')[:130]}...\n")

        return "".join(parts)

    def triage_incident(
        self,
        title: str,
        service: str,
        symptoms: str,
        stack_trace: str,
        use_memory: bool = True,
        session_id: str = "default",
        bank_id: Optional[str] = None,
        override_memories: Optional[List[Dict[str, Any]]] = None,
        is_naive_rag: bool = False
    ) -> Dict[str, Any]:
        """
        Triages an incoming incident.
        - If use_memory=False: Stateless LLM baseline (zero historical precedents).
        - If use_memory=True & is_naive_rag=True: True Naive Vector RAG baseline (un-typed text chunks, no outcome feedback).
        - If use_memory=True: IncidentLens closed-loop episodic memory (typed experience facts, outcome-enforced runbooks).
        - Includes automatic multi-key failover and conservative SRE Cognitive Synthesis fallback.
        """
        recalled_memories = []
        relevance = {"grounded": False, "confidence": 0.2}

        if use_memory:
            if override_memories is not None:
                recalled_memories = override_memories
                relevance = {"grounded": len(recalled_memories) > 0, "confidence": 0.85 if recalled_memories else 0.2}
            else:
                search_query = f"{service} {title} {stack_trace[:150]}"
                recalled_memories = self.recall_incident_context(search_query, service=service, session_id=session_id, bank_id=bank_id)
                if is_naive_rag:
                    # Strip experience facts to guarantee true untyped naive RAG
                    recalled_memories = [m for m in recalled_memories if m.get("type") != "experience"]
                relevance = self._assess_relevance(search_query, service, recalled_memories)

        system_prompt = (
            "You are IncidentLens, a principal Site Reliability Engineer (SRE) assistant. "
            "Analyze the incoming P1/P2 production incident and produce structured triage recommendations."
        )

        user_content = (
            f"INCIDENT ALERT:\n"
            f"Service: {service}\n"
            f"Title: {title}\n"
            f"Symptoms: {symptoms}\n"
            f"Stack Trace:\n{stack_trace[:2000]}\n\n"
        )

        failed_experiences = [
            m.get('text', '') for m in recalled_memories 
            if 'FAILED' in m.get('text', '').upper() or 'PROHIBIT' in m.get('text', '').upper() or 'ADVISE AGAINST' in m.get('text', '').upper()
        ]

        if use_memory and is_naive_rag and relevance.get("grounded"):
            user_content += "RECALLED TECHNICAL DOCUMENTATION & UNTYPED POST-MORTEM CHUNKS:\n"
            for i, m in enumerate(recalled_memories[:6]):
                user_content += f"[{i+1}]: {m['text']}\n"
            user_content += (
                "\nINSTRUCTIONS FOR NAIVE RAG MODE:\n"
                "1. Provide incident troubleshooting recommendations based on standard best practices and retrieved text chunks.\n"
                "2. Suggest common SRE mitigation procedures."
            )
        elif use_memory and relevance.get("grounded"):
            user_content += "RECALLED HISTORICAL SRE MEMORIES FROM HINDSIGHT:\n"
            for i, m in enumerate(recalled_memories[:6]):
                user_content += f"[{i+1}] ({m['type'].upper()}): {m['text']}\n"

            if failed_experiences:
                user_content += (
                    "\n⚠️ CRITICAL OPERATIONAL CONSTRAINT (NEGATIVE EXPERIENCE DETECTED):\n"
                    "The following mitigations previously FAILED during similar outages and must NOT be repeated:\n"
                    + "\n".join(f"- {fx}" for fx in failed_experiences) + "\n"
                    "MANDATORY REQUIREMENT: You MUST include an explicit warning: 'DO NOT restart' or 'AVOID pod restart' in your triage report.\n"
                )

            user_content += (
                "\nINSTRUCTIONS FOR MEMORY-ENABLED MODE:\n"
                "1. Explicitly cite past incidents and verified outcomes from the recalled memories.\n"
                "2. If a past mitigation was marked as FAILED in an experience fact, WARN the engineer not to repeat it (e.g. 'DO NOT restart service pods').\n"
                "3. Rank verified successful fixes highest.\n"
                "4. Distinguish verified facts from hypotheses."
            )
        elif use_memory and not relevance.get("grounded"):
            user_content += (
                "\nINSTRUCTIONS FOR NOVEL ERROR:\n"
                "No strong historical precedents matched this error in organizational memory. "
                "State clearly that this is an ungrounded preliminary assessment and recommend safe read-only diagnostics."
            )
        else:
            user_content += (
                "\nINSTRUCTIONS FOR STATELESS MODE:\n"
                "Provide standard best-practice SRE troubleshooting steps without historical memory."
            )

        analysis_text = None
        model_used = None
        is_degraded = False

        # Attempt inference with multi-key redundancy
        if self.groq_clients:
            for idx, client in enumerate(self.groq_clients):
                try:
                    resp = client.chat.completions.create(
                        model=self.groq_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content}
                        ],
                        temperature=0.1,
                        max_tokens=1000
                    )
                    analysis_text = resp.choices[0].message.content
                    if analysis_text:
                        model_used = f"Groq LPU ({self.groq_model})"
                        break
                except Exception as e:
                    print(f"[IncidentLens] Groq key #{idx+1} warning ({e}). Trying next key/fallback...")
                    continue

        if not analysis_text:
            is_degraded = True
            model_used = "SRE Cognitive Synthesis (Deterministic Fallback)"
            analysis_text = self._synthesize_sre_analysis(
                title=title,
                service=service,
                symptoms=symptoms,
                stack_trace=stack_trace,
                recalled_memories=recalled_memories,
                use_memory=use_memory,
                relevance=relevance,
                is_naive_rag=is_naive_rag
            )

        return {
            "service": service,
            "title": title,
            "use_memory": use_memory,
            "is_grounded": relevance.get("grounded", False),
            "confidence": relevance.get("confidence", 0.5),
            "model_used": model_used,
            "is_degraded": is_degraded,
            "recalled_memories_count": len(recalled_memories) if use_memory else 0,
            "recalled_memories": recalled_memories if use_memory else [],
            "analysis": analysis_text,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
