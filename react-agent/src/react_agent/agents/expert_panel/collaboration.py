"""Expert Panel Collaboration - 다중 전문가 응답 통합 로직"""

import logging
from typing import Dict, List, Optional

from .config import ExpertRole, EXPERT_REGISTRY

logger = logging.getLogger(__name__)


async def collaborate_experts(
    expert_responses: Dict[ExpertRole, str],
    query: str,
    category: Optional[str] = None,  # noqa: ARG001 - 향후 카테고리별 통합 로직 예정
) -> str:
    """
    다중 전문가 응답을 통합하여 최종 답변 생성

    Args:
        expert_responses: 전문가별 응답 딕셔너리 {ExpertRole: 응답 문자열}
        query: 사용자 원본 질문
        category: 질문 카테고리 (선택)

    Returns:
        통합된 최종 답변 문자열

    Example:
        >>> responses = {
        ...     ExpertRole.POLICY_EXPERT: "정책 관점에서...",
        ...     ExpertRole.MARKET_EXPERT: "시장 관점에서...",
        ... }
        >>> result = await collaborate_experts(responses, "탄소중립 정책이 시장에 미치는 영향")
    """
    if not expert_responses:
        logger.warning("No expert responses provided for collaboration")
        return "전문가 응답을 받지 못했습니다. 다시 시도해 주세요."

    # 단일 전문가 응답인 경우 그대로 반환
    if len(expert_responses) == 1:
        single_expert = list(expert_responses.keys())[0]
        single_response = list(expert_responses.values())[0]
        logger.info(f"Single expert response from {single_expert.value}, returning as-is")
        return single_response

    # 다중 전문가 응답 통합
    logger.info(
        f"Integrating responses from {len(expert_responses)} experts: "
        f"{[e.value for e in expert_responses.keys()]}"
    )

    integrated_response = await _integrate_responses(expert_responses, query)

    return integrated_response


async def _integrate_responses(
    expert_responses: Dict[ExpertRole, str],
    query: str,
) -> str:
    """
    다중 전문가 응답을 구조화하여 통합

    통합 구조:
    1. 헤더: Expert Panel 종합 분석
    2. 각 전문가 의견 섹션
    3. 종합 의견 섹션

    Args:
        expert_responses: 전문가별 응답 딕셔너리
        query: 사용자 원본 질문

    Returns:
        구조화된 통합 응답 문자열
    """
    sections = []

    # 1. 헤더 섹션
    expert_names = [
        EXPERT_REGISTRY[role].name for role in expert_responses.keys()
    ]
    header = f"""## Expert Panel 종합 분석

**질문**: {query}

**참여 전문가**: {', '.join(expert_names)}

---
"""
    sections.append(header)

    # 2. 각 전문가 의견 섹션
    for role, response in expert_responses.items():
        expert_header = format_expert_header(role)
        expert_section = f"""{expert_header}

{response}

---
"""
        sections.append(expert_section)

    # 3. 종합 의견 섹션
    synthesis = _generate_synthesis(expert_responses, query)
    synthesis_section = f"""## 종합 의견

{synthesis}

---

**더 깊이 알아보실 내용:**
- 각 전문가의 분석에 대한 추가 질문
- 특정 분야에 대한 심층 분석 요청
- 실무 적용을 위한 구체적인 가이드 요청
"""
    sections.append(synthesis_section)

    return "\n".join(sections)


def format_expert_header(role: ExpertRole) -> str:
    """
    전문가 응답 헤더 포맷 생성

    Args:
        role: 전문가 역할

    Returns:
        포맷팅된 헤더 문자열

    Example:
        >>> header = format_expert_header(ExpertRole.POLICY_EXPERT)
        >>> print(header)
        ### Dr. 김정책 | 정책/법규 전문가
        > 국제 기후변화 협약 및 국내 탄소중립 정책/법규 전문가
    """
    expert_config = EXPERT_REGISTRY.get(role)

    if not expert_config:
        logger.warning(f"Unknown expert role: {role}")
        return f"### 전문가 ({role.value})"

    # 역할명 한글 변환
    role_names = {
        ExpertRole.POLICY_EXPERT: "정책/법규 전문가",
        ExpertRole.CARBON_CREDIT_EXPERT: "탄소배출권 전문가",
        ExpertRole.MARKET_EXPERT: "시장/거래 전문가",
        ExpertRole.TECHNOLOGY_EXPERT: "감축기술 전문가",
        ExpertRole.MRV_EXPERT: "MRV/검증 전문가",
    }

    role_display = role_names.get(role, role.value)

    header = f"""### {expert_config.name} | {role_display}
> {expert_config.description}"""

    return header


def _generate_synthesis(
    expert_responses: Dict[ExpertRole, str],
    query: str,  # noqa: ARG001 - 향후 질문 기반 종합 생성 예정
) -> str:
    """
    전문가 응답들을 종합하여 핵심 인사이트 생성

    Args:
        expert_responses: 전문가별 응답 딕셔너리
        query: 사용자 원본 질문

    Returns:
        종합 인사이트 문자열
    """
    num_experts = len(expert_responses)
    expert_roles = list(expert_responses.keys())

    # 참여 전문가 분야 요약
    role_names = {
        ExpertRole.POLICY_EXPERT: "정책/법규",
        ExpertRole.CARBON_CREDIT_EXPERT: "탄소배출권",
        ExpertRole.MARKET_EXPERT: "시장/거래",
        ExpertRole.TECHNOLOGY_EXPERT: "감축기술",
        ExpertRole.MRV_EXPERT: "MRV/검증",
    }

    fields = [role_names.get(role) or role.value for role in expert_roles]
    fields_text = ", ".join(fields)

    synthesis = f"""위 질문에 대해 **{num_experts}명의 전문가**가 각자의 관점에서 분석을 제공했습니다.

**주요 분석 관점**:
- {fields_text} 분야의 전문적 시각을 종합

**활용 권장사항**:
1. 각 전문가의 의견을 통합적으로 검토하시기 바랍니다.
2. 특정 분야에 대해 더 깊은 분석이 필요하시면 해당 전문가에게 추가 질문을 해주세요.
3. 실무 적용 시에는 관련 규정 및 최신 동향을 반드시 확인하시기 바랍니다.

> 본 분석은 각 분야 박사급 전문가들의 의견을 종합한 것으로,
> 실제 의사결정에는 추가적인 검토와 전문가 상담을 권장합니다."""

    return synthesis


async def get_collaboration_summary(
    experts: List[ExpertRole],
    query: str,
) -> str:
    """
    전문가 협업 요약 정보 생성

    협업 시작 전 또는 진행 중 상태를 표시하기 위한 요약 문자열 생성

    Args:
        experts: 참여 전문가 역할 목록
        query: 사용자 질문

    Returns:
        협업 요약 문자열

    Example:
        >>> experts = [ExpertRole.POLICY_EXPERT, ExpertRole.MARKET_EXPERT]
        >>> summary = await get_collaboration_summary(experts, "탄소 정책과 시장 영향")
        >>> print(summary)
    """
    if not experts:
        logger.warning("No experts provided for collaboration summary")
        return "전문가 협업 정보가 없습니다."

    # 참여 전문가 정보 수집
    expert_info_list = []
    for role in experts:
        config = EXPERT_REGISTRY.get(role)
        if config:
            expert_info_list.append({
                "name": config.name,
                "role": role.value,
                "description": config.description,
            })

    # 요약 생성
    num_experts = len(expert_info_list)

    if num_experts == 1:
        collaboration_type = "단일 전문가 분석"
    elif num_experts == 2:
        collaboration_type = "2인 전문가 협업 분석"
    else:
        collaboration_type = f"{num_experts}인 전문가 패널 종합 분석"

    summary = f"""**{collaboration_type}**

**질문**: {query[:100]}{'...' if len(query) > 100 else ''}

**참여 전문가**:
"""

    for info in expert_info_list:
        summary += f"- **{info['name']}**: {info['description']}\n"

    summary += f"""
**분석 진행 중...**

> 각 전문가가 자신의 전문 분야 관점에서 분석을 수행합니다.
> 모든 분석이 완료되면 종합 의견을 제공해 드립니다.
"""

    logger.info(
        f"Collaboration summary generated for {num_experts} experts: "
        f"{[e.value for e in experts]}"
    )

    return summary
