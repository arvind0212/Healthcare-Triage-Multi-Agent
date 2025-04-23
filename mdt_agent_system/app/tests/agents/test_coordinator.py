import pytest
import asyncio
import uuid
from unittest.mock import AsyncMock, patch, call
from datetime import datetime
from typing import List, Dict, Any

from mdt_agent_system.app.agents.coordinator import run_mdt_simulation, AgentContext, AgentOutputPlaceholder
from mdt_agent_system.app.core.schemas import PatientCase, MDTReport, StatusUpdate
from mdt_agent_system.app.core.status import StatusUpdateService, Status

# --- Fixtures ---

@pytest.fixture
def sample_run_id() -> str:
    return str(uuid.uuid4())

@pytest.fixture
def sample_patient_case() -> PatientCase:
    # Create a minimal valid PatientCase for testing
    return PatientCase(
        patient_id="test-patient-001",
        demographics={"age": 65, "gender": "Male"},
        medical_history=[{"condition": "Hypertension"}],
        current_condition={"description": "Presenting with chest pain"},
        imaging_results=None, # Keep minimal
        pathology_results=None,
        lab_results=None
    )

@pytest.fixture
def mock_status_service() -> AsyncMock:
    mock = AsyncMock(spec=StatusUpdateService)
    mock.emitted_updates = [] # Add a list to store emitted updates

    async def _mock_emit(status_update: StatusUpdate):
        # Ensure status is an enum member before storing
        if isinstance(status_update.status, Status):
             status_update.status = status_update.status.value # Store the string value for easier assertion
        # Convert to dict for easier comparison if needed, or store the object
        mock.emitted_updates.append(status_update)
        # print(f"Mock Emit: {status_update.agent_id} - {status_update.status} - {status_update.message}") # Debug print

    async def _mock_emit_update(run_id: str, status_update_data: Dict[str, Any]):
        # Create a StatusUpdate object from the data
        status_update = StatusUpdate(
            run_id=run_id,
            event_id=len(mock.emitted_updates),  # Assign sequential event ID
            **status_update_data
        )
        mock.emitted_updates.append(status_update)

    mock.emit_status_update.side_effect = _mock_emit_update
    mock.emit_status.side_effect = _mock_emit
    return mock

# --- Test Cases ---

@pytest.mark.asyncio
@patch('mdt_agent_system.app.agents.coordinator._run_ehr_agent_step')
@patch('mdt_agent_system.app.agents.coordinator._run_imaging_agent_step')
@patch('mdt_agent_system.app.agents.coordinator._run_pathology_agent_step')
@patch('mdt_agent_system.app.agents.coordinator._run_guideline_agent_step')
@patch('mdt_agent_system.app.agents.coordinator._run_specialist_agent_step')
@patch('mdt_agent_system.app.agents.coordinator._run_evaluation_step')
async def test_coordinator_successful_run(
    mock_evaluation_step,
    mock_specialist_step,
    mock_guideline_step,
    mock_pathology_step,
    mock_imaging_step,
    mock_ehr_step,
    sample_run_id: str,
    sample_patient_case: PatientCase,
    mock_status_service: AsyncMock
):
    """Test a successful run of the coordinator with mocked agent steps."""
    # Setup mock returns for agent steps
    async def ehr_side_effect(context):
        context.ehr_analysis = AgentOutputPlaceholder(summary="EHR Analysis Complete (Simulated)")
        return context
    
    async def imaging_side_effect(context):
        context.imaging_analysis = AgentOutputPlaceholder(summary="Imaging Analysis Complete (Simulated)")
        return context
    
    async def pathology_side_effect(context):
        context.pathology_analysis = AgentOutputPlaceholder(summary="Pathology Analysis Complete (Simulated)")
        return context
    
    async def guideline_side_effect(context):
        context.guideline_recommendations = [{"recommendation": "Standard Guideline Applied (Simulated)"}]
        return context
    
    async def specialist_side_effect(context):
        context.specialist_assessment = AgentOutputPlaceholder(summary="Specialist Assessment Complete (Simulated)")
        return context
    
    async def evaluation_side_effect(context):
        context.evaluation = {"score": 0.85, "comments": "Evaluation Complete (Simulated)."}
        return context
    
    # Configure the mocks
    mock_ehr_step.side_effect = ehr_side_effect
    mock_imaging_step.side_effect = imaging_side_effect
    mock_pathology_step.side_effect = pathology_side_effect
    mock_guideline_step.side_effect = guideline_side_effect
    mock_specialist_step.side_effect = specialist_side_effect
    mock_evaluation_step.side_effect = evaluation_side_effect

    # Call the simulation function
    report = await run_mdt_simulation(
        run_id=sample_run_id,
        patient_case=sample_patient_case,
        status_service=mock_status_service
    )

    # 1. Check that all mock steps were called
    mock_ehr_step.assert_called_once()
    mock_imaging_step.assert_called_once()
    mock_pathology_step.assert_called_once()
    mock_guideline_step.assert_called_once()
    mock_specialist_step.assert_called_once()
    mock_evaluation_step.assert_called_once()

    # 2. Check Report Structure
    assert isinstance(report, MDTReport)
    assert report.patient_id == sample_patient_case.patient_id
    assert report.summary == "MDT Simulation Complete (Runnable Workflow)"
    assert report.ehr_analysis["summary"] == "EHR Analysis Complete (Simulated)"
    assert report.evaluation_score == 0.85
    assert report.guideline_recommendations == [{"recommendation": "Standard Guideline Applied (Simulated)"}]

    # 3. Check Status Updates Sequence and Content
    # The status updates will now come from our mocks and the coordinator
    updates = mock_status_service.emitted_updates
    assert len(updates) >= 2  # At minimum: init + final status
    assert updates[0].agent_id == "Coordinator"
    assert updates[0].status == Status.ACTIVE.value
    assert updates[0].message == "Initiating MDT Workflow"
    
    # Check final status
    assert updates[-1].agent_id == "Coordinator"
    assert updates[-1].status == Status.DONE.value
    assert updates[-1].message == "MDT Simulation Finished Successfully"


@pytest.mark.asyncio
async def test_coordinator_error_handling(
    sample_run_id: str,
    sample_patient_case: PatientCase,
    mock_status_service: AsyncMock
):
    """Test the coordinator's error handling when an agent step fails."""

    # Patch one of the agent step functions to raise an error
    error_message = "Simulated Pathology Failure"
    with patch(
        "mdt_agent_system.app.agents.coordinator._run_pathology_agent_step",
        new_callable=AsyncMock,
        side_effect=ValueError(error_message)
    ) as mock_failing_step:

        with pytest.raises(ValueError, match=error_message):
            await run_mdt_simulation(
                run_id=sample_run_id,
                patient_case=sample_patient_case,
                status_service=mock_status_service
            )

    # Check that the failing step was called
    mock_failing_step.assert_called_once()

    # Check Status Updates for Error
    updates = mock_status_service.emitted_updates

    # Verify sequence up to the failure point (Initiate, Handover EHR, EHR Active, EHR Done, Handover Imaging, Imaging Active, Imaging Done, Handover Path)
    assert len(updates) == 9  # Initial + 2 complete steps + part of pathology step + error
    assert updates[0].message == "Initiating MDT Workflow"
    assert updates[1].message == "Handing over to EHR Agent"
    assert updates[3].message == "EHR Analysis Finished"
    assert updates[4].message == "Handing over to Imaging Agent"
    assert updates[6].message == "Imaging Analysis Finished"
    assert updates[7].message == "Handing over to Pathology Agent"
    assert updates[7].agent_id == "Coordinator"

    # Check the final status update is an ERROR from the Coordinator
    assert updates[-1].agent_id == "Coordinator"
    assert updates[-1].status == Status.ERROR.value
    assert error_message in updates[-1].message
    assert updates[-1].details == {"error_type": "ValueError"} 