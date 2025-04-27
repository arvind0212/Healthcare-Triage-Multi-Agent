import pytest
from unittest.mock import Mock, AsyncMock
import json
from datetime import datetime

from mdt_agent_system.app.agents.pathology_agent import PathologyAgent
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
        pathology_results={
            "biopsy_date": "2024-03-15",
            "specimen_type": "Core needle biopsy",
            "specimen_site": "Left breast mass",
            "preliminary_findings": "Invasive ductal carcinoma"
        }
    )

@pytest.fixture
def sample_context():
    return {
        "ehr_analysis": {"key": "value"},
        "imaging_analysis": {
            "findings": "2.5 cm mass in left breast",
            "staging": "cT2N1M0"
        }
    }

@pytest.fixture
def mock_llm_response():
    return """---MARKDOWN---
# Pathology Report

## Specimen Details
- Core needle biopsy from left breast mass
- Adequate tissue for diagnosis
- Well-preserved specimen
- No processing artifacts

## Microscopic Findings
1. Histological Features
   - Invasive ductal carcinoma, grade 2
   - Moderate nuclear pleomorphism
   - Tubule formation present
   - Mitotic activity: 8/10 HPF

2. Molecular Results
   - ER: Positive (90%)
   - PR: Positive (80%)
   - HER2: Negative (IHC 1+)
   - Ki-67: 25%

## Clinical Implications
- Hormone receptor positive breast cancer
- Candidate for endocrine therapy
- Consider genomic testing (e.g., Oncotype DX)
- Additional tissue may be needed for complete biomarker assessment

---METADATA---
{
    "key_findings": [
        "Invasive ductal carcinoma, grade 2",
        "ER/PR positive, HER2 negative",
        "Ki-67: 25%"
    ],
    "molecular_profile": {
        "mutations": [],
        "biomarkers": {
            "ER": "Positive (90%)",
            "PR": "Positive (80%)",
            "HER2": "Negative",
            "Ki-67": "25%"
        },
        "therapeutic_targets": [
            "Hormone receptor positive - candidate for endocrine therapy"
        ]
    },
    "confidence_scores": {
        "diagnosis": 0.95,
        "molecular_results": 0.90,
        "treatment_implications": 0.85
    }
}"""

@pytest.mark.asyncio
async def test_pathology_agent_process(mock_status_service, sample_patient_case, sample_context, mock_llm_response, monkeypatch):
    # Create agent
    agent = PathologyAgent(run_id="test_run", status_service=mock_status_service)
    
    # Mock the LLM response
    async def mock_run_analysis(*args, **kwargs):
        return mock_llm_response
    
    monkeypatch.setattr(agent, "_run_analysis", mock_run_analysis)
    
    # Process the case
    result = await agent.process(sample_patient_case, sample_context)
    
    # Verify the structure of the output
    assert "markdown_content" in result
    assert "metadata" in result
    
    # Verify content from markdown was properly extracted
    assert "Invasive ductal carcinoma" in result["markdown_content"]
    assert "ER/PR positive" in result["metadata"]["key_findings"][1]
    
    # Verify metadata structure and content
    metadata = result["metadata"]
    assert "key_findings" in metadata
    assert "molecular_profile" in metadata
    assert "confidence_scores" in metadata
    
    # Verify molecular profile details
    molecular_profile = metadata["molecular_profile"]
    assert "mutations" in molecular_profile
    assert "biomarkers" in molecular_profile
    assert "therapeutic_targets" in molecular_profile
    
    # Verify specific biomarker values
    biomarkers = molecular_profile["biomarkers"]
    assert biomarkers["ER"] == "Positive (90%)"
    assert biomarkers["HER2"] == "Negative"
    
    # Verify confidence scores
    assert metadata["confidence_scores"]["diagnosis"] == 0.95
    assert metadata["confidence_scores"]["molecular_results"] == 0.90
    
    # Verify status updates were called
    assert mock_status_service.emit_status_update.call_count == 2

def test_pathology_agent_prepare_input(mock_status_service, sample_patient_case, sample_context):
    agent = PathologyAgent(run_id="test_run", status_service=mock_status_service)
    
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
    assert "pathology_results" in context_dict
    
    # Verify task contains structured format instructions
    assert "Specimen Assessment" in prepared_input["task"]
    assert "Diagnostic Findings" in prepared_input["task"]
    assert "Molecular Profile" in prepared_input["task"]
    assert "---MARKDOWN---" in prepared_input["task"]
    assert "---METADATA---" in prepared_input["task"]

def test_pathology_agent_structure_output(mock_status_service):
    agent = PathologyAgent(run_id="test_run", status_service=mock_status_service)
    
    # Test with raw unstructured output
    raw_output = """
    Specimen: Core biopsy
    Diagnosis: Invasive ductal carcinoma
    Grade: 2
    Biomarkers:
    - ER: Positive
    - HER2: Negative
    """
    
    # Test output structuring
    structured = agent._structure_output(raw_output)
    
    # Verify structure
    assert "markdown_content" in structured
    assert "metadata" in structured
    
    # Verify markdown sections
    markdown_content = structured["markdown_content"]
    assert "# Pathology Report" in markdown_content
    assert "## Specimen Details" in markdown_content
    assert "## Microscopic Findings" in markdown_content
    assert "## Clinical Implications" in markdown_content
    
    # Verify metadata structure
    metadata = structured["metadata"]
    assert "key_findings" in metadata
    assert "molecular_profile" in metadata
    assert "confidence_scores" in metadata
    
    # Verify metadata has required fields
    assert isinstance(metadata["key_findings"], list)
    assert isinstance(metadata["molecular_profile"]["mutations"], list)
    assert isinstance(metadata["molecular_profile"]["biomarkers"], dict)
    assert isinstance(metadata["confidence_scores"]["diagnosis"], float) 