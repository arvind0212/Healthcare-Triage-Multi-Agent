import pytest
from unittest.mock import Mock, AsyncMock
import json
from datetime import datetime

from mdt_agent_system.app.agents.imaging_agent import ImagingAgent
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
        }],
        imaging_results={
            "mammogram": {
                "date": "2024-03-15",
                "findings": "2.5 cm mass in upper outer quadrant of left breast"
            },
            "chest_ct": {
                "date": "2024-03-16",
                "findings": "No evidence of metastatic disease"
            }
        }
    )

@pytest.fixture
def sample_context():
    return {
        "ehr_analysis": {
            "key": "value",
            "relevant_history": "Previous imaging normal 1 year ago"
        }
    }

@pytest.fixture
def mock_llm_response():
    return """---MARKDOWN---
# Technical Assessment
- High quality diagnostic imaging obtained
- Comparison with prior studies from 2023
- No significant technical limitations

# Clinical Findings
## Primary Disease
- 2.5 cm irregular mass in left breast
- Upper outer quadrant location
- Spiculated margins

## Disease Extent
- Primary tumor: 2.5 cm mass with suspicious features
- Nodes: Two suspicious axillary lymph nodes
- Metastatic: No evidence of distant disease

## Secondary Findings
- Background fibroglandular density
- No additional suspicious lesions

# Staging Assessment
- Clinical stage: cT2N1M0
- Axillary nodes: Two suspicious nodes
- No evidence of distant metastases

## Clinical Correlation
- Findings support need for tissue sampling
- Consider breast MRI for extent of disease
- Suitable for image-guided biopsy

---METADATA---
{
    "key_findings": [
        "2.5 cm suspicious mass in left breast",
        "Two suspicious axillary nodes",
        "No distant metastases"
    ],
    "measurements": {
        "primary_lesion": "2.5 cm",
        "significant_nodes": ["1.2 cm", "0.8 cm"]
    },
    "confidence_scores": {
        "primary_finding": 0.95,
        "staging": 0.90,
        "progression": 0.85
    }
}"""

@pytest.mark.asyncio
async def test_imaging_agent_process(mock_status_service, sample_patient_case, sample_context, mock_llm_response, monkeypatch):
    # Create agent
    agent = ImagingAgent(run_id="test_run", status_service=mock_status_service)
    
    # Mock the LLM response
    async def mock_run_analysis(*args, **kwargs):
        return mock_llm_response
    
    monkeypatch.setattr(agent, "_run_analysis", mock_run_analysis)
    
    # Process the case
    result = await agent.process(sample_patient_case, sample_context)
    
    # Verify the structure of the output
    assert "summary" in result
    assert "disease_extent" in result
    assert "staging" in result
    assert "treatment_implications" in result
    assert "markdown_content" in result
    assert "metadata" in result
    
    # Verify content from markdown was properly extracted
    assert "2.5 cm" in result["disease_extent"]["primary_tumor"]
    assert "Two suspicious" in result["disease_extent"]["nodal_status"]
    assert "No evidence of distant" in result["disease_extent"]["metastatic_status"]
    assert "cT2N1M0" in result["staging"]["clinical_stage"]
    
    # Verify metadata was properly included
    assert result["metadata"]["measurements"]["primary_lesion"] == "2.5 cm"
    assert len(result["metadata"]["measurements"]["significant_nodes"]) == 2
    assert result["metadata"]["confidence_scores"]["primary_finding"] == 0.95
    
    # Verify status updates were called
    assert mock_status_service.emit_status_update.call_count == 2

def test_imaging_agent_prepare_input(mock_status_service, sample_patient_case, sample_context):
    agent = ImagingAgent(run_id="test_run", status_service=mock_status_service)
    
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
    assert "imaging_results" in context_dict
    assert "ehr_context" in context_dict
    
    # Verify task contains structured format instructions
    assert "Technical Assessment" in prepared_input["task"]
    assert "Clinical Findings" in prepared_input["task"]
    assert "Staging Assessment" in prepared_input["task"]

def test_imaging_agent_structure_output(mock_status_service):
    agent = ImagingAgent(run_id="test_run", status_service=mock_status_service)
    
    # Create a sample AgentOutput
    agent_output = AgentOutput(
        markdown_content="""# Clinical Findings
## Primary Disease
- Test mass
## Disease Extent
- Primary tumor: Test tumor details
- Nodes: Test node details
- Metastatic: No evidence
## Staging Assessment
- Clinical stage: T1N0M0""",
        metadata={
            "key_findings": ["Finding 1", "Finding 2"],
            "measurements": {
                "primary_lesion": "2.0 cm",
                "significant_nodes": ["1.0 cm"]
            },
            "confidence_scores": {
                "primary_finding": 0.9,
                "staging": 0.85
            }
        }
    )
    
    # Test output structuring
    structured = agent._structure_output(agent_output)
    
    # Verify structure
    assert "summary" in structured
    assert "disease_extent" in structured
    assert "staging" in structured
    assert "treatment_implications" in structured
    assert "markdown_content" in structured
    assert "metadata" in structured
    
    # Verify content mapping
    assert "Finding 1" in structured["summary"]
    assert "Test tumor details" in structured["disease_extent"]["primary_tumor"]
    assert "Test node details" in structured["disease_extent"]["nodal_status"]
    assert "T1N0M0" in structured["staging"]["clinical_stage"]
    assert structured["metadata"]["measurements"]["primary_lesion"] == "2.0 cm" 