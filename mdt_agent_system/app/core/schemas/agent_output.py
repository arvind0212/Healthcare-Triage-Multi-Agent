from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class AgentOutput(BaseModel):
    """
    Structured output format for MDT agents that includes markdown content and metadata.
    
    Attributes:
        markdown_content: The main content in markdown format
        metadata: Additional structured data about the analysis
        legacy_output: Optional field to maintain backward compatibility
    """
    markdown_content: str = Field(..., description="Main content in markdown format")
    metadata: Dict[str, Any] = Field(
        ...,
        description="Structured metadata about the analysis"
    )
    legacy_output: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional legacy format output for backward compatibility"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "markdown_content": "# Clinical Assessment\n## Key Findings\n- Finding 1\n- Finding 2",
                "metadata": {
                    "key_findings": ["Finding 1", "Finding 2"],
                    "confidence_scores": {
                        "diagnosis": 0.95,
                        "recommendations": 0.85
                    }
                }
            }
        } 