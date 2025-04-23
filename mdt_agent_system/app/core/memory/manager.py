from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
from .persistence import PersistentConversationMemory, JSONFileMemoryStore

class MemoryManager:
    """Manager for handling agent memory operations."""
    
    def __init__(self, base_path: str):
        """Initialize the memory manager.
        
        Args:
            base_path: Base directory for storing memory files.
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize stores for different types of memory
        self.conversation_store = JSONFileMemoryStore(str(self.base_path / "conversations.json"))
        self.state_store = JSONFileMemoryStore(str(self.base_path / "agent_states.json"))
        self.metadata_store = JSONFileMemoryStore(str(self.base_path / "metadata.json"))
    
    def create_conversation_memory(self, session_id: str, return_messages: bool = False) -> PersistentConversationMemory:
        """Create a new conversation memory instance.
        
        Args:
            session_id: Unique identifier for the conversation.
            return_messages: Whether to return messages directly or as a string.
            
        Returns:
            A new PersistentConversationMemory instance.
        """
        memory_path = str(self.base_path / "conversations.json")
        return PersistentConversationMemory(memory_path, session_id, return_messages)
    
    def save_agent_state(self, agent_id: str, state: Dict[str, Any]) -> None:
        """Save agent state to persistent storage.
        
        Args:
            agent_id: Unique identifier for the agent.
            state: Agent state to save.
        """
        state["last_updated"] = datetime.utcnow().isoformat()
        self.state_store.save_memory(agent_id, state)
    
    def get_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent state from persistent storage.
        
        Args:
            agent_id: Unique identifier for the agent.
            
        Returns:
            Agent state if found, None otherwise.
        """
        return self.state_store.get_memory(agent_id)
    
    def save_metadata(self, key: str, metadata: Dict[str, Any]) -> None:
        """Save metadata to persistent storage.
        
        Args:
            key: Unique identifier for the metadata.
            metadata: Metadata to save.
        """
        metadata["last_updated"] = datetime.utcnow().isoformat()
        self.metadata_store.save_memory(key, metadata)
    
    def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Get metadata from persistent storage.
        
        Args:
            key: Unique identifier for the metadata.
            
        Returns:
            Metadata if found, None otherwise.
        """
        return self.metadata_store.get_memory(key)
    
    def clear_conversation(self, session_id: str) -> None:
        """Clear conversation history for a session.
        
        Args:
            session_id: Unique identifier for the conversation.
        """
        self.conversation_store.delete_memory(session_id)
    
    def clear_agent_state(self, agent_id: str) -> None:
        """Clear agent state from storage.
        
        Args:
            agent_id: Unique identifier for the agent.
        """
        self.state_store.delete_memory(agent_id)
    
    def clear_metadata(self, key: str) -> None:
        """Clear metadata from storage.
        
        Args:
            key: Unique identifier for the metadata.
        """
        self.metadata_store.delete_memory(key)
    
    def list_conversations(self) -> List[str]:
        """List all conversation session IDs.
        
        Returns:
            List of conversation session IDs.
        """
        data = self.conversation_store._load_data()
        return list(data.keys())
    
    def list_agent_states(self) -> List[str]:
        """List all agent IDs with saved states.
        
        Returns:
            List of agent IDs.
        """
        data = self.state_store._load_data()
        return list(data.keys())
    
    def list_metadata_keys(self) -> List[str]:
        """List all metadata keys.
        
        Returns:
            List of metadata keys.
        """
        data = self.metadata_store._load_data()
        return list(data.keys()) 