import json
import logging
from typing import Dict, Any, List, Optional

from mdt_agent_system.app.core.schemas import PatientCase
from mdt_agent_system.app.core.schemas.agent_output import AgentOutput
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
            "task": (
                "Provide a comprehensive clinical assessment following this structure:\n\n"
                "1. Clinical Assessment\n"
                "   - Synthesize all available information\n"
                "   - Evaluate disease status and progression\n"
                "   - Consider patient-specific factors\n\n"
                "2. Treatment Planning\n"
                "   - Consider all therapeutic options\n"
                "   - Evaluate risk-benefit ratios\n"
                "   - Account for patient preferences\n\n"
                "3. Evidence Integration\n"
                "   - Apply current clinical guidelines\n"
                "   - Consider clinical trial options\n\n"
                "Format your response with markdown sections and include metadata."
            )
        }
    
    def _structure_output(self, parsed_output: AgentOutput) -> Dict[str, Any]:
        """Structure the parsed output into a standardized format.
        
        Args:
            parsed_output: The parsed output from the output parser
            
        Returns:
            A structured dictionary with the specialist assessment
        """
        # Create backward-compatible structure
        structured_output = {
            "overall_assessment": "",
            "treatment_considerations": [],
            "risk_assessment": "",
            "proposed_approach": "",
            "follow_up_recommendations": [],
            # New fields for enhanced output
            "markdown_content": parsed_output.markdown_content,
            "metadata": parsed_output.metadata
        }
        
        # Extract key sections from metadata if available
        if parsed_output.metadata:
            key_findings = parsed_output.metadata.get("key_findings", [])
            confidence_scores = parsed_output.metadata.get("confidence_scores", {})
            clinical_metrics = parsed_output.metadata.get("clinical_metrics", {})
            
            # Map metadata to legacy format
            if key_findings:
                structured_output["overall_assessment"] = " ".join(key_findings)
            
            if "treatment_plan" in confidence_scores:
                structured_output["proposed_approach"] = f"Treatment plan confidence: {confidence_scores['treatment_plan']}"
            
            if clinical_metrics:
                risk_level = clinical_metrics.get("case_complexity", "")
                urgency = clinical_metrics.get("treatment_urgency", "")
                structured_output["risk_assessment"] = f"Case complexity: {risk_level}, Urgency: {urgency}"
        
        # Extract sections from markdown content as fallback
        if not structured_output["overall_assessment"]:
            lines = parsed_output.markdown_content.split('\n')
            for line in lines:
                if "# Clinical Assessment" in line or "## Disease Status" in line:
                    next_idx = lines.index(line) + 1
                    if next_idx < len(lines):
                        structured_output["overall_assessment"] = lines[next_idx].strip('- ')
                        break
        
        # Extract treatment considerations from markdown
        treatment_section = False
        for line in parsed_output.markdown_content.split('\n'):
            if "## Treatment Recommendations" in line:
                treatment_section = True
                continue
            if treatment_section and line.strip() and line.startswith('- '):
                structured_output["treatment_considerations"].append(line.strip('- '))
        
        # Extract follow-up recommendations from markdown
        followup_section = False
        for line in parsed_output.markdown_content.split('\n'):
            if "## Follow-up Plan" in line:
                followup_section = True
                continue
            if followup_section and line.strip() and line.startswith('- '):
                structured_output["follow_up_recommendations"].append(line.strip('- '))
        
        # Ensure we have at least some basic content in required fields
        if not structured_output["overall_assessment"]:
            structured_output["overall_assessment"] = "Clinical assessment completed."
        
        if not structured_output["treatment_considerations"]:
            structured_output["treatment_considerations"] = ["Individualized treatment plan recommended."]
        
        if not structured_output["follow_up_recommendations"]:
            structured_output["follow_up_recommendations"] = ["Regular follow-up as clinically indicated."]
        
        return structured_output 