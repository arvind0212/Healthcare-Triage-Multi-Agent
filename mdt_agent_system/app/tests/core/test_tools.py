import pytest
from mdt_agent_system.app.core.tools import (
    MDTTool,
    PharmacologyReferenceTool,
    GuidelineReferenceTool,
    ToolRegistry
)
from unittest.mock import MagicMock

def test_base_tool():
    """Test the base MDTTool class."""
    class TestTool(MDTTool):
        name = "test_tool"
        description = "A test tool"
        
        def _run(self, **kwargs):
            return {"status": "success"}
    
    tool = TestTool()
    assert tool.name == "test_tool"
    assert tool.description == "A test tool"
    # Test field defaults through properties
    assert tool.max_retries == 3
    assert tool.retry_delay == 1.0

def test_pharmacology_tool():
    """Test the PharmacologyReferenceTool."""
    tool = PharmacologyReferenceTool()
    
    # Test successful query
    result = tool._run("aspirin")
    assert result["status"] == "success"
    assert result["drug"] == "aspirin"
    assert "class" in result["data"]
    
    # Test not found
    result = tool._run("unknown_drug")
    assert result["status"] == "not_found"

def test_guideline_tool():
    """Test the GuidelineReferenceTool."""
    tool = GuidelineReferenceTool()
    
    # Test successful query
    result = tool._run("chest_pain")
    assert result["status"] == "success"
    assert result["condition"] == "chest_pain"
    assert "recommendations" in result["guidelines"]
    
    # Test not found
    result = tool._run("unknown_condition")
    assert result["status"] == "not_found"

def test_tool_registry():
    """Test the ToolRegistry."""
    # Reset registry for testing
    ToolRegistry._tools = {}
    
    # Register default tools
    ToolRegistry._register_default_tools()
    
    # Test default tools are registered
    assert len(ToolRegistry) > 0
    assert "pharmacology_reference" in ToolRegistry.list_tools()
    assert "guideline_reference" in ToolRegistry.list_tools()
    
    # Test getting tool
    tool = ToolRegistry.get_tool("pharmacology_reference")
    assert isinstance(tool, PharmacologyReferenceTool)
    
    # Test tool descriptions
    descriptions = ToolRegistry.get_tool_descriptions()
    assert isinstance(descriptions, dict)
    assert all(isinstance(desc, str) for desc in descriptions.values())
    
    # Test registering duplicate tool
    with pytest.raises(ValueError):
        ToolRegistry.register_tool(PharmacologyReferenceTool())
    
    # Test getting non-existent tool
    with pytest.raises(KeyError):
        ToolRegistry.get_tool("non_existent_tool")
    
    # Test registering invalid tool type
    with pytest.raises(ValueError):
        ToolRegistry.register_tool("not_a_tool") 