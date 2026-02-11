"""LLM Expert Meeting Engine.

This module provides an LLM-based meeting mechanism where expert agents
conduct a "meeting" to determine appropriate expert assignment for complex
content that cannot be resolved by rule-based classification.
"""

import json
import re
from dataclasses import dataclass, field
from typing import List

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from react_agent.agents.expert_panel.config import ExpertRole, EXPERT_REGISTRY


@dataclass
class NewExpertProposal:
    """Proposal for creating a new expert role.

    When existing experts cannot adequately cover a domain, the meeting
    may propose creating a new specialist.

    Attributes:
        suggested_role: The proposed role identifier (e.g., "hydrogen_expert").
        suggested_name: The suggested name for the expert (e.g., "Dr. 수소").
        expertise: List of expertise areas for the new expert.
        keywords: List of keywords the new expert should handle.
        reason: Explanation for why this new expert is needed.
    """

    suggested_role: str
    suggested_name: str
    expertise: List[str]
    keywords: List[str]
    reason: str


@dataclass
class MeetingResult:
    """Result from an expert panel meeting.

    Contains the assigned experts, any proposals for new experts,
    and metadata about the decision process.

    Attributes:
        assigned_experts: List of ExpertRole assigned to handle the content.
        new_expert_proposals: Proposals for new expert roles if needed.
        reasoning: Explanation of the decision-making process.
        consensus_score: Agreement score among experts (0.0-1.0).
        raw_response: The raw LLM response for debugging.
    """

    assigned_experts: List[ExpertRole]
    new_expert_proposals: List[NewExpertProposal]
    reasoning: str
    consensus_score: float
    raw_response: str = ""


MEETING_SYSTEM_PROMPT = """당신은 탄소 전문가 패널 회의의 진행자입니다.

## 역할
주어진 콘텐츠를 분석하여 가장 적합한 전문가(들)를 결정하고,
필요시 새로운 전문가 역할을 제안합니다.

## 현재 전문가 패널
{expert_list}

## 분석 기준
1. 콘텐츠의 주요 주제와 키워드 파악
2. 각 전문가의 전문 분야와의 관련성 평가
3. 단일 전문가 vs 복수 전문가 협업 필요 여부 판단
4. 기존 전문가로 커버되지 않는 영역이 있는지 검토

## 응답 형식
반드시 다음 JSON 형식으로만 응답하세요. 다른 텍스트 없이 JSON만 출력합니다:

```json
{{
    "assigned_experts": ["expert_role1", "expert_role2"],
    "new_expert_proposals": [
        {{
            "suggested_role": "new_role_name",
            "suggested_name": "Dr. 이름",
            "expertise": ["전문분야1", "전문분야2"],
            "keywords": ["키워드1", "키워드2"],
            "reason": "이 전문가가 필요한 이유"
        }}
    ],
    "reasoning": "이 결정을 내린 상세한 이유",
    "consensus_score": 0.85
}}
```

## 주의사항
- assigned_experts에는 반드시 1개 이상의 전문가를 포함해야 합니다
- 사용 가능한 전문가 역할: policy_expert, carbon_credit_expert, market_expert, technology_expert, mrv_expert
- consensus_score는 0.0~1.0 사이의 값으로, 결정의 확신도를 나타냅니다
- new_expert_proposals는 정말 필요한 경우에만 제안하세요 (빈 배열 가능)
"""


class ExpertMeeting:
    """LLM-based expert meeting engine.

    Conducts a virtual "meeting" using an LLM to determine the best
    expert assignment for complex content that rule-based classification
    cannot resolve.

    Attributes:
        model_name: The name of the LLM model to use.
        llm: The ChatAnthropic LLM instance.
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514") -> None:
        """Initialize the expert meeting engine.

        Args:
            model: The model name to use for the LLM.
        """
        self.model_name = model
        self.llm = ChatAnthropic(model=model)

    def _get_expert_list(self) -> str:
        """Generate a formatted string of current experts.

        Returns:
            A formatted string describing all available experts.
        """
        lines = []
        for role, config in EXPERT_REGISTRY.items():
            lines.append(f"### {config.name} ({role.value})")
            lines.append(f"- 설명: {config.description}")
            lines.append(f"- 전문분야: {', '.join(config.expertise[:5])}")
            lines.append(f"- 키워드: {', '.join(config.keywords[:10])}")
            lines.append("")
        return "\n".join(lines)

    async def conduct_meeting(
        self,
        content: str,
        title: str,
        source: str,
    ) -> MeetingResult:
        """Conduct an expert meeting to determine content assignment.

        Args:
            content: The content text to analyze.
            title: The title of the content.
            source: The source of the content.

        Returns:
            MeetingResult containing the expert assignment decision.
        """
        expert_list = self._get_expert_list()
        system_prompt = MEETING_SYSTEM_PROMPT.format(expert_list=expert_list)

        user_message = f"""다음 콘텐츠에 대해 전문가 회의를 진행하고 담당 전문가를 결정해주세요.

## 콘텐츠 정보
- 제목: {title}
- 출처: {source}

## 내용
{content[:3000]}  # Limit content length

## 분석 요청
1. 이 콘텐츠를 담당할 가장 적합한 전문가(들)를 선정해주세요.
2. 기존 전문가로 충분히 커버되지 않는 영역이 있다면 새 전문가를 제안해주세요.
3. JSON 형식으로만 응답해주세요.
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        response = await self.llm.ainvoke(messages)
        response_text = response.content if hasattr(response, "content") else str(response)

        return self._parse_response(response_text)

    def _parse_response(self, response: str) -> MeetingResult:
        """Parse the LLM response into a MeetingResult.

        Args:
            response: The raw LLM response string.

        Returns:
            MeetingResult parsed from the response.
        """
        # Try to extract JSON from markdown code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_str = response.strip()

        try:
            data = json.loads(json_str)

            # Parse assigned experts
            assigned_experts = []
            for expert_str in data.get("assigned_experts", []):
                try:
                    role = ExpertRole(expert_str)
                    assigned_experts.append(role)
                except ValueError:
                    # Unknown expert role, skip
                    continue

            # If no valid experts parsed, default to policy expert
            if not assigned_experts:
                assigned_experts = [ExpertRole.POLICY_EXPERT]

            # Parse new expert proposals
            new_expert_proposals = []
            for proposal_data in data.get("new_expert_proposals", []):
                proposal = NewExpertProposal(
                    suggested_role=proposal_data.get("suggested_role", ""),
                    suggested_name=proposal_data.get("suggested_name", ""),
                    expertise=proposal_data.get("expertise", []),
                    keywords=proposal_data.get("keywords", []),
                    reason=proposal_data.get("reason", ""),
                )
                new_expert_proposals.append(proposal)

            return MeetingResult(
                assigned_experts=assigned_experts,
                new_expert_proposals=new_expert_proposals,
                reasoning=data.get("reasoning", ""),
                consensus_score=float(data.get("consensus_score", 0.0)),
                raw_response=response,
            )

        except (json.JSONDecodeError, KeyError, TypeError):
            # Fallback to default result if parsing fails
            return MeetingResult(
                assigned_experts=[ExpertRole.POLICY_EXPERT],
                new_expert_proposals=[],
                reasoning="JSON 파싱 실패로 기본 전문가 할당",
                consensus_score=0.0,
                raw_response=response,
            )
