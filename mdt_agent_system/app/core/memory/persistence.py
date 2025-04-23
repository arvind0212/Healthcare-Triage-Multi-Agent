import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from langchain_core.memory import BaseMemory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, messages_from_dict, messages_to_dict
from pydantic import BaseModel
from langchain.memory import ConversationBufferMemory
from mdt_agent_system.app.core.logging.logger import get_logger

logger = get_logger(__name__)

class JSONFileMemoryStore:
    """JSON file-based memory store for LangChain."""
    
    def __init__(self, file_path: str):
        """Initialize the memory store.
        
        Args:
            file_path: Path to the JSON file for storing memory.
        """
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._save_data({})
    
    def _load_data(self) -> Dict[str, Any]:
        """Load data from the JSON file."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def _save_data(self, data: Dict[str, Any]) -> None:
        """Save data to the JSON file."""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_memory(self, key: str) -> Optional[Dict[str, Any]]:
        """Get memory data for a specific key."""
        data = self._load_data()
        return data.get(key)
    
    def save_memory(self, key: str, memory_data: Dict[str, Any]) -> None:
        """Save memory data for a specific key."""
        data = self._load_data()
        data[key] = memory_data
        self._save_data(data)
    
    def delete_memory(self, key: str) -> None:
        """Delete memory data for a specific key."""
        data = self._load_data()
        if key in data:
            del data[key]
            self._save_data(data)

class JSONFileChatMessageHistory(BaseChatMessageHistory):
    """Chat message history that stores data in a JSON file."""
    
    def __init__(self, file_path: str, session_id: str):
        """Initialize the chat message history.
        
        Args:
            file_path: Path to the JSON file for storing messages.
            session_id: Unique identifier for the chat session.
        """
        self.store = JSONFileMemoryStore(file_path)
        self.session_id = session_id
        
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the history."""
        messages = self.messages
        messages.append(message)
        self._save_messages(messages)
    
    def clear(self) -> None:
        """Clear message history."""
        self._save_messages([])
    
    @property
    def messages(self) -> List[BaseMessage]:
        """Get all messages in history."""
        message_dicts = self.store.get_memory(self.session_id)
        if message_dicts is None:
            return []
        return messages_from_dict(message_dicts)
    
    def _save_messages(self, messages: List[BaseMessage]) -> None:
        """Save messages to storage."""
        message_dicts = messages_to_dict(messages)
        self.store.save_memory(self.session_id, message_dicts)

class PersistentConversationMemory:
    """Persistent conversation memory using JSON file storage."""
    
    def __init__(self, file_path: str, session_id: str, return_messages: bool = False):
        """Initialize the memory.
        
        Args:
            file_path: Path to the JSON file for storing memory.
            session_id: Unique identifier for the conversation.
            return_messages: Whether to return messages directly or as a string.
        """
        self.chat_memory = JSONFileChatMessageHistory(file_path, session_id)
        self.return_messages = return_messages
        self.session_id = session_id
        self.memory_variables = ["history"]
    
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Load memory variables."""
        if self.return_messages:
            return {"history": self.chat_memory.messages}
        
        # Convert messages to a string for text-based chains
        string_messages = []
        for message in self.chat_memory.messages:
            if hasattr(message, "content"):
                string_messages.append(f"{message.type}: {message.content}")
        return {"history": "\n".join(string_messages)}
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """Save context from this conversation to memory."""
        from langchain_core.messages import HumanMessage, AIMessage
        
        # Save human inputs
        if "input" in inputs:
            self.chat_memory.add_message(HumanMessage(content=inputs["input"]))
        
        # Save AI outputs
        if "output" in outputs:
            self.chat_memory.add_message(AIMessage(content=outputs["output"]))
    
    def clear(self) -> None:
        """Clear memory contents."""
        self.chat_memory.clear() 