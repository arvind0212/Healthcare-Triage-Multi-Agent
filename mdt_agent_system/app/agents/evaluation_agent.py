import json
import logging
from typing import Dict, Any, List, Optional

from mdt_agent_system.app.core.schemas import PatientCase
from mdt_agent_system.app.core.status import StatusUpdateService
from mdt_agent_system.app.core.logging import get_logger
from mdt_agent_system.app.agents.base_agent import BaseSpecializedAgent

logger = get_logger(__name__)

class EvaluationAgent(BaseSpecializedAgent):
    """Evaluation Agent responsible for assessing the quality and completeness of the MDT report.
    
    This agent focuses on:
    1. Reviewing the complete MDT report
    2. Assessing adherence to guidelines
    3. Evaluating completeness of assessment
    4. Checking for logical consistency
    5. Identifying any gaps or areas for improvement
    """
    
    def __init__(self, run_id: str, status_service: StatusUpdateService, callbacks=None):
        """Initialize the Evaluation Agent.
        
        Args:
            run_id: The current simulation run identifier
            status_service: The service for emitting status updates
            callbacks: Optional callback handlers for LangChain
        """
        super().__init__(
            agent_id="EvaluationAgent",
            run_id=run_id,
            status_service=status_service,
            callbacks=callbacks
        )
    
    def _get_agent_type(self) -> str:
        """Return the agent type for prompt template selection."""
        return "evaluation"
    
    def _prepare_input(self, patient_case: PatientCase, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare input for the Evaluation agent's analysis.
        
        This agent receives the complete MDT report to evaluate its quality and completeness.
        
        Args:
            patient_case: The patient case data
            context: Additional context from previous agent steps
            
        Returns:
            A dictionary with the prepared input for the Evaluation agent
        """
        # Create a structured MDT report from all previous analyses
        mdt_report = {
            "patient_id": patient_case.patient_id,
            "demographics": patient_case.demographics,
            "current_condition": patient_case.current_condition
        }
        
        # Process dictionary conversions to prevent [object Object] in the output
        def convert_to_dict(obj):
            if hasattr(obj, "dict") and callable(obj.dict):
                return obj.dict()
            elif hasattr(obj, "__dict__"):
                return obj.__dict__
            else:
                return obj
        
        # Add all available analyses from previous agent steps
        if context:
            if "ehr_analysis" in context:
                mdt_report["ehr_analysis"] = convert_to_dict(context["ehr_analysis"])
            if "imaging_analysis" in context:
                mdt_report["imaging_analysis"] = convert_to_dict(context["imaging_analysis"])
            if "pathology_analysis" in context:
                mdt_report["pathology_analysis"] = convert_to_dict(context["pathology_analysis"])
            if "guideline_recommendations" in context:
                # If it's a list, process each item
                if isinstance(context["guideline_recommendations"], list):
                    mdt_report["guideline_recommendations"] = [
                        convert_to_dict(item) for item in context["guideline_recommendations"]
                    ]
                else:
                    mdt_report["guideline_recommendations"] = convert_to_dict(context["guideline_recommendations"])
            if "specialist_assessment" in context:
                mdt_report["specialist_assessment"] = convert_to_dict(context["specialist_assessment"])
        
        # Define evaluation criteria for the agent
        evaluation_criteria = {
            "completeness": "Assesses if all relevant aspects of the case are covered",
            "evidence_based": "Evaluates adherence to clinical guidelines and evidence-based practices",
            "patient_centered": "Checks if patient-specific factors are adequately considered",
            "logical_consistency": "Evaluates if recommendations are consistent with findings",
            "documentation": "Assesses the clarity and completeness of documentation"
        }
        
        # Custom JSON encoder to handle complex objects
        class CustomJSONEncoder(json.JSONEncoder):
            def default(self, obj):
                if hasattr(obj, "dict") and callable(obj.dict):
                    return obj.dict()
                if hasattr(obj, "__dict__"):
                    return obj.__dict__
                # Handle other special types as needed
                return str(obj)  # Convert any other objects to string
        
        # Convert to JSON string with indentation for better LLM processing
        try:
            mdt_report_str = json.dumps(mdt_report, indent=2, cls=CustomJSONEncoder)
            criteria_str = json.dumps(evaluation_criteria, indent=2)
        except Exception as e:
            logger.error(f"Error serializing evaluation context: {str(e)}")
            # Fallback serialization with simpler data
            simple_report = {
                "patient_id": str(mdt_report.get("patient_id", "")),
                "error": f"Failed to serialize complete report: {str(e)}"
            }
            mdt_report_str = json.dumps(simple_report, indent=2)
            criteria_str = json.dumps(evaluation_criteria, indent=2)
        
        return {
            "context": f"MDT Report:\n{mdt_report_str}\n\nEvaluation Criteria:\n{criteria_str}",
            "task": "Evaluate the quality and completeness of this MDT report. Assess each criteria "
                    "and provide both a numerical score (0.0-1.0) and detailed comments. Identify "
                    "strengths, weaknesses, and any missing elements that should be addressed."
        }
    
    def _structure_output(self, llm_output: str) -> Dict[str, Any]:
        """Structure the LLM output into a standardized format.
        
        Attempts to parse the LLM output into a structured evaluation format.
        If parsing fails, returns a basic structure with the raw output.
        
        Args:
            llm_output: The raw output from the LLM
            
        Returns:
            A structured dictionary with the evaluation results
        """
        try:
            # Default structure for evaluation output
            structured_output = {
                "score": 0.0,
                "comments": "",
                "strengths": [],
                "areas_for_improvement": [],
                "missing_elements": []
            }
            
            # Parse the LLM output for evaluation data
            lines = llm_output.split('\n')
            current_section = None
            
            # First, try to extract the score - look for overall score
            overall_score = None
            for line in lines:
                line = line.strip()
                # Look for patterns like "Overall Quality Score: 0.85" or "Score: 0.9"
                if (("overall" in line.lower() and "score" in line.lower()) or 
                    line.lower().startswith("score:")) and ":" in line:
                    score_text = line.split(":", 1)[1].strip()
                    try:
                        # Extract number from text like "0.85" or "85%" or "Score: 0.85/1.0"
                        score_parts = score_text.replace("/1.0", "").replace("/1", "").replace("%", "").strip()
                        score_value = float(score_parts)
                        # If percentage, convert to decimal
                        if score_value > 1.0:
                            score_value /= 100
                        overall_score = round(score_value, 2)
                        # Ensure score is between 0 and 1
                        if overall_score < 0:
                            overall_score = 0.0
                        elif overall_score > 1:
                            overall_score = 1.0
                        break
                    except ValueError:
                        logger.warning(f"Could not parse overall score from text: {score_text}")
                        continue
            
            # If overall score was found, use it
            if overall_score is not None:
                structured_output["score"] = overall_score
            
            # Process the output by sections
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Detect section changes
                lower_line = line.lower()
                if "strength" in lower_line and (":" in line or line.endswith("strengths")):
                    current_section = "strengths"
                    continue
                elif any(x in lower_line for x in ["area", "improvement", "weakness"]) and (":" in line or line.endswith("improvements")):
                    current_section = "areas_for_improvement"
                    continue
                elif "missing" in lower_line and (":" in line or line.endswith("elements")):
                    current_section = "missing_elements"
                    continue
                elif "comment" in lower_line and ":" in line:
                    current_section = "comments"
                    structured_output["comments"] = line.split(":", 1)[1].strip()
                    continue
                
                # Add content to the current section
                if current_section == "strengths" and line and not line.endswith(":"):
                    structured_output["strengths"].append(line)
                elif current_section == "areas_for_improvement" and line and not line.endswith(":"):
                    structured_output["areas_for_improvement"].append(line)
                elif current_section == "missing_elements" and line and not line.endswith(":"):
                    structured_output["missing_elements"].append(line)
                elif current_section == "comments" and line and not line.endswith(":"):
                    structured_output["comments"] += " " + line
            
            # If we couldn't extract specific comments but have the overall output
            if not structured_output["comments"]:
                structured_output["comments"] = llm_output[:200] + "..." if len(llm_output) > 200 else llm_output
            
            # Ensure we have at least one strength if none were identified
            if not structured_output["strengths"]:
                for line in lines:
                    if len(line) > 10 and any(term in line.lower() for term in ["thorough", "comprehensive", "good", "excellent", "well"]):
                        if not line.endswith(":") and ":" not in line:
                            structured_output["strengths"].append(line)
                            if len(structured_output["strengths"]) >= 2:
                                break
            
            # Still no strengths - add a placeholder
            if not structured_output["strengths"]:
                structured_output["strengths"] = ["The report provides a structured analysis of the patient case."]
            
            # Ensure we have at least one area for improvement
            if not structured_output["areas_for_improvement"]:
                for line in lines:
                    if len(line) > 10 and any(term in line.lower() for term in ["could", "should", "missing", "lacks", "improve"]):
                        if not line.endswith(":") and ":" not in line:
                            structured_output["areas_for_improvement"].append(line)
                            if len(structured_output["areas_for_improvement"]) >= 2:
                                break
            
            # Still no areas for improvement - add a placeholder
            if not structured_output["areas_for_improvement"]:
                structured_output["areas_for_improvement"] = ["Consider providing more detailed treatment rationale."]
            
            # Create a formatted evaluation summary for display
            strengths_text = "\n- " + "\n- ".join(structured_output["strengths"][:3]) if structured_output["strengths"] else ""
            improvements_text = "\n- " + "\n- ".join(structured_output["areas_for_improvement"][:3]) if structured_output["areas_for_improvement"] else ""
            
            structured_output["evaluation_formatted"] = (
                f"Overall Score: {structured_output['score']:.2f}\n\n"
                f"Key Strengths:{strengths_text}\n\n"
                f"Areas for Improvement:{improvements_text}"
            )
            
            return structured_output
            
        except Exception as e:
            logger.warning(f"Error structuring Evaluation Agent output: {str(e)}")
            # Fallback to basic structure with raw output
            return {
                "score": 0.75,  # Default score
                "comments": "Evaluation completed with parsing limitations. See raw output for details.",
                "raw_output": llm_output,
                "strengths": ["See raw output for identified strengths"],
                "areas_for_improvement": ["See raw output for areas of improvement"],
                "evaluation_formatted": "Overall Score: 0.75\n\nEvaluation completed with parsing limitations.",
                "processing_error": str(e)
            } 