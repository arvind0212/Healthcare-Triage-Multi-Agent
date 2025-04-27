import json
from typing import Dict, Any, Union

# Assuming schemas are in the correct path relative to this file
# Adjust imports if necessary based on your project structure
from mdt_agent_system.app.core.schemas import PatientCase
from mdt_agent_system.app.core.status import StatusUpdateService
from mdt_agent_system.app.core.logging import get_logger
from mdt_agent_system.app.agents.base_agent import BaseSpecializedAgent
from mdt_agent_system.app.core.schemas import AgentOutput

logger = get_logger(__name__)

class SummaryAgent(BaseSpecializedAgent):
    """Summary Agent responsible for creating concise, markdown-formatted overview of MDT findings.
    
    This agent focuses on:
    1. Extracting key information from all previous agent outputs
    2. Creating a concise summary in markdown format
    3. Highlighting critical findings and recommendations
    4. Providing an executive summary for quick clinical decision-making
    """
    
    def __init__(self, run_id: str, status_service: StatusUpdateService, callbacks=None):
        super().__init__(
            agent_id="SummaryAgent",
            run_id=run_id,
            status_service=status_service,
            callbacks=callbacks
        )
    
    def _get_agent_type(self) -> str:
        """Return the agent type for prompt template selection."""
        return "summary"
        
    def _prepare_input(self, patient_case: PatientCase, context: Dict[str, Any]) -> Dict[str, Any]:
        """Convert complete MDT report data to LLM-friendly input for summarization"""
        logger.debug(f"Preparing input for SummaryAgent. Context keys: {list(context.keys())}")
        
        serializable_context = {}
        for key, value in context.items():
            try:
                json.dumps(value) 
                serializable_context[key] = value
            except (TypeError, OverflowError):
                logger.warning(f"Could not serialize context key '{key}', using string representation.")
                serializable_context[key] = str(value)

        # Create a string representation of the context for the LLM.
        context_str = json.dumps(serializable_context, indent=2, default=str)
        
        # Define the task for the prompt template
        return {
            "context": context_str,
            "task": "Create a concise, markdown-formatted executive summary of the MDT findings and recommendations."
        }
    
    def _structure_output(self, llm_output: Union[str, AgentOutput]) -> Dict[str, Any]:
        """Preserve markdown formatting from LLM output"""
        try:
            # Handle AgentOutput object
            if isinstance(llm_output, AgentOutput):
                return {
                    "markdown_content": llm_output.markdown_content,
                    "metadata": llm_output.metadata
                }
            
            # Handle string input
            logger.debug(f"Structuring SummaryAgent output from string input")
            return {"markdown_content": llm_output}
        except Exception as e:
            logger.error(f"Error structuring summary output: {e}")
            return {"markdown_content": str(llm_output)} 