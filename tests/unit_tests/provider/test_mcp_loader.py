import pytest
import requests
from unittest.mock import patch, MagicMock
from src.langbot.pkg.provider.tools.loaders.mcp import MCPLoader
from src.langbot.pkg.provider.tools.entities import LLMTool

@pytest.fixture
def mcp_loader():
    return MCPLoader()

@patch('requests.get')
def test_load_tools_from_valid_server(mock_get, mcp_loader):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "name": "get_stock_price",
            "description": "Get the current price of a stock.",
            "parameters": {
                "symbol": {
                    "type": "string",
                    "description": "The stock symbol, e.g., AAPL"
                }
            }
        },
        {
            "name": "lookup_domain",
            "description": "Look up information about a domain.",
            "parameters": {
                "domain_name": {
                    "type": "string",
                    "description": "The domain name to look up."
                }
            }
        }
    ]
    mock_get.return_value = mock_response

    tools = mcp_loader.load_tools_from_server("http://fake-mcp-server.com")
    
    assert len(tools) == 2
    assert isinstance(tools[0], LLMTool)
    assert tools[0].name == "get_stock_price"
    assert "symbol" in tools[0].parameters

@patch('requests.get')
def test_load_tools_from_server_with_request_exception(mock_get, mcp_loader):
    mock_get.side_effect = requests.exceptions.RequestException("Connection error")
    
    tools = mcp_loader.load_tools_from_server("http://fake-mcp-server.com")
    
    assert len(tools) == 0

@patch('requests.get')
def test_load_tools_from_server_with_bad_status_code(mock_get, mcp_loader):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Server error")
    mock_get.return_value = mock_response
    
    tools = mcp_loader.load_tools_from_server("http://fake-mcp-server.com")
    
    assert len(tools) == 0

@patch('requests.get')
def test_load_tools_from_server_with_invalid_json(mock_get, mcp_loader):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_get.return_value = mock_response
    
    tools = mcp_loader.load_tools_from_server("http://fake-mcp-server.com")
    
    assert len(tools) == 0

def test_parse_mcp_tool_with_missing_fields(mcp_loader):
    tool_def = {"name": "test_tool"}  # Missing description
    tool = mcp_loader._parse_mcp_tool(tool_def)
    assert tool is not None
    assert tool.name == "test_tool"
    assert tool.description is None
