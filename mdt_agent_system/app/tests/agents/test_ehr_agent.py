import pytest
from unittest.mock import Mock, AsyncMock
import json
from datetime import datetime

from mdt_agent_system.app.agents.ehr_agent import EHRAgent
from mdt_agent_system.app.core.schemas import PatientCase
from mdt_agent_system.app.core.schemas.agent_output import AgentOutput
from mdt_agent_system.app.core.status import StatusUpdateService

@pytest.fixture
def mock_status_service():
    service = Mock(spec=StatusUpdateService)
    service.emit_status_update = AsyncMock()
    return service

@pytest.fixture
def sample_patient_case():
    return PatientCase(
        patient_id="TEST001",
        demographics={
            "age": 65,
            "gender": "F",
            "ethnicity": "Caucasian"
        },
        medical_history=[
            {
                "condition": "Hypertension",
                "diagnosed": "2020-01-01",
                "status": "Ongoing"
            },
            {
                "condition": "Type 2 Diabetes",
                "diagnosed": "2019-06-15",
                "status": "Ongoing"
            }
        ],
        current_condition={
            "primary_diagnosis": "Stage II Breast Cancer",
            "onset_date": "2023-01-01",
            "status": "Active",
            "details": {
                "medications": [
                    {"name": "Metformin", "dose": "1000mg", "frequency": "BID"},
                    {"name": "Lisinopril", "dose": "10mg", "frequency": "Daily"}
                ],
                "allergies": ["Penicillin"]
            }
        },
        lab_results=[
            {"test": "HbA1c", "value": "6.8", "unit": "%", "date": "2023-01-15"},
            {"test": "Blood Pressure", "value": "130/80", "unit": "mmHg", "date": "2023-01-15"}
        ]
    )

@pytest.fixture
def mock_llm_response():
    return """---MARKDOWN---
# Patient Overview
- 65-year-old female with Stage II Breast Cancer
- Significant medical history of Hypertension and Type 2 Diabetes
- Current medications include Metformin and Lisinopril

## Medical History
- Hypertension - well controlled on current medication
- Type 2 Diabetes - moderate control (HbA1c 6.8%)

## Current Medications
- Metformin 1000mg BID for diabetes
- Lisinopril 10mg daily for hypertension

## Clinical Assessment
- Primary concern: Stage II Breast Cancer
- Comorbidities well managed
- Blood pressure within target range (130/80 mmHg)

## Risk Factors
- Age >65 years
- Diabetes may impact treatment choices
- Hypertension requires monitoring during therapy

---METADATA---
{
    "key_findings": [
        "Stage II Breast Cancer diagnosis",
        "Well-controlled hypertension and diabetes",
        "No major contraindications to standard therapy"
    ],
    "clinical_metrics": {
        "active_conditions": [
            "Stage II Breast Cancer",
            "Hypertension",
            "Type 2 Diabetes"
        ],
        "current_medications": [
            "Metformin 1000mg BID",
            "Lisinopril 10mg daily"
        ]
    },
    "risk_assessment": {
        "age_related": "moderate",
        "comorbidity": "moderate",
        "medication_interaction": "low"
    }
}"""

@pytest.mark.asyncio
async def test_ehr_agent_initialization(mock_status_service):
    """Test EHR Agent initialization."""
    agent = EHRAgent(run_id="test_run", status_service=mock_status_service)
    assert agent.agent_id == "EHRAgent"
    assert agent.run_id == "test_run"
    assert agent._get_agent_type() == "ehr"

@pytest.mark.asyncio
async def test_ehr_agent_process(mock_status_service, sample_patient_case, mock_llm_response, monkeypatch):
    # Create agent
    agent = EHRAgent(run_id="test_run", status_service=mock_status_service)
    
    # Mock the LLM response
    async def mock_run_analysis(*args, **kwargs):
        return mock_llm_response
    
    monkeypatch.setattr(agent, "_run_analysis", mock_run_analysis)
    
    # Process the case
    result = await agent.process(sample_patient_case, {})
    
    # Verify the structure of the output
    assert "patient_summary" in result
    assert "active_conditions" in result
    assert "medications" in result
    assert "risk_factors" in result
    assert "treatment_history" in result
    assert "markdown_content" in result
    assert "metadata" in result
    
    # Verify content from markdown was properly extracted
    assert "Stage II Breast Cancer" in result["patient_summary"]
    assert len(result["active_conditions"]) >= 3  # Cancer, HTN, Diabetes
    assert len(result["medications"]) >= 2  # Metformin, Lisinopril
    
    # Verify metadata was properly included
    assert len(result["metadata"]["key_findings"]) >= 3
    assert len(result["metadata"]["clinical_metrics"]["active_conditions"]) >= 3
    
    # Verify status updates were called
    assert mock_status_service.emit_status_update.call_count == 2

def test_ehr_agent_prepare_input(mock_status_service, sample_patient_case):
    agent = EHRAgent(run_id="test_run", status_service=mock_status_service)
    
    # Test input preparation
    prepared_input = agent._prepare_input(sample_patient_case, {})
    
    # Verify the structure
    assert "context" in prepared_input
    assert "task" in prepared_input
    
    # Verify context contains required fields
    context_dict = json.loads(prepared_input["context"])
    assert "patient_id" in context_dict
    assert "demographics" in context_dict
    assert "medical_history" in context_dict
    assert "current_condition" in context_dict
    assert "lab_results" in context_dict
    
    # Verify task contains structured format instructions
    assert "Patient Overview" in prepared_input["task"]
    assert "Medical History" in prepared_input["task"]
    assert "Clinical Assessment" in prepared_input["task"]

def test_ehr_agent_structure_output(mock_status_service):
    agent = EHRAgent(run_id="test_run", status_service=mock_status_service)
    
    # Create a sample AgentOutput
    agent_output = AgentOutput(
        markdown_content="""# Patient Overview
- Test patient summary
## Medical History
- Test condition 1
- Test condition 2
## Current Medications
- Test med 1
- Test med 2""",
        metadata={
            "key_findings": ["Finding 1", "Finding 2"],
            "clinical_metrics": {
                "active_conditions": ["Condition 1", "Condition 2"],
                "current_medications": ["Med 1", "Med 2"]
            },
            "risk_assessment": {
                "overall": "moderate"
            }
        }
    )
    
    # Test output structuring
    structured = agent._structure_output(agent_output)
    
    # Verify structure
    assert "patient_summary" in structured
    assert "active_conditions" in structured
    assert "medications" in structured
    assert "risk_factors" in structured
    assert "treatment_history" in structured
    assert "markdown_content" in structured
    assert "metadata" in structured
    
    # Verify content mapping
    assert "Test patient summary" in structured["patient_summary"]
    assert "Condition 1" in structured["active_conditions"]
    assert "Med 1" in structured["medications"] 