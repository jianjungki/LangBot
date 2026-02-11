"""
This module implements the loader for Anthropic-style skills.
"""

from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET
from ..entities import LLMTool

class SkillLoader:
    """
    A loader for parsing and loading skills defined in the Anthropic format.
    """

    def __init__(self):
        pass

    def load_skills_from_definition(self, definition: str) -> List[LLMTool]:
        """
        Parses a skill definition string (e.g., XML or Markdown) and returns a list of LLMTool objects.
        
        This is a placeholder and needs to be implemented based on the actual skill format.
        """
        try:
            root = ET.fromstring(definition)
            skills = []
            for tool_node in root.findall('tool'):
                skill = self._parse_xml_skill(tool_node)
                if skill:
                    skills.append(skill)
            return skills
        except ET.ParseError:
            # Potentially handle other formats here later
            return []

    def _parse_xml_skill(self, tool_node) -> Optional[LLMTool]:
        """Parses a single tool from an XML node."""
        try:
            name_node = tool_node.find('name')
            if name_node is None or not name_node.text:
                return None
            name = name_node.text
            
            description_node = tool_node.find('description')
            description = description_node.text if description_node is not None else None
            
            parameters = {}
            parameters_node = tool_node.find('parameters')
            if parameters_node:
                for param_node in parameters_node.findall('parameter'):
                    param_name = param_node.find('name').text
                    param_type = param_node.find('type').text
                    param_description = param_node.find('description').text
                    parameters[param_name] = {
                        "type": param_type,
                        "description": param_description
                    }
            
            return LLMTool(name=name, description=description, parameters=parameters)
        except AttributeError:
            # Handle cases where expected tags are missing
            return None

# Example of how it might be used:
if __name__ == '__main__':
    skill_definition = """
    <tool>
        <name>get_weather</name>
        <description>Get the current weather for a location.</description>
        <parameters>
            <parameter>
                <name>location</name>
                <type>string</type>
                <description>The city and state, e.g., San Francisco, CA</description>
            </parameter>
        </parameters>
    </tool>
    """
    
    loader = SkillLoader()
    tools = loader.load_skills_from_definition(skill_definition)
    
    for tool in tools:
        print(f"Loaded tool: {tool.name}")
