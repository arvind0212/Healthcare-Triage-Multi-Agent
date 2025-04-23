import asyncio
import pytest
import json
from fastapi.testclient import TestClient
from sse_starlette.sse import ServerSentEvent
from unittest.mock import patch, AsyncMock

# Revert to original absolute imports
from mdt_agent_system.app.main import app
from mdt_agent_system.app.core.status.status_service import StatusUpdateService, StatusUpdate
from mdt_agent_system.app.api.endpoints import get_status_service

# Use pytest-asyncio for async tests
pytestmark = pytest.mark.asyncio

# --- Mock Status Update Service ---
class MockStatusUpdateService:
    def __init__(self):
        self._subscribers = {}
        self._queues = {}

    async def subscribe(self, run_id):
        if run_id not in self._queues:
            self._queues[run_id] = asyncio.Queue()

        queue = self._queues[run_id]
        # Simulate receiving updates
        while True:
            update = await queue.get()
            if update is None: # Signal to stop iteration
                break
            yield update
            queue.task_done()

    async def emit_status_update(self, run_id, status_update):
        if run_id in self._queues:
            await self._queues[run_id].put(status_update)

    async def signal_end_of_stream(self, run_id):
        if run_id in self._queues:
            await self._queues[run_id].put(None) # Send stop signal

# Fixture to provide the mock service
@pytest.fixture
def mock_status_service():
    return MockStatusUpdateService()

# Override the dependency for testing
@pytest.fixture(autouse=True)
def override_dependency(mock_status_service):
    app.dependency_overrides[get_status_service] = lambda: mock_status_service
    yield
    app.dependency_overrides = {}

# --- Test Cases ---

async def test_sse_stream_receives_updates(mock_status_service):
    """Test that the SSE stream correctly receives and formats updates."""
    test_run_id = "test-stream-123"
    client = TestClient(app)

    async def emit_updates():
        # Wait briefly for the client to connect and subscribe
        await asyncio.sleep(0.1)
        update1 = StatusUpdate(run_id=test_run_id, agent_id="Agent1", status="PROCESSING", message="Step 1")
        await mock_status_service.emit_status_update(test_run_id, update1)
        await asyncio.sleep(0.05) # Short delay between emits
        update2 = StatusUpdate(run_id=test_run_id, agent_id="Agent2", status="DONE", message="Step 2 Complete")
        await mock_status_service.emit_status_update(test_run_id, update2)
        await asyncio.sleep(0.05)
        await mock_status_service.signal_end_of_stream(test_run_id) # Signal end

    emit_task = asyncio.create_task(emit_updates())

    received_events = []
    try:
        with client.stream("GET", f"/stream/{test_run_id}") as response:
            response.raise_for_status() # Ensure connection was successful (200 OK)
            for line in response.iter_lines():
                if line.startswith("event:"):
                    event_type = line.split(": ", 1)[1]
                elif line.startswith("data:"):
                    data = line.split(": ", 1)[1]
                    if event_type == "status_update":
                        received_events.append(json.loads(data))
                    elif event_type == "ping":
                        pass # Ignore pings for this test
                elif not line:
                    # End of an event
                    if len(received_events) >= 2: # Stop after receiving expected events
                        break
    finally:
        emit_task.cancel()
        try:
            await emit_task
        except asyncio.CancelledError:
            pass

    assert len(received_events) == 2
    # Compare relevant fields, ignoring timestamps for simplicity
    assert received_events[0]["agent_id"] == "Agent1"
    assert received_events[0]["status"] == "PROCESSING"
    assert received_events[1]["agent_id"] == "Agent2"
    assert received_events[1]["status"] == "DONE"

async def test_sse_stream_handles_disconnection(mock_status_service):
    """Test that the stream handles client disconnection gracefully (simulated)."""
    # This test primarily ensures the server-side generator exits without errors
    # when the client (TestClient) disconnects implicitly after the `with` block.
    test_run_id = "test-disconnect-456"
    client = TestClient(app)

    # Mock request.is_disconnected to simulate disconnection after first event
    is_disconnected_mock = AsyncMock(side_effect=[False, True, True]) # False first, then True

    try:
        with patch('fastapi.Request.is_disconnected', is_disconnected_mock):
            with client.stream("GET", f"/stream/{test_run_id}") as response:
                response.raise_for_status()
                # Emit one update
                update1 = StatusUpdate(run_id=test_run_id, agent_id="Agent1", status="START", message="Starting")
                await mock_status_service.emit_status_update(test_run_id, update1)
                # Consume the first event
                line_iter = response.iter_lines()
                while True:
                    line = next(line_iter)
                    if line.startswith("data:"):
                        break # Got the first data line
            # Exiting the 'with client.stream' block simulates disconnection

        # Allow some time for the server-side generator to potentially react and log
        await asyncio.sleep(0.2)
        # Check logs or add assertions here if specific cleanup behavior needs verification
        # For now, just assert that the test completes without server-side errors
        assert True # If we reach here without errors, the basic handling worked

    except Exception as e:
        pytest.fail(f"SSE stream test failed with exception: {e}")
    finally:
         await mock_status_service.signal_end_of_stream(test_run_id) 