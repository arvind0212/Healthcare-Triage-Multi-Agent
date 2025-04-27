import pytest
from unittest.mock import Mock, AsyncMock
import json
from datetime import datetime

from mdt_agent_system.app.agents.guideline_agent import GuidelineAgent
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
                "histology": "Invasive ductal carcinoma",
                "grade": "2",
                "receptor_status": {
                    "er": "Positive",
                    "pr": "Positive",
                    "her2": "Negative"
                }
            }
        }
    )

@pytest.fixture
def sample_context():
    return {
        "ehr_analysis": {
            "patient_summary": "65-year-old female with Stage II Breast Cancer and comorbidities",
            "active_conditions": ["Stage II Breast Cancer", "Hypertension", "Type 2 Diabetes"],
            "risk_factors": ["Age >65", "Multiple comorbidities"]
        },
        "imaging_analysis": {
            "findings": "2.5 cm mass in left breast, no distant metastases",
            "staging": "cT2N0M0"
        },
        "pathology_analysis": {
            "diagnosis": "Invasive ductal carcinoma",
            "grade": "2",
            "receptor_status": {
                "er": "Positive",
                "pr": "Positive",
                "her2": "Negative"
            }
        }
    }

@pytest.fixture
def mock_llm_response():
    return """---MARKDOWN---
# Guideline-Based Recommendations

## Disease Characteristics
- Stage II (T2N0M0) Breast Cancer
- Hormone receptor positive (ER+/PR+)
- HER2 negative
- Grade 2 invasive ductal carcinoma

## Treatment Guidelines
### Primary Treatment
- Surgery: Breast-conserving surgery (lumpectomy) with sentinel lymph node biopsy
- Alternative: Total mastectomy if breast conservation not suitable

### Systemic Therapy
- Endocrine therapy indicated (ER+/PR+ status)
- Consider chemotherapy based on genomic testing
- Duration: 5-10 years of endocrine therapy recommended

### Radiation Therapy
- Indicated after breast-conserving surgery
- Consider regional nodal irradiation based on risk factors

## Special Considerations
- Age >65: Consider comorbidities in treatment planning
- Diabetes and hypertension require careful monitoring
- Standard of care may need modification based on performance status

## Evidence Level
- Primary recommendations: Level 1A evidence
- Treatment sequence: Level 2A evidence
- Special population considerations: Level 2B evidence

---METADATA---
{
    "guideline_sources": [
        "NCCN Breast Cancer Guidelines Version 2.2024",
        "ASCO Clinical Practice Guidelines",
        "ESMO Clinical Practice Guidelines"
    ],
    "evidence_levels": {
        "primary_treatment": "1A",
        "systemic_therapy": "1A",
        "radiation_therapy": "1A",
        "special_considerations": "2B"
    },
    "treatment_priorities": [
        "Surgery with sentinel node biopsy",
        "Systemic therapy assessment",
        "Radiation therapy planning"
    ],
    "key_recommendations": [
        "Breast conservation with radiation is preferred if feasible",
        "Endocrine therapy is indicated",
        "Consider genomic testing for chemotherapy decision",
        "Careful monitoring of comorbidities during treatment"
    ]
}"""

@pytest.mark.asyncio
async def test_guideline_agent_initialization(mock_status_service):
    """Test Guideline Agent initialization."""
    agent = GuidelineAgent(run_id="test_run", status_service=mock_status_service)
    assert agent.agent_id == "GuidelineAgent"
    assert agent.run_id == "test_run"
    assert agent._get_agent_type() == "guideline"

@pytest.mark.asyncio
async def test_guideline_agent_process(mock_status_service, sample_patient_case, sample_context, mock_llm_response, monkeypatch):
    # Create agent
    agent = GuidelineAgent(run_id="test_run", status_service=mock_status_service)
    
    # Mock the LLM response
    async def mock_run_analysis(*args, **kwargs):
        return mock_llm_response
    
    monkeypatch.setattr(agent, "_run_analysis", mock_run_analysis)
    
    # Process the case
    result = await agent.process(sample_patient_case, sample_context)
    
    # Verify the structure of the output
    assert "disease_characteristics" in result
    assert "treatment_recommendations" in result
    assert "evidence_levels" in result
    assert "special_considerations" in result
    assert "markdown_content" in result
    assert "metadata" in result
    
    # Verify content from markdown was properly extracted
    assert "Stage II" in result["disease_characteristics"]
    assert "Surgery" in result["treatment_recommendations"]
    assert "Level 1A" in result["evidence_levels"]
    assert "Age >65" in result["special_considerations"]
    
    # Verify metadata was properly included
    assert len(result["metadata"]["guideline_sources"]) >= 2
    assert result["metadata"]["evidence_levels"]["primary_treatment"] == "1A"
    
    # Verify status updates were called
    assert mock_status_service.emit_status_update.call_count == 2

def test_guideline_agent_prepare_input(mock_status_service, sample_patient_case, sample_context):
    agent = GuidelineAgent(run_id="test_run", status_service=mock_status_service)
    
    # Test input preparation
    prepared_input = agent._prepare_input(sample_patient_case, sample_context)
    
    # Verify the structure
    assert "context" in prepared_input
    assert "task" in prepared_input
    
    # Verify context contains required fields
    context_dict = json.loads(prepared_input["context"])
    assert "patient_case" in context_dict
    assert "ehr_analysis" in context_dict
    assert "imaging_analysis" in context_dict
    assert "pathology_analysis" in context_dict
    
    # Verify task contains structured format instructions
    assert "Disease Characteristics" in prepared_input["task"]
    assert "Treatment Guidelines" in prepared_input["task"]
    assert "Evidence Level" in prepared_input["task"]

def test_guideline_agent_structure_output(mock_status_service):
    agent = GuidelineAgent(run_id="test_run", status_service=mock_status_service)
    
    # Create a sample AgentOutput
    agent_output = AgentOutput(
        markdown_content="""# Guideline-Based Recommendations
## Disease Characteristics
- Test characteristic 1
- Test characteristic 2
## Treatment Guidelines
- Test treatment 1
- Test treatment 2
## Evidence Level
- Test evidence 1""",
        metadata={
            "guideline_sources": ["Source 1", "Source 2"],
            "evidence_levels": {
                "primary_treatment": "1A",
                "systemic_therapy": "1B"
            },
            "key_recommendations": ["Rec 1", "Rec 2"]
        }
    )
    
    # Test output structuring
    structured = agent._structure_output(agent_output)
    
    # Verify structure
    assert "disease_characteristics" in structured
    assert "treatment_recommendations" in structured
    assert "evidence_levels" in structured
    assert "special_considerations" in structured
    assert "markdown_content" in structured
    assert "metadata" in structured
    
    # Verify content mapping
    assert "Test characteristic" in structured["disease_characteristics"]
    assert "Test treatment" in structured["treatment_recommendations"]
    assert "Test evidence" in structured["evidence_levels"]
    assert structured["metadata"]["guideline_sources"] == ["Source 1", "Source 2"] 