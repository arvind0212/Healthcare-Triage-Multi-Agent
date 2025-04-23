from datetime import datetime
from typing import Dict, Optional, Any, Literal
from pydantic import BaseModel, Field

class StatusUpdate(BaseModel):
    """Schema for agent status updates."""
    agent_id: str = Field(..., description="Identifier of the agent emitting the status")
    status: Literal["ACTIVE", "DONE", "ERROR", "WAITING"] = Field(..., description="Current status of the agent")
    message: str = Field(..., description="Human-readable status message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of the status update")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional status details")
    run_id: str = Field(..., description="Identifier for the simulation run")
    event_id: int = Field(..., description="Sequential event ID within the run for SSE")
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "ehr_agent",
                "status": "ACTIVE",
                "message": "Analyzing patient medical history",
                "timestamp": "2024-03-20T10:30:00Z",
                "details": {
                    "progress": "50%",
                    "current_task": "Processing diabetes history"
                },
                "run_id": "sim_123456",
                "event_id": 10
            }
        } 