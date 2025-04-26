import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from mdt_agent_system.app.agents.summary_agent import SummaryAgent
from mdt_agent_system.app.core.schemas import PatientCase
from mdt_agent_system.app.core.status import StatusUpdateService

# Sample test data
sample_patient_case = PatientCase(
    patient_id="P12345",
    demographics={
        "age": 45,
        "gender": "M",
        "ethnicity": "Caucasian"
    },
    medical_history=[
        {
            "condition": "Hypertension",
            "diagnosed": "2015-03-15",
            "status": "Ongoing"
        }
    ],
    current_condition={
        "primary_complaint": "Chest pain",
        "onset": "2023-12-01",
        "severity": "Moderate"
    }
)

sample_context = {
    "ehr_analysis": {
        "key_findings": ["Hypertension - controlled", "Recent onset chest pain"],
        "risk_factors": ["Hypertension", "Smoking history"]
    },
    "imaging_analysis": {
        "chest_xray": {
            "interpretation": "No acute abnormalities"
        }
    },
    "specialist_assessment": {
        "overall_assessment": "Low-risk chest pain, likely musculoskeletal",
        "recommendations": ["Stress test", "Risk factor modification"]
    },
    "evaluation": {
        "score": 0.85,
        "comments": "Comprehensive assessment"
    }
}

sample_llm_output = """# MDT Summary: P12345

## Diagnosis & Staging
- **Confirmed Diagnosis**: Musculoskeletal Chest Pain
- **Stage**: Low-risk
- **Key Molecular Findings**: None
- **Performance Status**: Good

## Key Recommendations
1. Stress test to rule out cardiac etiology
2. Risk factor modification for hypertension
3. NSAIDs for pain relief

## Critical Next Steps
- [ ] Schedule stress test within 1 week
- [ ] Follow-up with primary care in 2 weeks
- [ ] Smoking cessation counseling
"""

@pytest.mark.asyncio
async def test_summary_agent_process():
    """Test the entire SummaryAgent process method."""
    # Mock dependencies
    status_service = AsyncMock(spec=StatusUpdateService)
    status_service.emit_status_update = AsyncMock()
    
    # Create agent with mocked dependencies
    agent = SummaryAgent(
        run_id="test-run-123",
        status_service=status_service
    )
    
    # Mock the LLM interaction to return our sample output
    agent._run_analysis = AsyncMock(return_value=sample_llm_output)
    
    # Process the test data
    result = await agent.process(sample_patient_case, sample_context)
    
    # Validate the result
    assert "markdown_summary" in result
    assert result["markdown_summary"] == sample_llm_output
    assert "# MDT Summary: P12345" in result["markdown_summary"]
    
    # Verify status updates were emitted
    assert status_service.emit_status_update.call_count == 2
    
@pytest.mark.asyncio
async def test_summary_agent_prepare_input():
    """Test the prepare_input method of SummaryAgent."""
    # Create agent with mocked status service
    status_service = AsyncMock(spec=StatusUpdateService)
    agent = SummaryAgent(
        run_id="test-run-123",
        status_service=status_service
    )
    
    # Call the method
    result = agent._prepare_input(sample_patient_case, sample_context)
    
    # Validate the result
    assert "context" in result
    assert "task" in result
    assert "Create a concise" in result["task"]
    
    # Verify the context contains serialized data
    context_dict = json.loads(result["context"])
    assert "ehr_analysis" in context_dict
    assert "imaging_analysis" in context_dict
    assert "specialist_assessment" in context_dict
    assert "evaluation" in context_dict

def test_summary_agent_structure_output():
    """Test the structure_output method of SummaryAgent."""
    # Create agent with mocked status service
    status_service = MagicMock(spec=StatusUpdateService)
    agent = SummaryAgent(
        run_id="test-run-123",
        status_service=status_service
    )
    
    # Call the method
    result = agent._structure_output(sample_llm_output)
    
    # Validate the result
    assert "markdown_summary" in result
    assert result["markdown_summary"] == sample_llm_output 