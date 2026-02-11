import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
import json
from langbot.pkg.provider.runners.cowork_runner import CoworkRunner
import langbot_plugin.api.entities.builtin.pipeline.query as pipeline_query
import langbot_plugin.api.entities.builtin.provider.message as provider_message
from langbot.pkg.core.sandbox import SandboxInstance

@pytest.fixture
def mock_sandbox():
    sandbox = AsyncMock(spec=SandboxInstance)
    sandbox.id = "test-sandbox-id"
    sandbox.execute_command.return_value = (0, "output", "")
    return sandbox

@pytest.fixture
def mock_app(mock_sandbox):
    app = Mock()
    app.logger = Mock()
    app.sandbox_mgr = AsyncMock()
    app.sandbox_mgr.create_sandbox.return_value = mock_sandbox
    app.sandbox_mgr.get_sandbox.return_value = mock_sandbox
    app.model_mgr = AsyncMock()
    return app

@pytest.fixture
def mock_llm_model():
    model = Mock()
    model.provider = AsyncMock()
    model.model_entity = Mock()
    model.model_entity.extra_args = {}
    return model

@pytest.mark.asyncio
async def test_cowork_runner_initialization(mock_app):
    runner = CoworkRunner(mock_app)
    assert runner.agents["supervisor"].name == "supervisor"
    assert runner.agents["coder"].name == "coder"

@pytest.mark.asyncio
async def test_get_sandbox(mock_app, mock_sandbox):
    runner = CoworkRunner(mock_app)
    session_id = "test-session"
    
    # Test creation
    sb = await runner._get_sandbox(session_id)
    assert sb == mock_sandbox
    assert runner.sandbox_map[session_id] == mock_sandbox.id
    mock_app.sandbox_mgr.create_sandbox.assert_called_once()
    
    # Test retrieval
    sb2 = await runner._get_sandbox(session_id)
    assert sb2 == mock_sandbox
    mock_app.sandbox_mgr.get_sandbox.assert_called_once_with(mock_sandbox.id)

@pytest.mark.asyncio
async def test_sandbox_tools(mock_app, mock_sandbox):
    runner = CoworkRunner(mock_app)
    tools = runner._get_sandbox_tools(mock_sandbox)
    
    assert len(tools) == 3
    tool_names = [t.name for t in tools]
    assert "write_file" in tool_names
    assert "read_file" in tool_names
    assert "exec_command" in tool_names
    
    # Test exec_command tool
    exec_tool = next(t for t in tools if t.name == "exec_command")
    res = await exec_tool.func(command="echo hello")
    assert "Exit Code: 0" in res
    assert "Stdout: output" in res
    mock_sandbox.execute_command.assert_called_with("echo hello")

@pytest.mark.asyncio
async def test_run_agent_loop(mock_app, mock_sandbox, mock_llm_model):
    runner = CoworkRunner(mock_app)
    mock_app.model_mgr.get_model_by_uuid.return_value = mock_llm_model
    
    query = Mock(spec=pipeline_query.Query)
    query.use_llm_model_uuid = "test-model"
    
    agent = runner.agents["coder"]
    
    # Mock LLM response with tool call
    tool_call_msg = provider_message.Message(role="assistant", content="")
    tool_call_msg.tool_calls = [
        Mock(
            id="call_1",
            function=Mock(
                name="exec_command",
                arguments=json.dumps({"command": "ls"})
            )
        )
    ]
    
    final_msg = provider_message.Message(role="assistant", content="Done")
    
    # First call returns tool call, second call returns final message
    mock_llm_model.provider.invoke_llm.side_effect = [tool_call_msg, final_msg]
    
    result = await runner._run_agent_loop(query, agent, "Do something", mock_sandbox)
    
    assert result == "Done"
    assert mock_llm_model.provider.invoke_llm.call_count == 2
    mock_sandbox.execute_command.assert_called_with("ls")

@pytest.mark.asyncio
async def test_run_supervisor_delegation(mock_app, mock_sandbox, mock_llm_model):
    runner = CoworkRunner(mock_app)
    mock_app.model_mgr.get_model_by_uuid.return_value = mock_llm_model
    
    query = Mock(spec=pipeline_query.Query)
    query.session_id = "test-session"
    query.query_id = "test-query"
    query.prompt = Mock(messages=[])
    query.messages = []
    query.user_message = provider_message.Message(role="user", content="Help me code")
    query.use_llm_model_uuid = "test-model"
    
    # Mock Supervisor LLM response: Delegate to coder
    delegate_msg = provider_message.Message(role="assistant", content="")
    delegate_msg.tool_calls = [
        Mock(
            id="call_1",
            function=Mock(
                name="delegate_to_agent",
                arguments=json.dumps({"agent_name": "coder", "instruction": "Write code"})
            )
        )
    ]
    
    # Mock Coder LLM response (inside _run_agent_loop)
    coder_msg = provider_message.Message(role="assistant", content="Code written")
    
    # Mock Supervisor final response
    final_msg = provider_message.Message(role="assistant", content="Task complete")
    
    # We need to handle the nested LLM calls.
    # The runner calls invoke_llm for supervisor.
    # Then inside delegate_to_agent -> _run_agent_loop, it calls invoke_llm for coder.
    # Then supervisor is called again with the result.
    
    # side_effect for invoke_llm:
    # 1. Supervisor: Delegate
    # 2. Coder: Result (inside _run_agent_loop)
    # 3. Supervisor: Final
    mock_llm_model.provider.invoke_llm.side_effect = [delegate_msg, coder_msg, final_msg]
    
    gen = runner.run(query)
    
    # 1. "Delegating to coder..."
    msg1 = await anext(gen)
    assert "Delegating to **coder**" in msg1.content
    
    # 2. Final message
    msg2 = await anext(gen)
    assert msg2.content == "Task complete"
    
    assert mock_llm_model.provider.invoke_llm.call_count == 3
