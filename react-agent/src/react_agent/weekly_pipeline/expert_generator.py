"""Dynamic Expert Generator Module.

This module provides functionality to generate and register dynamic expert
configurations from NewExpertProposal objects created during LLM expert meetings.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from react_agent.agents.expert_panel.config import ExpertConfig, ExpertRole
from .expert_meeting import NewExpertProposal


# Module-level storage for dynamic experts
_DYNAMIC_EXPERTS: Dict[str, ExpertConfig] = {}


@dataclass
class DynamicExpertRole:
    """Dynamic expert role that can be created at runtime.

    Unlike ExpertRole enum which has fixed values, DynamicExpertRole
    allows creating new role identifiers dynamically.

    Attributes:
        value: The string identifier for this role.
    """

    value: str

    def __str__(self) -> str:
        """Return the role value as string."""
        return self.value

    def __hash__(self) -> int:
        """Make DynamicExpertRole hashable for use in sets/dicts."""
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        """Compare DynamicExpertRole instances by value."""
        if isinstance(other, DynamicExpertRole):
            return self.value == other.value
        return False


class ExpertGenerator:
    """Generator for creating ExpertConfig from NewExpertProposal.

    This class transforms proposals from LLM meetings into fully configured
    expert settings that can be registered in the dynamic expert registry.

    Attributes:
        PERSONA_TEMPLATE: Template string for generating expert personas.
        DEFAULT_TOOLS: Default tools assigned to new experts.
    """

    PERSONA_TEMPLATE: str = """당신은 {domain} 분야의 박사급 전문가입니다.
{expertise_description}에 대한 깊은 전문성을 보유하고 있습니다.
해당 분야의 최신 동향과 발전 방향에 대해 통찰력 있는 분석을 제공합니다.
실무 경험을 바탕으로 정확하고 실용적인 조언을 합니다."""

    DEFAULT_TOOLS: List[str] = ["tavily_search", "web_browser"]

    # Domain keywords mapping for inference
    _DOMAIN_KEYWORDS: Dict[str, List[str]] = {
        "통상": ["통상", "무역", "수출", "수입", "관세", "FTA", "WTO"],
        "금융": ["금융", "투자", "자본", "증권", "은행", "펀드", "자산"],
        "에너지": ["에너지", "전력", "발전", "재생", "신재생", "전기", "원자력"],
        "산업": ["산업", "제조", "공장", "생산", "설비", "제철", "철강"],
        "농업": ["농업", "농산", "식량", "농촌", "작물", "축산", "어업"],
        "해운": ["해운", "선박", "항만", "물류", "운송", "항공", "조선"],
    }

    def generate_from_proposal(
        self, proposal: NewExpertProposal
    ) -> Optional[ExpertConfig]:
        """Generate ExpertConfig from a NewExpertProposal.

        Args:
            proposal: The proposal containing suggested expert details.

        Returns:
            ExpertConfig if generation is successful, None if the proposal
            lacks required information (e.g., empty expertise).
        """
        # Validate proposal has required data
        if not proposal.expertise:
            return None

        # Infer domain from expertise
        domain = self._infer_domain(proposal.expertise)

        # Generate persona from template
        expertise_description = ", ".join(proposal.expertise[:5])
        persona = self.PERSONA_TEMPLATE.format(
            domain=domain, expertise_description=expertise_description
        )

        # Create description from reason or generate default
        description = proposal.reason if proposal.reason else f"{domain} 분야 전문가"

        # Create DynamicExpertRole
        role = DynamicExpertRole(value=proposal.suggested_role)

        # Build ExpertConfig
        config = ExpertConfig(
            role=role,  # type: ignore[arg-type]
            name=proposal.suggested_name,
            persona=persona,
            description=description,
            expertise=proposal.expertise,
            tools=self.DEFAULT_TOOLS.copy(),
            keywords=proposal.keywords,
        )

        return config

    def _infer_domain(self, expertise: List[str]) -> str:
        """Infer domain from expertise keywords.

        Analyzes the expertise list to determine the most likely domain
        category based on keyword matching.

        Args:
            expertise: List of expertise area strings.

        Returns:
            The inferred domain name (e.g., "통상", "금융", "에너지").
        """
        # Join expertise into searchable text
        expertise_text = " ".join(expertise).lower()

        # Count matches for each domain
        domain_scores: Dict[str, int] = {}
        for domain, keywords in self._DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in expertise_text)
            if score > 0:
                domain_scores[domain] = score

        # Return domain with highest score, or default
        if domain_scores:
            return max(domain_scores, key=lambda d: domain_scores[d])

        # Default domain for carbon-related expertise
        return "탄소"


def register_dynamic_expert(proposal: NewExpertProposal) -> bool:
    """Register a new dynamic expert from a proposal.

    Creates an ExpertConfig from the proposal and adds it to the
    dynamic expert registry.

    Args:
        proposal: The proposal containing expert details.

    Returns:
        True if registration was successful, False otherwise.
    """
    generator = ExpertGenerator()
    config = generator.generate_from_proposal(proposal)

    if config is None:
        return False

    _DYNAMIC_EXPERTS[proposal.suggested_role] = config
    return True


def get_dynamic_experts() -> List[ExpertConfig]:
    """Get all registered dynamic experts.

    Returns:
        List of all ExpertConfig objects in the dynamic registry.
    """
    return list(_DYNAMIC_EXPERTS.values())


def get_dynamic_expert(role: str) -> Optional[ExpertConfig]:
    """Get a specific dynamic expert by role.

    Args:
        role: The role identifier string.

    Returns:
        ExpertConfig if found, None otherwise.
    """
    return _DYNAMIC_EXPERTS.get(role)


def clear_dynamic_experts() -> None:
    """Clear all dynamic experts from the registry.

    This function is primarily intended for testing purposes
    to reset the registry state between tests.
    """
    _DYNAMIC_EXPERTS.clear()
