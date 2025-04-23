import json
import logging
from typing import Dict, Any, List, Optional

from mdt_agent_system.app.core.schemas import PatientCase
from mdt_agent_system.app.core.status import StatusUpdateService
from mdt_agent_system.app.core.logging import get_logger
from mdt_agent_system.app.agents.base_agent import BaseSpecializedAgent

logger = get_logger(__name__)

class SpecialistAgent(BaseSpecializedAgent):
    """Specialist Agent responsible for providing expert clinical assessment.
    
    This agent focuses on:
    1. Providing expert clinical assessment
    2. Synthesizing all available information
    3. Considering patient-specific factors
    4. Proposing treatment strategies
    5. Addressing complex clinical scenarios and questions
    """
    
    def __init__(self, run_id: str, status_service: StatusUpdateService, callbacks=None):
        """Initialize the Specialist Agent.
        
        Args:
            run_id: The current simulation run identifier
            status_service: The service for emitting status updates
            callbacks: Optional callback handlers for LangChain
        """
        super().__init__(
            agent_id="SpecialistAgent",
            run_id=run_id,
            status_service=status_service,
            callbacks=callbacks
        )
    
    def _get_agent_type(self) -> str:
        """Return the agent type for prompt template selection."""
        return "specialist"
    
    def _prepare_input(self, patient_case: PatientCase, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare input for the Specialist agent's analysis.
        
        This agent receives comprehensive information from all previous agents
        to make a holistic assessment.
        
        Args:
            patient_case: The patient case data
            context: Additional context from previous agent steps
            
        Returns:
            A dictionary with the prepared input for the Specialist agent
        """
        # The specialist needs comprehensive context from all previous analyses
        specialist_context = {
            "patient_id": patient_case.patient_id,
            "demographics": patient_case.demographics,
            "current_condition": patient_case.current_condition,
            "medical_history": patient_case.medical_history
        }
        
        # Add all available context from previous agent analyses
        if context:
            if "ehr_analysis" in context:
                specialist_context["ehr_analysis"] = context["ehr_analysis"]
            if "imaging_analysis" in context:
                specialist_context["imaging_analysis"] = context["imaging_analysis"]
            if "pathology_analysis" in context:
                specialist_context["pathology_analysis"] = context["pathology_analysis"]
            if "guideline_recommendations" in context:
                specialist_context["guideline_recommendations"] = context["guideline_recommendations"]
        
        # Convert to JSON string with indentation for better LLM processing
        context_str = json.dumps(specialist_context, indent=2)
        
        return {
            "context": context_str,
            "task": "Synthesize all available information and provide an expert clinical assessment "
                    "including treatment recommendations, risk stratification, and special considerations. "
                    "Consider both patient-specific factors and guideline recommendations."
        }
    
    def _structure_output(self, llm_output: str) -> Dict[str, Any]:
        """Structure the LLM output into a standardized format.
        
        Attempts to parse the LLM output into a structured format for the specialist assessment.
        If parsing fails, returns a basic structure with the raw output.
        
        Args:
            llm_output: The raw output from the LLM
            
        Returns:
            A structured dictionary with the specialist assessment
        """
        try:
            # Basic structure to ensure consistent output format
            structured_output = {
                "overall_assessment": "",
                "treatment_considerations": [],
                "risk_assessment": "",
                "proposed_approach": "",
                "follow_up_recommendations": []
            }
            
            # Simple parsing logic - in a production system, this would be more robust
            # using regex, structured output from the LLM, or a parser model
            
            # Extract key sections from the LLM output
            lines = llm_output.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Detect key sections by line content
                lower_line = line.lower()
                
                if any(x in lower_line for x in ["overall assessment", "clinical assessment", "assessment summary"]):
                    current_section = "overall_assessment"
                    content = line.split(":", 1)[1].strip() if ":" in line else ""
                    if content:
                        structured_output["overall_assessment"] = content
                
                elif any(x in lower_line for x in ["treatment consideration", "therapeutic consideration"]):
                    current_section = "treatment_considerations"
                
                elif any(x in lower_line for x in ["risk assessment", "risk stratification", "prognostic assessment"]):
                    current_section = "risk_assessment"
                    content = line.split(":", 1)[1].strip() if ":" in line else ""
                    if content:
                        structured_output["risk_assessment"] = content
                
                elif any(x in lower_line for x in ["proposed approach", "recommended approach", "treatment approach"]):
                    current_section = "proposed_approach"
                    content = line.split(":", 1)[1].strip() if ":" in line else ""
                    if content:
                        structured_output["proposed_approach"] = content
                
                elif any(x in lower_line for x in ["follow-up", "follow up", "follow-up recommendation"]):
                    current_section = "follow_up_recommendations"
                
                # Process line based on the current section
                elif current_section:
                    if current_section == "overall_assessment" and not structured_output["overall_assessment"]:
                        structured_output["overall_assessment"] = line
                    
                    elif current_section == "risk_assessment" and not structured_output["risk_assessment"]:
                        structured_output["risk_assessment"] = line
                    
                    elif current_section == "proposed_approach" and not structured_output["proposed_approach"]:
                        structured_output["proposed_approach"] = line
                    
                    elif current_section == "treatment_considerations":
                        if line.startswith("-") or line.startswith("*"):
                            structured_output["treatment_considerations"].append(line[1:].strip())
                        elif len(line) > 5:  # Avoid adding short lines or section headers
                            structured_output["treatment_considerations"].append(line)
                    
                    elif current_section == "follow_up_recommendations":
                        if line.startswith("-") or line.startswith("*"):
                            structured_output["follow_up_recommendations"].append(line[1:].strip())
                        elif len(line) > 5:  # Avoid adding short lines or section headers
                            structured_output["follow_up_recommendations"].append(line)
            
            # If we didn't extract a proper overall assessment, use the first paragraph
            if not structured_output["overall_assessment"] and len(lines) > 1:
                for line in lines[:5]:  # Check first few lines
                    if len(line.strip()) > 30:  # Reasonably long line
                        structured_output["overall_assessment"] = line.strip()
                        break
            
            # Ensure all required fields have values
            if not structured_output["overall_assessment"]:
                structured_output["overall_assessment"] = "Specialist assessment completed."
            
            if not structured_output["proposed_approach"]:
                # Try to derive from treatment considerations
                if structured_output["treatment_considerations"]:
                    structured_output["proposed_approach"] = "Treatment plan based on considerations listed."
                else:
                    structured_output["proposed_approach"] = "Individualized approach recommended."
            
            # Extract treatment considerations if they're not already identified
            if not structured_output["treatment_considerations"]:
                for line in lines:
                    line = line.strip()
                    if len(line) > 10 and any(term in line.lower() for term in ["treat", "therapy", "intervention", "management"]):
                        if not line.endswith(":") and not line.endswith("treatments") and not line.endswith("considerations"):
                            structured_output["treatment_considerations"].append(line)
                
                # Limit to a reasonable number of considerations
                structured_output["treatment_considerations"] = structured_output["treatment_considerations"][:5]
                
                # If still empty, add a placeholder
                if not structured_output["treatment_considerations"]:
                    structured_output["treatment_considerations"] = ["Individualized treatment recommended based on clinical factors."]
            
            return structured_output
            
        except Exception as e:
            logger.warning(f"Error structuring Specialist Agent output: {str(e)}")
            # Fallback to basic structure with raw output
            return {
                "overall_assessment": "Specialist assessment completed with parsing limitations.",
                "raw_output": llm_output,
                "treatment_considerations": ["See raw output for treatment details"],
                "proposed_approach": "Individualized approach recommended - see raw output for details.",
                "processing_error": str(e)
            } 