from fastapi import APIRouter, UploadFile, File, Depends, Request, Header
from fastapi import HTTPException, BackgroundTasks, status
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse, ServerSentEvent
from pydantic import ValidationError
import uuid
import json
import logging
import asyncio # Added for sleep in SSE stream
import os # For log file path
from typing import List, Optional
from datetime import datetime

from mdt_agent_system.app.core.schemas.common import PatientCase, StatusUpdate
# Import the actual status service instance getter
from mdt_agent_system.app.core.status.service import StatusUpdateService, get_status_service
# Correct config import
from mdt_agent_system.app.core.config.settings import settings
# Import the context variable
from mdt_agent_system.app.core.logging.logger import run_id_context
# Import the main simulation runner from the coordinator
from mdt_agent_system.app.agents.coordinator import run_mdt_simulation
from mdt_agent_system.app.core.samples.patient_case import get_sample_case

router = APIRouter()
logger = logging.getLogger(__name__)

# Placeholder function for the actual simulation logic
async def run_simulation_background(run_id: str, patient_case: PatientCase):
    """Runs the agent simulation in the background.
    Sets the run_id context for logging and calls the coordinator.
    """
    # Set the run_id in the context for this task's execution
    token = run_id_context.set(run_id)
    logger.info(f"Starting background simulation.") # run_id should be logged automatically now
    status_service = get_status_service() # Get the singleton instance

    try:
        # === Call the actual MDT simulation coordinator ===
        await run_mdt_simulation(
            run_id=run_id,
            patient_case=patient_case,
            status_service=status_service
        )
        # The coordinator now handles its own start/end/error status updates.
        logger.info(f"Background simulation finished successfully for run_id: {run_id}")

    except Exception as e:
        # The coordinator already logs the exception and emits an ERROR status.
        # This block catches potential errors *outside* the coordinator's main try/except
        # or if the coordinator re-raises an exception.
        logger.error(f"Unhandled exception caught in background task runner for run_id: {run_id}: {e}", exc_info=True)
        # Ensure an error status is emitted if the coordinator failed to do so
        try:
            await status_service.emit_status_update(
                run_id=run_id,
                status_update_data={ # Pass data as dict
                    "agent_id": "System",
                    "status": "ERROR",
                    "message": f"Simulation task failed unexpectedly: {str(e)}"
                }
            )
        except Exception as status_err:
            logger.error(f"Failed to emit final error status for run_id {run_id}: {status_err}", exc_info=True)

    finally:
        # --- Cleanup --- 
        # Clear run-specific data from status service
        try:
            await status_service.clear_run_data(run_id)
            logger.info(f"Cleared run data.") # run_id should be logged
        except Exception as cleanup_err:
             logger.error(f"Failed to clear run data for run_id {run_id}: {cleanup_err}", exc_info=True)
        finally:
             # Reset the context variable to its previous state regardless of cleanup success
            run_id_context.reset(token)


@router.post("/simulate", tags=["Simulation"], status_code=status.HTTP_202_ACCEPTED)
async def simulate_mdt(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    status_service: StatusUpdateService = Depends(get_status_service)
):
    """
    Endpoint to start the MDT simulation process.
    Accepts a JSON file representing the PatientCase.
    Validates the input and returns a run_id for tracking the simulation.
    Starts the simulation as a background task.
    """
    run_id = str(uuid.uuid4())
    logger.info(f"Received simulation request. Generated run_id: {run_id}")

    if file.content_type != "application/json":
        logger.error(f"Invalid file type received: {file.content_type}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type. Only JSON is accepted.")

    try:
        contents = await file.read()
        file_data = json.loads(contents)
        patient_case = PatientCase(**file_data)
        logger.info(f"PatientCase validated successfully for run_id: {run_id}")
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON for run_id: {run_id}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON file.")
    except ValidationError as e:
        logger.error(f"PatientCase validation failed for run_id: {run_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"PatientCase validation failed: {e.errors()}",
        )
    except Exception as e:
        logger.exception(f"An unexpected error occurred during file processing for run_id: {run_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during file processing.")
    finally:
        await file.close()

    # Start the simulation in the background
    background_tasks.add_task(run_simulation_background, run_id, patient_case)
    logger.info(f"Simulation background task added for run_id: {run_id}")

    # Emit initial status update
    try:
        # Pass data as dict to the modified emit_status_update
        await status_service.emit_status_update(
            run_id=run_id,
            status_update_data={ # Pass data as dict
                "agent_id": "API",
                "status": "ACTIVE", # Changed from RECEIVED
                "message": "Simulation request received and validated."
            }
        )
        logger.info(f"Emitted initial ACTIVE status for run_id: {run_id}")
    except Exception as e:
        # Log error but don't fail the request if status emission fails initially
        logger.error(f"Failed to emit initial status update for run_id {run_id}: {e}", exc_info=True)

    return {"run_id": run_id, "message": "Simulation request accepted and is being processed."}


@router.get("/status/{run_id}/stream")
async def stream_status(
    run_id: str,
    request: Request,
    last_event_id: Optional[str] = Header(None),
    status_service: StatusUpdateService = Depends(get_status_service)
) -> EventSourceResponse:
    """Stream status updates for a specific run using Server-Sent Events (SSE)."""
    logger.info(f"Starting SSE stream for run_id {run_id}, last_event_id: {last_event_id}")
    logger.debug(f"Request headers: {dict(request.headers)}")
    
    # Log client info
    client_host = request.client.host if request.client else "unknown"
    logger.info(f"Client connected from: {client_host}")

    async def event_generator():
        try:
            logger.debug(f"Starting event generator for run_id: {run_id}")
            async for update in status_service.subscribe(run_id, last_event_id):
                logger.debug(f"Generated event for run_id {run_id}: {update}")
                event_data = {
                    "agent_id": update.agent_id,
                    "status": update.status,
                    "message": update.message,
                    "timestamp": update.timestamp.isoformat(),
                    "details": update.details,
                    "run_id": update.run_id,
                    "event_id": update.event_id
                }
                yield {
                    "event": "status_update",
                    "id": str(update.event_id),
                    "data": json.dumps(event_data)
                }
        except asyncio.CancelledError:
            logger.info(f"SSE connection cancelled for run_id: {run_id}")
            raise
        except Exception as e:
            logger.error(f"Error in SSE stream for run_id {run_id}: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": str(e),
                    "run_id": run_id
                })
            }
        finally:
            logger.info(f"SSE connection closed for run_id: {run_id}")

    return EventSourceResponse(
        event_generator(),
        ping=15,  # Send ping every 15 seconds
        ping_message_factory=lambda: {"event": "ping", "data": ""}
    )


# --- Observability Endpoints ---

# Assume logs are written to LOGS_DIR/app.log as structured JSON lines
# Correct usage of settings
LOG_FILE_PATH = os.path.join(settings.LOG_DIR, "app.log")

@router.get("/logs/{run_id}", tags=["Observability"], response_model=List[str])
async def get_logs(run_id: str):
    """
    Endpoint to retrieve logs for a specific simulation run.
    Reads the application log file and filters lines containing the run_id.
    NOTE: Assumes structured JSON logging with a 'run_id' field.
    NOTE: This is inefficient for large log files; consider dedicated logging solutions.
    """
    logger.info(f"Log retrieval request for run_id: {run_id}")
    run_logs = []
    try:
        # Ensure log file exists before trying to open
        if not os.path.exists(LOG_FILE_PATH):
            logger.warning(f"Log file not found at: {LOG_FILE_PATH}")
            return [] # Return empty list if log file doesn't exist

        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                # Basic check: see if run_id appears in the line
                # A more robust check would parse JSON and check the field
                if f'"{run_id}"' in line or f'"{run_id}"' in line: # Check quoted run_id
                    try:
                         # Optional: Try parsing to verify it's valid JSON and contains the run_id field
                         log_entry = json.loads(line.strip())
                         if log_entry.get("run_id") == run_id:
                              run_logs.append(line.strip())
                         elif f'"run_id": "{run_id}"' in line: # Fallback for simple string check if parsing fails or run_id not top-level
                             run_logs.append(line.strip())
                    except json.JSONDecodeError:
                        # If line isn't valid JSON but contains the run_id string, maybe still include it?
                        if f'"{run_id}"' in line:
                           logger.debug(f"Including non-JSON log line containing run_id {run_id}")
                           run_logs.append(line.strip()) # Include potentially non-JSON lines if they contain the ID string

    except Exception as e:
        logger.error(f"Failed to read logs for run_id {run_id} from {LOG_FILE_PATH}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve logs.")

    logger.info(f"Retrieved {len(run_logs)} log entries for run_id: {run_id}")
    return run_logs

@router.get("/state/{run_id}/{agent_id}", tags=["Observability"], response_model=List[str])
async def get_agent_state(run_id: str, agent_id: str):
    """
    Endpoint to inspect the logged state/activity of a specific agent during a run.
    Filters logs for entries containing both the run_id and agent_id.
    NOTE: Relies on logging agent state changes effectively.
    NOTE: Inefficient for large log files.
    """
    logger.info(f"Agent state log retrieval request for run_id: {run_id}, agent_id: {agent_id}")
    agent_logs = []
    try:
         # Ensure log file exists before trying to open
        if not os.path.exists(LOG_FILE_PATH):
            logger.warning(f"Log file not found at: {LOG_FILE_PATH}")
            return [] # Return empty list if log file doesn't exist

        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                # Basic check: see if both run_id and agent_id appear
                 # Check quoted strings to avoid partial matches
                run_id_str = f'"{run_id}"'
                agent_id_str = f'"{agent_id}"'
                if run_id_str in line and agent_id_str in line:
                    try:
                        # Optional: Parse JSON for more precise check
                         log_entry = json.loads(line.strip())
                         if log_entry.get("run_id") == run_id and log_entry.get("agent_id") == agent_id:
                             agent_logs.append(line.strip())
                         # Fallback check if parsing fails or fields not top-level
                         elif f'"run_id": "{run_id}"' in line and f'"agent_id": "{agent_id}"' in line:
                             agent_logs.append(line.strip())
                    except json.JSONDecodeError:
                         # Include non-JSON line if it contains both ID strings
                         if run_id_str in line and agent_id_str in line:
                             logger.debug(f"Including non-JSON log line containing run_id {run_id} and agent_id {agent_id}")
                             agent_logs.append(line.strip())

    except Exception as e:
        logger.error(f"Failed to read agent state logs for run_id {run_id}, agent_id {agent_id} from {LOG_FILE_PATH}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve agent state logs.")

    logger.info(f"Retrieved {len(agent_logs)} log entries for run_id: {run_id}, agent_id: {agent_id}")
    return agent_logs

@router.get("/report/{run_id}", tags=["Simulation"], response_model=dict)
async def get_report(run_id: str):
    """
    Endpoint to retrieve the report for a given run_id directly (non-SSE).
    This is an alternative to using the SSE stream for clients that have issues with SSE.
    """
    logger.info(f"Direct report retrieval request for run_id: {run_id}")
    
    try:
        # First, check if the report file exists
        report_file_path = f"report_{run_id}.json"
        
        if os.path.exists(report_file_path):
            logger.info(f"Found report file for run_id: {run_id}")
            with open(report_file_path, "r") as file:
                report_data = json.load(file)
                return report_data
                
        # If file doesn't exist, check if we have any report in the status service
        status_service = get_status_service()
        if hasattr(status_service, "active_runs") and run_id in status_service.active_runs:
            for update in status_service.active_runs[run_id]:
                if update.status == "REPORT" and hasattr(update, "details") and update.details:
                    if isinstance(update.details, dict) and "report_data" in update.details:
                        logger.info(f"Found report in status updates for run_id: {run_id}")
                        return update.details["report_data"]
        
        # If all else fails, try to create a minimal report
        logger.warning(f"No report found for run_id: {run_id}, creating minimal report")
        return {
            "patient_id": run_id,
            "summary": "No report data available. The report may still be processing or failed to generate.",
            "timestamp": str(datetime.utcnow()),
            "error": "Report not found in storage or status service."
        }
    
    except Exception as e:
        logger.error(f"Error retrieving report for run_id {run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving report: {str(e)}"
        ) 