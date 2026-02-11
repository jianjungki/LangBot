import requests
from typing import Dict, List, Optional

from .entities import LLMTool
from .loaders.skill import SkillLoader
class SkillRegistry:
    def __init__(self):
        self.skills: Dict[str, LLMTool] = {}
        self.skill_loader = SkillLoader()

    def register_skill(self, skill: LLMTool):
        self.skills[skill.name] = skill

    def get_skill(self, name: str) -> Optional[LLMTool]:
        return self.skills.get(name)

    def get_all_skills(self) -> List[LLMTool]:
        return list(self.skills.values())

    def load_from_registry(self, registry_url: str):
        try:
            response = requests.get(registry_url)
            response.raise_for_status()  # Raise an exception for bad status codes
            skills_definition = response.text
            
            # Assuming the registry returns a definition that can be loaded by SkillLoader
            new_skills = self.skill_loader.load_skills_from_definition(skills_definition)
            
            for skill in new_skills:
                self.register_skill(skill)
        except requests.RequestException as e:
            print(f"Error loading skills from registry {registry_url}: {e}")
