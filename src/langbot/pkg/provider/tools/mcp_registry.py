from typing import Dict, List, Optional, Any
import requests

from .entities import LLMTool

class MCPRegistry:
    def __init__(self):
        self.servers: Dict[str, str] = {}  # name -> url
        self.tools: Dict[str, LLMTool] = {}

    def register_server(self, name: str, url: str):
        self.servers[name] = url

    def load_tools_from_all_servers(self):
        for name, url in self.servers.items():
            self.load_tools_from_server(url)

    def load_tools_from_server(self, server_url: str):
        try:
            response = requests.get(f"{server_url}/tools")
            response.raise_for_status()
            tool_definitions = response.json()
            
            for tool_def in tool_definitions:
                tool = self._parse_mcp_tool(tool_def)
                if tool:
                    self.tools[tool.name] = tool
        except requests.RequestException as e:
            print(f"Error loading tools from MCP server {server_url}: {e}")
        except ValueError:
            print(f"Error parsing JSON from MCP server {server_url}")

    def _parse_mcp_tool(self, tool_def: Dict[str, Any]) -> Optional[LLMTool]:
        try:
            name = tool_def['name']
            description = tool_def['description']
            parameters = tool_def.get('parameters', {})
            
            return LLMTool(name=name, description=description, parameters=parameters)
        except KeyError as e:
            print(f"Missing required key in MCP tool definition: {e}")
            return None

    def get_tool(self, name: str) -> Optional[LLMTool]:
        return self.tools.get(name)

    def get_all_tools(self) -> List[LLMTool]:
        return list(self.tools.values())
