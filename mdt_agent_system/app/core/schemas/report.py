from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class MDTReport(BaseModel):
    """Schema for MDT meeting report."""
    patient_id: str = Field(..., description="Patient identifier the report refers to")
    summary: str = Field(..., description="Overall case summary")
    ehr_analysis: Dict[str, Any] = Field(..., description="Analysis of electronic health records")
    imaging_analysis: Optional[Dict[str, Any]] = Field(None, description="Analysis of imaging studies")
    pathology_analysis: Optional[Dict[str, Any]] = Field(None, description="Analysis of pathology findings")
    guideline_recommendations: List[Dict[str, Any]] = Field(..., description="Relevant guideline recommendations")
    specialist_assessment: Dict[str, Any] = Field(..., description="Specialist's assessment and recommendations")
    treatment_options: List[Dict[str, Any]] = Field(..., description="Proposed treatment options")
    evaluation_score: Optional[float] = Field(None, description="Self-evaluation score of the report")
    evaluation_comments: Optional[str] = Field(None, description="Self-evaluation comments")
    evaluation_formatted: Optional[str] = Field(None, description="Formatted evaluation summary with score and key points")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Report generation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "P12345",
                "summary": "45-year-old female presenting with chest pain...",
                "ehr_analysis": {
                    "key_findings": ["Type 2 Diabetes - controlled", "Recent onset chest pain"],
                    "risk_factors": ["Diabetes", "Family history of CAD"]
                },
                "imaging_analysis": {
                    "chest_xray": {
                        "interpretation": "Normal cardiac silhouette, no acute findings"
                    }
                },
                "guideline_recommendations": [
                    {
                        "guideline": "AHA/ACC Chest Pain",
                        "recommendation": "Consider stress test"
                    }
                ],
                "specialist_assessment": {
                    "cardiology_opinion": "Low-intermediate risk for ACS",
                    "recommendations": ["Stress test", "Risk factor modification"]
                },
                "treatment_options": [
                    {
                        "option": "Conservative management",
                        "details": "Risk factor modification and monitoring"
                    }
                ]
            }
        } 