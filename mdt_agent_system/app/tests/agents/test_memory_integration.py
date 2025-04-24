import pytest
from unittest.mock import AsyncMock, patch
import asyncio
import os
import shutil
from pathlib import Path

from mdt_agent_system.app.agents.ehr_agent import EHRAgent
from mdt_agent_system.app.core.memory.persistence import PersistentConversationMemory
from mdt_agent_system.app.core.schemas import PatientCase

# Create a temp directory for test memory files
@pytest.fixture
def temp_memory_dir():
    # Create a temp directory for test
    test_dir = Path("temp_memory_test")
    test_dir.mkdir(exist_ok=True)
    yield test_dir
    # Clean up after test
    shutil.rmtree(test_dir)

@pytest.fixture
def mock_status_service():
    service = AsyncMock()
    service.emit_status_update = AsyncMock(return_value=None)
    return service

@pytest.mark.asyncio
async def test_agent_memory_integration(mock_status_service, temp_memory_dir):
    """Test that agents properly integrate with the memory system."""
    
    # Create an agent with a specific run_id for memory
    run_id = "test_memory_run"
    agent = EHRAgent(
        run_id=run_id,
        status_service=mock_status_service
    )
    
    # Initialize memory
    memory_path = temp_memory_dir / "ehr_agent_memory.json"
    agent.memory = PersistentConversationMemory(
        file_path=str(memory_path),
        session_id=f"{run_id}_{agent.agent_id}",
        return_messages=True
    )
    
    # Mock patient case
    patient_case = PatientCase(
        patient_id="TEST123",
        demographics={"age": 65, "gender": "male"},
        current_condition={"primary_diagnosis": "Test condition"},
        medical_history=[]
    )
    
    # Create mock input and output
    test_input = {"input": "Test input data"}
    test_output = {"output": "Test output data"}
    
    # Test saving to memory
    agent._save_to_memory(test_input, test_output)
    
    # Verify memory file was created
    assert memory_path.exists()
    
    # Create a new agent instance with the same memory path to test persistence
    new_agent = EHRAgent(
        run_id=run_id,
        status_service=mock_status_service
    )
    new_agent.memory = PersistentConversationMemory(
        file_path=str(memory_path),
        session_id=f"{run_id}_{agent.agent_id}",
        return_messages=True
    )
    
    # Load memory variables
    memory_variables = new_agent.memory.load_memory_variables({})
    
    # Verify memory contains our test data
    assert "history" in memory_variables
    assert len(memory_variables["history"]) == 2  # Should have human and AI messages
    
    # Test full agent process with memory integration
    with patch.object(new_agent, '_run_analysis', return_value="Mocked LLM response"):
        with patch.object(new_agent, '_structure_output', return_value={"summary": "Test summary"}):
            # Run the agent process
            result = await new_agent.process(patient_case, {})
            
            # Check memory was updated with this interaction
            memory_variables = new_agent.memory.load_memory_variables({})
            assert len(memory_variables["history"]) > 2  # Should have more messages now 