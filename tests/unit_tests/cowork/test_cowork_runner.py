import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from src.langbot.pkg.cowork.runner import CoworkRunner
from src.langbot.pkg.cowork.entities import WorkflowDefinition, AgentNode
from src.langbot.pkg.provider.tools.toolmgr import ToolManager
from src.langbot.pkg.provider.llm import LLMProvider
from src.langbot.pkg.provider.tools.entities import LLMTool

@pytest.fixture
def mock_tool_manager():
    return MagicMock(spec=ToolManager)

@pytest.fixture
def mock_llm_provider():
    provider = MagicMock(spec=LLMProvider)
    provider.generate = AsyncMock(return_value="Mocked LLM response")
    return provider

@pytest.fixture
def cowork_runner(mock_tool_manager, mock_llm_provider):
    return CoworkRunner(tool_manager=mock_tool_manager, llm_provider=mock_llm_provider)

@pytest.fixture
def sample_workflow():
    return WorkflowDefinition(
        name="test_workflow",
        description="A workflow for testing.",
        agents=[
            AgentNode(
                name="Supervisor",
                role="Orchestrator",
                system_prompt="You are a supervisor.",
                tool_names=["tool1"]
            ),
            AgentNode(
                name="Worker",
                role="Executor",
                system_prompt="You are a worker.",
                tool_names=["tool2"]
            )
        ],
        routing={"start": "Supervisor"}
    )

@pytest.mark.asyncio
async def test_run_workflow_starts_with_correct_agent(cowork_runner, sample_workflow, mock_llm_provider):
    await cowork_runner.run_workflow(sample_workflow, "Initial user input")
    
    # Check that the LLM was called with the supervisor's prompt
    mock_llm_provider.generate.assert_called_once()
    call_args, _ = mock_llm_provider.generate.call_args
    prompt = call_args[0]
    assert "You are a supervisor." in prompt
    assert "Initial user input" in prompt

@pytest.mark.asyncio
async def test_workflow_executes_agents_sequentially(cowork_runner, sample_workflow, mock_llm_provider):
    # Mock the generate function to return the input, simulating a pass-through
    async def echo_input(prompt, tools):
        # A bit of a hack to extract the user input from the prompt
        return prompt.split("User: ")[1].splitlines()[0]
    
    mock_llm_provider.generate = AsyncMock(side_effect=echo_input)
    
    final_result = await cowork_runner.run_workflow(sample_workflow, "Start")
    
    # Supervisor is called first, its output becomes worker's input
    # Worker is called second, its output is the final result
    assert mock_llm_provider.generate.call_count == 2
    assert final_result == "Start" # Because our mock LLM just echoes the input

@pytest.mark.asyncio
async def test_concurrent_agent_execution(cowork_runner, sample_workflow, mock_llm_provider):
    agents_to_run = sample_workflow.agents
    
    results = await cowork_runner._concurrently_execute_agents(agents_to_run, "Concurrent task")
    
    assert len(results) == 2
    assert mock_llm_provider.generate.call_count == 2
    # Both agents should have received the same initial input
    for call in mock_llm_provider.generate.call_args_list:
        prompt = call[0][0]
        assert "Concurrent task" in prompt
