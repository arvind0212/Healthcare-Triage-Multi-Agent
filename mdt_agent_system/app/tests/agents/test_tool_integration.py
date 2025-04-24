import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
from mdt_agent_system.app.agents.guideline_agent import GuidelineAgent
from mdt_agent_system.app.core.tools import ToolRegistry, GuidelineReferenceTool
from mdt_agent_system.app.core.schemas import PatientCase

@pytest.fixture
def mock_status_service():
    service = AsyncMock()
    # Configure the emit_status_update method to return a coroutine
    service.emit_status_update = AsyncMock(return_value=None)
    return service

@pytest.mark.asyncio
async def test_guideline_agent_tool_integration(mock_status_service):
    """Test that the Guideline Agent correctly integrates with tools."""
    # Reset tool registry for testing
    ToolRegistry._tools = {}
    
    # Initialize agent
    agent = GuidelineAgent(run_id="test_run", status_service=mock_status_service)
    
    # Verify that the guideline tool was registered
    assert "guideline_reference" in ToolRegistry.list_tools()
    guideline_tool = ToolRegistry.get_tool("guideline_reference")
    assert isinstance(guideline_tool, GuidelineReferenceTool)
    
    # Create a minimal patient case for testing
    patient_case = PatientCase(
        patient_id="TEST123",
        demographics={"age": 65, "gender": "male"},
        current_condition={"primary_diagnosis": "Test condition"},
        medical_history=[]
    )
    
    # Patch the entire process method to avoid LLM calls
    with patch.object(agent, '_run_analysis', return_value="Mocked LLM response"):
        with patch.object(agent, '_structure_output', return_value={"summary": "Test summary"}):
            # Run the agent process
            result = await agent.process(patient_case, {})
            
            # Verify the agent completed successfully
            assert result is not None
            # The mock status service should have been called for status updates
            mock_status_service.emit_status_update.assert_called()
            
            # Verify that the _prepare_input method includes tool information
            input_data = agent._prepare_input(patient_case, {})
            assert "available_tools" in input_data["context"] 