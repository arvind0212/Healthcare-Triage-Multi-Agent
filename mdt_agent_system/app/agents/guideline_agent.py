import json
import logging
from typing import Dict, Any, List, Optional

from langchain.tools import StructuredTool
from langchain_core.runnables import ConfigurableField, RunnableConfig

from mdt_agent_system.app.core.schemas import PatientCase
from mdt_agent_system.app.core.schemas.agent_output import AgentOutput
from mdt_agent_system.app.core.status import StatusUpdateService
from mdt_agent_system.app.core.logging import get_logger
from mdt_agent_system.app.agents.base_agent import BaseSpecializedAgent
from mdt_agent_system.app.core.tools import ToolRegistry, GuidelineReferenceTool

logger = get_logger(__name__)

class GuidelineAgent(BaseSpecializedAgent):
    """Guideline Agent responsible for providing evidence-based recommendations.
    
    This agent focuses on:
    1. Analyzing disease characteristics and stage
    2. Providing guideline-based treatment recommendations
    3. Evaluating evidence levels for recommendations
    4. Identifying special considerations and modifications
    5. Integrating multiple guideline sources
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
        
        # Check if the guideline tool is already registered before adding it
        if "guideline_reference" not in ToolRegistry.list_tools():
            # Register and make available the guidelines tool
            self.guideline_tool = GuidelineReferenceTool()
            ToolRegistry.register_tool(self.guideline_tool)
        else:
            # Tool already exists, just reference it
            self.guideline_tool = ToolRegistry.get_tool("guideline_reference")
        
    def _get_agent_type(self) -> str:
        """Return the agent type for prompt template selection."""
        return "guideline"
    
    def _prepare_input(self, patient_case: PatientCase, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare input for the guideline agent's analysis.
        
        Extracts relevant data from the patient case and previous analyses.
        
        Args:
            patient_case: The patient case data
            context: Additional context from previous agent steps
            
        Returns:
            A dictionary with the prepared input for the guideline agent
        """
        # Extract relevant information for guideline analysis
        guideline_context = {
            "patient_case": {
                "demographics": patient_case.demographics,
                "current_condition": patient_case.current_condition,
                "medical_history": patient_case.medical_history
            },
            "ehr_analysis": context.get("ehr_analysis", {}),
            "imaging_analysis": context.get("imaging_analysis", {}),
            "pathology_analysis": context.get("pathology_analysis", {})
        }
        
        # Convert to JSON string with indentation for better LLM processing
        try:
            context_str = json.dumps(guideline_context, indent=2)
        except Exception as e:
            logger.error(f"Error serializing guideline context: {str(e)}")
            # Fallback serialization with simpler data
            simple_context = {
                "current_condition": str(patient_case.current_condition),
                "ehr_summary": str(context.get("ehr_analysis", {}).get("patient_summary", ""))
            }
            context_str = json.dumps(simple_context, indent=2)
        
        return {
            "context": context_str,
            "task": (
                "Provide evidence-based guideline recommendations following this structure:\n\n"
                "1. Disease Characteristics\n"
                "   - Disease type and stage\n"
                "   - Relevant biomarkers\n"
                "   - Risk stratification\n\n"
                "2. Treatment Guidelines\n"
                "   - Primary treatment options\n"
                "   - Systemic therapy recommendations\n"
                "   - Adjuvant therapy considerations\n"
                "   - Treatment sequencing\n\n"
                "3. Special Considerations\n"
                "   - Age-related modifications\n"
                "   - Comorbidity adjustments\n"
                "   - Quality of life factors\n\n"
                "4. Evidence Level\n"
                "   - Strength of recommendations\n"
                "   - Quality of evidence\n"
                "   - Guideline sources\n\n"
                "Format your response with markdown sections and include metadata with guideline sources and evidence levels."
            )
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
    
    def _structure_output(self, parsed_output: AgentOutput) -> Dict[str, Any]:
        """Structure the parsed output into a standardized format.
        
        Args:
            parsed_output: The parsed output from the output parser
            
        Returns:
            A structured dictionary with the guideline analysis results
        """
        # Define the standard output structure
        structured_output = {
            "disease_characteristics": "",
            "treatment_recommendations": "",
            "evidence_levels": "",
            "special_considerations": "",
            "markdown_content": parsed_output.markdown_content,
            "metadata": parsed_output.metadata
        }

        try:
            # Define section mapping with multiple possible headers for each section
            section_mapping = {
                "disease_characteristics": [
                    "## Disease Characteristics",
                    "## Disease Status",
                    "## Clinical Characteristics"
                ],
                "treatment_recommendations": [
                    "## Treatment Guidelines",
                    "## Treatment Recommendations",
                    "## Therapeutic Approach"
                ],
                "special_considerations": [
                    "## Special Considerations",
                    "## Patient-Specific Factors",
                    "## Additional Considerations"
                ],
                "evidence_levels": [
                    "## Evidence Level",
                    "## Evidence Levels",
                    "## Evidence Grading"
                ]
            }

            # Extract content from markdown sections
            lines = parsed_output.markdown_content.split('\n')
            current_section = None
            current_subsection = None
            section_content = []
            subsection_content = {}

            for line in lines:
                line_stripped = line.strip()
                if not line_stripped:
                    continue

                # Check if this line starts a new section
                found_section = False
                for section_key, headers in section_mapping.items():
                    if any(line_stripped.startswith(header) for header in headers):
                        # Save content from previous section if it exists
                        if current_section:
                            if current_subsection and subsection_content:
                                section_content.extend(self._format_subsections(subsection_content))
                            structured_output[current_section] = self._clean_section_content(section_content)
                        # Start new section
                        current_section = section_key
                        section_content = []
                        subsection_content = {}
                        current_subsection = None
                        found_section = True
                        break

                # Check for subsection headers (###)
                if not found_section and line_stripped.startswith('### '):
                    if current_subsection and subsection_content.get(current_subsection):
                        section_content.extend(self._format_subsections({current_subsection: subsection_content[current_subsection]}))
                    current_subsection = line_stripped[4:].strip()
                    subsection_content[current_subsection] = []
                    continue

                # Add content to appropriate section/subsection
                if current_section:
                    if current_subsection:
                        subsection_content[current_subsection].append(line_stripped)
                    else:
                        section_content.append(line_stripped)

            # Save the last section
            if current_section:
                if current_subsection and subsection_content:
                    section_content.extend(self._format_subsections(subsection_content))
                structured_output[current_section] = self._clean_section_content(section_content)

            # Extract additional information from metadata
            if parsed_output.metadata:
                self._enhance_with_metadata(structured_output, parsed_output.metadata)

            # Validate and ensure content
            self._validate_metadata(structured_output)
            self._ensure_section_content(structured_output)

            return structured_output

        except Exception as e:
            logger.error(f"Error in _structure_output: {str(e)}", exc_info=True)
            return self._create_fallback_output(parsed_output, str(e))

    def _format_subsections(self, subsections: Dict[str, List[str]]) -> List[str]:
        """Format subsection content into a structured list.
        
        Args:
            subsections: Dictionary of subsection name to content lines
            
        Returns:
            List of formatted lines including subsection headers and content
        """
        formatted = []
        for subsection, content in subsections.items():
            if content:
                formatted.append(f"**{subsection}**")
                formatted.extend(content)
                formatted.append("")  # Add spacing between subsections
        return formatted

    def _validate_metadata(self, structured_output: Dict[str, Any]):
        """Validate and normalize metadata in the structured output.
        
        Args:
            structured_output: The structured output dictionary to validate
        """
        metadata = structured_output.get("metadata", {})
        if not metadata:
            logger.warning("No metadata found in structured output")
            return

        # Required metadata fields
        required_fields = ["guideline_sources", "evidence_levels"]
        for field in required_fields:
            if field not in metadata:
                logger.warning(f"Required metadata field '{field}' missing")
                metadata[field] = []

        # Validate evidence levels
        if isinstance(metadata["evidence_levels"], dict):
            # Map evidence levels to sections
            for section in structured_output.keys():
                if section not in ["markdown_content", "metadata"]:
                    section_key = section.replace("_", " ")
                    if section_key not in metadata["evidence_levels"]:
                        logger.warning(f"No evidence level found for section: {section_key}")
                        metadata["evidence_levels"][section_key] = "Not specified"

    def _clean_section_content(self, content: List[str]) -> str:
        """Clean and format section content.
        
        Args:
            content: List of content lines
            
        Returns:
            Cleaned and formatted content string
        """
        if not content:
            return ""

        # Remove markdown list markers while preserving hierarchy
        cleaned_lines = []
        for line in content:
            line = line.strip()
            if line.startswith('- '):
                cleaned_lines.append(line[2:])
            elif line.startswith('* '):
                cleaned_lines.append(line[2:])
            elif line.startswith('  - '):
                cleaned_lines.append('  ' + line[4:])
            elif line.startswith('    - '):
                cleaned_lines.append('    ' + line[6:])
            else:
                cleaned_lines.append(line)

        # Join lines and clean up extra whitespace
        content_str = '\n'.join(cleaned_lines)
        content_str = '\n'.join(line.strip() for line in content_str.split('\n') if line.strip())
        
        return content_str

    def _enhance_with_metadata(self, structured_output: Dict[str, Any], metadata: Dict[str, Any]):
        """Enhance structured output with metadata information.
        
        Args:
            structured_output: The structured output to enhance
            metadata: The metadata dictionary
        """
        try:
            # Add guideline sources to evidence levels section
            if "guideline_sources" in metadata:
                sources = metadata["guideline_sources"]
                if isinstance(sources, list) and sources:
                    source_text = "\nGuideline Sources:\n" + "\n".join(f"- {source}" for source in sources)
                    structured_output["evidence_levels"] = (
                        structured_output["evidence_levels"] + source_text
                        if structured_output["evidence_levels"]
                        else source_text.lstrip()
                    )

            # Add evidence levels to respective sections
            if "evidence_levels" in metadata and isinstance(metadata["evidence_levels"], dict):
                for section, level in metadata["evidence_levels"].items():
                    section_key = section.replace(" ", "_")
                    if section_key in structured_output and structured_output[section_key]:
                        structured_output[section_key] += f"\n\nEvidence Level: {level}"

            # Add key recommendations if available
            if "key_recommendations" in metadata:
                recommendations = metadata["key_recommendations"]
                if isinstance(recommendations, list) and recommendations:
                    rec_text = "\nKey Recommendations:\n" + "\n".join(f"- {rec}" for rec in recommendations)
                    structured_output["treatment_recommendations"] = (
                        structured_output["treatment_recommendations"] + rec_text
                        if structured_output["treatment_recommendations"]
                        else rec_text.lstrip()
                    )

        except Exception as e:
            logger.error(f"Error enhancing output with metadata: {str(e)}", exc_info=True)

    def _ensure_section_content(self, structured_output: Dict[str, Any]):
        """Ensure all sections have meaningful content.
        
        Args:
            structured_output: The structured output to validate
        """
        default_messages = {
            "disease_characteristics": "Disease characteristics not provided in the analysis.",
            "treatment_recommendations": "No specific treatment recommendations available.",
            "evidence_levels": "Evidence levels not specified in the analysis.",
            "special_considerations": "No special considerations identified."
        }

        for section, default_msg in default_messages.items():
            if not structured_output.get(section):
                logger.warning(f"Empty section found: {section}")
                structured_output[section] = default_msg

    def _create_fallback_output(self, parsed_output: AgentOutput, error: str) -> Dict[str, Any]:
        """Create a fallback output when structuring fails.
        
        Args:
            parsed_output: The original parsed output
            error: The error message
            
        Returns:
            A basic structured output with error information
        """
        logger.error(f"Creating fallback output due to error: {error}")
        return {
            "disease_characteristics": "Error processing disease characteristics.",
            "treatment_recommendations": "Error processing treatment recommendations.",
            "evidence_levels": "Error processing evidence levels.",
            "special_considerations": "Error processing special considerations.",
            "markdown_content": parsed_output.markdown_content,
            "metadata": {
                "error": error,
                "original_metadata": parsed_output.metadata
            }
        } 