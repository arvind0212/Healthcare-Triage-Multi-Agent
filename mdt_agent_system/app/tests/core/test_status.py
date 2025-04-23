import pytest
import asyncio
from datetime import datetime
from mdt_agent_system.app.core.status.service import StatusUpdateService, get_status_service
from mdt_agent_system.app.core.status.storage import JSONStore
from mdt_agent_system.app.core.schemas.status import StatusUpdate
from mdt_agent_system.app.core.status.callback import StatusUpdateCallbackHandler
from unittest.mock import AsyncMock, MagicMock
import uuid
import os

@pytest.fixture
def status_service(tmp_path):
    """Create a temporary status update service."""
    return StatusUpdateService(str(tmp_path / "status_updates.json"))

@pytest.fixture
def callback_handler(status_service):
    """Create a callback handler for testing."""
    return StatusUpdateCallbackHandler(status_service, "test_run_123")

def test_status_update_emission(status_service):
    """Test basic status update emission and retrieval."""
    update = StatusUpdate(
        agent_id="test_agent",
        status="ACTIVE",
        message="Test message",
        run_id="test_run_123"
    )
    
    status_service.emit_status(update)
    updates = status_service.get_run_updates("test_run_123")
    
    assert len(updates) == 1
    assert updates[0].agent_id == "test_agent"
    assert updates[0].status == "ACTIVE"
    assert updates[0].message == "Test message"

def test_status_persistence(tmp_path):
    """Test that status updates persist across service instances."""
    # Create first service instance
    service1 = StatusUpdateService(str(tmp_path / "status_updates.json"))
    update = StatusUpdate(
        agent_id="test_agent",
        status="ACTIVE",
        message="Test message",
        run_id="test_run_123"
    )
    service1.emit_status(update)
    
    # Create second service instance
    service2 = StatusUpdateService(str(tmp_path / "status_updates.json"))
    updates = service2.get_run_updates("test_run_123")
    
    assert len(updates) == 1
    assert updates[0].agent_id == "test_agent"

@pytest.mark.asyncio
async def test_status_subscription(status_service):
    """Test subscribing to status updates."""
    updates_received = []
    
    async def collect_updates():
        async for update in status_service.subscribe("test_run_123"):
            updates_received.append(update)
            if len(updates_received) == 2:
                break
    
    # Start collecting updates
    task = asyncio.create_task(collect_updates())
    
    # Emit some updates
    update1 = StatusUpdate(
        agent_id="test_agent",
        status="ACTIVE",
        message="First update",
        run_id="test_run_123"
    )
    update2 = StatusUpdate(
        agent_id="test_agent",
        status="DONE",
        message="Second update",
        run_id="test_run_123"
    )
    
    status_service.emit_status(update1)
    status_service.emit_status(update2)
    
    # Wait for updates to be collected
    await task
    
    assert len(updates_received) == 2
    assert updates_received[0].message == "First update"
    assert updates_received[1].message == "Second update"

def test_callback_handler_agent_lifecycle(callback_handler, status_service):
    """Test callback handler for agent lifecycle events."""
    # Test agent start
    callback_handler.on_agent_start("test_agent")
    updates = status_service.get_run_updates("test_run_123")
    assert len(updates) == 1
    assert updates[0].status == "ACTIVE"
    
    # Test agent finish
    callback_handler.on_agent_finish("test_agent")
    updates = status_service.get_run_updates("test_run_123")
    assert len(updates) == 2
    assert updates[1].status == "DONE"
    
    # Test agent error
    callback_handler.on_agent_error("test_agent", "Test error")
    updates = status_service.get_run_updates("test_run_123")
    assert len(updates) == 3
    assert updates[2].status == "ERROR"
    assert "Test error" in updates[2].message

def test_callback_handler_tool_events(callback_handler, status_service):
    """Test callback handler for tool events."""
    # Set agent ID
    callback_handler.on_agent_start("test_agent")
    
    # Test tool start
    callback_handler.on_tool_start("test_tool", "test input")
    updates = status_service.get_run_updates("test_run_123")
    assert any(u.message.startswith("Using tool:") for u in updates)
    
    # Test tool error
    callback_handler.on_tool_error("test_tool", "test input", "Tool failed")
    updates = status_service.get_run_updates("test_run_123")
    assert any(u.status == "ERROR" and "Tool failed" in u.message for u in updates)

def test_clear_run(status_service):
    """Test clearing status updates for a run."""
    update = StatusUpdate(
        agent_id="test_agent",
        status="ACTIVE",
        message="Test message",
        run_id="test_run_123"
    )
    status_service.emit_status(update)
    
    # Verify update exists
    assert len(status_service.get_run_updates("test_run_123")) == 1
    
    # Clear the run
    status_service.clear_run("test_run_123")
    
    # Verify update is gone
    assert len(status_service.get_run_updates("test_run_123")) == 0 