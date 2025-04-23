import json
import logging
from typing import Dict, Any, List, Optional

from mdt_agent_system.app.core.schemas import PatientCase
from mdt_agent_system.app.core.status import StatusUpdateService
from mdt_agent_system.app.core.logging import get_logger
from mdt_agent_system.app.agents.base_agent import BaseSpecializedAgent

logger = get_logger(__name__)

class ImagingAgent(BaseSpecializedAgent):
    """Imaging Agent responsible for analyzing radiological findings.
    
    This agent focuses on:
    1. Reviewing all imaging studies
    2. Analyzing disease extent and characteristics
    3. Assessing for complications
    4. Providing staging information based on imaging
    5. Evaluating treatment implications from an imaging perspective
    """
    
    def __init__(self, run_id: str, status_service: StatusUpdateService, callbacks=None):
        """Initialize the Imaging Agent.
        
        Args:
            run_id: The current simulation run identifier
            status_service: The service for emitting status updates
            callbacks: Optional callback handlers for LangChain
        """
        super().__init__(
            agent_id="ImagingAgent",
            run_id=run_id,
            status_service=status_service,
            callbacks=callbacks
        )
    
    def _get_agent_type(self) -> str:
        """Return the agent type for prompt template selection."""
        return "imaging"
    
    def _prepare_input(self, patient_case: PatientCase, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare input for the Imaging agent's analysis.
        
        Extracts relevant imaging data from the patient case.
        
        Args:
            patient_case: The patient case data
            context: Additional context from previous agent steps
            
        Returns:
            A dictionary with the prepared input for the Imaging agent
        """
        # Extract relevant imaging information from the patient_case
        imaging_context = {
            "patient_id": patient_case.patient_id,
            "demographics": patient_case.demographics,
            "imaging_results": patient_case.imaging_results if hasattr(patient_case, 'imaging_results') else {},
            "current_condition": patient_case.current_condition
        }
        
        # Add EHR context if available
        if context and "ehr_analysis" in context:
            imaging_context["ehr_context"] = context["ehr_analysis"]
        
        # Convert to JSON string with indentation for better LLM processing
        context_str = json.dumps(imaging_context, indent=2)
        
        return {
            "context": context_str,
            "task": "Analyze the patient's imaging studies. Provide a structured interpretation of key findings, "
                    "disease extent, staging assessment, and implications for treatment planning."
        }
    
    def _structure_output(self, llm_output: str) -> Dict[str, Any]:
        """Structure the LLM output into a standardized format.
        
        Attempts to parse the LLM output into a structured format for the imaging analysis.
        If parsing fails, returns a basic structure with the raw output.
        
        Args:
            llm_output: The raw output from the LLM
            
        Returns:
            A structured dictionary with the imaging analysis results
        """
        try:
            # Basic structure to ensure consistent output format
            structured_output = {
                "summary": "",
                "disease_extent": {
                    "primary_tumor": "",
                    "nodal_status": "",
                    "metastatic_status": ""
                },
                "staging": {
                    "clinical_stage": "",
                    "key_findings": []
                },
                "treatment_implications": []
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
                
                if "summary" in lower_line and (":" in line or line.endswith("summary")):
                    current_section = "summary"
                    content = line.split(":", 1)[1].strip() if ":" in line else ""
                    if content:
                        structured_output["summary"] = content
                
                elif "disease extent" in lower_line or "tumor extent" in lower_line:
                    current_section = "disease_extent"
                
                elif "primary" in lower_line and ("tumor" in lower_line or "lesion" in lower_line):
                    if ":" in line:
                        structured_output["disease_extent"]["primary_tumor"] = line.split(":", 1)[1].strip()
                    current_section = "primary_tumor"
                
                elif "nodal" in lower_line or "lymph node" in lower_line:
                    if ":" in line:
                        structured_output["disease_extent"]["nodal_status"] = line.split(":", 1)[1].strip()
                    current_section = "nodal_status"
                
                elif "metasta" in lower_line or "distant" in lower_line:
                    if ":" in line:
                        structured_output["disease_extent"]["metastatic_status"] = line.split(":", 1)[1].strip()
                    current_section = "metastatic_status"
                
                elif "staging" in lower_line or "stage" in lower_line:
                    current_section = "staging"
                
                elif "clinical stage" in lower_line or "tnm" in lower_line:
                    if ":" in line:
                        structured_output["staging"]["clinical_stage"] = line.split(":", 1)[1].strip()
                    current_section = "clinical_stage"
                
                elif "key finding" in lower_line or "important finding" in lower_line:
                    current_section = "key_findings"
                
                elif "treatment" in lower_line and "implication" in lower_line:
                    current_section = "treatment_implications"
                
                # Process line based on the current section
                elif current_section:
                    if current_section == "summary" and not structured_output["summary"]:
                        structured_output["summary"] = line
                    
                    elif current_section == "primary_tumor" and not structured_output["disease_extent"]["primary_tumor"]:
                        structured_output["disease_extent"]["primary_tumor"] = line
                    
                    elif current_section == "nodal_status" and not structured_output["disease_extent"]["nodal_status"]:
                        structured_output["disease_extent"]["nodal_status"] = line
                    
                    elif current_section == "metastatic_status" and not structured_output["disease_extent"]["metastatic_status"]:
                        structured_output["disease_extent"]["metastatic_status"] = line
                    
                    elif current_section == "clinical_stage" and not structured_output["staging"]["clinical_stage"]:
                        structured_output["staging"]["clinical_stage"] = line
                    
                    elif current_section == "key_findings":
                        if line.startswith("-") or line.startswith("*"):
                            structured_output["staging"]["key_findings"].append(line[1:].strip())
                        elif len(line) > 3:  # Avoid adding short lines or section headers
                            structured_output["staging"]["key_findings"].append(line)
                    
                    elif current_section == "treatment_implications":
                        if line.startswith("-") or line.startswith("*"):
                            structured_output["treatment_implications"].append(line[1:].strip())
                        elif len(line) > 3:  # Avoid adding short lines or section headers
                            structured_output["treatment_implications"].append(line)
            
            # If we didn't extract a proper summary, use the first paragraph
            if not structured_output["summary"] and len(lines) > 1:
                for line in lines[:5]:  # Check first few lines
                    if len(line.strip()) > 30:  # Reasonably long line
                        structured_output["summary"] = line.strip()
                        break
            
            # Ensure all required fields have values
            if not structured_output["summary"]:
                structured_output["summary"] = "Imaging analysis completed."
            
            if not structured_output["disease_extent"]["primary_tumor"]:
                structured_output["disease_extent"]["primary_tumor"] = "Details not specified"
                
            if not structured_output["staging"]["key_findings"] and lines:
                # Extract potential findings from the text if no structured findings were identified
                for line in lines:
                    if len(line.strip()) > 10 and any(term in line.lower() for term in ["mass", "lesion", "nodule", "opacity"]):
                        structured_output["staging"]["key_findings"].append(line.strip())
                
                # If still empty, add a placeholder
                if not structured_output["staging"]["key_findings"]:
                    structured_output["staging"]["key_findings"] = ["Imaging findings analyzed"]
            
            return structured_output
            
        except Exception as e:
            logger.warning(f"Error structuring Imaging Agent output: {str(e)}")
            # Fallback to basic structure with raw output
            return {
                "summary": "Imaging analysis completed with parsing limitations.",
                "raw_output": llm_output,
                "disease_extent": {
                    "primary_tumor": "See raw output",
                    "nodal_status": "See raw output",
                    "metastatic_status": "See raw output"
                },
                "staging": {
                    "clinical_stage": "Not extracted",
                    "key_findings": ["See raw output"]
                },
                "processing_error": str(e)
            } 