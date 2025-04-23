from typing import Dict, List, Optional, Any, AsyncIterator
from datetime import datetime
import asyncio
from mdt_agent_system.app.core.schemas.status import StatusUpdate
from mdt_agent_system.app.core.status.storage import JSONStore
from mdt_agent_system.app.core.logging.logger import get_logger
from mdt_agent_system.app.core.config.settings import settings
import os

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
        logger.info(f"New subscriber added for run_id: {run_id}. Total: {len(self.subscribers[run_id])}")

        try:
            # Send historical updates missed by the client
            missed_updates = self.get_run_updates(run_id, last_event_id)
            if missed_updates:
                logger.info(f"Sending {len(missed_updates)} missed updates to subscriber for run_id: {run_id} (after event_id {last_event_id})")
                for update in missed_updates:
                    await queue.put(update)
            else:
                 logger.info(f"No missed updates for subscriber run_id: {run_id} (after event_id {last_event_id})")

            # Yield updates from the queue (both historical and live)
            while True:
                update = await queue.get()
                yield update
                queue.task_done() # Mark task as done for queue management
        except asyncio.CancelledError:
             logger.info(f"Subscription cancelled for run_id: {run_id}")
             raise # Re-raise CancelledError to ensure cleanup
        finally:
            # Clean up subscription
            logger.info(f"Removing subscriber for run_id: {run_id}")
            if run_id in self.subscribers:
                 try:
                    self.subscribers[run_id].remove(queue)
                    if not self.subscribers[run_id]:
                        del self.subscribers[run_id]
                        logger.info(f"Last subscriber removed for run_id: {run_id}. Removed run from subscribers dict.")
                 except ValueError:
                     logger.warning(f"Queue already removed for subscriber of run_id: {run_id}. This might happen during concurrent cleanup.")
            else:
                logger.warning(f"Run_id {run_id} not found in subscribers during cleanup. Might have been cleared already.")

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