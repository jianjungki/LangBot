from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class AgentNode:
    """Represents a specialized agent in a cowork workflow."""
    name: str
    role: str  # e.g., "Supervisor", "SecurityAuditor", "CodeGenerator"
    system_prompt: str
    tool_names: List[str] = field(default_factory=list) # Names of tools/skills this agent can use

@dataclass
class WorkflowDefinition:
    """Defines the structure and flow of a multi-agent collaboration."""
    name: str
    description: str
    agents: List[AgentNode] = field(default_factory=list)
    # Simple routing logic for now, can be expanded later
    # e.g., {"start": "Supervisor", "Supervisor": {"route_to": ["SecurityAuditor", "CodeGenerator"]}}
    routing: Dict[str, Any] = field(default_factory=dict)
