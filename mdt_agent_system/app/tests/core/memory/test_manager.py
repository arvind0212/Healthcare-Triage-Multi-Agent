import pytest
from pathlib import Path
from datetime import datetime
from mdt_agent_system.app.core.memory.manager import MemoryManager
from mdt_agent_system.app.core.memory.persistence import PersistentConversationMemory

@pytest.fixture
def temp_memory_dir(tmp_path):
    return str(tmp_path / "memory")

class TestMemoryManager:
    def test_initialization(self, temp_memory_dir):
        manager = MemoryManager(temp_memory_dir)
        assert Path(temp_memory_dir).exists()
        assert (Path(temp_memory_dir) / "conversations.json").exists()
        assert (Path(temp_memory_dir) / "agent_states.json").exists()
        assert (Path(temp_memory_dir) / "metadata.json").exists()
    
    def test_create_conversation_memory(self, temp_memory_dir):
        manager = MemoryManager(temp_memory_dir)
        memory = manager.create_conversation_memory("test_session")
        assert isinstance(memory, PersistentConversationMemory)
        assert memory.session_id == "test_session"
        
        # Test with return_messages=True
        memory_with_messages = manager.create_conversation_memory("test_session", return_messages=True)
        assert memory_with_messages.return_messages is True
    
    def test_agent_state_operations(self, temp_memory_dir):
        manager = MemoryManager(temp_memory_dir)
        test_state = {"name": "test_agent", "status": "active"}
        
        # Save state
        manager.save_agent_state("agent1", test_state)
        
        # Get state
        retrieved_state = manager.get_agent_state("agent1")
        assert retrieved_state["name"] == test_state["name"]
        assert retrieved_state["status"] == test_state["status"]
        assert "last_updated" in retrieved_state
        
        # Clear state
        manager.clear_agent_state("agent1")
        assert manager.get_agent_state("agent1") is None
    
    def test_metadata_operations(self, temp_memory_dir):
        manager = MemoryManager(temp_memory_dir)
        test_metadata = {"version": "1.0", "environment": "test"}
        
        # Save metadata
        manager.save_metadata("config1", test_metadata)
        
        # Get metadata
        retrieved_metadata = manager.get_metadata("config1")
        assert retrieved_metadata["version"] == test_metadata["version"]
        assert retrieved_metadata["environment"] == test_metadata["environment"]
        assert "last_updated" in retrieved_metadata
        
        # Clear metadata
        manager.clear_metadata("config1")
        assert manager.get_metadata("config1") is None
    
    def test_conversation_operations(self, temp_memory_dir):
        manager = MemoryManager(temp_memory_dir)
        memory = manager.create_conversation_memory("test_session")
        
        # Add some conversation data
        inputs = {"input": "Hello"}
        outputs = {"output": "Hi there!"}
        memory.save_context(inputs, outputs)
        
        # Verify conversation is listed
        conversations = manager.list_conversations()
        assert "test_session" in conversations
        
        # Clear conversation
        manager.clear_conversation("test_session")
        conversations = manager.list_conversations()
        assert "test_session" not in conversations
    
    def test_list_operations(self, temp_memory_dir):
        manager = MemoryManager(temp_memory_dir)
        
        # Add test data
        manager.save_agent_state("agent1", {"status": "active"})
        manager.save_agent_state("agent2", {"status": "inactive"})
        manager.save_metadata("config1", {"version": "1.0"})
        manager.save_metadata("config2", {"version": "2.0"})
        
        # Test listing
        agent_states = manager.list_agent_states()
        assert len(agent_states) == 2
        assert "agent1" in agent_states
        assert "agent2" in agent_states
        
        metadata_keys = manager.list_metadata_keys()
        assert len(metadata_keys) == 2
        assert "config1" in metadata_keys
        assert "config2" in metadata_keys
    
    def test_nonexistent_data(self, temp_memory_dir):
        manager = MemoryManager(temp_memory_dir)
        
        # Test getting non-existent data
        assert manager.get_agent_state("nonexistent") is None
        assert manager.get_metadata("nonexistent") is None
        
        # Test clearing non-existent data (should not raise errors)
        manager.clear_agent_state("nonexistent")
        manager.clear_metadata("nonexistent")
        manager.clear_conversation("nonexistent") 