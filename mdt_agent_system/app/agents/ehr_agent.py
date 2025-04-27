import json
import logging
from typing import Dict, Any, List, Optional

from mdt_agent_system.app.core.schemas import PatientCase
from mdt_agent_system.app.core.schemas.agent_output import AgentOutput
from mdt_agent_system.app.core.status import StatusUpdateService
from mdt_agent_system.app.core.logging import get_logger
from mdt_agent_system.app.agents.base_agent import BaseSpecializedAgent

logger = get_logger(__name__)

class EHRAgent(BaseSpecializedAgent):
    """EHR Agent responsible for analyzing electronic health records.
    
    This agent focuses on:
    1. Reviewing patient medical history
    2. Analyzing current medications and allergies
    3. Evaluating comorbidities and risk factors
    4. Identifying relevant past treatments
    5. Assessing patient-specific considerations
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
        
        Extracts relevant EHR data from the patient case.
        
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
            "medical_history": patient_case.medical_history if hasattr(patient_case, 'medical_history') else {},
            "current_medications": patient_case.current_medications if hasattr(patient_case, 'current_medications') else [],
            "allergies": patient_case.allergies if hasattr(patient_case, 'allergies') else [],
            "current_condition": patient_case.current_condition,
            "lab_results": patient_case.lab_results if hasattr(patient_case, 'lab_results') else []
        }
        
        # Convert to JSON string with indentation for better LLM processing
        # Use a custom JSON encoder to handle datetime objects and other special types
        class CustomJSONEncoder(json.JSONEncoder):
            def default(self, obj):
                if hasattr(obj, "dict") and callable(obj.dict):
                    return obj.dict()
                if hasattr(obj, "__dict__"):
                    return obj.__dict__
                return str(obj)  # Convert any other objects to string
        
        try:
            context_str = json.dumps(ehr_context, indent=2, cls=CustomJSONEncoder)
        except Exception as e:
            logger.error(f"Error serializing EHR context: {str(e)}")
            # Fallback serialization with simpler data
            simple_context = {
                "patient_id": str(ehr_context.get("patient_id", "")),
                "current_condition": str(ehr_context.get("current_condition", ""))
            }
            context_str = json.dumps(simple_context, indent=2)
        
        return {
            "context": context_str,
            "task": (
                "Provide a comprehensive EHR analysis following this structure:\n\n"
                "1. Patient Overview\n"
                "   - Demographics\n"
                "2. Medical History\n"
                "   - Past medical conditions\n"
                "   - Current medications\n"
                "   - Allergies\n"
                "3. Clinical Assessment\n"
                "   - Active conditions\n"
                "   - Comorbidities\n"
                "   - Risk factors\n"
                "4. Treatment History\n"
                "   - Past interventions\n"
                "   - Response to treatments\n"
                "   - Adverse events\n\n"
                "Format your response with markdown sections and include metadata."
            )
        }
    
    def _structure_output(self, parsed_output: AgentOutput) -> Dict[str, Any]:
        """Structure the parsed output into a standardized format.
        
        Args:
            parsed_output: The parsed output from the output parser
            
        Returns:
            A structured dictionary with the EHR analysis results
        """
        # Create backward-compatible structure
        structured_output = {
            "patient_summary": "",
            "active_conditions": [],
            "medications": [],
            "risk_factors": [],
            "treatment_history": [],
            # New fields for enhanced output
            "markdown_content": parsed_output.markdown_content,
            "metadata": parsed_output.metadata
        }
        
        # Extract key sections from metadata if available
        if parsed_output.metadata:
            key_findings = parsed_output.metadata.get("key_findings", [])
            clinical_metrics = parsed_output.metadata.get("clinical_metrics", {})
            risk_assessment = parsed_output.metadata.get("risk_assessment", {})
            
            # Map metadata to legacy format
            if key_findings:
                structured_output["patient_summary"] = " ".join(key_findings)
            
            if clinical_metrics:
                if "active_conditions" in clinical_metrics:
                    structured_output["active_conditions"].extend(clinical_metrics["active_conditions"])
                if "current_medications" in clinical_metrics:
                    structured_output["medications"].extend(clinical_metrics["current_medications"])
            
            if risk_assessment:
                structured_output["risk_factors"] = [
                    f"{risk}: {score}" for risk, score in risk_assessment.items()
                ]
        
        # Extract sections from markdown content
        lines = parsed_output.markdown_content.split('\n')
        overview_text = []
        in_overview = False
        for line in lines:
            if line.strip().startswith('# Patient Overview'):
                in_overview = True
                continue
            elif line.startswith('#'):
                in_overview = False
            elif in_overview and line.strip() and not line.strip().startswith('#'):
                overview_text.append(line.strip('- ').strip())
        
        # Use markdown content for patient summary if available and not already set from metadata
        if overview_text:
            structured_output["patient_summary"] = " ".join(overview_text)
        
        # Extract active conditions from markdown
        conditions_section = False
        for line in parsed_output.markdown_content.split('\n'):
            if "## Active Conditions" in line or "## Disease Status" in line:
                conditions_section = True
                continue
            if conditions_section and line.strip() and line.startswith('- '):
                structured_output["active_conditions"].append(line.strip('- '))
            elif conditions_section and line.startswith('#'):
                conditions_section = False
        
        # Extract medications from markdown
        medications_section = False
        for line in parsed_output.markdown_content.split('\n'):
            if "## Current Medications" in line:
                medications_section = True
                continue
            if medications_section and line.strip() and line.startswith('- '):
                structured_output["medications"].append(line.strip('- '))
            elif medications_section and line.startswith('#'):
                medications_section = False
        
        # Extract treatment history from markdown
        history_section = False
        for line in parsed_output.markdown_content.split('\n'):
            if "## Treatment History" in line:
                history_section = True
                continue
            if history_section and line.strip() and line.startswith('- '):
                structured_output["treatment_history"].append(line.strip('- '))
            elif history_section and line.startswith('#'):
                history_section = False
        
        # Ensure we have at least some basic content in required fields
        if not structured_output["patient_summary"]:
            structured_output["patient_summary"] = "EHR analysis completed."
        
        if not structured_output["active_conditions"]:
            structured_output["active_conditions"] = ["Current medical conditions under review."]
        
        if not structured_output["medications"]:
            structured_output["medications"] = ["Current medications under review."]
        
        if not structured_output["treatment_history"]:
            structured_output["treatment_history"] = ["Past treatment history under review."]
        
        return structured_output 