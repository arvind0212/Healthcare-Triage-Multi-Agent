from typing import Any, Dict, Optional
from langchain.tools import BaseTool
from pydantic import Field, BaseModel, ConfigDict

class MDTToolConfig(BaseModel):
    """Configuration for MDT tools."""
    max_retries: int = Field(default=3, description="Maximum number of retry attempts")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")

class MDTTool(BaseTool):
    """Base class for all MDT tools extending LangChain's BaseTool."""
    name: str = Field(..., description="The name of the tool")
    description: str = Field(..., description="A description of what the tool does")
    
    def __init__(self, **data: Any):
        super().__init__(**data)
        # Store config as a private attribute
        self.__dict__['_config'] = MDTToolConfig()
    
    @property
    def max_retries(self) -> int:
        """Get maximum number of retries."""
        return self._config.max_retries
    
    @property
    def retry_delay(self) -> float:
        """Get delay between retries."""
        return self._config.retry_delay
    
    def _handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle tool execution errors."""
        return {
            "status": "error",
            "error": str(error),
            "error_type": error.__class__.__name__
        }
    
    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the tool synchronously."""
        raise NotImplementedError("Tool must implement _run method")
    
    async def _arun(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the tool asynchronously."""
        # Default to synchronous execution
        return self._run(*args, **kwargs) 