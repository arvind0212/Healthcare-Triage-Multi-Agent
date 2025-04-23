import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

from mdt_agent_system.app.agents.evaluation_agent import EvaluationAgent
from mdt_agent_system.app.core.schemas import PatientCase
from mdt_agent_system.app.core.status import StatusUpdateService
from mdt_agent_system.app.agents.coordinator import AgentOutputPlaceholder


@pytest.fixture
def mock_status_service():
    service = AsyncMock(spec=StatusUpdateService)
    # Track emitted updates for tests
    service.emitted_updates = []
    
    async def emit_status_update(run_id, status_update_data):
        service.emitted_updates.append(status_update_data)
        return True
    
    service.emit_status_update = emit_status_update
    return service


@pytest.fixture
def sample_patient_case():
    # Create a minimal patient case for testing
    return PatientCase(
        patient_id="TEST123",
        demographics={"age": 62, "gender": "Female"},
        medical_history=[{"condition": "Hypertension"}],
        current_condition={"primary_complaint": "Chest pain"}
    )


@pytest.fixture
def sample_agent_context():
    # Create a context dictionary with output from previous agents
    return {
        "ehr_analysis": AgentOutputPlaceholder(
            summary="EHR analysis summary",
            details={
                "key_history_points": ["Hypertension", "Type 2 Diabetes"],
                "current_presentation": {
                    "main_symptoms": ["Chest pain", "Shortness of breath"]
                }
            }
        ).dict(),
        "imaging_analysis": AgentOutputPlaceholder(
            summary="Imaging analysis summary",
            details={
                "disease_extent": {
                    "primary_tumor": "3.8 cm RUL mass"
                },
                "staging": {
                    "clinical_stage": "Stage IIIA"
                }
            }
        ).dict(),
        "pathology_analysis": AgentOutputPlaceholder(
            summary="Pathology analysis summary",
            details={
                "histology": "Adenocarcinoma",
                "molecular_profile": {
                    "key_mutations": "KRAS G12C mutation"
                }
            }
        ).dict(),
        "guideline_recommendations": [
            {
                "guideline": "NCCN Non-Small Cell Lung Cancer",
                "recommendation": "Consider concurrent chemoradiation"
            }
        ],
        "specialist_assessment": AgentOutputPlaceholder(
            summary="Specialist assessment summary",
            details={
                "overall_assessment": "Potentially curable stage IIIA NSCLC",
                "treatment_considerations": [
                    "High PD-L1 expression favors immunotherapy"
                ]
            }
        ).dict()
    }


def test_initialization():
    """Test the agent initialization."""
    service = AsyncMock(spec=StatusUpdateService)
    agent = EvaluationAgent(run_id="test-run", status_service=service)
    
    assert agent.agent_id == "EvaluationAgent"
    assert agent.run_id == "test-run"
    assert agent._get_agent_type() == "evaluation"


def test_prepare_input(sample_patient_case, sample_agent_context):
    """Test the input preparation logic."""
    service = AsyncMock(spec=StatusUpdateService)
    agent = EvaluationAgent(run_id="test-run", status_service=service)
    
    result = agent._prepare_input(sample_patient_case, sample_agent_context)
    
    # Check basic structure
    assert "context" in result
    assert "task" in result
    
    # The context should include the MDT report sections
    context = result["context"]
    assert "MDT Report" in context
    assert "Evaluation Criteria" in context
    
    # Verify all agent outputs are included
    assert "patient_id" in context
    assert "ehr_analysis" in context
    assert "imaging_analysis" in context
    assert "pathology_analysis" in context
    assert "guideline_recommendations" in context
    assert "specialist_assessment" in context
    
    # Check that task is properly set
    assert "Evaluate the quality and completeness" in result["task"]
    assert "numerical score" in result["task"]


def test_structure_output_with_well_formatted_response():
    """Test output structuring with a well-formatted LLM response."""
    service = AsyncMock(spec=StatusUpdateService)
    agent = EvaluationAgent(run_id="test-run", status_service=service)
    
    # Sample well-formatted LLM output
    llm_output = """
    # MDT Report Evaluation

    ## Overall Score: 0.85

    ## Comments:
    The MDT report is comprehensive and follows evidence-based guidelines. It provides thorough analysis of patient history, imaging, and pathology findings. Treatment recommendations are aligned with guidelines.

    ## Strengths:
    - Comprehensive coverage of patient history and current presentation
    - Detailed imaging analysis with proper staging
    - Molecular profiling results clearly presented
    - Guideline-based treatment recommendations provided
    - Specialist assessment includes treatment considerations

    ## Areas for Improvement:
    - More detailed discussion of treatment alternatives
    - Limited consideration of patient preferences and quality of life
    - Dosing recommendations for therapy not specified

    ## Missing Elements:
    - Follow-up plan not clearly defined
    - No discussion of potential clinical trials
    """
    
    result = agent._structure_output(llm_output)
    
    # Check basic structure
    assert "score" in result
    assert "comments" in result
    assert "strengths" in result
    assert "areas_for_improvement" in result
    assert "missing_elements" in result
    
    # Check values
    assert result["score"] == 0.85
    assert "comprehensive" in result["comments"].lower()
    assert len(result["strengths"]) >= 3
    assert len(result["areas_for_improvement"]) >= 2
    assert len(result["missing_elements"]) >= 1


def test_structure_output_with_poorly_formatted_response():
    """Test output structuring with a poorly-formatted LLM response."""
    service = AsyncMock(spec=StatusUpdateService)
    agent = EvaluationAgent(run_id="test-run", status_service=service)
    
    # Sample poorly-formatted LLM output without clear sections
    llm_output = """
    The MDT report has been reviewed. It covers most essential elements but could be improved.
    I would rate it 75% complete based on the criteria.
    There are some good aspects including the detailed pathology analysis.
    However, treatment alternatives should be discussed more thoroughly.
    The report should also include a follow-up plan.
    """
    
    result = agent._structure_output(llm_output)
    
    # Check that we still get a valid structure
    assert "score" in result
    assert "comments" in result
    assert "strengths" in result
    assert "areas_for_improvement" in result
    
    # Score should be extracted and converted from percentage
    assert result["score"] == 0.75
    
    # Should have some default values
    assert len(result["strengths"]) > 0
    assert len(result["areas_for_improvement"]) > 0


@pytest.mark.asyncio
@patch('mdt_agent_system.app.agents.evaluation_agent.EvaluationAgent._run_analysis')
async def test_process_flow(mock_run_analysis, sample_patient_case, sample_agent_context, mock_status_service):
    """Test the complete agent processing flow with a mocked LLM response."""
    # Set up the mock response
    mock_run_analysis.return_value = """
    ## Overall Score: 0.85
    
    ## Comments:
    The MDT report is comprehensive and follows evidence-based guidelines.
    
    ## Strengths:
    - Comprehensive coverage of patient history
    - Detailed imaging analysis
    - Molecular profiling results
    
    ## Areas for Improvement:
    - More detailed discussion of treatment alternatives
    - Limited consideration of patient preferences
    
    ## Missing Elements:
    - Follow-up plan not clearly defined
    """
    
    # Create the agent
    agent = EvaluationAgent(run_id="test-run", status_service=mock_status_service)
    
    # Process the patient case
    result = await agent.process(sample_patient_case, sample_agent_context)
    
    # Verify the result
    assert result["score"] == 0.85
    assert len(result["strengths"]) >= 3
    assert len(result["areas_for_improvement"]) >= 2
    
    # Verify status updates were emitted
    assert len(mock_status_service.emitted_updates) == 2
    assert mock_status_service.emitted_updates[0]["status"] == "ACTIVE"
    assert mock_status_service.emitted_updates[1]["status"] == "DONE"
    
    # Verify the LLM was called with appropriate input
    mock_run_analysis.assert_called_once()
    input_data = agent._prepare_input(sample_patient_case, sample_agent_context)
    assert "MDT Report" in input_data["context"] 