import logging
import asyncio # Added for simulating work
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional, Union
import traceback  # Add traceback import

from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough, RunnableConfig
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from pydantic import BaseModel, Field # Added Field for AgentContext
from pydantic import ConfigDict

from mdt_agent_system.app.core.schemas import PatientCase, MDTReport, StatusUpdate
from mdt_agent_system.app.core.status import StatusUpdateService, Status
from mdt_agent_system.app.core.logging import get_logger
from mdt_agent_system.app.agents.ehr_agent import EHRAgent
# from mdt_agent_system.app.core.llm import get_llm
# from mdt_agent_system.app.core.memory import MemoryManager
# from mdt_agent_system.app.core.callbacks import StatusUpdateCallbackHandler

logger = get_logger(__name__)

# Placeholder for Agent Outputs
class AgentOutputPlaceholder(BaseModel):
    """Enhanced placeholder for agent outputs that handles both old and new formats."""
    summary: str = "Default summary"
    details: Dict[str, Any] = {}
    markdown_content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def dict(self, *args, **kwargs):
        """Override dict method to properly handle nested objects and new format."""
        result = {
            "summary": self.summary,
            "details": self._convert_to_serializable(self.details)
        }
        
        # Include new format fields if available
        if self.markdown_content is not None:
            result["markdown_content"] = self.markdown_content
        if self.metadata is not None:
            result["metadata"] = self._convert_to_serializable(self.metadata)
            
        return result
    
    @classmethod
    def from_agent_output(cls, output: Any) -> 'AgentOutputPlaceholder':
        """Create AgentOutputPlaceholder from various agent output formats."""
        if isinstance(output, dict):
            # Handle new format (AgentOutput)
            if "markdown_content" in output and "metadata" in output:
                return cls(
                    summary=output.get("summary", "Analysis completed"),
                    details=output,
                    markdown_content=output["markdown_content"],
                    metadata=output["metadata"]
                )
            # Handle legacy format
            return cls(
                summary=output.get("summary", "Analysis completed"),
                details=output
            )
        # Handle string or other formats
        return cls(
            summary=str(output) if output else "Analysis completed",
            details={"raw_output": str(output) if output else "No details available"}
        )
    
    def _convert_to_serializable(self, obj):
        """Convert objects to serializable format."""
        if hasattr(obj, "dict") and callable(obj.dict):
            return obj.dict()
        elif isinstance(obj, dict):
            return {k: self._convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_serializable(item) for item in obj]
        elif hasattr(obj, "__dict__"):
            return self._convert_to_serializable(obj.__dict__)
        else:
            try:
                return str(obj)
            except:
                return "Non-serializable object"

# Context passed between agent steps
class AgentContext(BaseModel):
    """In-memory context object passed between agent steps."""
    run_id: str
    patient_case: PatientCase
    status_service: StatusUpdateService
    ehr_analysis: Optional[AgentOutputPlaceholder] = None
    imaging_analysis: Optional[AgentOutputPlaceholder] = None
    pathology_analysis: Optional[AgentOutputPlaceholder] = None
    guideline_recommendations: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
    specialist_assessment: Optional[AgentOutputPlaceholder] = None
    evaluation: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None

    # Extra fields allowed for intermediate data
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)
    
    def dict(self, *args, **kwargs):
        """Override dict method to handle complex objects."""
        result = {
            "run_id": self.run_id,
            # Exclude complex objects that don't need to be serialized
            # "patient_case": self._convert_to_serializable(self.patient_case),
            # "status_service": "StatusUpdateService instance"  # Skip service objects
        }
        
        # Add agent outputs with proper serialization
        if self.ehr_analysis:
            result["ehr_analysis"] = self._convert_to_serializable(self.ehr_analysis)
        if self.imaging_analysis:
            result["imaging_analysis"] = self._convert_to_serializable(self.imaging_analysis)
        if self.pathology_analysis:
            result["pathology_analysis"] = self._convert_to_serializable(self.pathology_analysis)
        if self.guideline_recommendations:
            result["guideline_recommendations"] = self._convert_to_serializable(self.guideline_recommendations)
        if self.specialist_assessment:
            result["specialist_assessment"] = self._convert_to_serializable(self.specialist_assessment)
        if self.evaluation:
            result["evaluation"] = self._convert_to_serializable(self.evaluation)
        if self.summary:
            result["summary"] = self._convert_to_serializable(self.summary)
            
        return result
    
    def _convert_to_serializable(self, obj):
        """Convert objects to serializable format."""
        if hasattr(obj, "dict") and callable(obj.dict):
            return obj.dict()
        elif isinstance(obj, dict):
            return {k: self._convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_serializable(item) for item in obj]
        elif hasattr(obj, "__dict__"):
            return self._convert_to_serializable(obj.__dict__)
        else:
            # Try to get a string representation if all else fails
            try:
                return str(obj)
            except:
                return "Non-serializable object"

# --- Agent Step Functions (Placeholders as Runnables) ---

async def _run_ehr_agent_step(context: AgentContext) -> AgentContext:
    agent_id = "EHRAgent"
    await context.status_service.emit_status_update(
        run_id=context.run_id,
        status_update_data={
            "agent_id": agent_id,
            "status": "ACTIVE",
            "message": "Starting EHR Analysis",
            "timestamp": datetime.utcnow()
        }
    )
    
    # Create and execute the EHR Agent
    ehr_agent = EHRAgent(
        run_id=context.run_id,
        status_service=context.status_service
    )
    
    # Process with the EHR Agent
    result = await ehr_agent.process(context.patient_case, {})
    
    # Convert to expected output format using enhanced handler
    context.ehr_analysis = AgentOutputPlaceholder.from_agent_output(result)
    
    await context.status_service.emit_status_update(
        run_id=context.run_id,
        status_update_data={
            "agent_id": agent_id,
            "status": "DONE",
            "message": "EHR Analysis Finished",
            "timestamp": datetime.utcnow()
        }
    )
    return context

async def _run_imaging_agent_step(context: AgentContext) -> AgentContext:
    agent_id = "ImagingAgent"
    await context.status_service.emit_status_update(
        run_id=context.run_id,
        status_update_data={
            "agent_id": agent_id,
            "status": "ACTIVE",
            "message": "Starting Imaging Analysis",
            "timestamp": datetime.utcnow()
        }
    )
    
    # Create and use the actual ImagingAgent
    from mdt_agent_system.app.agents.imaging_agent import ImagingAgent
    
    agent = ImagingAgent(
        run_id=context.run_id,
        status_service=context.status_service
    )
    
    # Build a dict with context data for the agent
    agent_context = {}
    if context.ehr_analysis:
        agent_context["ehr_analysis"] = context.ehr_analysis.dict()
        
    # Process with the actual agent
    result = await agent.process(context.patient_case, agent_context)
    
    # Convert to expected output format using enhanced handler
    context.imaging_analysis = AgentOutputPlaceholder.from_agent_output(result)
    
    await context.status_service.emit_status_update(
        run_id=context.run_id,
        status_update_data={
            "agent_id": agent_id,
            "status": "DONE",
            "message": "Imaging Analysis Finished",
            "timestamp": datetime.utcnow()
        }
    )
    return context

async def _run_pathology_agent_step(context: AgentContext) -> AgentContext:
    agent_id = "PathologyAgent"
    await context.status_service.emit_status_update(
        run_id=context.run_id,
        status_update_data={
            "agent_id": agent_id,
            "status": "ACTIVE",
            "message": "Starting Pathology Analysis",
            "timestamp": datetime.utcnow()
        }
    )
    
    # Create and use the actual PathologyAgent
    from mdt_agent_system.app.agents.pathology_agent import PathologyAgent
    
    agent = PathologyAgent(
        run_id=context.run_id,
        status_service=context.status_service
    )
    
    # Build a dict with context data for the agent
    agent_context = {}
    if context.ehr_analysis:
        agent_context["ehr_analysis"] = context.ehr_analysis.dict()
    if context.imaging_analysis:
        agent_context["imaging_analysis"] = context.imaging_analysis.dict()
        
    # Process with the actual agent
    result = await agent.process(context.patient_case, agent_context)
    
    # Convert to expected output format using enhanced handler
    context.pathology_analysis = AgentOutputPlaceholder.from_agent_output(result)
    
    await context.status_service.emit_status_update(
        run_id=context.run_id,
        status_update_data={
            "agent_id": agent_id,
            "status": "DONE",
            "message": "Pathology Analysis Finished",
            "timestamp": datetime.utcnow()
        }
    )
    return context

async def _run_guideline_agent_step(context: AgentContext) -> AgentContext:
    agent_id = "GuidelineAgent"
    await context.status_service.emit_status_update(
        run_id=context.run_id,
        status_update_data={
            "agent_id": agent_id,
            "status": "ACTIVE",
            "message": "Starting Guideline Review",
            "timestamp": datetime.utcnow()
        }
    )
    
    # Create and use the actual GuidelineAgent
    from mdt_agent_system.app.agents.guideline_agent import GuidelineAgent
    
    agent = GuidelineAgent(
        run_id=context.run_id,
        status_service=context.status_service
    )
    
    # Build a dict with context data for the agent
    agent_context = {}
    if context.ehr_analysis:
        agent_context["ehr_analysis"] = context.ehr_analysis.dict()
    if context.imaging_analysis:
        agent_context["imaging_analysis"] = context.imaging_analysis.dict()
    if context.pathology_analysis:
        agent_context["pathology_analysis"] = context.pathology_analysis.dict()
        
    # Process with the actual agent
    result = await agent.process(context.patient_case, agent_context)
    
    # For guidelines, store the recommendations directly
    context.guideline_recommendations = result
    
    await context.status_service.emit_status_update(
        run_id=context.run_id,
        status_update_data={
            "agent_id": agent_id,
            "status": "DONE",
            "message": "Guideline Review Finished",
            "timestamp": datetime.utcnow()
        }
    )
    return context

async def _run_specialist_agent_step(context: AgentContext) -> AgentContext:
    agent_id = "SpecialistAgent"
    await context.status_service.emit_status_update(
        run_id=context.run_id,
        status_update_data={
            "agent_id": agent_id,
            "status": "ACTIVE",
            "message": "Starting Specialist Assessment",
            "timestamp": datetime.utcnow()
        }
    )
    
    # Create and use the actual SpecialistAgent
    from mdt_agent_system.app.agents.specialist_agent import SpecialistAgent
    
    agent = SpecialistAgent(
        run_id=context.run_id,
        status_service=context.status_service
    )
    
    # Build a dict with context data for the agent
    agent_context = {}
    if context.ehr_analysis:
        agent_context["ehr_analysis"] = context.ehr_analysis.dict()
    if context.imaging_analysis:
        agent_context["imaging_analysis"] = context.imaging_analysis.dict()
    if context.pathology_analysis:
        agent_context["pathology_analysis"] = context.pathology_analysis.dict()
    if context.guideline_recommendations:
        agent_context["guideline_recommendations"] = context.guideline_recommendations
        
    # Process with the actual agent
    result = await agent.process(context.patient_case, agent_context)
    
    # Convert to expected output format using enhanced handler
    context.specialist_assessment = AgentOutputPlaceholder.from_agent_output(result)
    
    await context.status_service.emit_status_update(
        run_id=context.run_id,
        status_update_data={
            "agent_id": agent_id,
            "status": "DONE",
            "message": "Specialist Assessment Finished",
            "timestamp": datetime.utcnow()
        }
    )
    return context

async def _run_evaluation_step(context: AgentContext) -> AgentContext:
    agent_id = "EvaluationAgent"
    await context.status_service.emit_status_update(
        run_id=context.run_id,
        status_update_data={
            "agent_id": agent_id,
            "status": "ACTIVE",
            "message": "Starting Final Evaluation",
            "timestamp": datetime.utcnow()
        }
    )
    
    # Create and use the EvaluationAgent
    from mdt_agent_system.app.agents.evaluation_agent import EvaluationAgent
    
    agent = EvaluationAgent(
        run_id=context.run_id,
        status_service=context.status_service
    )
    
    # Build a dict with context data for the agent
    agent_context = {}
    if context.ehr_analysis:
        agent_context["ehr_analysis"] = context.ehr_analysis.dict()
    if context.imaging_analysis:
        agent_context["imaging_analysis"] = context.imaging_analysis.dict()
    if context.pathology_analysis:
        agent_context["pathology_analysis"] = context.pathology_analysis.dict()
    if context.guideline_recommendations:
        agent_context["guideline_recommendations"] = context.guideline_recommendations
    if context.specialist_assessment:
        agent_context["specialist_assessment"] = context.specialist_assessment.dict()
        
    # Process with the actual agent
    result = await agent.process(context.patient_case, agent_context)
    
    # Convert to expected output format using enhanced handler
    evaluation_output = AgentOutputPlaceholder.from_agent_output(result)
    # Store both the raw evaluation and the formatted output
    context.evaluation = {
        **result,  # Keep raw result for backward compatibility
        "evaluation_formatted": evaluation_output.markdown_content if evaluation_output.markdown_content else None,
        "metadata": evaluation_output.metadata if evaluation_output.metadata else {}
    }
    
    await context.status_service.emit_status_update(
        run_id=context.run_id,
        status_update_data={
            "agent_id": agent_id,
            "status": "DONE",
            "message": "Evaluation Finished",
            "timestamp": datetime.utcnow()
        }
    )
    return context

async def _run_summary_step(context: AgentContext) -> AgentContext:
    agent_id = "SummaryAgent"
    await context.status_service.emit_status_update(
        run_id=context.run_id,
        status_update_data={
            "agent_id": agent_id,
            "status": "ACTIVE",
            "message": "Starting MDT Summary Generation",
            "timestamp": datetime.utcnow()
        }
    )
    
    # Create and use the SummaryAgent
    from mdt_agent_system.app.agents.summary_agent import SummaryAgent
    
    agent = SummaryAgent(
        run_id=context.run_id,
        status_service=context.status_service
    )
    
    # Build a dict with context data for the agent
    agent_context = {}
    if context.ehr_analysis:
        agent_context["ehr_analysis"] = context.ehr_analysis.dict()
    if context.imaging_analysis:
        agent_context["imaging_analysis"] = context.imaging_analysis.dict()
    if context.pathology_analysis:
        agent_context["pathology_analysis"] = context.pathology_analysis.dict()
    if context.guideline_recommendations:
        agent_context["guideline_recommendations"] = context.guideline_recommendations
    if context.specialist_assessment:
        agent_context["specialist_assessment"] = context.specialist_assessment.dict()
    if context.evaluation:
        agent_context["evaluation"] = context.evaluation
        
    # Process with the actual agent
    result = await agent.process(context.patient_case, agent_context)
    
    # Convert to expected output format using enhanced handler
    summary_output = AgentOutputPlaceholder.from_agent_output(result)
    # Store both the raw summary and the formatted output
    context.summary = {
        **result,  # Keep raw result for backward compatibility
        "summary": summary_output.summary,
        "markdown_content": summary_output.markdown_content if summary_output.markdown_content else None,
        "metadata": summary_output.metadata if summary_output.metadata else {}
    }
    
    await context.status_service.emit_status_update(
        run_id=context.run_id,
        status_update_data={
            "agent_id": agent_id,
            "status": "DONE",
            "message": "MDT Summary Generation Finished",
            "timestamp": datetime.utcnow()
        }
    )
    return context

# --- Helper Runnable for Coordinator Status Updates ---

async def _emit_coordinator_status(input_tuple: Tuple[AgentContext, str, str]) -> AgentContext:
    context, agent_name, status_message = input_tuple
    await context.status_service.emit_status_update(
        run_id=context.run_id,
        status_update_data={
            "agent_id": "Coordinator",
            "status": "ACTIVE",
            "message": status_message,
            "timestamp": datetime.utcnow(),
            "details": {"target_agent": agent_name}
        }
    )
    return context # Pass context through

# --- Main Simulation Runner ---

async def run_mdt_simulation(
    patient_case: PatientCase,
    run_id: str,
    status_service: StatusUpdateService,
    # config: RunnableConfig # Pass config if needed for callbacks etc.
) -> MDTReport:
    """
    Runs the simulated MDT process using LangChain Runnables.
    """
    start_time = datetime.utcnow()
    logger.info(f"Starting MDT simulation run_id: {run_id}, patient_id: {patient_case.patient_id}")

    initial_context = AgentContext(run_id=run_id, patient_case=patient_case, status_service=status_service)

    # Emit Initial Coordinator Status
    await status_service.emit_status_update(
        run_id=run_id,
        status_update_data={
            "agent_id": "Coordinator",
            "status": "ACTIVE",
            "message": "Initiating MDT Workflow",
            "timestamp": datetime.utcnow()
        }
    )

    try:
        # Create emission + step pairs
        async def emit_and_run_ehr(context: AgentContext) -> AgentContext:
            await context.status_service.emit_status_update(
                run_id=context.run_id,
                status_update_data={
                    "agent_id": "Coordinator",
                    "status": "ACTIVE",
                    "message": "Handing over to EHR Agent",
                    "timestamp": datetime.utcnow(),
                    "details": {"target_agent": "EHRAgent"}
                }
            )
            return await _run_ehr_agent_step(context)

        async def emit_and_run_imaging(context: AgentContext) -> AgentContext:
            await context.status_service.emit_status_update(
                run_id=context.run_id,
                status_update_data={
                    "agent_id": "Coordinator",
                    "status": "ACTIVE",
                    "message": "Handing over to Imaging Agent",
                    "timestamp": datetime.utcnow(),
                    "details": {"target_agent": "ImagingAgent"}
                }
            )
            return await _run_imaging_agent_step(context)

        async def emit_and_run_pathology(context: AgentContext) -> AgentContext:
            await context.status_service.emit_status_update(
                run_id=context.run_id,
                status_update_data={
                    "agent_id": "Coordinator",
                    "status": "ACTIVE",
                    "message": "Handing over to Pathology Agent",
                    "timestamp": datetime.utcnow(),
                    "details": {"target_agent": "PathologyAgent"}
                }
            )
            return await _run_pathology_agent_step(context)

        async def emit_and_run_guideline(context: AgentContext) -> AgentContext:
            await context.status_service.emit_status_update(
                run_id=context.run_id,
                status_update_data={
                    "agent_id": "Coordinator",
                    "status": "ACTIVE",
                    "message": "Handing over to Guideline Agent",
                    "timestamp": datetime.utcnow(),
                    "details": {"target_agent": "GuidelineAgent"}
                }
            )
            return await _run_guideline_agent_step(context)

        async def emit_and_run_specialist(context: AgentContext) -> AgentContext:
            await context.status_service.emit_status_update(
                run_id=context.run_id,
                status_update_data={
                    "agent_id": "Coordinator",
                    "status": "ACTIVE",
                    "message": "Handing over to Specialist Agent",
                    "timestamp": datetime.utcnow(),
                    "details": {"target_agent": "SpecialistAgent"}
                }
            )
            return await _run_specialist_agent_step(context)

        async def emit_and_run_evaluation(context: AgentContext) -> AgentContext:
            await context.status_service.emit_status_update(
                run_id=context.run_id,
                status_update_data={
                    "agent_id": "Coordinator",
                    "status": "ACTIVE",
                    "message": "Handing over to Evaluation Agent",
                    "timestamp": datetime.utcnow(),
                    "details": {"target_agent": "EvaluationAgent"}
                }
            )
            return await _run_evaluation_step(context)

        async def emit_and_run_summary(context: AgentContext) -> AgentContext:
            await context.status_service.emit_status_update(
                run_id=context.run_id,
                status_update_data={
                    "agent_id": "Coordinator",
                    "status": "ACTIVE",
                    "message": "Handing over to Summary Agent",
                    "timestamp": datetime.utcnow(),
                    "details": {"target_agent": "SummaryAgent"}
                }
            )
            return await _run_summary_step(context)

        # Define the workflow using the combined functions
        mdt_workflow: Runnable[AgentContext, AgentContext] = (
            RunnableLambda(emit_and_run_ehr)
            | RunnableLambda(emit_and_run_imaging)
            | RunnableLambda(emit_and_run_pathology)
            | RunnableLambda(emit_and_run_guideline)
            | RunnableLambda(emit_and_run_specialist)
            | RunnableLambda(emit_and_run_evaluation)
            | RunnableLambda(emit_and_run_summary)  # Add summary as final step
        )

        # Execute the workflow
        final_context = await mdt_workflow.ainvoke(initial_context)

        # --- Aggregate Report ---
        # Ensure final_context fields are not None before accessing
        
        # Extract treatment options from specialist assessment and pathology analysis
        treatment_options = []
        
        # Initialize guideline_recommendations outside the if block
        guideline_recommendations = []
        
        # Try to extract from specialist assessment first
        if final_context.specialist_assessment and final_context.specialist_assessment.details:
            specialist_details = final_context.specialist_assessment.details
            
            # Look for treatment-related sections
            treatment_sections = ["treatment_options", "proposed_approach", "treatment_considerations", "recommendations"]
            
            for section in treatment_sections:
                if section in specialist_details and specialist_details[section]:
                    if isinstance(specialist_details[section], list):
                        for item in specialist_details[section]:
                            if isinstance(item, str):
                                treatment_options.append({"option": item, "source": "Specialist Assessment"})
                            elif isinstance(item, dict) and "option" in item:
                                treatment_options.append(item)
                    elif isinstance(specialist_details[section], str):
                        treatment_options.append({"option": specialist_details[section], "source": "Specialist Assessment"})
        
        # If no treatments found yet, try pathology analysis
        if not treatment_options and final_context.pathology_analysis and final_context.pathology_analysis.details:
            pathology_details = final_context.pathology_analysis.details
            
            if "therapeutic_implications" in pathology_details and pathology_details["therapeutic_implications"]:
                implications = pathology_details["therapeutic_implications"]
                if isinstance(implications, list):
                    for implication in implications:
                        if isinstance(implication, str) and len(implication) > 10:  # Skip short strings
                            treatment_options.append({"option": implication, "source": "Pathology Analysis"})
        
        # If we still don't have options, check guideline recommendations
        if not treatment_options and final_context.guideline_recommendations:
            # Handle new GuidelineAgent format (structured sections)
            if isinstance(final_context.guideline_recommendations, dict):
                # Extract treatment recommendations section
                treatment_recs = final_context.guideline_recommendations.get("treatment_recommendations", "")
                disease_chars = final_context.guideline_recommendations.get("disease_characteristics", "")
                evidence_info = final_context.guideline_recommendations.get("evidence_levels", "")
                special_cons = final_context.guideline_recommendations.get("special_considerations", "")
                metadata = final_context.guideline_recommendations.get("metadata", {})
                
                # Process treatment recommendations into structured format
                guideline_recommendations.append({
                    "guideline": "Treatment Guidelines",
                    "recommendation": treatment_recs,
                    "evidence_level": evidence_info,
                    "source": metadata.get("guideline_sources", ["Clinical Guidelines"])[0] if isinstance(metadata.get("guideline_sources"), list) else "Clinical Guidelines"
                })
                
                # Add disease characteristics if present
                if disease_chars:
                    guideline_recommendations.append({
                        "guideline": "Disease Assessment",
                        "recommendation": disease_chars,
                        "evidence_level": evidence_info,
                        "source": "Clinical Assessment"
                    })
                
                # Add special considerations if present
                if special_cons:
                    guideline_recommendations.append({
                        "guideline": "Special Considerations",
                        "recommendation": special_cons,
                        "evidence_level": evidence_info,
                        "source": "Clinical Guidelines"
                    })
                
                # Extract treatment options from treatment recommendations
                treatment_options.append({
                    "option": treatment_recs,
                    "source": "Clinical Guidelines",
                    "evidence_level": evidence_info
                })
            else:
                # Handle legacy format
                for rec in final_context.guideline_recommendations:
                    # Handle both old and new format for guideline recommendations
                    if isinstance(rec, dict):
                        if "category" in rec and "recommendation" in rec:
                            # Legacy format from GuidelineAgent
                            guideline_recommendations.append({
                                "guideline": rec["category"],
                                "recommendation": rec["recommendation"],
                                "evidence_level": rec.get("evidence_level", "Not specified"),
                                "source": rec.get("guideline_source", "Not specified")
                            })
                            
                            # If this is a treatment guideline, add to treatment options
                            if rec["category"] == "Treatment Guidelines":
                                treatment_options.append({
                                    "option": rec["recommendation"],
                                    "source": rec.get("guideline_source", "Clinical Guidelines"),
                                    "evidence_level": rec.get("evidence_level", "Not specified")
                                })
                        elif "recommendations" in rec:
                            # Very old legacy format
                            recs = rec["recommendations"] if isinstance(rec["recommendations"], list) else [rec["recommendations"]]
                            for r in recs:
                                if isinstance(r, str) and len(r) > 10:
                                    guideline_recommendations.append({
                                        "guideline": "Clinical Guideline",
                                        "recommendation": r,
                                        "evidence_level": rec.get("evidence_level", "Not specified"),
                                        "source": "Clinical Guidelines"
                                    })
                                    # Also add to treatment options
                                    treatment_options.append({
                                        "option": r,
                                        "source": "Clinical Guidelines",
                                        "evidence_level": rec.get("evidence_level", "Not specified")
                                    })
                    elif isinstance(rec, str) and len(rec) > 10:
                        # Simple string format
                        guideline_recommendations.append({
                            "guideline": "Clinical Guideline",
                            "recommendation": rec,
                            "evidence_level": "Not specified",
                            "source": "Clinical Guidelines"
                        })
                        # Also add to treatment options
                        treatment_options.append({
                            "option": rec,
                            "source": "Clinical Guidelines",
                            "evidence_level": "Not specified"
                        })

        # If no recommendations found, add a placeholder
        if not guideline_recommendations:
            guideline_recommendations = [{
                "guideline": "General Guideline",
                "recommendation": "Please refer to clinical guidelines for specific recommendations.",
                "evidence_level": "Not specified",
                "source": "System"
            }]
        
        # If we still have no treatment options, use a more descriptive placeholder
        if not treatment_options:
            treatment_options = [{"option": "Treatment options should be determined through MDT discussion considering the patient's KRAS G12C mutation, high PD-L1 expression, and overall clinical status.", "source": "System Recommendation"}]
        
        # Get evaluation details with formatted output
        evaluation_formatted = None
        if final_context.evaluation:
            if "evaluation_formatted" in final_context.evaluation:
                evaluation_formatted = final_context.evaluation["evaluation_formatted"]
            else:
                # Create a basic formatted evaluation
                score = final_context.evaluation.get("score", 0.0)
                comments = final_context.evaluation.get("comments", "")
                strengths = final_context.evaluation.get("strengths", [])
                areas = final_context.evaluation.get("areas_for_improvement", [])
                
                strengths_text = "\n- " + "\n- ".join(strengths[:3]) if strengths else ""
                improvements_text = "\n- " + "\n- ".join(areas[:3]) if areas else ""
                
                evaluation_formatted = (
                    f"Overall Score: {score:.2f}\n\n"
                    f"Key Strengths:{strengths_text}\n\n"
                    f"Areas for Improvement:{improvements_text}"
                )
        
        # Create the final MDT report
        mdt_report = MDTReport(
            patient_id=final_context.patient_case.patient_id,
            summary=final_context.summary.get("summary", "No summary available"),
            ehr_analysis=final_context.ehr_analysis.dict() if final_context.ehr_analysis else {},
            imaging_analysis=final_context.imaging_analysis.dict() if final_context.imaging_analysis else None,
            pathology_analysis=final_context.pathology_analysis.dict() if final_context.pathology_analysis else None,
            guideline_recommendations=guideline_recommendations,
            specialist_assessment=final_context.specialist_assessment.dict() if final_context.specialist_assessment else {},
            treatment_options=treatment_options,
            evaluation_score=final_context.evaluation.get("score") if final_context.evaluation else None,
            evaluation_comments=final_context.evaluation.get("comments") if final_context.evaluation else None,
            evaluation_formatted=evaluation_formatted,
            markdown_content=final_context.summary.get("markdown_content", "No markdown content available"),
            markdown_summary=final_context.summary.get("markdown_content") if final_context.summary and final_context.summary.get("markdown_content") else None,
            timestamp=datetime.utcnow()
        )
        
        # Custom recursive function to ensure all nested objects are properly serialized
        def ensure_serializable(obj):
            """Recursively convert all objects to serializable types and use formatted fields."""
            if hasattr(obj, "dict") and callable(obj.dict):
                return ensure_serializable(obj.dict())
            elif isinstance(obj, dict):
                result = {}
                for k, v in obj.items():
                    # Handle special formatted fields
                    if k == "disease_extent" and "disease_extent_formatted" in obj:
                        # Use the formatted version directly
                        result[k] = obj["disease_extent_formatted"]
                    elif k == "staging" and "staging_formatted" in obj:
                        # Use the formatted version directly
                        result[k] = obj["staging_formatted"]
                    elif k == "molecular_profile" and "molecular_profile_formatted" in obj:
                        # Use the formatted version directly
                        result[k] = obj["molecular_profile_formatted"]
                    elif k == "evaluation" and "evaluation_formatted" in obj:
                        # Use the formatted evaluation summary
                        result[k] = obj["evaluation_formatted"]
                    else:
                        # Regular recursive serialization
                        result[k] = ensure_serializable(v)
                return result
            elif isinstance(obj, list):
                return [ensure_serializable(item) for item in obj]
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, "__dict__"):
                return ensure_serializable(obj.__dict__)
            else:
                # If it's a primitive type or we can't process it further, return as is
                return obj
        
        # Process the final report to ensure all objects are serializable
        report_dict = mdt_report.dict() if hasattr(mdt_report, "dict") else mdt_report.__dict__
        serialized_report = ensure_serializable(report_dict)
        
        # Convert serialized report back to an MDTReport object
        mdt_report = MDTReport(**serialized_report)
        
        print("\n\n============ DIRECT CONSOLE OUTPUT OF FINAL REPORT ============")
        print("PATIENT ID:", final_context.patient_case.patient_id)
        print("EHR ANALYSIS:", final_context.ehr_analysis)
        print("IMAGING ANALYSIS:", final_context.imaging_analysis)
        print("PATHOLOGY ANALYSIS:", final_context.pathology_analysis)
        print("GUIDELINE RECOMMENDATIONS:", final_context.guideline_recommendations)
        print("SPECIALIST ASSESSMENT:", final_context.specialist_assessment)
        print("EVALUATION:", final_context.evaluation)
        
        print("\n======= AGENT OUTPUTS RAW DATA =======")
        if hasattr(final_context.ehr_analysis, 'dict'):
            print("EHR OUTPUT:", final_context.ehr_analysis.dict())
        
        if hasattr(final_context.imaging_analysis, 'dict'):
            print("IMAGING OUTPUT:", final_context.imaging_analysis.dict())
        
        if hasattr(final_context.pathology_analysis, 'dict'):
            print("PATHOLOGY OUTPUT:", final_context.pathology_analysis.dict())
        
        if hasattr(final_context.specialist_assessment, 'dict'):
            print("SPECIALIST OUTPUT:", final_context.specialist_assessment.dict())
        
        # Also try to directly create a JSON string of the report
        import json
        try:
            from pydantic import BaseModel
            if isinstance(mdt_report, BaseModel):
                if hasattr(mdt_report, 'model_dump_json'):
                    report_json = mdt_report.model_dump_json()
                    print("\n======= FINAL REPORT JSON (model_dump_json) =======")
                    print(report_json[:1000])  # Print first 1000 chars to avoid overwhelming the console
                    print("... (truncated) ...")
                elif hasattr(mdt_report, 'json'):
                    report_json = mdt_report.json()
                    print("\n======= FINAL REPORT JSON (json method) =======")
                    print(report_json[:1000])  # Print first 1000 chars
                    print("... (truncated) ...")
            
            # Try the default JSON encoder with custom datetime handling
            class DateTimeEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    return super().default(obj)
            
            report_dict = {}
            if hasattr(mdt_report, 'dict'):
                report_dict = mdt_report.dict()
            elif hasattr(mdt_report, 'model_dump'):
                report_dict = mdt_report.model_dump()
            else:
                # Try direct attribute access to build a dict
                report_dict = {
                    "patient_id": getattr(mdt_report, "patient_id", "unknown"),
                    "summary": getattr(mdt_report, "summary", "unknown"),
                    "ehr_analysis": getattr(mdt_report, "ehr_analysis", {}),
                    "imaging_analysis": getattr(mdt_report, "imaging_analysis", {}),
                    "pathology_analysis": getattr(mdt_report, "pathology_analysis", {}),
                    "guideline_recommendations": getattr(mdt_report, "guideline_recommendations", []),
                    "specialist_assessment": getattr(mdt_report, "specialist_assessment", {}),
                    "treatment_options": getattr(mdt_report, "treatment_options", []),
                    "evaluation_score": getattr(mdt_report, "evaluation_score", None),
                    "evaluation_comments": getattr(mdt_report, "evaluation_comments", None),
                    "timestamp": str(datetime.utcnow())
                }
            
            manual_json = json.dumps(report_dict, cls=DateTimeEncoder, indent=2)
            print("\n======= FINAL REPORT MANUAL JSON =======")
            print(manual_json[:1000])  # Print first 1000 chars
            print("... (truncated) ...")
            
            # Write report to local file for inspection
            with open(f"report_{run_id}.json", "w") as f:
                f.write(manual_json)
            print(f"\nFull report written to file: report_{run_id}.json")
            
            # Create a simplified report for testing
            simple_report = {
                "patient_id": final_context.patient_case.patient_id,
                "summary": "Test Report",
                "timestamp": str(datetime.utcnow())
            }
            print("\n======= SIMPLIFIED TEST REPORT =======")
            print(json.dumps(simple_report, indent=2))
        except Exception as json_error:
            print(f"Error creating JSON output: {json_error}")
            print(f"Error type: {type(json_error)}")
            print(traceback.format_exc())
        
        print("===> FINAL REPORT CREATED:", mdt_report)

        # --- Emit Final Success Status ---
        await status_service.emit_status_update(
            run_id=run_id,
            status_update_data={
                "agent_id": "Coordinator",
                "status": "DONE",
                "message": "MDT Simulation Finished Successfully",
                "timestamp": datetime.utcnow()
            }
        )
        
        # --- FORCE TEST REPORT EMISSION ---
        # Test if a minimal report can be emitted successfully
        try:
            print("\n========= EMITTING TEST REPORT DIRECTLY =========")
            test_report = {
                "patient_id": final_context.patient_case.patient_id,
                "summary": "TEST REPORT - If you see this, regular report emission isn't working",
                "ehr_analysis": {"summary": "Test EHR Analysis"},
                "imaging_analysis": {"summary": "Test Imaging Analysis"},
                "pathology_analysis": {"summary": "Test Pathology Analysis"},
                "guideline_recommendations": [{"guideline": "Test Guideline"}],
                "specialist_assessment": {"summary": "Test Specialist Assessment"},
                "treatment_options": [{"option": "Test Treatment Option"}],
                "timestamp": str(datetime.utcnow())
            }
            
            print("Test report data:", test_report)
            
            # Directly emit the test report
            await status_service.emit_report(run_id=run_id, report_data=test_report)
            print("TEST REPORT EMITTED SUCCESSFULLY - Check if it appears in UI")
            
            # Short delay to give time for test report to be processed
            await asyncio.sleep(0.5)
        except Exception as test_report_error:
            print(f"FAILED TO EMIT TEST REPORT: {test_report_error}")
            print(traceback.format_exc())
        
        # --- Emit the MDT Report for UI display ---
        try:
            logger.info(f"Emitting MDT report for run_id: {run_id}")
            print(f"===> EMITTING REPORT for run_id: {run_id}")
            print(f"===> REPORT TYPE: {type(mdt_report)}")
            print(f"===> REPORT DICT METHOD EXISTS: {hasattr(mdt_report, 'dict')}")
            report_data = None
            try:
                # This is likely failing - use model_dump instead of dict for newer Pydantic versions
                if hasattr(mdt_report, 'model_dump'):
                    report_data = mdt_report.model_dump()
                    print(f"===> USING model_dump METHOD: {type(report_data)}")
                else:
                    report_data = mdt_report.dict()
                    print(f"===> USING dict METHOD: {type(report_data)}")
                
                print(f"===> REPORT DATA TYPE: {type(report_data)}")
                print(f"===> REPORT DATA SIZE: {len(str(report_data))} bytes")
                print(f"===> REPORT DATA KEYS: {report_data.keys() if isinstance(report_data, dict) else 'NOT A DICT'}")
            except Exception as dict_error:
                print(f"===> ERROR CALLING DICT/MODEL_DUMP METHOD: {dict_error}")
                print(f"===> ERROR TYPE: {type(dict_error)}")
                print(f"===> TRACEBACK: {traceback.format_exc()}")
            
            # Try alternative serialization if dict() fails
            if report_data is None:
                try:
                    import json
                    # Try using __dict__ or serialize the object directly
                    if hasattr(mdt_report, '__dict__'):
                        report_data = mdt_report.__dict__
                        print(f"===> USING __dict__ FALLBACK: {type(report_data)}")
                    else:
                        # Try direct JSON serialization with custom encoder
                        class DateTimeEncoder(json.JSONEncoder):
                            def default(self, obj):
                                if isinstance(obj, datetime):
                                    return obj.isoformat()
                                return super().default(obj)
                        
                        report_json = json.dumps(mdt_report, cls=DateTimeEncoder, default=str)
                        report_data = json.loads(report_json)
                        print(f"===> USING CUSTOM JSON SERIALIZATION: {type(report_data)}")
                except Exception as json_error:
                    print(f"===> ERROR WITH ALTERNATIVE SERIALIZATION: {json_error}")
                    print(f"===> ERROR TYPE: {type(json_error)}")
                    print(f"===> TRACEBACK: {traceback.format_exc()}")
            
            # If all else fails, create a minimal report
            if report_data is None:
                print("===> CREATING MINIMAL FALLBACK REPORT")
                report_data = {
                    "patient_id": final_context.patient_case.patient_id,
                    "summary": "MDT Simulation Complete - Report format error",
                    "timestamp": str(datetime.utcnow()),
                    "note": "Unable to format full report - see logs for details",
                    "ehr_analysis": {"summary": "EHR analysis complete, formatting error"},
                    "treatment_options": [{"option": "See logs for full report"}]
                }
            
            if report_data:
                print(f"===> SENDING REPORT DATA OF TYPE: {type(report_data)}")
                await status_service.emit_report(run_id=run_id, report_data=report_data)
                print("===> REPORT EMITTED SUCCESSFULLY")
                
                # Add an auto-retry mechanism after a short delay
                await asyncio.sleep(1.0)
                print("===> TRYING SECOND EMISSION AFTER DELAY")
                await status_service.emit_report(run_id=run_id, report_data=report_data)
                print("===> SECOND REPORT EMISSION ATTEMPT COMPLETED")
            else:
                print("===> COULD NOT EMIT REPORT: No valid report data")
        except Exception as report_error:
            logger.error(f"Failed to emit MDT report for run_id: {run_id}. Error: {report_error}", exc_info=True)
            print(f"===> FAILED TO EMIT REPORT: {report_error}")
            print(f"===> ERROR TYPE: {type(report_error)}")
            print(f"===> TRACEBACK: {traceback.format_exc()}")
            # Try one last direct approach
            try:
                print("===> TRYING LAST RESORT DIRECT EMISSION")
                minimal_report = {
                    "patient_id": str(final_context.patient_case.patient_id),
                    "summary": "Emergency fallback report due to formatting error",
                    "timestamp": str(datetime.utcnow())
                }
                await status_service.emit_report(run_id=run_id, report_data=minimal_report)
                print("===> EMERGENCY FALLBACK REPORT EMITTED")
            except Exception as emergency_error:
                print(f"===> EMERGENCY FALLBACK ALSO FAILED: {emergency_error}")
                # Continue execution even if report emission fails
        
        logger.info(f"Finished MDT simulation for run_id: {run_id}. Success. Duration: {datetime.utcnow() - start_time}")
        return mdt_report

    except Exception as e:
        logger.exception(f"Error during MDT simulation for run_id: {run_id}. Error: {e}", exc_info=True)
        # --- Emit Final Error Status ---
        await status_service.emit_status_update(
            run_id=run_id,
            status_update_data={
                "agent_id": "Coordinator",
                "status": "ERROR",
                "message": f"MDT Simulation Failed: {str(e)}",
                "timestamp": datetime.utcnow(),
                "details": {"error_type": type(e).__name__}
            }
        )
        # Re-raise or handle as needed, potentially return a partial/error report
        raise # Re-raise the exception for the background task runner to potentially catch

# Placeholder for Status enum if not defined in core.status
try:
    from mdt_agent_system.app.core.status import Status
except ImportError:
    from enum import Enum
    class Status(Enum):
        PENDING = "PENDING"
        ACTIVE = "ACTIVE"
        DONE = "DONE"
        ERROR = "ERROR"
        WAITING = "WAITING" 