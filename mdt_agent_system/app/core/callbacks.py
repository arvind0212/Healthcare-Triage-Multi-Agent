import logging
from typing import Any, Dict, List
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)

class LoggingCallbackHandler(BaseCallbackHandler):
    """Callback Handler that logs LLM starts and ends."""

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *, 
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: List[str] | None = None,
        metadata: Dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Log the start of an LLM call."""
        logger.info(
            f"LLM Start (Run ID: {run_id})", 
            extra={
                "run_id": str(run_id),
                "parent_run_id": str(parent_run_id) if parent_run_id else None,
                "tags": tags,
                "metadata": metadata,
                "llm_prompts": prompts # Consider potential PII/length implications
            }
        )

    def on_llm_end(
        self,
        response: LLMResult,
        *, 
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Log the end of an LLM call."""
        # Extract token usage if available
        token_usage = response.llm_output.get('tokenUsage', {}) if response.llm_output else {}
        # Extract finish reason if available
        finish_reason = None
        if response.generations and response.generations[0]:
             gen_info = response.generations[0][0].generation_info
             finish_reason = gen_info.get('finish_reason', None) if gen_info else None

        logger.info(
            f"LLM End (Run ID: {run_id})", 
            extra={
                "run_id": str(run_id),
                "parent_run_id": str(parent_run_id) if parent_run_id else None,
                "llm_output": response.llm_output, # Contains model-specific output info
                "finish_reason": finish_reason,
                "token_usage_input": token_usage.get('promptTokenCount'),
                "token_usage_output": token_usage.get('candidatesTokenCount')
                # Avoid logging raw response generations by default due to size/PII
            }
        )

    def on_llm_error(
        self,
        error: Exception | KeyboardInterrupt,
        *, 
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Log an error during an LLM call."""
        logger.error(
            f"LLM Error (Run ID: {run_id}): {error}",
            exc_info=error, # Include stack trace
            extra={
                "run_id": str(run_id),
                "parent_run_id": str(parent_run_id) if parent_run_id else None,
            }
        ) 