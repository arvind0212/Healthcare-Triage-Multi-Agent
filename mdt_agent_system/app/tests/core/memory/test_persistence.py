import json
import os
import pytest
from pathlib import Path
from datetime import datetime
from langchain.schema import HumanMessage, AIMessage
from mdt_agent_system.app.core.memory.persistence import (
    JSONFileMemoryStore,
    JSONFileChatMessageHistory,
    PersistentConversationMemory
)

@pytest.fixture
def temp_json_file(tmp_path):
    return str(tmp_path / "test_memory.json")

class TestJSONFileMemoryStore:
    def test_init_creates_file(self, temp_json_file):
        store = JSONFileMemoryStore(temp_json_file)
        assert Path(temp_json_file).exists()
        
    def test_save_and_get_memory(self, temp_json_file):
        store = JSONFileMemoryStore(temp_json_file)
        test_data = {"key1": "value1"}
        store.save_memory("test_key", test_data)
        
        retrieved_data = store.get_memory("test_key")
        assert retrieved_data == test_data
        
    def test_delete_memory(self, temp_json_file):
        store = JSONFileMemoryStore(temp_json_file)
        test_data = {"key1": "value1"}
        store.save_memory("test_key", test_data)
        
        store.delete_memory("test_key")
        assert store.get_memory("test_key") is None
        
    def test_nonexistent_key_returns_none(self, temp_json_file):
        store = JSONFileMemoryStore(temp_json_file)
        assert store.get_memory("nonexistent_key") is None

class TestJSONFileChatMessageHistory:
    def test_add_and_get_messages(self, temp_json_file):
        history = JSONFileChatMessageHistory(temp_json_file, "test_session")
        
        # Add messages
        human_msg = HumanMessage(content="Hello")
        ai_msg = AIMessage(content="Hi there!")
        
        history.add_message(human_msg)
        history.add_message(ai_msg)
        
        # Retrieve messages
        messages = history.messages
        assert len(messages) == 2
        assert messages[0].content == "Hello"
        assert messages[1].content == "Hi there!"
        
    def test_clear_messages(self, temp_json_file):
        history = JSONFileChatMessageHistory(temp_json_file, "test_session")
        
        history.add_message(HumanMessage(content="Hello"))
        history.clear()
        
        assert len(history.messages) == 0
        
    def test_multiple_sessions(self, temp_json_file):
        history1 = JSONFileChatMessageHistory(temp_json_file, "session1")
        history2 = JSONFileChatMessageHistory(temp_json_file, "session2")
        
        history1.add_message(HumanMessage(content="Message 1"))
        history2.add_message(HumanMessage(content="Message 2"))
        
        assert len(history1.messages) == 1
        assert len(history2.messages) == 1
        assert history1.messages[0].content == "Message 1"
        assert history2.messages[0].content == "Message 2"

class TestPersistentConversationMemory:
    def test_save_and_load_context(self, temp_json_file):
        memory = PersistentConversationMemory(temp_json_file, "test_session")
        
        # Save context
        inputs = {"input": "What is the weather?"}
        outputs = {"output": "It's sunny today!"}
        memory.save_context(inputs, outputs)
        
        # Load variables
        variables = memory.load_memory_variables({})
        assert "history" in variables
        
        # The string will contain lowercase "human" and "ai" in the message types
        history_text = variables["history"]
        assert "What is the weather?" in history_text
        assert "It's sunny today!" in history_text
        
    def test_return_messages_format(self, temp_json_file):
        memory = PersistentConversationMemory(
            file_path=temp_json_file,
            session_id="test_session",
            return_messages=True
        )
        
        inputs = {"input": "Hello"}
        outputs = {"output": "Hi!"}
        memory.save_context(inputs, outputs)
        
        variables = memory.load_memory_variables({})
        assert len(variables["history"]) == 2
        assert isinstance(variables["history"][0], HumanMessage)
        assert isinstance(variables["history"][1], AIMessage)
        
    def test_clear_memory(self, temp_json_file):
        memory = PersistentConversationMemory(temp_json_file, "test_session")
        
        inputs = {"input": "Hello"}
        outputs = {"output": "Hi!"}
        memory.save_context(inputs, outputs)
        
        memory.clear()
        variables = memory.load_memory_variables({})
        assert variables["history"] == "" 