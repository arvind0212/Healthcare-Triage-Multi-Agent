from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class PatientCase(BaseModel):
    """Schema for patient case data."""
    patient_id: str = Field(..., description="Unique identifier for the patient")
    demographics: Dict[str, Any] = Field(..., description="Patient demographic information")
    medical_history: List[Dict[str, Any]] = Field(..., description="List of medical history entries")
    current_condition: Dict[str, Any] = Field(..., description="Current medical condition details")
    imaging_results: Optional[Dict[str, Any]] = Field(None, description="Results from imaging studies")
    pathology_results: Optional[Dict[str, Any]] = Field(None, description="Results from pathology studies")
    lab_results: Optional[List[Dict[str, Any]]] = Field(None, description="Laboratory test results")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of case creation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "P12345",
                "demographics": {
                    "age": 45,
                    "gender": "F",
                    "ethnicity": "Caucasian"
                },
                "medical_history": [
                    {
                        "condition": "Type 2 Diabetes",
                        "diagnosed": "2018-03-15",
                        "status": "Ongoing"
                    }
                ],
                "current_condition": {
                    "primary_complaint": "Chest pain",
                    "onset": "2023-12-01",
                    "severity": "Moderate"
                },
                "imaging_results": {
                    "chest_xray": {
                        "date": "2023-12-02",
                        "findings": "No acute abnormalities"
                    }
                }
            }
        } 