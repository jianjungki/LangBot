from __future__ import annotations

import typing
import copy
import json
import asyncio
import os
import tempfile
from .. import runner
import langbot_plugin.api.entities.builtin.pipeline.query as pipeline_query
import langbot_plugin.api.entities.builtin.provider.message as provider_message
import langbot_plugin.api.entities.builtin.resource.tool as resource_tool
from langbot.pkg.core.sandbox import SandboxInstance

@runner.runner_class('cowork-runner')
class CoworkRunner(runner.RequestRunner):
    """Cowork Agent Runner for Multi-Agent Orchestration"""

    class AgentNode:
        """Represents a specialized agent in the cowork network"""
        name: str
        system_prompt: str
        tools: list[str]
        
        def __init__(self, name: str, system_prompt: str, tools: list[str]):
            self.name = name
            self.system_prompt = system_prompt
            self.tools = tools

    # Map: session_id -> sandbox_id
    sandbox_map: dict[str, str] = {}
    
    # Define available agents
    agents: dict[str, AgentNode] = {
        "supervisor": AgentNode(
            name="supervisor",
            system_prompt="You are a supervisor agent. Your goal is to coordinate other agents to solve the user's problem. "
                          "You have access to the following agents: 'researcher', 'coder'. "
                          "You can delegate tasks to them simultaneously by calling 'delegate_to_agent' multiple times. "
                          "Combine their outputs to answer the user.",
            tools=["delegate_to_agent"]
        ),
        "researcher": AgentNode(
            name="researcher",
            system_prompt="You are a researcher agent. You can search for information and summarize it.",
            tools=[] # Add search tools here if available
        ),
        "coder": AgentNode(
            name="coder",
            system_prompt="You are a coder agent. You can write and analyze code. "
                          "You have access to a sandbox environment to execute code. "
                          "Use 'write_file' to create files, 'exec_command' to run them, and 'read_file' to read results. "
                          "Always verify your code by executing it.",
            tools=["write_file", "read_file", "exec_command"]
        )
    }

    async def _get_sandbox(self, session_id: str) -> SandboxInstance:
        if session_id in self.sandbox_map:
            sb = await self.ap.sandbox_mgr.get_sandbox(self.sandbox_map[session_id])
            if sb:
                return sb
        
        # Create new
        sb = await self.ap.sandbox_mgr.create_sandbox("docker")
        self.sandbox_map[session_id] = sb.id
        return sb

    def _get_sandbox_tools(self, sandbox: SandboxInstance) -> list[resource_tool.LLMTool]:
        async def write_file(path: str, content: str):
            """Write content to a file in the sandbox."""
            fd, tmp_path = tempfile.mkstemp()
            try:
                with os.fdopen(fd, 'w') as tmp:
                    tmp.write(content)
                
                # Ensure directory exists
                dir_path = os.path.dirname(path)
                if dir_path and dir_path != ".":
                    await sandbox.execute_command(f"mkdir -p {dir_path}")

                await sandbox.upload_file(tmp_path, path)
                return f"Successfully wrote to {path}"
            except Exception as e:
                return f"Error writing file: {e}"
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        async def read_file(path: str):
            """Read content from a file in the sandbox."""
            fd, tmp_path = tempfile.mkstemp()
            os.close(fd)
            
            try:
                await sandbox.download_file(path, tmp_path)
                with open(tmp_path, 'r') as f:
                    return f.read()
            except Exception as e:
                return f"Error reading file: {e}"
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        async def exec_command(command: str):
            """Execute a shell command in the sandbox."""
            code, stdout, stderr = await sandbox.execute_command(command)
            return f"""Exit Code: {code}
Stdout: {stdout}
Stderr: {stderr}"""

        return [
            resource_tool.LLMTool(
                name="write_file",
                description="Write content to a file in the sandbox",
                human_desc="Write file",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["path", "content"]
                },
                func=write_file
            ),
            resource_tool.LLMTool(
                name="read_file",
                description="Read content from a file in the sandbox",
                human_desc="Read file",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                },
                func=read_file
            ),
            resource_tool.LLMTool(
                name="exec_command",
                description="Execute a shell command in the sandbox",
                human_desc="Execute command",
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"}
                    },
                    "required": ["command"]
                },
                func=exec_command
            )
        ]

    async def _run_agent_loop(self, query: pipeline_query.Query, agent: AgentNode, instruction: str, sandbox: SandboxInstance) -> str:
        messages = [
            provider_message.Message(role="system", content=agent.system_prompt),
            provider_message.Message(role="user", content=instruction)
        ]
        
        # Get tools
        tools = []
        if "write_file" in agent.tools:
            tools.extend(self._get_sandbox_tools(sandbox))
        
        # Add other tools if needed (e.g. search for researcher)
        # for tool_name in agent.tools:
        #     if tool_name not in ["write_file", "read_file", "exec_command"]:
        #         tool = await self.ap.tool_mgr.get_tool(tool_name)
        #         if tool:
        #             tools.append(tool)

        max_turns = 10
        for _ in range(max_turns):
            use_llm_model = await self.ap.model_mgr.get_model_by_uuid(query.use_llm_model_uuid)
            msg = await use_llm_model.provider.invoke_llm(
                query, use_llm_model, messages, tools, extra_args=use_llm_model.model_entity.extra_args
            )
            
            messages.append(msg)
            
            if msg.tool_calls:
                tool_results = []
                for tool_call in msg.tool_calls:
                    tool = next((t for t in tools if t.name == tool_call.function.name), None)
                    if tool:
                        args = json.loads(tool_call.function.arguments)
                        try:
                            if asyncio.iscoroutinefunction(tool.func):
                                res = await tool.func(**args)
                            else:
                                res = tool.func(**args)
                        except Exception as e:
                            res = f"Error: {e}"
                        
                        tool_results.append(provider_message.Message(
                            role="tool",
                            content=str(res),
                            tool_call_id=tool_call.id,
                            name=tool_call.function.name
                        ))
                messages.extend(tool_results)
            else:
                return msg.content
        
        return "Agent execution timed out (max turns reached)."

    async def run(
        self, query: pipeline_query.Query
    ) -> typing.AsyncGenerator[provider_message.Message | provider_message.MessageChunk, None]:
        
        session_id = query.session_id or query.query_id
        sandbox = await self._get_sandbox(session_id)
        
        current_agent = self.agents["supervisor"]
        
        req_messages = []
        req_messages.append(provider_message.Message(
            role="system",
            content=current_agent.system_prompt
        ))
        req_messages.extend(query.prompt.messages)
        req_messages.extend(query.messages)
        req_messages.append(query.user_message)

        async def delegate_to_agent(agent_name: str, instruction: str):
            """Delegate a task to a specific agent."""
            if agent_name not in self.agents:
                return f"Agent {agent_name} not found."
            
            target_agent = self.agents[agent_name]
            self.ap.logger.info(f"Delegating to {agent_name}: {instruction}")
            
            result = await self._run_agent_loop(query, target_agent, instruction, sandbox)
            return f"Agent {agent_name} result: {result}"

        delegate_tool = resource_tool.LLMTool(
            name="delegate_to_agent",
            description="Delegate a task to a specific agent.",
            human_desc="Delegate task",
            parameters={
                "type": "object",
                "properties": {
                    "agent_name": {"type": "string", "enum": list(self.agents.keys())},
                    "instruction": {"type": "string"}
                },
                "required": ["agent_name", "instruction"]
            },
            func=delegate_to_agent
        )
        
        tools = [delegate_tool]
        
        max_supervisor_turns = 5
        for _ in range(max_supervisor_turns):
            use_llm_model = await self.ap.model_mgr.get_model_by_uuid(query.use_llm_model_uuid)
            msg = await use_llm_model.provider.invoke_llm(
                query, use_llm_model, req_messages, tools, extra_args=use_llm_model.model_entity.extra_args
            )
            
            if msg.tool_calls:
                tasks = []
                tool_calls_to_process = []
                
                for tool_call in msg.tool_calls:
                    if tool_call.function.name == "delegate_to_agent":
                        args = json.loads(tool_call.function.arguments)
                        tasks.append(delegate_to_agent(**args))
                        tool_calls_to_process.append(tool_call)
                        
                        yield provider_message.Message(
                            role="assistant",
                            content=f"🤖 Delegating to **{args.get('agent_name')}**..."
                        )
                
                if tasks:
                    results = await asyncio.gather(*tasks)
                    
                    req_messages.append(msg)
                    
                    for i, res in enumerate(results):
                        tool_call = tool_calls_to_process[i]
                        req_messages.append(provider_message.Message(
                            role="tool",
                            content=res,
                            tool_call_id=tool_call.id,
                            name=tool_call.function.name
                        ))
                else:
                    yield msg
                    return
            else:
                yield msg
                return
