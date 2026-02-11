"""Expert Panel - 박사급 전문가 에이전트 패널"""

from .config import (
    ExpertRole,
    ExpertConfig,
    EXPERT_REGISTRY,
    get_expert_by_role,
    get_all_experts,
    get_expert_keywords,
)
from .prompts import (
    EXPERT_PANEL_IDENTITY,
    EXPERT_PROMPT_TEMPLATE,
    ANTI_HALLUCINATION_EXPERT,
    get_expert_prompt,
    get_expert_prompt_with_question,
    get_all_expert_prompts,
    get_expert_summary,
)
from .router import (
    route_to_expert,
    should_use_expert_panel,
    needs_collaboration,
    get_best_expert_for_query,
    get_expert_team_for_query,
    EXPERT_TRIGGER_KEYWORDS,
    COLLABORATION_PATTERNS,
)
from .collaboration import (
    collaborate_experts,
    format_expert_header,
    get_collaboration_summary,
)
from .nodes import (
    expert_panel_router,
    expert_panel_agent,
)

__all__ = [
    # Config
    "ExpertRole",
    "ExpertConfig",
    "EXPERT_REGISTRY",
    "get_expert_by_role",
    "get_all_experts",
    "get_expert_keywords",
    # Prompts
    "EXPERT_PANEL_IDENTITY",
    "EXPERT_PROMPT_TEMPLATE",
    "ANTI_HALLUCINATION_EXPERT",
    "get_expert_prompt",
    "get_expert_prompt_with_question",
    "get_all_expert_prompts",
    "get_expert_summary",
    # Router
    "route_to_expert",
    "should_use_expert_panel",
    "needs_collaboration",
    "get_best_expert_for_query",
    "get_expert_team_for_query",
    "EXPERT_TRIGGER_KEYWORDS",
    "COLLABORATION_PATTERNS",
    # Collaboration
    "collaborate_experts",
    "format_expert_header",
    "get_collaboration_summary",
    # Nodes
    "expert_panel_router",
    "expert_panel_agent",
]
