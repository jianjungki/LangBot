import pytest
from unittest.mock import MagicMock
from src.langbot.pkg.provider.tools.toolmgr import ToolManager
from src.langbot.pkg.provider.tools.registry import SkillRegistry
from src.langbot.pkg.provider.tools.mcp_registry import MCPRegistry
from src.langbot.pkg.provider.tools.entities import LLMTool

@pytest.fixture
def mock_skill_registry():
    return MagicMock(spec=SkillRegistry)

@pytest.fixture
def mock_mcp_registry():
    return MagicMock(spec=MCPRegistry)

@pytest.fixture
def tool_manager(mock_skill_registry, mock_mcp_registry):
    tm = ToolManager(skill_registry=mock_skill_registry, mcp_registry=mock_mcp_registry)
    tm.skill_loader = MagicMock()
    return tm

def test_load_skills(tool_manager, mock_skill_registry):
    definition = "<tools></tools>"
    tool_manager.load_skills_from_definition(definition)
    # Since load_skills_from_definition returns a list, we can't directly check register_skill.
    # Instead, we can check that the loader was called.
    # A more thorough test would involve a mock loader returning mock skills.
    tool_manager.skill_loader.load_skills_from_definition.assert_called_once_with(definition)
    # We can't assert register_skill was called without more complex mocking,
    # as it's called on the result of another mock call.

def test_load_mcp_tools(tool_manager, mock_mcp_registry):
    server_url = "http://fake-mcp.com"
    tool_manager.load_mcp_tools_from_server(server_url)
    mock_mcp_registry.load_tools_from_server.assert_called_once_with(server_url)

def test_get_tool(tool_manager, mock_skill_registry, mock_mcp_registry):
    # Test getting a skill
    mock_skill_registry.get_skill.return_value = LLMTool(name="skill_tool", description="A skill")
    
    tool = tool_manager.get_tool("skill_tool")
    mock_skill_registry.get_skill.assert_called_once_with("skill_tool")
    assert tool is not None
    assert tool.name == "skill_tool"
    
    # Reset mock for the next call
    mock_skill_registry.reset_mock()

    # Test getting an MCP tool by returning None from skill_registry
    mock_skill_registry.get_skill.return_value = None
    mock_mcp_registry.get_tool.return_value = LLMTool(name="mcp_tool", description="An MCP tool")
    
    tool = tool_manager.get_tool("mcp_tool")
    mock_skill_registry.get_skill.assert_called_once_with("mcp_tool") # It will be called first
    mock_mcp_registry.get_tool.assert_called_once_with("mcp_tool")
    assert tool is not None
    assert tool.name == "mcp_tool"

    # Test getting a nonexistent tool
    mock_skill_registry.get_skill.return_value = None
    mock_mcp_registry.get_tool.return_value = None
    
    tool = tool_manager.get_tool("nonexistent")
    assert tool is None

def test_get_all_tools(tool_manager, mock_skill_registry, mock_mcp_registry):
    mock_skill_registry.get_all_skills.return_value = [LLMTool(name="skill1"), LLMTool(name="skill2")]
    mock_mcp_registry.get_all_tools.return_value = [LLMTool(name="mcp1")]
    
    all_tools = tool_manager.get_all_tools()
    
    assert len(all_tools) == 3
    assert "skill1" in [t.name for t in all_tools]
    assert "mcp1" in [t.name for t in all_tools]
