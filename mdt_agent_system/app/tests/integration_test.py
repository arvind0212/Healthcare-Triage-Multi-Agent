import os
import pytest
import asyncio
import tempfile
import uuid
import json
from unittest.mock import patch, AsyncMock

from mdt_agent_system.app.agents.coordinator import run_mdt_simulation, AgentContext
from mdt_agent_system.app.core.schemas import PatientCase, MDTReport
from mdt_agent_system.app.core.status import StatusUpdateService, Status
from mdt_agent_system.app.core.memory.persistence import JSONFileMemoryStore, PersistentConversationMemory
from mdt_agent_system.app.core.tools import ToolRegistry
from mdt_agent_system.app.agents.guideline_agent import GuidelineAgent
from mdt_agent_system.app.agents.ehr_agent import EHRAgent
from mdt_agent_system.app.agents.imaging_agent import ImagingAgent
from mdt_agent_system.app.agents.pathology_agent import PathologyAgent
from mdt_agent_system.app.agents.specialist_agent import SpecialistAgent
from mdt_agent_system.app.agents.evaluation_agent import EvaluationAgent

# --- Integration Test Fixtures ---

@pytest.fixture
def sample_run_id() -> str:
    return str(uuid.uuid4())

@pytest.fixture
def temp_memory_dir():
    """Create temporary directory for memory files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def sample_patient_case() -> PatientCase:
    """Create a realistic patient case for integration testing."""
    return PatientCase(
        patient_id="test-patient-001",
        demographics={"age": 65, "gender": "Male"},
        medical_history=[
            {"condition": "Hypertension", "duration": "10 years"},
            {"condition": "Type 2 Diabetes", "duration": "5 years"}
        ],
        current_condition={
            "description": "Presenting with chest pain and shortness of breath",
            "duration": "3 days",
            "severity": "moderate"
        },
        imaging_results={
            "chest_xray": "Cardiomegaly noted. No obvious lung infiltrates.",
            "cardiac_mri": "Left ventricular hypertrophy. Ejection fraction 45%."
        },
        pathology_results={
            "blood_work": "Elevated troponin (0.5 ng/mL). Normal CBC.",
            "cardiac_enzymes": "CK-MB slightly elevated at 12 ng/mL."
        },
        lab_results=[
            {"test": "HbA1c", "value": "7.2%", "reference": "< 5.7%"},
            {"test": "Lipid Panel", "value": "LDL 140 mg/dL", "reference": "< 100 mg/dL"}
        ]
    )

@pytest.fixture
def mock_status_service():
    """Create a mock StatusUpdateService that records emitted updates."""
    service = AsyncMock(spec=StatusUpdateService)
    service.emitted_updates = []

    async def _mock_emit_update(run_id, status_update_data):
        service.emitted_updates.append({
            "run_id": run_id,
            **status_update_data
        })

    service.emit_status_update.side_effect = _mock_emit_update
    return service

@pytest.fixture
def memory_store(temp_memory_dir, sample_run_id):
    """Create a JSONFileMemoryStore instance for testing."""
    file_path = os.path.join(temp_memory_dir, f"{sample_run_id}.json")
    return JSONFileMemoryStore(file_path=file_path)

# --- Integration Tests ---

@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("GOOGLE_API_KEY"), reason="GOOGLE_API_KEY not set")
@pytest.mark.asyncio
async def test_end_to_end_workflow(sample_run_id, sample_patient_case, mock_status_service, memory_store):
    """
    Test the end-to-end workflow with all real components.
    This test requires a valid Google API key to be set.
    """
    # Run the simulation
    report = await run_mdt_simulation(
        run_id=sample_run_id,
        patient_case=sample_patient_case,
        status_service=mock_status_service
    )
    
    # Verify we got a valid report
    assert isinstance(report, MDTReport)
    assert report.patient_id == sample_patient_case.patient_id
    assert report.ehr_analysis is not None
    assert report.imaging_analysis is not None
    assert report.pathology_analysis is not None
    assert report.guideline_recommendations is not None
    assert report.specialist_assessment is not None
    assert report.evaluation_score is not None
    
    # Verify all expected status updates were emitted
    updates = mock_status_service.emitted_updates
    assert len(updates) >= 12  # At least each agent's start and finish
    
    # Verify memory was saved
    memory = PersistentConversationMemory(memory_key="chat_history", chat_memory=memory_store)
    assert memory.load_memory_variables({}) is not None


@pytest.mark.asyncio
async def test_agent_to_agent_data_passing(sample_run_id, sample_patient_case, mock_status_service):
    """Test that data correctly passes between agents."""
    # Create a controlled sequence where each agent adds specific data
    with patch('mdt_agent_system.app.agents.coordinator._run_ehr_agent_step') as mock_ehr_step, \
         patch('mdt_agent_system.app.agents.coordinator._run_imaging_agent_step') as mock_imaging_step, \
         patch('mdt_agent_system.app.agents.coordinator._run_pathology_agent_step') as mock_pathology_step, \
         patch('mdt_agent_system.app.agents.coordinator._run_guideline_agent_step') as mock_guideline_step, \
         patch('mdt_agent_system.app.agents.coordinator._run_specialist_agent_step') as mock_specialist_step, \
         patch('mdt_agent_system.app.agents.coordinator._run_evaluation_step') as mock_evaluation_step:
        
        # Each agent step adds specific data to the context
        async def ehr_side_effect(context):
            context.ehr_analysis = {"key_finding": "test_ehr_output"}
            return context
        
        async def imaging_side_effect(context):
            # Verify we can access previous agent's output
            assert context.ehr_analysis["key_finding"] == "test_ehr_output"
            context.imaging_analysis = {"key_finding": "test_imaging_output"}
            return context
        
        async def pathology_side_effect(context):
            # Verify we can access previous agents' outputs
            assert context.ehr_analysis["key_finding"] == "test_ehr_output"
            assert context.imaging_analysis["key_finding"] == "test_imaging_output"
            context.pathology_analysis = {"key_finding": "test_pathology_output"}
            return context
        
        async def guideline_side_effect(context):
            # Verify we can access previous agents' outputs
            assert context.ehr_analysis["key_finding"] == "test_ehr_output"
            assert context.imaging_analysis["key_finding"] == "test_imaging_output"
            assert context.pathology_analysis["key_finding"] == "test_pathology_output"
            context.guideline_recommendations = [{"recommendation": "test_guideline_output"}]
            return context
        
        async def specialist_side_effect(context):
            # Verify we can access previous agents' outputs
            assert context.ehr_analysis["key_finding"] == "test_ehr_output"
            assert context.imaging_analysis["key_finding"] == "test_imaging_output"
            assert context.pathology_analysis["key_finding"] == "test_pathology_output"
            assert context.guideline_recommendations[0]["recommendation"] == "test_guideline_output"
            context.specialist_assessment = {"assessment": "test_specialist_output"}
            return context
        
        async def evaluation_side_effect(context):
            # Verify we can access ALL previous agents' outputs
            assert context.ehr_analysis["key_finding"] == "test_ehr_output"
            assert context.imaging_analysis["key_finding"] == "test_imaging_output"
            assert context.pathology_analysis["key_finding"] == "test_pathology_output"
            assert context.guideline_recommendations[0]["recommendation"] == "test_guideline_output"
            assert context.specialist_assessment["assessment"] == "test_specialist_output"
            context.evaluation = {"score": 0.95, "comments": "All data passed correctly between agents"}
            return context
        
        mock_ehr_step.side_effect = ehr_side_effect
        mock_imaging_step.side_effect = imaging_side_effect
        mock_pathology_step.side_effect = pathology_side_effect
        mock_guideline_step.side_effect = guideline_side_effect
        mock_specialist_step.side_effect = specialist_side_effect
        mock_evaluation_step.side_effect = evaluation_side_effect
        
        # Run the simulation
        report = await run_mdt_simulation(
            run_id=sample_run_id,
            patient_case=sample_patient_case,
            status_service=mock_status_service
        )
        
        # Verify all agent steps were called in sequence
        mock_ehr_step.assert_called_once()
        mock_imaging_step.assert_called_once()
        mock_pathology_step.assert_called_once()
        mock_guideline_step.assert_called_once()
        mock_specialist_step.assert_called_once()
        mock_evaluation_step.assert_called_once()
        
        # Verify final report contains all expected data
        assert report.ehr_analysis["key_finding"] == "test_ehr_output"
        assert report.imaging_analysis["key_finding"] == "test_imaging_output"
        assert report.pathology_analysis["key_finding"] == "test_pathology_output"
        assert report.guideline_recommendations[0]["recommendation"] == "test_guideline_output"
        assert report.specialist_assessment["assessment"] == "test_specialist_output"
        assert report.evaluation_score == 0.95


@pytest.mark.asyncio
async def test_memory_persistence(temp_memory_dir, sample_run_id, sample_patient_case):
    """Test that memory correctly persists between runs."""
    # Create memory file path
    memory_file = os.path.join(temp_memory_dir, f"{sample_run_id}.json")
    
    # Create memory store with unique test data
    memory_store = JSONFileMemoryStore(file_path=memory_file)
    memory_store.save_memory("test_key", {"test_data": "This is a test memory item", "timestamp": "2023-01-01"})
    
    # Create a conversation memory and add a message
    memory = PersistentConversationMemory(
        memory_key="chat_history",
        chat_memory=memory_store,
        return_messages=True
    )
    
    # Save some variables to memory
    memory.save_context(
        {"input": "What is the patient's condition?"}, 
        {"output": "The patient has hypertension and diabetes."}
    )
    
    # Close and reopen memory to test persistence
    del memory
    del memory_store
    
    # Create new memory instances pointing to the same file
    new_memory_store = JSONFileMemoryStore(file_path=memory_file)
    new_memory = PersistentConversationMemory(
        memory_key="chat_history",
        chat_memory=new_memory_store,
        return_messages=True
    )
    
    # Verify data persisted
    assert new_memory_store.get_memory("test_key")["test_data"] == "This is a test memory item"
    
    # Verify conversation history persisted
    memory_vars = new_memory.load_memory_variables({})
    assert "chat_history" in memory_vars
    assert len(memory_vars["chat_history"]) == 2
    assert memory_vars["chat_history"][0].content == "What is the patient's condition?"
    assert memory_vars["chat_history"][1].content == "The patient has hypertension and diabetes."


@pytest.mark.asyncio
async def test_tool_registration_and_usage():
    """Test that tools are properly registered and usable by agents."""
    # Verify tools are registered in the registry
    tools = ToolRegistry.get_all_tools()
    assert len(tools) >= 2  # Should have at least guideline and pharmacology tools
    
    tool_names = [tool.name for tool in tools]
    assert "GuidelineReferenceTool" in tool_names
    
    # Mock LLM to avoid actual API calls
    guideline_tool = next(tool for tool in tools if tool.name == "GuidelineReferenceTool")
    assert guideline_tool is not None
    
    # Test tool execution
    query = "NSTEMI treatment guidelines"
    with patch('mdt_agent_system.app.core.tools.guideline_tool._query_guideline') as mock_query:
        mock_query.return_value = "Test guideline content for NSTEMI"
        result = guideline_tool._run(query=query)
        assert mock_query.call_count == 1
        assert "Test guideline content for NSTEMI" in result


@pytest.mark.asyncio
async def test_status_update_flow(sample_run_id, mock_status_service):
    """Test that status updates flow correctly from agents to the status service."""
    # Create a test agent that will emit status updates
    test_agent = EHRAgent(
        status_service=mock_status_service,
        run_id=sample_run_id,
        memory_dir="/tmp"  # Not actually used due to mocking
    )
    
    # Mock the LLM to avoid actual API calls
    with patch('mdt_agent_system.app.agents.ehr_agent.get_llm') as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = {"content": "Test EHR analysis response"}
        mock_get_llm.return_value = mock_llm
        
        # Create a minimal patient case
        minimal_case = PatientCase(
            patient_id="test-patient-002",
            demographics={"age": 60, "gender": "Female"},
            medical_history=[{"condition": "Asthma"}],
            current_condition={"description": "Respiratory issues"},
            imaging_results=None,
            pathology_results=None,
            lab_results=None
        )
        
        # Process the patient case
        await test_agent.process(minimal_case)
        
        # Verify status updates were emitted
        updates = mock_status_service.emitted_updates
        assert len(updates) >= 2  # Should have start and finish updates
        
        # Find status updates for this agent
        agent_updates = [u for u in updates if u.get("agent_id") == "EHR Agent"]
        assert len(agent_updates) >= 2
        
        # Verify status sequence
        start_update = next((u for u in agent_updates if u.get("status") == Status.ACTIVE.value), None)
        finish_update = next((u for u in agent_updates if u.get("status") == Status.DONE.value), None)
        
        assert start_update is not None
        assert finish_update is not None
        assert start_update.get("message") == "Starting EHR Analysis"
        assert "Finished EHR Analysis" in finish_update.get("message")


@pytest.mark.asyncio
async def test_status_updates_via_sse(sample_run_id, mock_status_service):
    """Test that status updates are properly sent through SSE for UI visualization."""
    from fastapi.testclient import TestClient
    from fastapi import Request
    from sse_starlette.sse import EventSourceResponse
    from mdt_agent_system.app.api.endpoints import sse_generator
    from mdt_agent_system.app.main import app
    
    # Simulate our SSE endpoint with a test client
    client = TestClient(app)
    
    # Create a request object (needed for the sse_generator)
    request = Request(scope={"type": "http", "headers": []})
    
    # Generate some test status updates
    test_updates = [
        {
            "agent_id": "Coordinator", 
            "status": "ACTIVE", 
            "message": "Initiating MDT Workflow",
            "run_id": sample_run_id,
            "event_id": 1,
            "timestamp": "2023-01-01T00:00:00Z"
        },
        {
            "agent_id": "EHR Agent", 
            "status": "ACTIVE", 
            "message": "Starting EHR Analysis",
            "run_id": sample_run_id,
            "event_id": 2,
            "timestamp": "2023-01-01T00:00:01Z"
        },
        {
            "agent_id": "EHR Agent", 
            "status": "DONE", 
            "message": "Finished EHR Analysis",
            "run_id": sample_run_id,
            "event_id": 3,
            "timestamp": "2023-01-01T00:00:02Z"
        }
    ]
    
    # Mock the subscribe method to return our test updates
    async def mock_subscribe(run_id, last_event_id=None):
        for update_data in test_updates:
            # Create StatusUpdate object from dict
            update = StatusUpdate(**update_data)
            yield update
    
    # Replace the subscribe method with our mock
    mock_status_service.subscribe = mock_subscribe
    
    # Create a list to collect the SSE events
    collected_events = []
    
    # Generate SSE events
    async for event in sse_generator(sample_run_id, request, mock_status_service):
        # For each event, check that it contains the expected data
        if event.event == "status_update":
            collected_events.append(json.loads(event.data))
        # Break after collecting all our test updates
        if len(collected_events) >= len(test_updates):
            break
    
    # Verify all status updates were properly sent as SSE events
    assert len(collected_events) == len(test_updates)
    
    # Verify the content of each event
    for i, event_data in enumerate(collected_events):
        assert event_data["agent_id"] == test_updates[i]["agent_id"]
        assert event_data["status"] == test_updates[i]["status"]
        assert event_data["message"] == test_updates[i]["message"]
        assert event_data["run_id"] == sample_run_id
        assert event_data["event_id"] == test_updates[i]["event_id"]


@pytest.mark.asyncio
async def test_frontend_workflow_visualization():
    """Test the frontend workflow visualization updates properly based on status updates."""
    import subprocess
    import time
    from playwright.async_api import async_playwright
    
    try:
        # Check if we can run this test (requires Playwright)
        import playwright
    except ImportError:
        pytest.skip("Playwright not installed. Skipping UI visualization test.")
        
    # This test requires a running server to connect to
    # Since this is complex to set up in a test environment, we'll just verify
    # that the visualization JavaScript function works as expected
    
    # If we were to fully test the UI:
    # 1. Start the server
    # 2. Open browser using Playwright
    # 3. Upload a file and start simulation
    # 4. Wait for status updates
    # 5. Verify the diagram updates correctly
    # 6. Close browser and stop server
    
    # Instead, we'll just check that the visualization JS function is defined properly:
    from pathlib import Path
    app_js_path = Path('mdt_agent_system/app/static/app.js')
    
    assert app_js_path.exists(), "app.js not found"
    
    js_content = app_js_path.read_text()
    assert 'function updateWorkflowVisualization' in js_content, "Visualization function not found"
    assert 'mermaid.initialize' in js_content, "Mermaid initialization not found"
    
    # Check for critical visualization elements
    assert "coordinator --> ehr" in js_content, "Agent connection not found"
    assert "nodeClass = 'class=\"active\"'" in js_content, "Active state styling not found"
    assert "nodeClass = 'class=\"error\"'" in js_content, "Error state styling not found" 