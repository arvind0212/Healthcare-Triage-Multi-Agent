from typing import Dict, List, Optional, Any, AsyncIterator
from datetime import datetime
import asyncio
from mdt_agent_system.app.core.schemas.status import StatusUpdate
from mdt_agent_system.app.core.status.storage import JSONStore
from mdt_agent_system.app.core.logging.logger import get_logger
from mdt_agent_system.app.core.config.settings import settings
import os
import json

logger = get_logger(__name__)

class StatusUpdateService:
    """Service for handling agent status updates with persistence and SSE reconnection support."""
    
    def __init__(self, persistence_path: str):
        """Initialize the status update service. Loads existing data from persistence."""
        self.store = JSONStore(persistence_path) # Persistence for historical updates
        # In-memory cache: run_id -> list of StatusUpdate objects (ordered by event_id)
        self.active_runs: Dict[str, List[StatusUpdate]] = {}
        # In-memory counter for next event_id per run
        self.run_event_counters: Dict[str, int] = {}
        # Subscribers: run_id -> list of asyncio.Queues for live updates
        self.subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._load_from_persistence()

    def _load_from_persistence(self):
        """Load existing run data from the JSON store into memory."""
        try:
            all_data = self.store.get_all() # Assuming get_all loads the entire JSON content
            if isinstance(all_data, dict):
                for run_id, updates_data in all_data.items():
                    if isinstance(updates_data, list):
                        self.active_runs[run_id] = [StatusUpdate(**update) for update in updates_data]
                        # Set the counter based on the highest existing event_id for the run
                        if self.active_runs[run_id]:
                           self.run_event_counters[run_id] = max(u.event_id for u in self.active_runs[run_id]) + 1
                        else:
                           self.run_event_counters[run_id] = 0
                        logger.info(f"Loaded {len(self.active_runs[run_id])} status updates for run_id: {run_id}")
                    else:
                        logger.warning(f"Invalid data format for run_id {run_id} in persistence file.")
            else:
                 logger.info("Persistence file is empty or has invalid root structure. Starting fresh.")
        except FileNotFoundError:
            logger.info("Persistence file not found. Starting fresh.")
        except Exception as e:
            logger.error(f"Failed to load status updates from persistence: {e}", exc_info=True)

    def _get_next_event_id(self, run_id: str) -> int:
        """Get the next sequential event ID for a given run."""
        if run_id not in self.run_event_counters:
            self.run_event_counters[run_id] = 0
        event_id = self.run_event_counters[run_id]
        self.run_event_counters[run_id] += 1
        return event_id

    # Renamed from emit_status for clarity
    async def emit_status_update(self, run_id: str, status_update_data: Dict[str, Any]):
        """Generate event_id, create, store, persist, and notify status update."""
        event_id = self._get_next_event_id(run_id)
        try:
            # Create StatusUpdate object with the new event_id
            update = StatusUpdate(
                run_id=run_id,
                event_id=event_id,
                **status_update_data # Pass other fields like agent_id, status, message
            )
            # Store in memory cache
            if run_id not in self.active_runs:
                self.active_runs[run_id] = []
            self.active_runs[run_id].append(update)

            # Persist the entire run's updates (can be optimized if needed)
            self._persist_run_updates(run_id)

            # Notify live subscribers
            await self._notify_subscribers(update)

            logger.info(f"Status update emitted: event_id={update.event_id}",
                       extra={"agent_id": update.agent_id,
                              "status": update.status,
                              "run_id": update.run_id})
        except Exception as e:
            logger.error(f"Failed to emit status update for run_id {run_id}: {e}", exc_info=True)
            # Rollback counter if emission failed? Consider implications.
            # self.run_event_counters[run_id] -= 1 # Be careful with concurrency if added

    async def emit_report(self, run_id: str, report_data: Dict[str, Any]):
        """Emit a report event to all subscribers for a given run.
        
        This differs from status updates as it uses the 'report' event type
        instead of 'status_update' to trigger the report display in the UI.
        
        Args:
            run_id: The run ID to emit the report for
            report_data: The report data to emit
        """
        print(f"===> SERVICE.EMIT_REPORT CALLED for run_id: {run_id}")
        try:
            # Ensure report_data is a proper dictionary
            if not isinstance(report_data, dict):
                print(f"===> WARNING: report_data is not a dict but {type(report_data)}. Attempting to convert.")
                try:
                    # Try to convert to dict if it's a Pydantic model
                    if hasattr(report_data, 'dict'):
                        report_data = report_data.dict()
                        print("===> Converted using .dict() method")
                    elif hasattr(report_data, 'model_dump'):
                        report_data = report_data.model_dump()
                        print("===> Converted using .model_dump() method")
                    elif hasattr(report_data, '__dict__'):
                        report_data = report_data.__dict__
                        print("===> Converted using .__dict__ attribute")
                    else:
                        # Last resort: convert to string and back to dict
                        report_data = json.loads(json.dumps(report_data, default=str))
                        print("===> Converted using json dumps/loads")
                except Exception as conv_error:
                    print(f"===> ERROR CONVERTING REPORT DATA: {conv_error}")
                    # Create a minimal valid report
                    report_data = {
                        "patient_id": str(getattr(report_data, "patient_id", "unknown")),
                        "summary": "Report conversion error",
                        "timestamp": str(datetime.utcnow()),
                        "error": str(conv_error),
                        "original_type": str(type(report_data))
                    }
            
            # Convert any datetime objects to strings in the report data
            def convert_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return obj
            
            report_data = json.loads(json.dumps(report_data, default=convert_datetime))
            
            # Create a special status update for the report using a valid status
            event_id = self._get_next_event_id(run_id)
            update = StatusUpdate(
                run_id=run_id,
                event_id=event_id,
                agent_id="Coordinator",
                status="DONE",  # Using valid status
                message="MDT Report Generated",
                timestamp=datetime.utcnow(),
                details={"report_data": report_data, "is_report": True}  # Flag to identify this as a report
            )
            
            print(f"===> CREATED REPORT STATUS UPDATE with event_id: {update.event_id}")
            
            # Store in memory cache
            if run_id not in self.active_runs:
                self.active_runs[run_id] = []
            self.active_runs[run_id].append(update)
            
            # Persist updates
            self._persist_run_updates(run_id)
            
            # Notify live subscribers
            if run_id in self.subscribers:
                print(f"===> RUN_ID {run_id} HAS {len(self.subscribers[run_id])} SUBSCRIBERS")
                tasks = []
                for queue in self.subscribers[run_id]:
                    tasks.append(queue.put(update))
                if tasks:
                    await asyncio.gather(*tasks)
                    print(f"===> SENT REPORT TO {len(tasks)} SUBSCRIBERS")
                else:
                    print("===> NO TASKS CREATED FOR SUBSCRIBERS")
            else:
                print(f"===> NO SUBSCRIBERS FOR RUN_ID: {run_id}")
                
            logger.info(f"Report emitted for run_id: {run_id}")
            
        except Exception as e:
            print(f"===> ERROR IN EMIT_REPORT: {e}")
            logger.error(f"Failed to emit report for run_id {run_id}: {e}", exc_info=True)
            
            # Try emergency fallback with valid status
            try:
                print("===> TRYING EMERGENCY REPORT FALLBACK")
                minimal_report = {
                    "patient_id": "emergency",
                    "summary": "Error generating proper report. Check logs.",
                    "timestamp": str(datetime.utcnow()),
                    "error": str(e)
                }
                
                fallback_event_id = self._get_next_event_id(run_id)
                fallback_update = StatusUpdate(
                    run_id=run_id,
                    event_id=fallback_event_id,
                    agent_id="System",
                    status="DONE",  # Using valid status
                    message="Emergency Report Fallback",
                    timestamp=datetime.utcnow(),
                    details={"report_data": minimal_report, "is_report": True}
                )
                
                if run_id in self.subscribers:
                    for queue in self.subscribers[run_id]:
                        await queue.put(fallback_update)
                    print("===> EMERGENCY REPORT FALLBACK SENT")
            except Exception as fallback_error:
                print(f"===> EMERGENCY REPORT FALLBACK FAILED: {fallback_error}")

    def _persist_run_updates(self, run_id: str):
        """Persist all status updates for a specific run to the store."""
        if run_id in self.active_runs:
            updates_to_persist = [update.model_dump() for update in self.active_runs[run_id]]
            try:
                 # Assuming store.save handles overwriting the data for the key run_id
                 self.store.save(run_id, updates_to_persist)
            except Exception as e:
                 logger.error(f"Failed to persist updates for run_id {run_id}: {e}", exc_info=True)

    # Modified to support last_event_id
    def get_run_updates(self, run_id: str, last_event_id: Optional[str] = None) -> List[StatusUpdate]:
        """Get status updates for a specific run, optionally filtering by last_event_id.

        Args:
            run_id: The run ID to get updates for.
            last_event_id: The last event ID received by the client (for SSE reconnection).

        Returns:
            List of status updates for the run, filtered if last_event_id is provided.
        """
        updates = self.active_runs.get(run_id, [])

        if last_event_id is not None:
            try:
                last_id = int(last_event_id)
                # Return updates with event_id strictly greater than last_id
                return [update for update in updates if update.event_id > last_id]
            except ValueError:
                logger.warning(f"Invalid last_event_id format '{last_event_id}' for run_id {run_id}. Returning all updates.")
                return updates # Or potentially raise an error? Returning all is safer for client.
        else:
            # Return all updates if no last_event_id
            return updates

    # Modified to use get_run_updates with last_event_id
    async def subscribe(self, run_id: str, last_event_id: Optional[str] = None) -> AsyncIterator[StatusUpdate]:
        """Subscribe to status updates for a specific run, supporting reconnection."""
        if run_id not in self.subscribers:
            self.subscribers[run_id] = []

        queue: asyncio.Queue[StatusUpdate] = asyncio.Queue()
        self.subscribers[run_id].append(queue)
        logger.info(f"New subscriber added for run_id: {run_id}. Total subscribers: {len(self.subscribers[run_id])}")

        try:
            # Send historical updates if requested
            if last_event_id is not None:
                try:
                    last_id = int(last_event_id)
                    missed_updates = [update for update in self.active_runs.get(run_id, []) if update.event_id > last_id]
                    for update in missed_updates:
                        await queue.put(update)
                except ValueError:
                    logger.warning(f"Invalid last_event_id format: {last_event_id}")

            # Yield updates from the queue
            while True:
                try:
                    update = await queue.get()
                    yield update
                    queue.task_done()
                except asyncio.CancelledError:
                    logger.info(f"Subscription cancelled for run_id: {run_id}")
                    break
                except Exception as e:
                    logger.error(f"Error processing update for run_id {run_id}: {e}")
                    break

        finally:
            # Clean up subscription
            if run_id in self.subscribers:
                try:
                    self.subscribers[run_id].remove(queue)
                    if not self.subscribers[run_id]:
                        del self.subscribers[run_id]
                    logger.info(f"Subscriber removed for run_id: {run_id}. Remaining subscribers: {len(self.subscribers.get(run_id, []))}")
                except ValueError:
                    pass  # Queue might have been removed already

    async def _notify_subscribers(self, update: StatusUpdate):
        """Notify live subscribers of a new status update."""
        if update.run_id in self.subscribers:
            # Create tasks to put items in queues concurrently
            tasks = [queue.put(update) for queue in self.subscribers[update.run_id]]
            if tasks:
                await asyncio.gather(*tasks) # Wait for all queues to receive the update

    # Renamed from clear_run for clarity and added clearing of counters/subscribers
    def clear_run_data(self, run_id: str):
        """Clear all data associated with a specific run (memory, persistence, counters, subscribers)."""
        logger.info(f"Clearing data for run_id: {run_id}")
        # Clear memory cache
        if run_id in self.active_runs:
            del self.active_runs[run_id]
        # Clear event counter
        if run_id in self.run_event_counters:
            del self.run_event_counters[run_id]
        # Clear subscribers (prevent new subscriptions, allow existing to finish)
        # Existing subscribe tasks will clean themselves up in their finally block
        if run_id in self.subscribers:
             # We might want to gracefully close queues here if required
             # for queue in self.subscribers[run_id]:
             #     await queue.put(None) # Signal end, depends on subscriber logic
             del self.subscribers[run_id]
        # Clear from persistence
        try:
            self.store.delete(run_id) # Assuming delete removes the key run_id
            logger.info(f"Cleared persisted status updates for run_id: {run_id}")
        except Exception as e:
             logger.error(f"Failed to clear persisted status updates for run_id {run_id}: {e}", exc_info=True)

    def emit_status(self, update: StatusUpdate) -> None:
        """Synchronously emit a status update for compatibility with existing tests."""
        # Assign next event ID
        event_id = self._get_next_event_id(update.run_id)
        update.event_id = event_id
        # Store in memory cache
        if update.run_id not in self.active_runs:
            self.active_runs[update.run_id] = []
        self.active_runs[update.run_id].append(update)
        # Persist updates
        self._persist_run_updates(update.run_id)
        # Notify live subscribers asynchronously
        try:
            asyncio.create_task(self._notify_subscribers(update))
        except RuntimeError:
            # If no running event loop, skip notifying
            pass

    def clear_run(self, run_id: str) -> None:
        """Alias for clear_run_data to satisfy test name clear_run."""
        self.clear_run_data(run_id)

# Singleton instance management remains the same
_status_service: Optional[StatusUpdateService] = None

def get_status_service() -> StatusUpdateService:
    """Get or create the singleton StatusUpdateService instance."""
    global _status_service
    if _status_service is None:
        settings_obj = settings # Use the imported settings object directly
        # Use a more descriptive path if possible, e.g., dedicated status dir
        # Ensure MEMORY_DIR exists in settings.py
        memory_dir = getattr(settings_obj, 'MEMORY_DIR', 'memory_data') # Default if not set
        persistence_file_path = f"{memory_dir}/status_updates.json"
        # Ensure the directory exists
        os.makedirs(memory_dir, exist_ok=True)
        _status_service = StatusUpdateService(persistence_file_path)
        logger.info(f"StatusUpdateService initialized with persistence path: {persistence_file_path}")
    return _status_service

# Helper for API endpoint signature (if needed, or pass the dict directly)
# async def emit_status(run_id: str, status_update_data: Dict[str, Any], status_service: StatusUpdateService = Depends(get_status_service)):
#    await status_service.emit_status_update(run_id, status_update_data) 