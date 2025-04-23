import json
import logging
from typing import Dict, Any, List, Optional

from langchain.tools import StructuredTool
from langchain_core.runnables import ConfigurableField, RunnableConfig

from mdt_agent_system.app.core.schemas import PatientCase
from mdt_agent_system.app.core.status import StatusUpdateService
from mdt_agent_system.app.core.logging import get_logger
from mdt_agent_system.app.agents.base_agent import BaseSpecializedAgent
from mdt_agent_system.app.core.tools import ToolRegistry, GuidelineReferenceTool

logger = get_logger(__name__)

class GuidelineAgent(BaseSpecializedAgent):
    """Guideline Agent responsible for applying evidence-based guidelines to patient cases.
    
    This agent focuses on:
    1. Applying current guidelines to the case
    2. Identifying evidence-based treatment options
    3. Consider clinical trial eligibility
    4. Evaluating guideline adherence
    5. Highlighting any deviations from standard practice
    """
    
    def __init__(self, run_id: str, status_service: StatusUpdateService, callbacks=None):
        """Initialize the Guideline Agent.
        
        Args:
            run_id: The current simulation run identifier
            status_service: The service for emitting status updates
            callbacks: Optional callback handlers for LangChain
        """
        super().__init__(
            agent_id="GuidelineAgent",
            run_id=run_id,
            status_service=status_service,
            callbacks=callbacks
        )
        
        # Register and make available the guidelines tool
        self.guideline_tool = GuidelineReferenceTool()
        ToolRegistry.register_tool(self.guideline_tool)
        
    def _get_agent_type(self) -> str:
        """Return the agent type for prompt template selection."""
        return "guideline"
    
    def _prepare_input(self, patient_case: PatientCase, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare input for the Guideline agent's analysis.
        
        Extracts relevant data from the patient case and previous agent analyses.
        
        Args:
            patient_case: The patient case data
            context: Additional context from previous agent steps
            
        Returns:
            A dictionary with the prepared input for the Guideline agent
        """
        # Build guideline relevant context from patient case and previous analyses
        guideline_context = {
            "patient_id": patient_case.patient_id,
            "demographics": patient_case.demographics,
            "current_condition": patient_case.current_condition,
            "medical_history": patient_case.medical_history
        }
        
        # Add context from previous agent analyses, which is critical for guideline application
        if context:
            if "ehr_analysis" in context:
                guideline_context["ehr_analysis"] = context["ehr_analysis"]
            if "imaging_analysis" in context:
                guideline_context["imaging_analysis"] = context["imaging_analysis"]
            if "pathology_analysis" in context:
                guideline_context["pathology_analysis"] = context["pathology_analysis"]
        
        # Add information about available tools
        available_tools = [
            {
                "name": self.guideline_tool.name,
                "description": self.guideline_tool.description,
                "usage": "You can use this tool to look up medical guidelines by condition. Example: guideline_reference(condition='type_2_diabetes')"
            }
        ]
        
        guideline_context["available_tools"] = available_tools
        
        # Convert to JSON string with indentation for better LLM processing
        context_str = json.dumps(guideline_context, indent=2)
        
        return {
            "context": context_str,
            "task": "Analyze the patient case in relation to evidence-based guidelines. Identify applicable guidelines, "
                    "evidence-based treatment options, and clinical trial eligibility. You can use the guideline_reference tool "
                    "to look up specific guidelines."
        }
    
    async def _run_analysis(self, input_data: Dict[str, Any]) -> str:
        """Run the LLM analysis with the prepared input, including tool access.
        
        This overrides the base class method to add tool handling.
        
        Args:
            input_data: The prepared input data
            
        Returns:
            The LLM's response as a string
        """
        # Configure the LLM run with callbacks
        config = RunnableConfig(
            callbacks=self.callbacks,
            run_name=f"{self.agent_id}_analysis"
        )
        
        # Format the prompt with input data
        prompt = self.prompt_template.format_messages(
            context=input_data.get("context", ""),
            task=input_data.get("task", "Analyze the patient case in relation to guidelines")
        )
        
        # Get the guideline tool from registry
        guideline_tool = ToolRegistry.get_tool("guideline_reference")
        if not guideline_tool:
            logger.warning(f"Guideline reference tool not found in registry")
            # Proceed without tool
            response = await self.llm.ainvoke(prompt, config=config)
            return response.content
        
        # Create a structured tool for LangChain use
        structured_tool = StructuredTool.from_function(
            func=guideline_tool._run,
            name=guideline_tool.name,
            description=guideline_tool.description
        )
        
        # Bind the tool to the LLM
        llm_with_tools = self.llm.bind_tools([structured_tool])
        
        # Invoke LLM with tools 
        try:
            response = await llm_with_tools.ainvoke(prompt, config=config)
            return response.content
        except Exception as e:
            logger.error(f"Error in guideline agent tool-using LLM call: {str(e)}")
            # Fallback to regular LLM call if tool usage fails
            response = await self.llm.ainvoke(prompt, config=config)
            return response.content + "\n\nNote: Tool usage was attempted but failed."
    
    def _structure_output(self, llm_output: str) -> Dict[str, Any]:
        """Structure the LLM output into a standardized format.
        
        Attempts to parse the LLM output into a structured format for guideline recommendations.
        If parsing fails, returns a basic structure with the raw output.
        
        Args:
            llm_output: The raw output from the LLM
            
        Returns:
            A structured list of guideline recommendations
        """
        try:
            # For guidelines, we'll return a list of recommendation objects
            recommendations = []
            
            # Simple parsing logic
            lines = llm_output.split('\n')
            current_guideline = None
            current_recommendation = {
                "guideline": "",
                "version": "",
                "category": "",
                "recommendations": []
            }
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                lower_line = line.lower()
                
                # Check for guideline references
                if ("guideline" in lower_line or "guidelines" in lower_line) and ":" in line:
                    # If we were already processing a guideline, save it before starting a new one
                    if current_guideline and current_recommendation["recommendations"]:
                        recommendations.append(current_recommendation.copy())
                        
                    # Start a new guideline
                    current_guideline = line.split(":", 1)[1].strip()
                    current_recommendation = {
                        "guideline": current_guideline,
                        "version": "",
                        "category": "",
                        "recommendations": []
                    }
                
                # Check for version information
                elif "version" in lower_line and ":" in line:
                    current_recommendation["version"] = line.split(":", 1)[1].strip()
                
                # Check for category information
                elif "category" in lower_line and ":" in line:
                    current_recommendation["category"] = line.split(":", 1)[1].strip()
                
                # Collect recommendations - typically bullet points or numbered items
                elif line.startswith("-") or line.startswith("*") or (line[0].isdigit() and line[1:3] in [". ", ") "]):
                    recommendation_text = line[1:].strip() if line.startswith("-") or line.startswith("*") else line[line.find(" ")+1:].strip()
                    if recommendation_text and current_guideline:
                        current_recommendation["recommendations"].append(recommendation_text)
                
                # Also check for recommendation sections without bullet points
                elif "recommend" in lower_line and len(line) > 15 and current_guideline:
                    # This looks like a recommendation but isn't formatted as a bullet point
                    current_recommendation["recommendations"].append(line)
            
            # Don't forget to add the last guideline if there is one
            if current_guideline and current_recommendation["recommendations"]:
                recommendations.append(current_recommendation.copy())
            
            # If no structured recommendations were found, try to extract any recommendation-like statements
            if not recommendations:
                potential_recommendation = {
                    "guideline": "Clinical Practice Guidelines",
                    "version": "Current",
                    "category": "Treatment Recommendations",
                    "recommendations": []
                }
                
                for line in lines:
                    line = line.strip()
                    lower_line = line.lower()
                    if any(keyword in lower_line for keyword in ["recommend", "should", "advised", "treatment", "therapy", "standard of care"]):
                        if len(line) > 15:  # Reasonably detailed line
                            potential_recommendation["recommendations"].append(line)
                
                if potential_recommendation["recommendations"]:
                    recommendations.append(potential_recommendation)
            
            # If we still don't have recommendations, create a basic placeholder
            if not recommendations:
                recommendations = [{
                    "guideline": "General Clinical Guidelines",
                    "version": "Current",
                    "category": "Standard of Care",
                    "recommendations": ["Standard guideline-based care is recommended."]
                }]
            
            return recommendations
            
        except Exception as e:
            logger.warning(f"Error structuring Guideline Agent output: {str(e)}")
            # Fallback to a simple structured format
            return [{
                "guideline": "Clinical Guidelines",
                "version": "Current",
                "category": "Treatment Recommendation",
                "recommendations": ["Review of guidelines completed - see raw output for details"],
                "raw_output": llm_output,
                "processing_error": str(e)
            }] 