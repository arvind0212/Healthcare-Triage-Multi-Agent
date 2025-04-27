import pytest
from unittest.mock import Mock, AsyncMock
import json
from datetime import datetime

from mdt_agent_system.app.agents.specialist_agent import SpecialistAgent
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
        demographics={"age": 45, "gender": "F"},
        current_condition={
            "primary_diagnosis": "Breast cancer",
            "stage": "Newly diagnosed",
            "details": "Pending full workup"
        },
        medical_history=[{
            "condition": "No significant past medical history",
            "status": "Historical",
            "date_noted": datetime.now().isoformat()
        }]
    )

@pytest.fixture
def sample_context():
    return {
        "ehr_analysis": {"key": "value"},
        "imaging_analysis": {"key": "value"},
        "pathology_analysis": {"key": "value"}
    }

@pytest.fixture
def mock_llm_response():
    return """---MARKDOWN---
# Clinical Assessment
## Disease Status
- Stage II breast cancer, newly diagnosed
- No evidence of metastatic disease

## Treatment Recommendations
- Neoadjuvant chemotherapy recommended
- Consider clinical trial participation
- Surgery planning after chemotherapy response

## Risk Assessment
- Intermediate risk category
- Good performance status
- No significant comorbidities

## Follow-up Plan
- Weekly monitoring during chemotherapy
- Imaging reassessment at 3 months
- MDT review of response

---METADATA---
{
    "key_findings": [
        "Stage II breast cancer",
        "Candidate for neoadjuvant therapy",
        "No metastatic disease"
    ],
    "confidence_scores": {
        "diagnosis": 0.95,
        "treatment_plan": 0.85,
        "prognosis": 0.80
    },
    "clinical_metrics": {
        "case_complexity": "medium",
        "treatment_urgency": "routine",
        "evidence_level": "A"
    }
}"""

@pytest.mark.asyncio
async def test_specialist_agent_process(mock_status_service, sample_patient_case, sample_context, mock_llm_response, monkeypatch):
    # Create agent
    agent = SpecialistAgent(run_id="test_run", status_service=mock_status_service)
    
    # Mock the LLM response
    async def mock_run_analysis(*args, **kwargs):
        return mock_llm_response
    
    monkeypatch.setattr(agent, "_run_analysis", mock_run_analysis)
    
    # Process the case
    result = await agent.process(sample_patient_case, sample_context)
    
    # Verify the structure of the output
    assert "overall_assessment" in result
    assert "treatment_considerations" in result
    assert "risk_assessment" in result
    assert "follow_up_recommendations" in result
    assert "markdown_content" in result
    assert "metadata" in result
    
    # Verify content from markdown was properly extracted
    assert "Stage II breast cancer" in result["overall_assessment"]
    assert "Neoadjuvant chemotherapy recommended" in result["treatment_considerations"]
    assert len(result["follow_up_recommendations"]) > 0
    
    # Verify metadata was properly included
    assert result["metadata"]["confidence_scores"]["diagnosis"] == 0.95
    assert result["metadata"]["clinical_metrics"]["case_complexity"] == "medium"
    
    # Verify status updates were called
    assert mock_status_service.emit_status_update.call_count == 2
    
def test_specialist_agent_prepare_input(mock_status_service, sample_patient_case, sample_context):
    agent = SpecialistAgent(run_id="test_run", status_service=mock_status_service)
    
    # Test input preparation
    prepared_input = agent._prepare_input(sample_patient_case, sample_context)
    
    # Verify the structure
    assert "context" in prepared_input
    assert "task" in prepared_input
    
    # Verify context contains all necessary information
    context_dict = json.loads(prepared_input["context"])
    assert "patient_id" in context_dict
    assert "demographics" in context_dict
    assert "current_condition" in context_dict
    assert "medical_history" in context_dict
    assert "ehr_analysis" in context_dict
    assert "imaging_analysis" in context_dict
    assert "pathology_analysis" in context_dict
    
    # Verify task contains structured format instructions
    assert "Clinical Assessment" in prepared_input["task"]
    assert "Treatment Planning" in prepared_input["task"]
    assert "Evidence Integration" in prepared_input["task"]

def test_specialist_agent_structure_output(mock_status_service):
    agent = SpecialistAgent(run_id="test_run", status_service=mock_status_service)
    
    # Create a sample AgentOutput
    agent_output = AgentOutput(
        markdown_content="""# Clinical Assessment
## Disease Status
- Test condition
## Treatment Recommendations
- Test treatment 1
- Test treatment 2
## Follow-up Plan
- Test followup 1""",
        metadata={
            "key_findings": ["Finding 1", "Finding 2"],
            "confidence_scores": {"treatment_plan": 0.9},
            "clinical_metrics": {
                "case_complexity": "low",
                "treatment_urgency": "routine"
            }
        }
    )
    
    # Test output structuring
    structured = agent._structure_output(agent_output)
    
    # Verify structure
    assert "overall_assessment" in structured
    assert "treatment_considerations" in structured
    assert "risk_assessment" in structured
    assert "follow_up_recommendations" in structured
    assert "markdown_content" in structured
    assert "metadata" in structured
    
    # Verify content mapping
    assert "Finding 1" in structured["overall_assessment"]
    assert "Test treatment 1" in structured["treatment_considerations"]
    assert "Test followup 1" in structured["follow_up_recommendations"]
    assert "Case complexity: low" in structured["risk_assessment"] 