import json
import logging
from typing import Dict, Any, List, Optional, Union

from mdt_agent_system.app.core.schemas import PatientCase
from mdt_agent_system.app.core.schemas.agent_output import AgentOutput
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
        # Use a custom JSON encoder to handle datetime objects and other special types
        class CustomJSONEncoder(json.JSONEncoder):
            def default(self, obj):
                if hasattr(obj, "dict") and callable(obj.dict):
                    return obj.dict()
                if hasattr(obj, "__dict__"):
                    return obj.__dict__
                return str(obj)  # Convert any other objects to string
        
        try:
            context_str = json.dumps(pathology_context, indent=2, cls=CustomJSONEncoder)
        except Exception as e:
            logger.error(f"Error serializing pathology context: {str(e)}")
            # Fallback serialization with simpler data
            simple_context = {
                "patient_id": str(pathology_context.get("patient_id", "")),
                "current_condition": str(pathology_context.get("current_condition", ""))
            }
            context_str = json.dumps(simple_context, indent=2)
        
        return {
            "context": context_str,
            "task": (
                "You are an expert pathologist with molecular diagnostics expertise. "
                "Provide a comprehensive pathological and molecular analysis following this structure:\n\n"
                "1. Specimen Assessment\n"
                "   - Specimen adequacy\n"
                "   - Processing quality\n"
                "   - Sampling adequacy\n\n"
                "2. Diagnostic Findings\n"
                "   - Histological type\n"
                "   - Grade/differentiation\n"
                "   - Invasion status\n"
                "   - Margin status\n\n"
                "3. Molecular Profile\n"
                "   - Key mutations\n"
                "   - Biomarker status\n"
                "   - Therapeutic targets\n\n"
                "Format your response with the following sections:\n\n"
                "---MARKDOWN---\n"
                "# Pathology Report\n\n"
                "## Specimen Details\n"
                "- Type and adequacy\n"
                "- Processing notes\n"
                "- Quality indicators\n\n"
                "## Microscopic Findings\n"
                "1. Histological Features\n"
                "   - Type and grade\n"
                "   - Special features\n"
                "   - Prognostic factors\n\n"
                "2. Molecular Results\n"
                "   - Mutation status\n"
                "   - Biomarker levels\n"
                "   - Therapeutic targets\n\n"
                "## Clinical Implications\n"
                "- Treatment relevance\n"
                "- Prognostic factors\n"
                "- Additional testing needs\n\n"
                "---METADATA---\n"
                "{\n"
                '    "key_findings": [\n'
                '        "Critical pathological findings",\n'
                '        "Key molecular results",\n'
                '        "Treatment-relevant markers"\n'
                "    ],\n"
                '    "molecular_profile": {\n'
                '        "mutations": ["list"],\n'
                '        "biomarkers": {"marker": "status"},\n'
                '        "therapeutic_targets": ["list"]\n'
                "    },\n"
                '    "confidence_scores": {\n'
                '        "diagnosis": 0.0-1.0,\n'
                '        "molecular_results": 0.0-1.0,\n'
                '        "treatment_implications": 0.0-1.0\n'
                "    }\n"
                "}"
            )
        }
    
    def _structure_output(self, llm_output: Union[str, AgentOutput]) -> Dict[str, Any]:
        """Structure the LLM output into the standardized markdown format with metadata.
        
        Args:
            llm_output: The raw output from the LLM or an AgentOutput object
            
        Returns:
            A dictionary containing markdown_content and metadata
        """
        try:
            # Handle AgentOutput object
            if isinstance(llm_output, AgentOutput):
                return {
                    "markdown_content": llm_output.markdown_content,
                    "metadata": llm_output.metadata
                }
            
            # Handle string input
            # Split on markdown and metadata sections
            parts = llm_output.split("---MARKDOWN---")
            if len(parts) != 2:
                # If not in correct format, create structured markdown
                markdown_content = self._create_structured_markdown(llm_output)
                metadata = self._extract_metadata(llm_output)
            else:
                markdown_and_metadata = parts[1].split("---METADATA---")
                if len(markdown_and_metadata) != 2:
                    markdown_content = markdown_and_metadata[0].strip()
                    metadata = self._extract_metadata(llm_output)
                else:
                    markdown_content = markdown_and_metadata[0].strip()
                    try:
                        metadata = json.loads(markdown_and_metadata[1].strip())
                    except:
                        metadata = self._extract_metadata(llm_output)
            
            return {
                "markdown_content": markdown_content,
                "metadata": metadata
            }
        except Exception as e:
            logger.error(f"Error structuring output: {e}")
            return {
                "markdown_content": str(llm_output),
                "metadata": self._extract_metadata(str(llm_output))
            }

    def _create_structured_markdown(self, raw_output: str) -> str:
        """Create structured markdown from raw output.
        
        Args:
            raw_output: The raw LLM output
            
        Returns:
            Formatted markdown string
        """
        lines = raw_output.split('\n')
        sections = {
            "specimen": [],
            "microscopic": [],
            "implications": []
        }
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            lower_line = line.lower()
            
            # Detect sections
            if "specimen" in lower_line or "sample" in lower_line:
                current_section = "specimen"
            elif "microscopic" in lower_line or "histolog" in lower_line:
                current_section = "microscopic"
            elif "therapeutic" in lower_line or "clinical" in lower_line or "implication" in lower_line:
                current_section = "implications"
            elif current_section and (line.startswith("-") or line.startswith("*") or len(line) > 10):
                sections[current_section].append(line)
        
        # Format the markdown
        markdown = "# Pathology Report\n\n"
        
        markdown += "## Specimen Details\n"
        if sections["specimen"]:
            for line in sections["specimen"]:
                markdown += f"- {line.strip('- *')}\n"
        else:
            markdown += "- Specimen details not specified\n"
        
        markdown += "\n## Microscopic Findings\n"
        if sections["microscopic"]:
            for line in sections["microscopic"]:
                markdown += f"- {line.strip('- *')}\n"
        else:
            markdown += "- Microscopic findings not specified\n"
        
        markdown += "\n## Clinical Implications\n"
        if sections["implications"]:
            for line in sections["implications"]:
                markdown += f"- {line.strip('- *')}\n"
        else:
            markdown += "- Clinical implications not specified\n"
        
        return markdown

    def _extract_metadata(self, raw_output: str) -> Dict[str, Any]:
        """Extract metadata from raw output.
        
        Args:
            raw_output: The raw LLM output
            
        Returns:
            Structured metadata dictionary
        """
        # Initialize metadata structure as per medical_agent_prompts.md
        metadata = {
            "key_findings": [],
            "molecular_profile": {
                "mutations": [],
                "biomarkers": {},
                "therapeutic_targets": []
            },
            "confidence_scores": {
                "diagnosis": 0.8,  # Default confidence scores
                "molecular_results": 0.8,
                "treatment_implications": 0.8
            }
        }
        
        lines = raw_output.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            lower_line = line.lower()
            
            # Extract mutations
            if any(term in lower_line for term in ["mutation", "variant", "alteration"]):
                if line.startswith("-") or line.startswith("*"):
                    metadata["molecular_profile"]["mutations"].append(line.strip("- *"))
            
            # Extract biomarkers
            for marker in ["PD-L1", "MSI", "TMB", "HER2", "ER", "PR"]:
                if marker.lower() in lower_line and ":" in line:
                    key, value = line.split(":", 1)
                    metadata["molecular_profile"]["biomarkers"][marker] = value.strip()
            
            # Extract therapeutic targets
            if any(term in lower_line for term in ["target", "actionable", "druggable"]):
                if line.startswith("-") or line.startswith("*"):
                    metadata["molecular_profile"]["therapeutic_targets"].append(line.strip("- *"))
            
            # Extract key findings
            if len(line) > 20 and (line.startswith("-") or line.startswith("*")):
                metadata["key_findings"].append(line.strip("- *"))
        
        # Ensure we have at least one key finding
        if not metadata["key_findings"]:
            metadata["key_findings"].append("Pathology analysis completed")
        
        return metadata 