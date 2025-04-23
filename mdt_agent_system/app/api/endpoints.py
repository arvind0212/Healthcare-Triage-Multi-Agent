from fastapi import APIRouter, UploadFile, File, Depends, Request
from fastapi import HTTPException, BackgroundTasks, status
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse, ServerSentEvent
from pydantic import ValidationError
import uuid
import json
import logging
import asyncio # Added for sleep in SSE stream
import os # For log file path
from typing import List

from mdt_agent_system.app.core.schemas.common import PatientCase, StatusUpdate
# Import the actual status service instance getter
from mdt_agent_system.app.core.status.service import StatusUpdateService, get_status_service
# Correct config import
from mdt_agent_system.app.core.config.settings import settings
# Import the context variable
from mdt_agent_system.app.core.logging.logger import run_id_context
# Import the main simulation runner from the coordinator
from mdt_agent_system.app.agents.coordinator import run_mdt_simulation

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


async def sse_generator(run_id: str, request: Request, status_service: StatusUpdateService):
    """Async generator for sending StatusUpdates via SSE, supports reconnection."""
    # Read Last-Event-ID header sent by the client
    last_event_id = request.headers.get("last-event-id")
    logger.info(f"SSE connection request for run_id: {run_id}. Last-Event-ID: {last_event_id}")

    # Use a queue to decouple subscription from sending
    queue = asyncio.Queue()
    # Use an event to signal when the subscriber task has finished
    subscriber_finished_event = asyncio.Event()

    async def _subscribe_and_queue():
        """Task to subscribe to status updates and put them in the queue."""
        try:
            # Subscribe using the modified service method, passing last_event_id
            async for update in status_service.subscribe(run_id, last_event_id):
                if await request.is_disconnected():
                    logger.info(f"SSE client disconnected during subscription for run_id: {run_id}. Stopping.")
                    break
                await queue.put(update)
        except asyncio.CancelledError:
            logger.info(f"SSE subscription task cancelled for run_id: {run_id}")
        except Exception as e:
            logger.error(f"Error in SSE subscription task for run_id {run_id}: {e}", exc_info=True)
            # Optionally put an error indicator in the queue or handle differently
            await queue.put(None) # Signal error/end
        finally:
            logger.info(f"SSE subscription ended for run_id: {run_id}")
            await queue.put(None) # Signal the consumer loop to stop
            subscriber_finished_event.set() # Signal that the subscriber task is done

    subscription_task = asyncio.create_task(_subscribe_and_queue())
    ping_interval = 15 # Send a ping every 15 seconds

    try:
        while True:
            if await request.is_disconnected():
                logger.info(f"SSE client disconnected in main generator loop for run_id: {run_id}. Breaking loop.")
                break

            try:
                # Wait for an update from the queue or timeout for ping
                update = await asyncio.wait_for(queue.get(), timeout=ping_interval)

                if update is None: # End of stream signal from subscriber task
                    logger.info(f"Received None signal in SSE generator for run_id: {run_id}. Ending stream.")
                    break

                if await request.is_disconnected():
                    logger.info(f"SSE client disconnected before sending event_id {update.event_id} for run_id: {run_id}. Breaking loop.")
                    break

                # Use model_dump_json for Pydantic v2
                event_data = update.model_dump_json()
                # Create ServerSentEvent with the sequential event_id from the update
                sse_event = ServerSentEvent(
                    data=event_data,
                    event="status_update",
                    id=str(update.event_id) # Set the ID for reconnection
                )
                yield sse_event
                queue.task_done() # Mark item as processed

            except asyncio.TimeoutError:
                # Send a keep-alive ping
                if await request.is_disconnected():
                    logger.info(f"SSE client disconnected during ping check for run_id: {run_id}. Breaking loop.")
                    break
                yield ServerSentEvent(data="ping", event="ping")
                logger.debug(f"Sent keep-alive ping for run_id: {run_id}")

            except Exception as e:
                logger.error(f"Error in SSE generator loop for run_id {run_id}: {e}", exc_info=True)
                if not await request.is_disconnected():
                    yield ServerSentEvent(data=json.dumps({"error": "Internal server error during stream."}), event="error")
                break # Stop streaming on unexpected error

    except asyncio.CancelledError:
        logger.info(f"SSE generator task cancelled by server/client for run_id: {run_id}")
    finally:
        logger.info(f"Cleaning up SSE generator for run_id: {run_id}")
        # Ensure the subscription task is cancelled if the generator exits prematurely
        if not subscription_task.done():
            logger.info(f"Cancelling subscription task for run_id: {run_id} from generator finally block.")
            subscription_task.cancel()
            # Wait for the subscriber task to finish its cleanup
            await subscriber_finished_event.wait()


@router.get("/stream/{run_id}", tags=["Simulation"], response_class=EventSourceResponse)
async def stream_status(
    run_id: str,
    request: Request, # Request is needed to check for disconnection
    status_service: StatusUpdateService = Depends(get_status_service)
):
    """
    Endpoint to stream simulation status updates using Server-Sent Events (SSE).
    """
    logger.info(f"SSE connection established for run_id: {run_id}")
    # EventSourceResponse handles the generator and headers
    return EventSourceResponse(sse_generator(run_id, request, status_service))


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