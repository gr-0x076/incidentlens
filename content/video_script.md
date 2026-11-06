# IncidentLens — 3-Minute Demo Video Script & YouTube Package

## 5 High-Performing YouTube Titles
1. **Why Your AI Coding Assistant Fails at 3 AM Outages**
2. **I Stopped Using Stateless RAG for DevOps (Here's What Happened)**
3. **Building an SRE Agent That Remembers Past Production Disasters**
4. **How Agent Memory Fixes Cascading Microservice Failures in 60 Seconds**
5. **From Amnesia to SRE Copilot: Closed-Loop Agent Memory with Hindsight**

---

## YouTube Thumbnail Prompt (For Google Gemini / Nano Banana)
```
A bold, high-contrast, attention-grabbing YouTube thumbnail (16:9 aspect ratio) for senior software engineers. 
Split composition: 
On the left, a dark terminal screen displaying chaotic red cascading P1 incident alerts with "STATELESS RAG: 502 BAD GATEWAY". 
On the right, a calm, glowing emerald memory node graph linking microservice entities with "INCIDENTLENS: VERIFIED RESOLUTION RECALLED". 
Bold text overlay in punchy typography: "AI THAT REMEMBERS OUTAGES". Minimalist, clean, authentic developer aesthetic, no cartoonish graphics.
```

---

## 3-Minute Screen Recording Script

**Screen Setup:** 1080p recording, font size scaled up (16pt+), notifications silenced. Terminal or Web Dashboard visible.

### [0:00 – 0:30] Segment 1: Quick Introduction & The Hook
* **Visual Cue:** Full-screen terminal or browser header showing `IncidentLens | SRE Post-Mortem Memory Agent`.
* **Narration:**
  > "Hi, I'm Mohith. If you've ever been on call at 3:00 AM when production goes down, you know the sinking feeling of pasting a cryptic stack trace into an AI assistant, only to get generic advice like 'restart your pods'—advice that wastes critical minutes and often makes cascading outages worse. 
  > We built **IncidentLens**: an SRE incident agent that uses Hindsight episodic memory to remember how past outages were diagnosed, which fixes actually worked, and which ones failed."

---

### [0:30 – 1:00] Segment 2: The Problem (Stateless Agent Amnesia)
* **Visual Cue:** Show `use_memory: false` toggle in UI or run `test_stateless.py`. A live alert pops up: `payment-gw HTTP 502 with JedisConnectionException: Could not get resource from pool`.
* **Narration:**
  > "Let's see what happens without memory. We feed this P1 Redis connection pool exhaustion alert to a stateless LLaMA 3.3 model. 
  > The model suggests: 'Restart your payment gateway pods.' 
  > But here's the trap: in a shared-tier microservice architecture, restarting payment-gw does nothing because an upstream authentication canary is leaking connections. A stateless model doesn't know that. It has total amnesia."

---

### [1:00 – 2:30] Segment 3: Live Demo — The Closed Feedback Loop
* **Visual Cue:** Switch `use_memory: true`. Re-run the triage on the exact same error.
* **Narration:**
  > "Now watch what happens with IncidentLens and Hindsight's 4-way parallel recall. 
  > Instead of generic advice, IncidentLens immediately recalls Incident 101 from six weeks ago. It highlights that restarting pods was previously attempted and **FAILED**, draining the pool again in 90 seconds. 
  > Instead, it ranks the verified successful mitigation: rolling back the upstream auth-service canary deploy.
  > But here is the real innovation: the **closed feedback loop**. 
  > When an engineer executes a mitigation, they mark it as 'WORKED' or 'FAILED'. Watch: I click 'WORKED'. IncidentLens calls `hs.retain()` to store this as an Experience Fact. 
  > Now, if an engineer tries to apply a fix from our Python inventory service to our Java payment gateway, Hindsight's `reflect()` operation actively identifies the policy conflict and warns against thread pool saturation."

---

### [2:30 – 3:00] Segment 4: Key Takeaway & Real Evaluation
* **Visual Cue:** Show the benchmark summary table from `evaluate_agent.py` on screen (80% verified fix identification rate, 100% repeat mistake warning rate).
* **Narration:**
  > "Across our 20-incident microservice benchmark, IncidentLens achieved an 80% first-pass verified fix recall rate and a 100% warning rate on repeat mistakes. 
  > The biggest lesson we learned: agents don't need larger context windows; they need structured episodic memory that learns from verified human outcomes. 
  > You can explore our open code and evaluation harness at the GitHub link below. Thanks for watching!"
