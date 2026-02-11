from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class LLMTool:
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    sandbox_config: Dict[str, Any] = field(default_factory=dict)
