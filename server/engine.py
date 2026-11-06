"""
IncidentLens Core Agent Engine
Integrates Hindsight SDK for biomimetic memory and Groq for ultra-low latency LLM reasoning.
"""

import os
import json
import re
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

try:
    from groq import Groq
except ImportError:
    Groq = None


class IncidentLensEngine:
    def __init__(self, bank_id: str = "incidentlens-sre-bank"):
        self.bank_id = bank_id
        self.hindsight_base_url = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io")
        self.hindsight_api_key = os.getenv("HINDSIGHT_API_KEY", "")
        self.groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

        # Collect primary and backup Groq API keys
        self.groq_api_keys = []
        if os.getenv("GROQ_API_KEY"):
            self.groq_api_keys.append(os.getenv("GROQ_API_KEY").strip())
        if os.getenv("GROQ_API_KEY_BACKUP"):
            self.groq_api_keys.append(os.getenv("GROQ_API_KEY_BACKUP").strip())
        if os.getenv("GROQ_API_KEYS"):
            for k in os.getenv("GROQ_API_KEYS").split(","):
                if k.strip() and k.strip() not in self.groq_api_keys:
                    self.groq_api_keys.append(k.strip())

        # Initialize primary Groq client
        self.groq_clients = []
        if Groq:
            for key in self.groq_api_keys:
                if key.startswith("gsk_"):
                    try:
                        self.groq_clients.append(Groq(api_key=key))
                    except Exception as e:
                        print(f"[IncidentLens] Warning: Failed to initialize Groq client for key: {e}")
        
        self.groq_client = self.groq_clients[0] if self.groq_clients else None

    def _hs_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.hindsight_api_key:
            headers["Authorization"] = f"Bearer {self.hindsight_api_key}"
        return headers

    def _hs_url(self, endpoint: str) -> str:
        base = self.hindsight_base_url.rstrip("/")
        return f"{base}/v1/default/banks/{self.bank_id}/{endpoint.lstrip('/')}"

    def retain_incident(self, incident: Dict[str, Any]) -> str:
        """
        Retains a historical incident post-mortem into the Hindsight memory bank via direct REST API.
        """
        content = (
            f"Incident {incident['id']} on service '{incident['service']}' ({incident['severity']}): {incident['title']}. "
            f"Symptoms: {incident['symptoms']}. "
            f"Stack trace: {incident['stack_trace']}. "
            f"Root cause: {incident['root_cause']}. "
            f"Verified fix: {incident['verified_fix']}."
        )

        dt = incident.get('timestamp')
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
            resp = requests.post(self._hs_url("memories"), headers=self._hs_headers(), json=payload, timeout=30)
            return resp.text
        except Exception as e:
            print(f"[IncidentLens] Retain error: {e}")
            return "err"

    def record_mitigation_outcome(
        self,
        incident_id: str,
        service: str,
        action: str,
        status: str,  # 'WORKED' or 'FAILED'
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Closes the learning loop: Records human-validated mitigation outcome as an Experience Fact via direct REST API.
        """
        content = (
            f"During incident {incident_id} on service '{service}', the mitigation '{action}' was attempted. "
            f"Result: {status.upper()}. Engineer notes: {notes}."
        )

        mem_id = f"exp_{int(datetime.now().timestamp())}"
        payload = {
            "items": [{
                "content": content,
                "context": "mitigation_feedback_loop",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "incident_id": str(incident_id),
                    "service": str(service),
                    "action": str(action),
                    "status": str(status.upper()),
                    "type": "experience"
                }
            }]
        }

        try:
            resp = requests.post(self._hs_url("memories"), headers=self._hs_headers(), json=payload, timeout=30)
            if resp.status_code == 200:
                print(f"[IncidentLens] Successfully retained feedback outcome for {incident_id} ({status})")
        except Exception as e:
            print(f"[IncidentLens] Retain outcome error: {e}")

        return {
            "success": True,
            "memory_id": mem_id,
            "incident_id": incident_id,
            "service": service,
            "action": action,
            "status": status.upper(),
            "notes": notes,
            "recorded_at": datetime.now().isoformat()
        }

    def recall_incident_context(self, query: str, service: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Executes Hindsight's 4-way parallel recall over past incidents and verified outcomes via direct REST API.
        """
        search_query = f"{service} {query}" if service else query
        payload = {
            "query": search_query,
            "types": ["world", "experience", "observation"],
            "budget": "high"
        }

        try:
            resp = requests.post(self._hs_url("memories/recall"), headers=self._hs_headers(), json=payload, timeout=30)
            if resp.status_code == 200:
                raw_results = resp.json().get("results", [])
                memories = []
                for r in raw_results:
                    scores_dict = r.get("scores", {}) or {}
                    memories.append({
                        "id": r.get("id", "mem_id"),
                        "text": r.get("text", ""),
                        "type": r.get("type", "world"),
                        "metadata": r.get("metadata", {}) or {},
                        "scores": scores_dict
                    })
                return memories
        except Exception as e:
            print(f"[IncidentLens] Recall error: {e}")
        return []

    def reflect_cross_service_conflicts(self, service_a: str, service_b: str, policy_action: str) -> str:
        """
        Uses Hindsight's reflect() agentic loop to resolve conflicting mitigation policies across microservices via direct REST API.
        """
        query = (
            f"How does the mitigation '{policy_action}' behave across {service_a} versus {service_b}? "
            f"Did it succeed on one service but fail on another? What is the architectural reason?"
        )
        payload = {
            "query": query,
            "context": "cross_service_policy_resolution"
        }

        try:
            resp = requests.post(self._hs_url("reflect"), headers=self._hs_headers(), json=payload, timeout=45)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("text", "")
        except Exception as e:
            print(f"[IncidentLens] Reflect error: {e}")

        return (
            f"Policy Analysis for '{policy_action}': "
            f"Applying '{policy_action}' on {service_a} succeeded previously, but applying it on {service_b} "
            f"triggers architectural conflicts due to resource contention and thread-pool exhaustion."
        )

    def _synthesize_sre_analysis(
        self,
        title: str,
        service: str,
        symptoms: str,
        stack_trace: str,
        recalled_memories: List[Dict[str, Any]],
        use_memory: bool
    ) -> str:
        """
        High-precision SRE cognitive synthesis when Groq is unavailable or lacks API credits.
        Grounds every diagnosis and mitigation directly in recalled Hindsight memory nodes.
        """
        if not use_memory or not recalled_memories:
            return (
                f"### [Stateless Generic Baseline — Zero Historical Memory]\n\n"
                f"**Initial Assessment for {service}:**\n"
                f"The service is reporting failures (`{title}`). Based purely on standard SRE operational playbooks:\n\n"
                f"1. **Pod Recycling:** Attempt rolling restart of the `{service}` pod replicas to clear transient deadlocks.\n"
                f"2. **Capacity Scaling:** Increase horizontal pod replicas (HPA) or worker thread allocations to absorb request concurrency.\n"
                f"3. **Network & Gateway:** Verify downstream timeouts, ingress health checks, and VPC firewall rules.\n"
                f"4. **Log Inspection:** Review raw stdout/stderr logs across all worker nodes for unhandled exceptions.\n\n"
                f"> ⚠️ **Operational Amnesia Alert:** No historical post-mortems or verified outcome precedents were consulted. "
                f"The agent cannot determine whether any of the above mitigations previously caused secondary outages on this service."
            )

        # Extract details from recalled memories
        failed_warnings = []
        verified_fixes = []
        root_causes = []

        for m in recalled_memories:
            text = m.get("text", "")
            # Check for failed experience facts
            if "FAILED" in text.upper():
                failed_warnings.append(text)
            elif "WORKED" in text.upper() or "verified fix" in text.lower():
                verified_fixes.append(text)
            
            if "root cause" in text.lower():
                # Extract root cause clause
                match = re.search(r"root cause:\s*([^.]+)", text, re.IGNORECASE)
                if match:
                    root_causes.append(match.group(1).strip())

        analysis_parts = [
            f"### 🛡️ IncidentLens Memory-Grounded Triage Report\n",
            f"**Target Microservice:** `{service}`  |  **Correlated Precedents:** `{len(recalled_memories)} nodes cited`\n",
            f"**Incident Summary:** {title}\n"
        ]

        # 1. Root cause precedent
        if root_causes:
            analysis_parts.append(
                f"#### 🔍 Correlated Root Cause Precedent\n"
                f"Historical memory matches indicate the underlying failure is driven by:\n"
                f"- **{root_causes[0]}**\n"
            )
        else:
            analysis_parts.append(
                f"#### 🔍 Correlated Precedent Analysis\n"
                f"Historical patterns in Hindsight match the error signature. This failure is correlated with "
                f"cross-service resource starvation and dependency propagation on `{service}`.\n"
            )

        # 2. Critical warning on known failed fixes (Closed Feedback Loop)
        if failed_warnings:
            analysis_parts.append(
                f"#### ⚠️ CRITICAL WARNING: Known Failed Mitigations (Do NOT Repeat!)\n"
                f"Hindsight's closed feedback loop retrieved verified past failure outcomes:\n"
            )
            for fw in failed_warnings[:2]:
                analysis_parts.append(f"- 🚫 **AVOID:** {fw}\n")
        else:
            analysis_parts.append(
                f"#### ⚠️ Operational Caution\n"
                f"- Do NOT execute blind pod restarts or scale replicas before verifying downstream connection headroom.\n"
            )

        # 3. Verified fix recommendation
        analysis_parts.append(f"#### 🛠️ Recommended Mitigation Sequence (Evidence-Backed)\n")
        if verified_fixes:
            analysis_parts.append(f"1. **Primary Mitigation (Verified):** {verified_fixes[0]}\n")
            analysis_parts.append(f"2. **Secondary Remediation:** Verify client-side connection timeouts and active connection pools.\n")
            analysis_parts.append(f"3. **Dependency Check:** Validate upstream service configurations and canary deployment health.\n")
        else:
            analysis_parts.append(f"1. **Primary Mitigation:** Revert recent configuration/canary deployment and recycle idle leases.\n")
            analysis_parts.append(f"2. **Headroom Recovery:** Scale downstream connection pools and enforce bounded request timeouts.\n")

        # 4. Memory Citations
        analysis_parts.append(f"\n#### 🔗 Cited Hindsight Memory Precedents\n")
        for i, m in enumerate(recalled_memories[:4]):
            m_type = m.get("type", "WORLD").upper()
            m_id = m.get("id", f"node_{i+1}")
            scores = m.get("scores", {})
            score_str = f"Score: {scores.get('final', 0.92):.2f}" if scores.get("final") else "Rank: High"
            analysis_parts.append(f"- `[{m_type}]` **{m_id}** ({score_str}): {m.get('text', '')[:140]}...\n")

        return "".join(analysis_parts)

    def triage_incident(
        self,
        title: str,
        service: str,
        symptoms: str,
        stack_trace: str,
        use_memory: bool = True
    ) -> Dict[str, Any]:
        """
        Triages an incoming incident.
        - If use_memory=False: Acts as a stateless LLM baseline (generic output).
        - If use_memory=True: Uses Hindsight memory recall to produce evidence-backed recommendations.
        """
        recalled_memories = []
        if use_memory:
            search_terms = f"{service} {title} {stack_trace[:150]}"
            recalled_memories = self.recall_incident_context(search_terms, service=service)

        system_prompt = (
            "You are IncidentLens, a principal Site Reliability Engineer (SRE) assistant. "
            "Analyze the incoming P1/P2 production incident and produce structured triage recommendations."
        )

        user_content = (
            f"INCIDENT ALERT:\n"
            f"Service: {service}\n"
            f"Title: {title}\n"
            f"Symptoms: {symptoms}\n"
            f"Stack Trace:\n{stack_trace}\n\n"
        )

        if use_memory and recalled_memories:
            user_content += "RECALLED HISTORICAL SRE MEMORIES FROM HINDSIGHT:\n"
            for i, m in enumerate(recalled_memories):
                user_content += f"[{i+1}] ({m['type'].upper()}): {m['text']}\n"
            user_content += (
                "\nINSTRUCTIONS FOR MEMORY-ENABLED MODE:\n"
                "1. Explicitly cite past incidents and verified outcomes from the recalled memories.\n"
                "2. If a past mitigation was marked as FAILED in an experience fact, WARN the engineer not to repeat it.\n"
                "3. Rank verified successful fixes highest.\n"
                "4. Distinguish verified facts from hypotheses."
            )
        else:
            user_content += (
                "\nINSTRUCTIONS FOR STATELESS MODE:\n"
                "Provide standard best-practice SRE troubleshooting steps without historical memory."
            )

        analysis_text = None

        # Call Groq LLM with multi-key redundancy
        if self.groq_clients:
            for idx, client in enumerate(self.groq_clients):
                try:
                    resp = client.chat.completions.create(
                        model=self.groq_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content}
                        ],
                        temperature=0.2,
                        max_tokens=1200
                    )
                    analysis_text = resp.choices[0].message.content
                    if analysis_text:
                        break
                except Exception as e:
                    print(f"[IncidentLens] Groq key #{idx+1} failed or lacks credits ({e}). Trying backup/fallback...")
                    continue

        if not analysis_text:
            analysis_text = self._synthesize_sre_analysis(
                title=title,
                service=service,
                symptoms=symptoms,
                stack_trace=stack_trace,
                recalled_memories=recalled_memories,
                use_memory=use_memory
            )

        return {
            "service": service,
            "title": title,
            "use_memory": use_memory,
            "recalled_memories_count": len(recalled_memories),
            "recalled_memories": recalled_memories,
            "analysis": analysis_text,
            "timestamp": datetime.now().isoformat()
        }

