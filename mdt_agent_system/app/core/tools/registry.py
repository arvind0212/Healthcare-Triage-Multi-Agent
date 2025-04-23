from typing import Dict, List, Type
from .base import MDTTool
from .medical import PharmacologyReferenceTool, GuidelineReferenceTool

class ToolRegistry:
    """Registry for managing and accessing MDT tools."""
    
    # Class-level registry
    _tools: Dict[str, MDTTool] = {}
    
    @classmethod
    def _register_default_tools(cls):
        """Register the default set of tools."""
        if not cls._tools:  # Only register defaults if the registry is empty
            default_tools = [
                PharmacologyReferenceTool(),
                GuidelineReferenceTool()
            ]
            for tool in default_tools:
                cls.register_tool(tool)
    
    @classmethod
    def register_tool(cls, tool: MDTTool) -> None:
        """Register a new tool."""
        if not isinstance(tool, MDTTool):
            raise ValueError(f"Tool must be an instance of MDTTool, got {type(tool)}")
        
        if tool.name in cls._tools:
            raise ValueError(f"Tool with name '{tool.name}' is already registered")
        
        cls._tools[tool.name] = tool
    
    @classmethod
    def get_tool(cls, name: str) -> MDTTool:
        """Get a tool by name."""
        # Ensure defaults are registered
        cls._register_default_tools()
        
        if name not in cls._tools:
            raise KeyError(f"Tool '{name}' not found in registry")
        return cls._tools[name]
    
    @classmethod
    def list_tools(cls) -> List[str]:
        """List all registered tool names."""
        # Ensure defaults are registered
        cls._register_default_tools()
        
        return list(cls._tools.keys())
    
    @classmethod
    def get_tool_descriptions(cls) -> Dict[str, str]:
        """Get descriptions of all registered tools."""
        # Ensure defaults are registered
        cls._register_default_tools()
        
        return {name: tool.description for name, tool in cls._tools.items()}
    
    @classmethod
    def __len__(cls) -> int:
        # Ensure defaults are registered
        cls._register_default_tools()
        
        return len(cls._tools) 