"""Expert Panel - 박사급 전문가 에이전트 패널 (Enhanced)

다각적 분석, 확대된 전문성, 신규 토픽 출력 기능 포함
"""

from .config import (
    ExpertRole,
    ExpertConfig,
    EXPERT_REGISTRY,
    get_expert_by_role,
    get_all_experts,
    get_expert_keywords,
    get_all_hot_topics,
    get_expert_by_keyword,
    get_cross_domain_experts,
)
from .prompts import (
    EXPERT_PANEL_IDENTITY,
    EXPERT_PROMPT_TEMPLATE,
    ANTI_HALLUCINATION_EXPERT,
    MULTI_PERSPECTIVE_ANALYSIS,
    get_expert_prompt,
    get_expert_prompt_with_question,
    get_all_expert_prompts,
    get_expert_summary,
    get_combined_hot_topics,
)
from .topics import (
    get_recent_documents,
    extract_weekly_updates,
    get_topics_by_category,
    get_trending_topics,
    format_weekly_summary,
    get_expert_recent_topics,
    get_expert_topic_summary,
    get_all_topics_info,
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
    "get_all_hot_topics",
    "get_expert_by_keyword",
    "get_cross_domain_experts",
    # Prompts
    "EXPERT_PANEL_IDENTITY",
    "EXPERT_PROMPT_TEMPLATE",
    "ANTI_HALLUCINATION_EXPERT",
    "MULTI_PERSPECTIVE_ANALYSIS",
    "get_expert_prompt",
    "get_expert_prompt_with_question",
    "get_all_expert_prompts",
    "get_expert_summary",
    "get_combined_hot_topics",
    # Topics (신규 토픽 관리)
    "get_recent_documents",
    "extract_weekly_updates",
    "get_topics_by_category",
    "get_trending_topics",
    "format_weekly_summary",
    "get_expert_recent_topics",
    "get_expert_topic_summary",
    "get_all_topics_info",
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
