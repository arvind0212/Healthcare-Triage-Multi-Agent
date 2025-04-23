from typing import Any, Dict, List, Optional
from datetime import datetime
from langchain.callbacks.base import BaseCallbackHandler
from mdt_agent_system.app.core.schemas.status import StatusUpdate
from .service import StatusUpdateService

class StatusUpdateCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that emits status updates."""
    
    def __init__(self, service: StatusUpdateService, run_id: str):
        """Initialize the callback handler.
        
        Args:
            service: The status update service to use.
            run_id: The run ID to associate updates with.
        """
        self.service = service
        self.run_id = run_id
        self.agent_id: Optional[str] = None
    
    def on_agent_start(
        self,
        agent_id: str,
        **kwargs: Any,
    ) -> None:
        """Called when an agent starts processing.
        
        Args:
            agent_id: The ID of the agent that started.
        """
        self.agent_id = agent_id
        self.service.emit_status(
            StatusUpdate(
                agent_id=agent_id,
                status="ACTIVE",
                message=f"Agent {agent_id} started processing",
                run_id=self.run_id
            )
        )
    
    def on_agent_finish(
        self,
        agent_id: str,
        **kwargs: Any,
    ) -> None:
        """Called when an agent finishes processing.
        
        Args:
            agent_id: The ID of the agent that finished.
        """
        self.service.emit_status(
            StatusUpdate(
                agent_id=agent_id,
                status="DONE",
                message=f"Agent {agent_id} finished processing",
                run_id=self.run_id
            )
        )
    
    def on_agent_error(
        self,
        agent_id: str,
        error: str,
        **kwargs: Any,
    ) -> None:
        """Called when an agent encounters an error.
        
        Args:
            agent_id: The ID of the agent that errored.
            error: The error message.
        """
        self.service.emit_status(
            StatusUpdate(
                agent_id=agent_id,
                status="ERROR",
                message=f"Agent {agent_id} encountered an error: {error}",
                run_id=self.run_id,
                details={"error": error}
            )
        )
    
    def on_tool_start(
        self,
        tool_name: str,
        tool_input: str,
        **kwargs: Any,
    ) -> None:
        """Called when a tool starts executing.
        
        Args:
            tool_name: The name of the tool being used.
            tool_input: The input provided to the tool.
        """
        if self.agent_id:
            self.service.emit_status(
                StatusUpdate(
                    agent_id=self.agent_id,
                    status="ACTIVE",
                    message=f"Using tool: {tool_name}",
                    run_id=self.run_id,
                    details={"tool": tool_name, "input": tool_input}
                )
            )
    
    def on_tool_error(
        self,
        tool_name: str,
        tool_input: str,
        error: str,
        **kwargs: Any,
    ) -> None:
        """Called when a tool encounters an error.
        
        Args:
            tool_name: The name of the tool that errored.
            tool_input: The input provided to the tool.
            error: The error message.
        """
        if self.agent_id:
            self.service.emit_status(
                StatusUpdate(
                    agent_id=self.agent_id,
                    status="ERROR",
                    message=f"Tool {tool_name} failed: {error}",
                    run_id=self.run_id,
                    details={
                        "tool": tool_name,
                        "input": tool_input,
                        "error": error
                    }
                )
            )
    
    def on_llm_start(
        self,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM starts processing."""
        if self.agent_id:
            self.service.emit_status(
                StatusUpdate(
                    agent_id=self.agent_id,
                    status="ACTIVE",
                    message="Processing with LLM",
                    run_id=self.run_id
                )
            ) 