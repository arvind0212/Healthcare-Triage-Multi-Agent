import logging
import asyncio # Added for simulating work
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

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
    summary: str = "Default summary"
    details: Dict[str, Any] = {}

# Context passed between agent steps
class AgentContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    run_id: str
    patient_case: PatientCase
    status_service: StatusUpdateService
    ehr_analysis: Optional[AgentOutputPlaceholder] = None
    imaging_analysis: Optional[AgentOutputPlaceholder] = None
    pathology_analysis: Optional[AgentOutputPlaceholder] = None
    guideline_recommendations: Optional[List[Dict[str, Any]]] = None
    specialist_assessment: Optional[AgentOutputPlaceholder] = None
    evaluation: Optional[Dict[str, Any]] = None

    # Extra fields allowed for intermediate data
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

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
    
    # Create an AgentOutputPlaceholder from the result
    context.ehr_analysis = AgentOutputPlaceholder(
        summary=result.get("summary", "EHR Analysis Complete"),
        details=result
    )
    
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
    
    # Convert to expected output format
    context.imaging_analysis = AgentOutputPlaceholder(
        summary=result.get("summary", "Imaging Analysis Completed"),
        details=result
    )
    
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
    
    # Convert to expected output format
    context.pathology_analysis = AgentOutputPlaceholder(
        summary=result.get("summary", "Pathology Analysis Completed"),
        details=result
    )
    
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
    
    # For guidelines, the result is already a list
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
    
    # Convert to expected output format
    context.specialist_assessment = AgentOutputPlaceholder(
        summary=result.get("overall_assessment", "Specialist Assessment Completed"),
        details=result
    )
    
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
    
    # Store result directly in context.evaluation
    context.evaluation = result
    
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

        # Define the workflow using the combined functions
        mdt_workflow: Runnable[AgentContext, AgentContext] = (
            RunnableLambda(emit_and_run_ehr)
            | RunnableLambda(emit_and_run_imaging)
            | RunnableLambda(emit_and_run_pathology)
            | RunnableLambda(emit_and_run_guideline)
            | RunnableLambda(emit_and_run_specialist)
            | RunnableLambda(emit_and_run_evaluation)
        )

        # Execute the workflow
        final_context = await mdt_workflow.ainvoke(initial_context)

        # --- Aggregate Report ---
        # Ensure final_context fields are not None before accessing
        final_report = MDTReport(
            patient_id=final_context.patient_case.patient_id,
            summary="MDT Simulation Complete (Runnable Workflow)",
            ehr_analysis=final_context.ehr_analysis.dict() if final_context.ehr_analysis else {},
            imaging_analysis=final_context.imaging_analysis.dict() if final_context.imaging_analysis else {},
            pathology_analysis=final_context.pathology_analysis.dict() if final_context.pathology_analysis else {},
            guideline_recommendations=final_context.guideline_recommendations if final_context.guideline_recommendations else [],
            specialist_assessment=final_context.specialist_assessment.dict() if final_context.specialist_assessment else {},
            treatment_options=[{"option": "Placeholder Treatment Option"}], # Still placeholder
            evaluation_score=final_context.evaluation.get("score") if final_context.evaluation else None,
            evaluation_comments=final_context.evaluation.get("comments") if final_context.evaluation else None,
            timestamp=datetime.utcnow(),
        )

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
        logger.info(f"Finished MDT simulation for run_id: {run_id}. Success. Duration: {datetime.utcnow() - start_time}")
        return final_report

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