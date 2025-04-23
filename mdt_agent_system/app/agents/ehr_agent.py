import json
import logging
from typing import Dict, Any, List, Optional

from mdt_agent_system.app.core.schemas import PatientCase
from mdt_agent_system.app.core.status import StatusUpdateService
from mdt_agent_system.app.core.logging import get_logger
from mdt_agent_system.app.agents.base_agent import BaseSpecializedAgent

logger = get_logger(__name__)

class EHRAgent(BaseSpecializedAgent):
    """EHR Agent responsible for analyzing patient history and current condition.
    
    This agent focuses on:
    1. Patient demographics and history
    2. Current symptoms and clinical status
    3. Comorbidities and their impact
    4. Performance status evaluation
    5. Risk factor assessment
    """
    
    def __init__(self, run_id: str, status_service: StatusUpdateService, callbacks=None):
        """Initialize the EHR Agent.
        
        Args:
            run_id: The current simulation run identifier
            status_service: The service for emitting status updates
            callbacks: Optional callback handlers for LangChain
        """
        super().__init__(
            agent_id="EHRAgent",
            run_id=run_id,
            status_service=status_service,
            callbacks=callbacks
        )
    
    def _get_agent_type(self) -> str:
        """Return the agent type for prompt template selection."""
        return "ehr"
    
    def _prepare_input(self, patient_case: PatientCase, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare input for the EHR agent's analysis.
        
        Extracts relevant patient data including demographics, medical history,
        and current condition from the patient case.
        
        Args:
            patient_case: The patient case data
            context: Additional context from previous agent steps
            
        Returns:
            A dictionary with the prepared input for the EHR agent
        """
        # Extract relevant EHR information from the patient_case
        ehr_context = {
            "patient_id": patient_case.patient_id,
            "demographics": patient_case.demographics,
            "medical_history": patient_case.medical_history,
            "current_condition": patient_case.current_condition,
            "lab_results": patient_case.lab_results if hasattr(patient_case, 'lab_results') else []
        }
        
        # Convert to JSON string with indentation for better LLM processing
        context_str = json.dumps(ehr_context, indent=2)
        
        return {
            "context": context_str,
            "task": "Analyze the patient's medical history, demographics, and current condition. "
                    "Provide a structured analysis of key clinical factors, performance status, "
                    "and implications for treatment planning."
        }
    
    def _structure_output(self, llm_output: str) -> Dict[str, Any]:
        """Structure the LLM output into a standardized format.
        
        Attempts to parse the LLM output into a structured format for the EHR analysis.
        If parsing fails, returns a basic structure with the raw output.
        
        Args:
            llm_output: The raw output from the LLM
            
        Returns:
            A structured dictionary with the EHR analysis results
        """
        try:
            # Basic structure to ensure consistent output format
            structured_output = {
                "summary": "",
                "key_history_points": [],
                "current_presentation": {
                    "main_symptoms": [],
                    "performance_status": "",
                    "comorbidity_impact": ""
                },
                "risk_factors": [],
                "clinical_implications": []
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
                
                # Try to identify sections
                lower_line = line.lower()
                if "summary" in lower_line or "assessment" in lower_line:
                    current_section = "summary"
                    structured_output["summary"] = line.split(":", 1)[1].strip() if ":" in line else line
                elif "history" in lower_line or "key points" in lower_line:
                    current_section = "key_history_points"
                elif "symptoms" in lower_line or "presentation" in lower_line:
                    current_section = "main_symptoms"
                elif "performance status" in lower_line or "ecog" in lower_line:
                    current_section = "performance_status"
                    if ":" in line:
                        structured_output["current_presentation"]["performance_status"] = line.split(":", 1)[1].strip()
                elif "comorbidity" in lower_line or "comorbidities" in lower_line:
                    current_section = "comorbidity_impact"
                    if ":" in line:
                        structured_output["current_presentation"]["comorbidity_impact"] = line.split(":", 1)[1].strip()
                elif "risk factor" in lower_line:
                    current_section = "risk_factors"
                elif "implication" in lower_line:
                    current_section = "clinical_implications"
                # Process line based on current section
                elif current_section == "key_history_points" and line.startswith("- "):
                    structured_output["key_history_points"].append(line[2:])
                elif current_section == "main_symptoms" and line.startswith("- "):
                    structured_output["current_presentation"]["main_symptoms"].append(line[2:])
                elif current_section == "risk_factors" and line.startswith("- "):
                    structured_output["risk_factors"].append(line[2:])
                elif current_section == "clinical_implications" and line.startswith("- "):
                    structured_output["clinical_implications"].append(line[2:])
            
            # If we couldn't extract a good summary, create one from the first few lines
            if not structured_output["summary"]:
                structured_output["summary"] = ' '.join(lines[:3]) if lines else "EHR Analysis Completed"
            
            # Include raw output for reference
            structured_output["raw_output"] = llm_output
            
            return structured_output
            
        except Exception as e:
            logger.exception(f"Error structuring EHR output: {str(e)}")
            # Fallback to a basic structure with raw output
            return {
                "summary": "Error structuring output, please see raw response",
                "raw_output": llm_output
            } 