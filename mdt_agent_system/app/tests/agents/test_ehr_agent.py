import pytest
import asyncio
import json
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from mdt_agent_system.app.core.schemas import PatientCase
from mdt_agent_system.app.core.status import StatusUpdateService
from mdt_agent_system.app.agents.ehr_agent import EHRAgent

# Sample patient case for testing
SAMPLE_PATIENT_CASE = PatientCase(
    patient_id="TEST001",
    demographics={
        "age": 65,
        "gender": "Female",
        "ethnicity": "Caucasian"
    },
    medical_history=[
        {"condition": "Hypertension", "year_diagnosed": 2010, "status": "Active"},
        {"condition": "Type 2 Diabetes", "year_diagnosed": 2015, "status": "Active"}
    ],
    current_condition={
        "chief_complaint": "Persistent cough with occasional hemoptysis",
        "duration": "3 months",
        "symptoms": ["cough", "hemoptysis", "weight loss"]
    },
    imaging_results={
        "chest_xray": "Suspicious mass in right upper lobe"
    },
    pathology_results={
        "biopsy_result": "Adenocarcinoma of the lung"
    }
)

@pytest.fixture
def mock_status_service():
    """Create a mock status update service."""
    service = MagicMock(spec=StatusUpdateService)
    service.emit_status_update = AsyncMock()
    return service

@pytest.fixture
def mock_llm():
    """Create a mock LLM that returns a predefined response."""
    mock = AsyncMock()
    mock.ainvoke.return_value = MagicMock(
        content="""
Summary: 65-year-old female with suspected lung cancer, active hypertension and diabetes.

Key History Points:
- Hypertension diagnosed in 2010, currently active
- Type 2 Diabetes diagnosed in 2015, currently active
- No previous cancer history noted

Current Presentation:
- Persistent cough with occasional hemoptysis for 3 months
- Associated weight loss
- Performance Status: ECOG 1 based on reported symptoms
- Comorbidity Impact: Diabetes and hypertension may affect treatment options

Risk Factors:
- Age >65 years
- Possible smoking history (not specified)

Clinical Implications:
- Multiple comorbidities require careful treatment planning
- Active diabetes may affect surgical options and recovery
- Hypertension needs to be well-controlled before invasive procedures
- Weight loss suggests advanced disease or metabolic impact
"""
    )
    return mock

@pytest.mark.asyncio
async def test_ehr_agent_init(mock_status_service):
    """Test EHR Agent initialization."""
    agent = EHRAgent(run_id="test_run", status_service=mock_status_service)
    assert agent.agent_id == "EHRAgent"
    assert agent.run_id == "test_run"
    assert agent._get_agent_type() == "ehr"

@pytest.mark.asyncio
async def test_ehr_agent_prepare_input(mock_status_service):
    """Test input preparation for the EHR Agent."""
    agent = EHRAgent(run_id="test_run", status_service=mock_status_service)
    input_data = agent._prepare_input(SAMPLE_PATIENT_CASE, {})
    
    # Check that input contains the expected keys
    assert "context" in input_data
    assert "task" in input_data
    
    # Check that context is a JSON string containing patient data
    context_dict = json.loads(input_data["context"])
    assert context_dict["patient_id"] == "TEST001"
    assert "demographics" in context_dict
    assert "medical_history" in context_dict
    assert "current_condition" in context_dict

@pytest.mark.asyncio
async def test_ehr_agent_structure_output(mock_status_service):
    """Test output structuring for the EHR Agent."""
    agent = EHRAgent(run_id="test_run", status_service=mock_status_service)
    
    # Sample LLM output for testing
    sample_output = """
Summary: Test summary

Key History Points:
- Point 1
- Point 2

Current Presentation:
- Symptom 1
- Symptom 2
Performance Status: ECOG 2
Comorbidity Impact: Significant

Risk Factors:
- Risk 1
- Risk 2

Clinical Implications:
- Implication 1
- Implication 2
"""
    
    structured_output = agent._structure_output(sample_output)
    
    # Check structured output format
    assert "summary" in structured_output
    assert "key_history_points" in structured_output
    assert "current_presentation" in structured_output
    assert "risk_factors" in structured_output
    assert "clinical_implications" in structured_output
    
    # Check content extraction
    assert "Test summary" in structured_output["summary"]
    assert len(structured_output["key_history_points"]) == 2
    assert structured_output["current_presentation"]["performance_status"] == "ECOG 2"
    assert structured_output["current_presentation"]["comorbidity_impact"] == "Significant"
    assert len(structured_output["risk_factors"]) == 2
    assert len(structured_output["clinical_implications"]) == 2

@pytest.mark.asyncio
@patch('mdt_agent_system.app.agents.base_agent.get_llm')
async def test_ehr_agent_process(mock_get_llm, mock_status_service, mock_llm):
    """Test the complete EHR Agent process flow."""
    # Configure the mock
    mock_get_llm.return_value = mock_llm
    
    agent = EHRAgent(run_id="test_run", status_service=mock_status_service)
    
    # Process the patient case
    result = await agent.process(SAMPLE_PATIENT_CASE, {})
    
    # Check that status updates were emitted
    assert mock_status_service.emit_status_update.call_count >= 2
    
    # Check that the LLM was invoked
    assert mock_llm.ainvoke.call_count == 1
    
    # Check the structure of the result
    assert "summary" in result
    assert "raw_output" in result
    assert "key_history_points" in result
    assert "current_presentation" in result
    assert "risk_factors" in result
    assert "clinical_implications" in result

@pytest.mark.asyncio
@patch('mdt_agent_system.app.agents.base_agent.get_llm')
async def test_ehr_agent_error_handling(mock_get_llm, mock_status_service):
    """Test EHR Agent error handling."""
    # Configure the mock to raise an exception
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = Exception("Test error")
    mock_get_llm.return_value = mock_llm
    
    agent = EHRAgent(run_id="test_run", status_service=mock_status_service)
    
    # Process the patient case and expect an exception
    with pytest.raises(Exception):
        await agent.process(SAMPLE_PATIENT_CASE, {})
    
    # Check that error status was emitted
    error_call = False
    for call in mock_status_service.emit_status_update.call_args_list:
        args, kwargs = call
        if kwargs.get("status_update_data", {}).get("status") == "ERROR":
            error_call = True
            break
    
    assert error_call, "Expected an ERROR status update" 