import json
import logging
from typing import Dict, Any, List, Optional

from mdt_agent_system.app.core.schemas import PatientCase
from mdt_agent_system.app.core.status import StatusUpdateService
from mdt_agent_system.app.core.logging import get_logger
from mdt_agent_system.app.agents.base_agent import BaseSpecializedAgent

logger = get_logger(__name__)

class PathologyAgent(BaseSpecializedAgent):
    """Pathology Agent responsible for analyzing pathological and molecular findings.
    
    This agent focuses on:
    1. Reviewing pathological findings
    2. Interpreting molecular testing results
    3. Assessing biomarkers and their relevance
    4. Providing diagnostic confirmation
    5. Guiding therapeutic implications based on molecular profile
    """
    
    def __init__(self, run_id: str, status_service: StatusUpdateService, callbacks=None):
        """Initialize the Pathology Agent.
        
        Args:
            run_id: The current simulation run identifier
            status_service: The service for emitting status updates
            callbacks: Optional callback handlers for LangChain
        """
        super().__init__(
            agent_id="PathologyAgent",
            run_id=run_id,
            status_service=status_service,
            callbacks=callbacks
        )
    
    def _get_agent_type(self) -> str:
        """Return the agent type for prompt template selection."""
        return "pathology"
    
    def _prepare_input(self, patient_case: PatientCase, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare input for the Pathology agent's analysis.
        
        Extracts relevant pathology data from the patient case.
        
        Args:
            patient_case: The patient case data
            context: Additional context from previous agent steps
            
        Returns:
            A dictionary with the prepared input for the Pathology agent
        """
        # Extract relevant pathology information from the patient_case
        pathology_context = {
            "patient_id": patient_case.patient_id,
            "demographics": patient_case.demographics,
            "pathology_results": patient_case.pathology_results if hasattr(patient_case, 'pathology_results') else {},
            "current_condition": patient_case.current_condition
        }
        
        # Add context from previous agents if available
        if context:
            if "ehr_analysis" in context:
                pathology_context["ehr_context"] = context["ehr_analysis"]
            if "imaging_analysis" in context:
                pathology_context["imaging_context"] = context["imaging_analysis"]
        
        # Convert to JSON string with indentation for better LLM processing
        context_str = json.dumps(pathology_context, indent=2)
        
        return {
            "context": context_str,
            "task": "Analyze the patient's pathological and molecular findings. Provide a structured interpretation "
                    "including histological classification, molecular profile, biomarker status, and therapeutic implications."
        }
    
    def _structure_output(self, llm_output: str) -> Dict[str, Any]:
        """Structure the LLM output into a standardized format.
        
        Attempts to parse the LLM output into a structured format for the pathology analysis.
        If parsing fails, returns a basic structure with the raw output.
        
        Args:
            llm_output: The raw output from the LLM
            
        Returns:
            A structured dictionary with the pathology analysis results
        """
        try:
            # Basic structure to ensure consistent output format
            structured_output = {
                "summary": "",
                "histology": "",
                "molecular_profile": {
                    "key_mutations": "",
                    "immunotherapy_markers": "",
                    "other_markers": {}
                },
                "therapeutic_implications": []
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
                
                elif "histolog" in lower_line and (":" in line or "classification" in lower_line):
                    current_section = "histology"
                    content = line.split(":", 1)[1].strip() if ":" in line else ""
                    if content:
                        structured_output["histology"] = content
                
                elif "molecular" in lower_line and ("profile" in lower_line or "findings" in lower_line):
                    current_section = "molecular_profile"
                
                elif "mutation" in lower_line or "gene" in lower_line:
                    if "key" in lower_line or "driver" in lower_line:
                        if ":" in line:
                            structured_output["molecular_profile"]["key_mutations"] = line.split(":", 1)[1].strip()
                        current_section = "key_mutations"
                
                elif "immunotherapy" in lower_line or "pd-l1" in lower_line or "pd-1" in lower_line:
                    if ":" in line:
                        structured_output["molecular_profile"]["immunotherapy_markers"] = line.split(":", 1)[1].strip()
                    current_section = "immunotherapy_markers"
                
                elif any(marker in lower_line for marker in ["egfr", "alk", "ros1", "braf", "her2", "kras", "ntrk"]):
                    # Detect specific marker lines
                    for marker in ["egfr", "alk", "ros1", "braf", "her2", "kras", "ntrk"]:
                        if marker.upper() in line or marker.lower() in lower_line:
                            if ":" in line:
                                marker_key = marker.upper()
                                marker_value = line.split(":", 1)[1].strip()
                                structured_output["molecular_profile"]["other_markers"][marker_key] = marker_value
                
                elif "therapeutic" in lower_line or "treatment" in lower_line and "implication" in lower_line:
                    current_section = "therapeutic_implications"
                
                # Process line based on the current section
                elif current_section:
                    if current_section == "summary" and not structured_output["summary"]:
                        structured_output["summary"] = line
                    
                    elif current_section == "histology" and not structured_output["histology"]:
                        structured_output["histology"] = line
                    
                    elif current_section == "key_mutations" and not structured_output["molecular_profile"]["key_mutations"]:
                        structured_output["molecular_profile"]["key_mutations"] = line
                    
                    elif current_section == "immunotherapy_markers" and not structured_output["molecular_profile"]["immunotherapy_markers"]:
                        structured_output["molecular_profile"]["immunotherapy_markers"] = line
                    
                    elif current_section == "therapeutic_implications":
                        if line.startswith("-") or line.startswith("*"):
                            structured_output["therapeutic_implications"].append(line[1:].strip())
                        elif len(line) > 5:  # Avoid adding short lines or section headers
                            structured_output["therapeutic_implications"].append(line)
            
            # If we didn't extract a proper summary, use the first paragraph
            if not structured_output["summary"] and len(lines) > 1:
                for line in lines[:5]:  # Check first few lines
                    if len(line.strip()) > 30:  # Reasonably long line
                        structured_output["summary"] = line.strip()
                        break
            
            # Ensure all required fields have values
            if not structured_output["summary"]:
                structured_output["summary"] = "Pathology analysis completed."
            
            if not structured_output["histology"]:
                structured_output["histology"] = "Histology details not specified"
                
            if not structured_output["molecular_profile"]["key_mutations"]:
                structured_output["molecular_profile"]["key_mutations"] = "Key mutations not specified"
                
            if not structured_output["therapeutic_implications"]:
                for line in lines:
                    if "target" in line.lower() or "therapy" in line.lower() or "treatment" in line.lower():
                        if len(line.strip()) > 10:
                            structured_output["therapeutic_implications"].append(line.strip())
                
                # If still empty, add a placeholder
                if not structured_output["therapeutic_implications"]:
                    structured_output["therapeutic_implications"] = ["Therapeutic implications not specified"]
            
            # Add formatted string representation of molecular profile
            molecular_profile = structured_output["molecular_profile"]
            
            # Format key mutations and immunotherapy markers
            formatted_parts = []
            if molecular_profile["key_mutations"]:
                formatted_parts.append(f"Key Mutations: {molecular_profile['key_mutations']}")
            if molecular_profile["immunotherapy_markers"]:
                formatted_parts.append(f"Immunotherapy Markers: {molecular_profile['immunotherapy_markers']}")
            
            # Format other markers if present
            other_markers = molecular_profile.get("other_markers", {})
            if other_markers:
                other_markers_text = ", ".join([f"{key}: {value}" for key, value in other_markers.items()])
                formatted_parts.append(f"Other Markers: {other_markers_text}")
            
            # Combine all parts
            structured_output["molecular_profile_formatted"] = ". ".join(formatted_parts)
            if not structured_output["molecular_profile_formatted"]:
                structured_output["molecular_profile_formatted"] = "No molecular profile data specified"
            
            return structured_output
            
        except Exception as e:
            logger.warning(f"Error structuring Pathology Agent output: {str(e)}")
            # Fallback to basic structure with raw output
            return {
                "summary": "Pathology analysis completed with parsing limitations.",
                "raw_output": llm_output,
                "histology": "See raw output",
                "molecular_profile": {
                    "key_mutations": "See raw output",
                    "immunotherapy_markers": "See raw output",
                    "other_markers": {}
                },
                "molecular_profile_formatted": "Error parsing molecular profile information. See raw output.",
                "processing_error": str(e)
            } 