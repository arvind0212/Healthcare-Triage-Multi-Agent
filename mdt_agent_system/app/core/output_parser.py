import json
import logging
from typing import Optional, Dict, Any

from .schemas.agent_output import AgentOutput

logger = logging.getLogger(__name__)

class MDTOutputParser:
    """Parser for converting LLM outputs into structured AgentOutput format."""
    
    MARKDOWN_DELIMITER = "---MARKDOWN---"
    METADATA_DELIMITER = "---METADATA---"
    
    def __init__(self):
        """Initialize the MDT output parser."""
        pass
    
    def _extract_sections(self, llm_output: str) -> tuple[Optional[str], Optional[str]]:
        """
        Extract markdown and metadata sections from LLM output.
        
        Args:
            llm_output: Raw LLM output string
            
        Returns:
            Tuple of (markdown_content, metadata_json_str)
        """
        try:
            # Split on markdown section
            parts = llm_output.split(self.MARKDOWN_DELIMITER)
            if len(parts) != 2:
                logger.warning(f"Missing {self.MARKDOWN_DELIMITER} section")
                return llm_output, None
                
            # Split metadata section
            markdown_and_metadata = parts[1].split(self.METADATA_DELIMITER)
            if len(markdown_and_metadata) != 2:
                logger.warning(f"Missing {self.METADATA_DELIMITER} section")
                return markdown_and_metadata[0].strip(), None
                
            return markdown_and_metadata[0].strip(), markdown_and_metadata[1].strip()
            
        except Exception as e:
            logger.error(f"Error extracting sections: {str(e)}")
            return llm_output, None
    
    def _parse_metadata(self, metadata_str: Optional[str]) -> Dict[str, Any]:
        """
        Parse metadata JSON string into dictionary.
        
        Args:
            metadata_str: JSON string containing metadata
            
        Returns:
            Dictionary of metadata or empty dict if parsing fails
        """
        if not metadata_str:
            return {}
            
        try:
            return json.loads(metadata_str)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing metadata JSON: {str(e)}")
            return {}
    
    def parse_llm_output(self, llm_output: str, preserve_legacy: bool = True) -> AgentOutput:
        """
        Parse LLM output into structured AgentOutput format.
        
        Args:
            llm_output: Raw output string from LLM
            preserve_legacy: Whether to store original output in legacy_output field
            
        Returns:
            AgentOutput object containing parsed content
        """
        # Extract markdown and metadata sections
        markdown_content, metadata_str = self._extract_sections(llm_output)
        
        # Parse metadata
        metadata = self._parse_metadata(metadata_str)
        
        # Create AgentOutput
        return AgentOutput(
            markdown_content=markdown_content,
            metadata=metadata,
            legacy_output={"raw_output": llm_output} if preserve_legacy else None
        ) 