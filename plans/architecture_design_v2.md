# LangBot Architecture Design for Sandbox, Cowork, and Skills

## 1. Overview

This document outlines the architectural changes required to introduce Sandbox (Firecracker), Cowork (Agent Orchestration), and Skills (Anthropic Standard) support to LangBot.

## 2. New Components

### 2.1. Sandbox Service (Firecracker)

**Goal**: Provide a secure, isolated environment for executing untrusted code or tools.

**Architecture**:
- **`SandboxManager`**: A new core service responsible for managing the lifecycle of Firecracker microVMs.
    - `start_vm(config)`: Starts a new microVM.
    - `stop_vm(vm_id)`: Stops a microVM.
    - `execute_command(vm_id, command)`: Executes a command inside the VM.
    - `upload_file(vm_id, src, dest)`: Uploads files to the VM.
    - `download_file(vm_id, src, dest)`: Downloads files from the VM.
- **`SandboxProvider`**: An abstraction layer to support different sandbox backends (Firecracker, Docker, gVisor), with Firecracker being the primary implementation.
- **Integration**:
    - Tools defined in `ToolManager` can be marked as `requires_sandbox`.
    - When `LocalAgentRunner` or `ToolManager` executes such a tool, it requests a VM from `SandboxManager` and executes the tool logic inside it.

### 2.2. Skill Manager (Anthropic Skills)

**Goal**: Support the standardized definition of "Skills" as proposed by Anthropic, allowing for easier sharing and reuse of agent capabilities.

**Architecture**:
- **`SkillLoader`**: A new loader in `src/langbot/pkg/provider/tools/loaders/` specifically for parsing Anthropic Skill definitions (likely XML/JSON format).
- **`SkillRegistry`**: Stores loaded skills.
- **`SkillEntity`**: Internal representation of a skill, mapping it to the `LLMTool` format used by LangBot.
- **Integration**:
    - `ToolManager` will initialize `SkillLoader` alongside `PluginToolLoader` and `MCPLoader`.
    - Skills will be exposed as standard tools to the LLM.

### 2.3. Cowork Engine (Agent Orchestration)

**Goal**: Enable multi-agent collaboration where a "Supervisor" or "Orchestrator" agent can delegate tasks to specialized "Worker" agents.

**Architecture**:
- **`CoworkRunner`**: A new runner type (replacing or extending `LocalAgentRunner`) capable of managing a conversation state across multiple agents.
- **`AgentNode`**: Represents a specialized agent with a specific set of tools/skills and a specific system prompt.
- **`Orchestrator`**: Logic to route messages between the User and AgentNodes, or between AgentNodes.
- **`WorkflowDefinition`**: A configuration format (YAML/JSON) to define the agent topology (e.g., Supervisor-Worker, Sequential, Hierarchical).

## 3. Detailed Design & Modifications

### 3.1. `src/langbot/pkg/core/`

- **`sandbox.py`**: New module for `SandboxManager`.
- **`cowork.py`**: New module for `CoworkManager` (if needed globally) or keep it within `provider/runners`.

### 3.2. `src/langbot/pkg/provider/tools/`

- **`loaders/skill.py`**: New loader for Anthropic Skills.
- **`toolmgr.py`**: Update `ToolManager` to include `SkillLoader`.
- **`entities.py`**: Update `LLMTool` to support `sandbox_config` (e.g., docker image, resource limits).

### 3.3. `src/langbot/pkg/provider/runners/`

- **`cowork_runner.py`**: New runner implementing the multi-agent logic.
    - It will need to maintain a `conversation_state` that tracks which agent is currently active.
    - It will use `ToolManager` to call tools, but some "tools" might actually be calls to other agents.

### 3.4. `src/langbot/pkg/persistence/`

- **`migrations/`**: New migrations to support storing Skill definitions and Cowork workflows.
- **`entities.py`**: Update database models.

## 4. Workflow Example (Cowork + Sandbox)

1.  **User** sends a request: "Analyze this Python script for security vulnerabilities."
2.  **CoworkRunner** (Supervisor) receives the request.
3.  **Supervisor** decides to delegate to **SecurityAuditAgent**.
4.  **SecurityAuditAgent** receives the script. It has a tool `run_static_analysis` which is marked as `requires_sandbox`.
5.  **ToolManager** sees the sandbox requirement.
6.  **SandboxManager** spins up a Firecracker VM (or uses a warm one).
7.  **ToolManager** injects the script into the VM and runs the analysis tool.
8.  **SandboxManager** returns the output (stdout/stderr).
9.  **SecurityAuditAgent** interprets the output and reports back to **Supervisor**.
10. **Supervisor** formulates the final response to the **User**.

## 5. Implementation Steps

1.  **Phase 1: Sandbox Foundation**
    - Implement `SandboxManager` and Firecracker integration.
    - Add `sandbox_config` to `LLMTool`.
    - Test running simple shell commands in Firecracker.

2.  **Phase 2: Skill System**
    - Implement `SkillLoader` to parse the specified format.
    - Integrate with `ToolManager`.

3.  **Phase 3: Cowork Engine**
    - Design the `Workflow` configuration.
    - Implement `CoworkRunner`.
    - Create a sample "Supervisor-Worker" workflow.

4.  **Phase 4: Integration & UI**
    - Expose new configurations in the Frontend (if applicable, or just API/Config files first).
    - End-to-end testing.

## 6. Questions for User

1.  **Firecracker Environment**: Do you have a specific base image or kernel you want to use for the Firecracker VMs?
2.  **Skill Format**: Can you confirm the exact format of the "Anthropic Skills"? (The link provided `llms.txt` suggests a text-based format, possibly Markdown or XML).
3.  **Cowork State**: Do we need to persist the internal state of the multi-agent conversation across server restarts?
