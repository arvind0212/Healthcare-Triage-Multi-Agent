import logging
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from uuid import UUID

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.callbacks import BaseCallbackHandler, Callbacks
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import BaseMessage

from mdt_agent_system.app.core.schemas import PatientCase, StatusUpdate
from mdt_agent_system.app.core.schemas.agent_output import AgentOutput
from mdt_agent_system.app.core.status import StatusUpdateService, Status
from mdt_agent_system.app.core.llm import get_llm
from mdt_agent_system.app.core.memory.persistence import PersistentConversationMemory
from mdt_agent_system.app.core.logging import get_logger
from mdt_agent_system.app.core.samples.prompts import get_prompt_template
from mdt_agent_system.app.core.output_parser import MDTOutputParser

logger = get_logger(__name__)

class BaseSpecializedAgent(ABC):
    """Base class for all specialized MDT agents.
    
    Implements common functionality for agent initialization, status updates,
    memory integration, and communication with the LLM.
    """
    
    def __init__(self, 
                 agent_id: str,
                 run_id: str,
                 status_service: StatusUpdateService,
                 callbacks: Optional[List[BaseCallbackHandler]] = None):
        """Initialize the base specialized agent."""
        self.agent_id = agent_id
        self.run_id = run_id
        self.status_service = status_service
        self.callbacks = callbacks or []
        self.llm = get_llm(callbacks=self.callbacks)
        self.output_parser = MDTOutputParser()
        
        memory_session_id = f"{run_id}_{agent_id}"
        self.memory = PersistentConversationMemory(
            file_path=f"memory_data/{agent_id}_memory.json",
            session_id=memory_session_id,
            return_messages=True
        )
        
        agent_type = self._get_agent_type()
        self.prompt_template = ChatPromptTemplate.from_template(
            get_prompt_template(agent_type)
        )
        
        logger.info(f"Initialized {agent_id} with run_id: {run_id}")
    
    @abstractmethod
    def _get_agent_type(self) -> str:
        """Return the type of agent for prompt template selection."""
        pass
    
    async def _emit_status(self, status: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Emit a status update."""
        await self.status_service.emit_status_update(
            run_id=self.run_id,
            status_update_data={
                "agent_id": self.agent_id,
                "status": status,
                "message": message,
                "details": details or {}
            }
        )
    
    async def process(self, patient_case: PatientCase, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process the patient case with this specialized agent."""
        try:
            await self._emit_status("ACTIVE", f"Starting {self.agent_id} analysis")
            
            agent_input = self._prepare_input(patient_case, context)
            result = await self._run_analysis(agent_input)
            parsed_output = self.output_parser.parse_llm_output(result)
            structured_output = self._structure_output(parsed_output)
            
            self._save_to_memory(agent_input, structured_output)
            await self._emit_status("DONE", f"Completed {self.agent_id} analysis")
            
            return structured_output
            
        except Exception as e:
            logger.exception(f"Error in {self.agent_id} analysis: {str(e)}")
            await self._emit_status("ERROR", f"Error in {self.agent_id} analysis: {str(e)}")
            raise
    
    @abstractmethod
    def _prepare_input(self, patient_case: PatientCase, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare the input for the agent's analysis."""
        pass
    
    async def _run_analysis(self, input_data: Dict[str, Any]) -> str:
        """Run the LLM analysis with the prepared input."""
        config = RunnableConfig(
            callbacks=self.callbacks,
            run_name=f"{self.agent_id}_analysis"
        )
        
        prompt = self.prompt_template.format_messages(
            context=input_data.get("context", ""),
            task=input_data.get("task", "Analyze the patient case")
        )
        
        response = await self.llm.ainvoke(prompt, config=config)
        return response.content
    
    @abstractmethod
    def _structure_output(self, parsed_output: AgentOutput) -> Dict[str, Any]:
        """Structure the parsed output into a standardized format."""
        pass
    
    def _save_to_memory(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """Save the interaction to memory."""
        try:
            memory_output = {
                "structured_output": outputs,
                "markdown_content": outputs.get("markdown_content", ""),
                "metadata": outputs.get("metadata", {})
            }
            
            self.memory.save_context(
                {"input": str(inputs)},
                {"output": str(memory_output)}
            )
            logger.debug(f"Saved {self.agent_id} interaction to memory")
        except Exception as e:
            logger.warning(f"Failed to save to memory: {str(e)}") 