import pytest
from src.langbot.pkg.provider.tools.registry import SkillRegistry
from src.langbot.pkg.provider.tools.entities import LLMTool

@pytest.fixture
def skill_registry():
    return SkillRegistry()

@pytest.fixture
def sample_skill():
    return LLMTool(
        name="test_skill",
        description="A skill for testing.",
        parameters={"param1": {"type": "string"}}
    )

def test_register_skill(skill_registry, sample_skill):
    skill_registry.register_skill(sample_skill)
    assert skill_registry.get_skill("test_skill") == sample_skill

def test_get_nonexistent_skill(skill_registry):
    assert skill_registry.get_skill("nonexistent") is None

def test_get_all_skills(skill_registry, sample_skill):
    skill_registry.register_skill(sample_skill)
    
    another_skill = LLMTool(name="another_skill", description="Another one.")
    skill_registry.register_skill(another_skill)
    
    all_skills = skill_registry.get_all_skills()
    assert len(all_skills) == 2
    assert sample_skill in all_skills
    assert another_skill in all_skills

# Mocking requests for loading from registry
from unittest.mock import patch, MagicMock
import requests

@patch('requests.get')
def test_load_from_registry_success(mock_get, skill_registry):
    mock_xml = """
    <tools>
        <tool>
            <name>registry_skill</name>
            <description>Loaded from a registry.</description>
        </tool>
    </tools>
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = mock_xml
    mock_get.return_value = mock_response
    
    skill_registry.load_from_registry("http://fake-registry.com/skills.xml")
    
    loaded_skill = skill_registry.get_skill("registry_skill")
    assert loaded_skill is not None
    assert loaded_skill.name == "registry_skill"

@patch('requests.get')
def test_load_from_registry_http_error(mock_get, skill_registry):
    mock_get.side_effect = requests.exceptions.RequestException("Connection failed")
    
    skill_registry.load_from_registry("http://fake-registry.com/skills.xml")
    
    assert len(skill_registry.get_all_skills()) == 0
