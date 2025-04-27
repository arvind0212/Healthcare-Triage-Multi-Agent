import json
import logging
from typing import Dict, Any, List, Optional

from mdt_agent_system.app.core.schemas import PatientCase
from mdt_agent_system.app.core.schemas.agent_output import AgentOutput
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
            # Ensure we're not passing an object with dict() method but actual dictionary data
            if hasattr(context["ehr_analysis"], "dict") and callable(context["ehr_analysis"].dict):
                imaging_context["ehr_context"] = context["ehr_analysis"].dict()
            else:
                imaging_context["ehr_context"] = context["ehr_analysis"]
        
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
            context_str = json.dumps(imaging_context, indent=2, cls=CustomJSONEncoder)
        except Exception as e:
            logger.error(f"Error serializing imaging context: {str(e)}")
            # Fallback serialization with simpler data
            simple_context = {
                "patient_id": str(imaging_context.get("patient_id", "")),
                "current_condition": str(imaging_context.get("current_condition", ""))
            }
            context_str = json.dumps(simple_context, indent=2)
        
        return {
            "context": context_str,
            "task": (
                "Provide a comprehensive imaging analysis following this structure:\n\n"
                "1. Technical Assessment\n"
                "   - Study quality\n"
                "   - Comparison with prior imaging\n"
                "   - Technical limitations\n\n"
                "2. Clinical Findings\n"
                "   - Primary lesion characteristics\n"
                "   - Disease extent\n"
                "   - Secondary findings\n\n"
                "3. Staging Assessment\n"
                "   - TNM classification\n"
                "   - Size measurements\n"
                "   - Progression criteria\n\n"
                "Format your response with markdown sections and include metadata."
            )
        }
    
    def _structure_output(self, parsed_output: AgentOutput) -> Dict[str, Any]:
        """Structure the parsed output into a standardized format.
        
        Args:
            parsed_output: The parsed output from the output parser
            
        Returns:
            A structured dictionary with the imaging analysis results
        """
        # Create backward-compatible structure
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
            "treatment_implications": [],
            # New fields for enhanced output
            "markdown_content": parsed_output.markdown_content,
            "metadata": parsed_output.metadata
        }
        
        # Extract key sections from metadata if available
        if parsed_output.metadata:
            measurements = parsed_output.metadata.get("measurements", {})
            key_findings = parsed_output.metadata.get("key_findings", [])
            confidence_scores = parsed_output.metadata.get("confidence_scores", {})
            
            # Map metadata to legacy format
            if measurements:
                if "primary_lesion" in measurements:
                    structured_output["disease_extent"]["primary_tumor"] = f"Size: {measurements['primary_lesion']}"
                if "significant_nodes" in measurements:
                    structured_output["disease_extent"]["nodal_status"] = f"Nodes: {', '.join(measurements['significant_nodes'])}"
            
            if key_findings:
                structured_output["staging"]["key_findings"].extend(key_findings)
                structured_output["summary"] = " ".join(key_findings[:2])  # Use first two findings as summary
        
        # Extract sections from markdown content as fallback
        if not structured_output["summary"]:
            lines = parsed_output.markdown_content.split('\n')
            for line in lines:
                if "# Clinical Findings" in line or "## Primary Disease" in line:
                    next_idx = lines.index(line) + 1
                    if next_idx < len(lines):
                        structured_output["summary"] = lines[next_idx].strip('- ')
                        break
        
        # Extract disease extent from markdown
        disease_section = False
        for line in parsed_output.markdown_content.split('\n'):
            if "## Disease Extent" in line:
                disease_section = True
                continue
            if disease_section and line.strip() and line.startswith('- '):
                content = line.strip('- ')
                if "primary" in content.lower() or "tumor" in content.lower():
                    structured_output["disease_extent"]["primary_tumor"] = content
                elif "node" in content.lower() or "lymph" in content.lower():
                    structured_output["disease_extent"]["nodal_status"] = content
                elif "metasta" in content.lower() or "distant" in content.lower():
                    structured_output["disease_extent"]["metastatic_status"] = content
        
        # Extract staging from markdown
        staging_section = False
        for line in parsed_output.markdown_content.split('\n'):
            if "# Staging Assessment" in line or "## Staging Assessment" in line:
                staging_section = True
                continue
            if staging_section and line.strip():
                if line.startswith('#'):  # Exit if we hit another section
                    staging_section = False
                    continue
                if line.startswith('- '):
                    content = line.strip('- ').strip()
                    if "stage:" in content.lower() or "clinical stage:" in content.lower():
                        # Extract the actual stage value after the colon
                        stage_parts = content.split(':')
                        if len(stage_parts) > 1:
                            structured_output["staging"]["clinical_stage"] = stage_parts[1].strip()
                        else:
                            structured_output["staging"]["clinical_stage"] = content
                    else:
                        structured_output["staging"]["key_findings"].append(content)
        
        # Extract treatment implications from markdown
        implications_section = False
        for line in parsed_output.markdown_content.split('\n'):
            if "## Clinical Correlation" in line:
                implications_section = True
                continue
            if implications_section and line.strip() and line.startswith('- '):
                structured_output["treatment_implications"].append(line.strip('- '))
        
        # Ensure we have at least some basic content in required fields
        if not structured_output["summary"]:
            structured_output["summary"] = "Imaging analysis completed."
        
        if not structured_output["disease_extent"]["primary_tumor"]:
            structured_output["disease_extent"]["primary_tumor"] = "Primary tumor assessment completed."
        
        if not structured_output["staging"]["clinical_stage"]:
            structured_output["staging"]["clinical_stage"] = "Staging assessment completed."
        
        if not structured_output["treatment_implications"]:
            structured_output["treatment_implications"] = ["Treatment implications based on imaging findings."]
        
        return structured_output 