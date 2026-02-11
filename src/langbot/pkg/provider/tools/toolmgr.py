from typing import Dict, List, Optional
from .loaders.skill import SkillLoader
from .entities import LLMTool
from .registry import SkillRegistry
from .mcp_registry import MCPRegistry
from .loaders.mcp import MCPLoader

class ToolManager:
    def __init__(self, skill_registry: SkillRegistry, mcp_registry: MCPRegistry):
        self.skill_loader = SkillLoader()
        self.mcp_loader = MCPLoader()
        self.skill_registry = skill_registry
        self.mcp_registry = mcp_registry

    def load_skills_from_definition(self, definition: str):
        skills = self.skill_loader.load_skills_from_definition(definition)
        for skill in skills:
            self.skill_registry.register_skill(skill)

    def get_tool(self, name: str) -> Optional[LLMTool]:
        tool = self.skill_registry.get_skill(name)
        if tool is None:
            tool = self.mcp_registry.get_tool(name)
        return tool

    def get_all_tools(self) -> List[LLMTool]:
        skills = self.skill_registry.get_all_skills()
        mcp_tools = self.mcp_registry.get_all_tools()
        return skills + mcp_tools

    def load_mcp_tools_from_server(self, server_url: str):
        self.mcp_registry.load_tools_from_server(server_url)
