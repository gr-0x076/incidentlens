"""
IncidentLens FastAPI Application
Exposes REST endpoints for incident triage, memory inspection, closed-loop feedback, and evaluation.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from dataset import INCIDENTS
from engine import IncidentLensEngine

app = FastAPI(
    title="IncidentLens SRE Agent API",
    description="Site Reliability Engineering Agent with Closed-Loop Hindsight Memory",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_ui():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "IncidentLens API is running. Static UI not found."}

engine = IncidentLensEngine()


class TriageRequest(BaseModel):
    title: str
    service: str
    symptoms: str
    stack_trace: str
    use_memory: bool = True


class FeedbackRequest(BaseModel):
    incident_id: str
    service: str
    action: str
    status: str  # 'WORKED' or 'FAILED'
    notes: Optional[str] = ""


class ReflectRequest(BaseModel):
    service_a: str
    service_b: str
    policy_action: str


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "IncidentLens",
        "hindsight_connected": engine.hs_client is not None,
        "groq_connected": engine.groq_client is not None,
        "model": engine.groq_model
    }


@app.get("/api/incidents")
def list_incidents():
    return {"incidents": INCIDENTS, "count": len(INCIDENTS)}


@app.post("/api/incidents/triage")
def triage_incident(req: TriageRequest):
    result = engine.triage_incident(
        title=req.title,
        service=req.service,
        symptoms=req.symptoms,
        stack_trace=req.stack_trace,
        use_memory=req.use_memory
    )
    return result


@app.post("/api/incidents/feedback")
def submit_feedback(req: FeedbackRequest):
    if req.status.upper() not in ["WORKED", "FAILED"]:
        raise HTTPException(status_code=400, detail="Status must be 'WORKED' or 'FAILED'")

    result = engine.record_mitigation_outcome(
        incident_id=req.incident_id,
        service=req.service,
        action=req.action,
        status=req.status,
        notes=req.notes or ""
    )
    return result


@app.post("/api/incidents/reflect")
def reflect_conflicts(req: ReflectRequest):
    answer = engine.reflect_cross_service_conflicts(
        service_a=req.service_a,
        service_b=req.service_b,
        policy_action=req.policy_action
    )
    return {
        "service_a": req.service_a,
        "service_b": req.service_b,
        "policy_action": req.policy_action,
        "resolution": answer
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
