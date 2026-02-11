import pytest
from src.langbot.pkg.provider.tools.loaders.skill import SkillLoader
from src.langbot.pkg.provider.tools.entities import LLMTool

@pytest.fixture
def skill_loader():
    return SkillLoader()

def test_load_skills_from_valid_definition(skill_loader):
    xml_definition = """
    <tools>
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
        <tool>
            <name>send_email</name>
            <description>Sends an email.</description>
            <parameters>
                <parameter>
                    <name>recipient</name>
                    <type>string</type>
                    <description>The email address of the recipient.</description>
                </parameter>
                <parameter>
                    <name>subject</name>
                    <type>string</type>
                    <description>The subject of the email.</description>
                </parameter>
                <parameter>
                    <name>body</name>
                    <type>string</type>
                    <description>The body of the email.</description>
                </parameter>
            </parameters>
        </tool>
    </tools>
    """
    skills = skill_loader.load_skills_from_definition(xml_definition)
    assert len(skills) == 2
    
    weather_skill = skills[0]
    assert isinstance(weather_skill, LLMTool)
    assert weather_skill.name == "get_weather"
    assert weather_skill.description == "Get the current weather for a location."
    assert "location" in weather_skill.parameters
    assert weather_skill.parameters["location"]["type"] == "string"

    email_skill = skills[1]
    assert isinstance(email_skill, LLMTool)
    assert email_skill.name == "send_email"
    assert "recipient" in email_skill.parameters
    assert "subject" in email_skill.parameters
    assert "body" in email_skill.parameters

def test_load_skills_from_invalid_xml(skill_loader):
    xml_definition = "<tools><tool><name>test</name></tool"  # Malformed XML
    skills = skill_loader.load_skills_from_definition(xml_definition)
    assert len(skills) == 0

def test_load_skills_from_empty_definition(skill_loader):
    skills = skill_loader.load_skills_from_definition("")
    assert len(skills) == 0

def test_load_skills_with_missing_fields(skill_loader):
    xml_definition = """
    <tools>
        <tool>
            <name>get_weather</name>
        </tool>
        <tool>
            <description>This one is missing a name.</description>
        </tool>
    </tools>
    """
    skills = skill_loader.load_skills_from_definition(xml_definition)
    assert len(skills) == 1
    assert skills[0].name == "get_weather"
    assert skills[0].description is None
