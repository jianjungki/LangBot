import pytest
from unittest.mock import patch, MagicMock
from src.langbot.pkg.provider.tools.mcp_registry import MCPRegistry
from src.langbot.pkg.provider.tools.entities import LLMTool

@pytest.fixture
def mcp_registry():
    return MCPRegistry()

@pytest.fixture
def sample_mcp_tool():
    return LLMTool(
        name="mcp_tool",
        description="An MCP tool for testing.",
        parameters={"mcp_param": {"type": "integer"}}
    )

def test_register_server(mcp_registry):
    mcp_registry.register_server("test_server", "http://mcp.test")
    assert mcp_registry.servers["test_server"] == "http://mcp.test"

@patch('requests.get')
def test_load_tools_from_server(mock_get, mcp_registry):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "name": "tool1",
            "description": "First tool from server."
        }
    ]
    mock_get.return_value = mock_response
    
    mcp_registry.load_tools_from_server("http://mcp.test")
    
    assert "tool1" in mcp_registry.tools
    assert mcp_registry.get_tool("tool1").description == "First tool from server."

def test_get_and_get_all_tools(mcp_registry, sample_mcp_tool):
    mcp_registry.tools["mcp_tool"] = sample_mcp_tool
    
    assert mcp_registry.get_tool("mcp_tool") == sample_mcp_tool
    assert mcp_registry.get_tool("nonexistent") is None
    
    all_tools = mcp_registry.get_all_tools()
    assert len(all_tools) == 1
    assert sample_mcp_tool in all_tools
