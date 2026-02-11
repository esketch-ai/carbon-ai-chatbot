"""Expert Panel Router - 질문 분석 및 전문가 라우팅 로직"""

import logging
from typing import List, Tuple, Optional

from .config import ExpertRole, ExpertConfig, EXPERT_REGISTRY

logger = logging.getLogger(__name__)


# Expert Panel 사용을 트리거하는 고급 키워드
EXPERT_TRIGGER_KEYWORDS = [
    "파리협정",
    "UNFCCC",
    "NDC",
    "국가결정기여",
    "IPCC",
    "EU ETS",
    "K-ETS",
    "탄소중립",
    "탄소국경조정",
    "CBAM",
    "GHG Protocol",
    "Scope",
    "CCUS",
    "탄소포집",
]

# 협업이 필요한 패턴 정의 (패턴: (트리거 키워드들, 추가 전문가들))
COLLABORATION_PATTERNS: List[Tuple[List[str], List[ExpertRole]]] = [
    # 정책 + 시장 협업
    (
        ["정책", "시장", "가격"],
        [ExpertRole.POLICY_EXPERT, ExpertRole.MARKET_EXPERT],
    ),
    (
        ["규제", "거래", "ETS"],
        [ExpertRole.POLICY_EXPERT, ExpertRole.MARKET_EXPERT],
    ),
    # 기술 + MRV 협업
    (
        ["기술", "검증", "측정"],
        [ExpertRole.TECHNOLOGY_EXPERT, ExpertRole.MRV_EXPERT],
    ),
    (
        ["감축", "Scope", "산정"],
        [ExpertRole.TECHNOLOGY_EXPERT, ExpertRole.MRV_EXPERT],
    ),
    # 배출권 + 시장 협업
    (
        ["배출권", "거래", "가격"],
        [ExpertRole.CARBON_CREDIT_EXPERT, ExpertRole.MARKET_EXPERT],
    ),
    (
        ["KAU", "시장", "전망"],
        [ExpertRole.CARBON_CREDIT_EXPERT, ExpertRole.MARKET_EXPERT],
    ),
    # 정책 + 기술 협업
    (
        ["탄소중립", "기술", "로드맵"],
        [ExpertRole.POLICY_EXPERT, ExpertRole.TECHNOLOGY_EXPERT],
    ),
    (
        ["NDC", "감축", "이행"],
        [ExpertRole.POLICY_EXPERT, ExpertRole.TECHNOLOGY_EXPERT],
    ),
    # 배출권 + MRV 협업
    (
        ["외부사업", "방법론", "검증"],
        [ExpertRole.CARBON_CREDIT_EXPERT, ExpertRole.MRV_EXPERT],
    ),
    (
        ["상쇄", "인증", "MRV"],
        [ExpertRole.CARBON_CREDIT_EXPERT, ExpertRole.MRV_EXPERT],
    ),
    # 전체 협업 (복합 주제)
    (
        ["탄소중립", "전략", "종합"],
        [
            ExpertRole.POLICY_EXPERT,
            ExpertRole.TECHNOLOGY_EXPERT,
            ExpertRole.MARKET_EXPERT,
        ],
    ),
]


def _calculate_match_score(
    query_lower: str,
    config: ExpertConfig,
    category: Optional[str] = None,
) -> float:
    """
    질문과 전문가 간의 매칭 점수 계산

    점수 구성:
    - 키워드 매칭: 최대 0.6점
    - 전문성 매칭: 최대 0.3점
    - 카테고리 보너스: 0.1점

    Args:
        query_lower: 소문자로 변환된 질문
        config: 전문가 설정
        category: 질문 카테고리 (선택)

    Returns:
        매칭 점수 (0.0 ~ 1.0)
    """
    score = 0.0

    # 1. 키워드 매칭 점수 (최대 0.6점)
    keyword_matches = 0
    for keyword in config.keywords:
        if keyword.lower() in query_lower:
            keyword_matches += 1

    if config.keywords:
        keyword_ratio = min(keyword_matches / len(config.keywords), 1.0)
        # 매칭된 키워드 수에 따른 보너스
        if keyword_matches >= 3:
            keyword_score = 0.6
        elif keyword_matches >= 2:
            keyword_score = 0.5
        elif keyword_matches >= 1:
            keyword_score = 0.3 + (keyword_ratio * 0.2)
        else:
            keyword_score = 0.0
        score += keyword_score

    # 2. 전문성 매칭 점수 (최대 0.3점)
    expertise_matches = 0
    for expertise in config.expertise:
        # 전문성의 핵심 단어들 추출
        expertise_words = expertise.lower().replace("(", " ").replace(")", " ").split()
        for word in expertise_words:
            if len(word) >= 2 and word in query_lower:
                expertise_matches += 1
                break  # 해당 전문성에서 하나만 매칭되면 충분

    if config.expertise:
        expertise_ratio = min(expertise_matches / len(config.expertise), 1.0)
        expertise_score = expertise_ratio * 0.3
        score += expertise_score

    # 3. 카테고리 보너스 (0.1점)
    if category:
        category_lower = category.lower()

        # 카테고리와 역할 매칭 확인
        category_mappings = {
            "policy": [ExpertRole.POLICY_EXPERT],
            "정책": [ExpertRole.POLICY_EXPERT],
            "credit": [ExpertRole.CARBON_CREDIT_EXPERT],
            "배출권": [ExpertRole.CARBON_CREDIT_EXPERT],
            "market": [ExpertRole.MARKET_EXPERT],
            "시장": [ExpertRole.MARKET_EXPERT],
            "거래": [ExpertRole.MARKET_EXPERT],
            "technology": [ExpertRole.TECHNOLOGY_EXPERT],
            "기술": [ExpertRole.TECHNOLOGY_EXPERT],
            "감축": [ExpertRole.TECHNOLOGY_EXPERT],
            "mrv": [ExpertRole.MRV_EXPERT],
            "검증": [ExpertRole.MRV_EXPERT],
            "측정": [ExpertRole.MRV_EXPERT],
        }

        for cat_key, matched_roles in category_mappings.items():
            if cat_key in category_lower and config.role in matched_roles:
                score += 0.1
                break

    return min(score, 1.0)  # 최대 1.0으로 제한


def route_to_expert(
    query: str,
    category: Optional[str] = None,
    top_k: int = 1,
) -> List[Tuple[ExpertRole, float]]:
    """
    질문을 분석하여 가장 적합한 전문가(들)를 선정

    Args:
        query: 사용자 질문
        category: 질문 카테고리 (선택)
        top_k: 반환할 전문가 수 (기본값: 1)

    Returns:
        (전문가 역할, 매칭 점수) 튜플의 리스트 (점수 내림차순)
    """
    query_lower = query.lower()
    expert_scores: List[Tuple[ExpertRole, float]] = []

    for role, config in EXPERT_REGISTRY.items():
        score = _calculate_match_score(query_lower, config, category)
        expert_scores.append((role, score))

    # 점수 내림차순 정렬
    expert_scores.sort(key=lambda x: x[1], reverse=True)

    # 상위 k개 선택
    selected = expert_scores[:top_k]

    logger.debug(
        f"Expert routing result for query: '{query[:50]}...'\n"
        f"Top {top_k} experts: {[(e.value, f'{s:.2f}') for e, s in selected]}"
    )

    return selected


def should_use_expert_panel(
    complexity: str,
    confidence: float,
    query: str,
) -> bool:
    """
    Expert Panel 사용 여부 결정

    다음 조건 중 하나라도 만족하면 Expert Panel 사용:
    1. 복잡도가 'complex'인 경우
    2. 신뢰도가 낮은 경우 (0.5 미만)
    3. 특정 고급 키워드가 포함된 경우

    Args:
        complexity: 질문 복잡도 ('simple', 'medium', 'complex')
        confidence: 일반 응답의 신뢰도 (0.0 ~ 1.0)
        query: 사용자 질문

    Returns:
        Expert Panel 사용 여부
    """
    # 1. 복잡도가 complex면 무조건 사용
    if complexity.lower() == "complex":
        logger.info(f"Expert Panel activated: complexity is 'complex'")
        return True

    # 2. 신뢰도가 낮으면 사용
    if confidence < 0.5:
        logger.info(f"Expert Panel activated: low confidence ({confidence:.2f})")
        return True

    # 3. 고급 키워드 포함 시 사용
    query_lower = query.lower()
    for keyword in EXPERT_TRIGGER_KEYWORDS:
        if keyword.lower() in query_lower:
            logger.info(f"Expert Panel activated: trigger keyword '{keyword}' found")
            return True

    return False


def needs_collaboration(
    query: str,
    primary_expert: ExpertRole,
) -> Optional[List[ExpertRole]]:
    """
    다중 전문가 협업이 필요한지 판단

    특정 패턴의 질문은 여러 전문가의 협업이 필요할 수 있음

    Args:
        query: 사용자 질문
        primary_expert: 주 전문가 역할

    Returns:
        추가로 필요한 전문가 목록 (협업 불필요 시 None)
    """
    query_lower = query.lower()

    for trigger_keywords, collaboration_experts in COLLABORATION_PATTERNS:
        # 모든 트리거 키워드가 질문에 포함되어야 함
        matches = sum(1 for kw in trigger_keywords if kw.lower() in query_lower)

        # 트리거 키워드 중 2개 이상 매칭 시 협업 필요
        if matches >= 2:
            # 주 전문가를 제외한 추가 전문가 목록 생성
            additional_experts = [
                expert
                for expert in collaboration_experts
                if expert != primary_expert
            ]

            if additional_experts:
                logger.info(
                    f"Collaboration needed: primary={primary_expert.value}, "
                    f"additional={[e.value for e in additional_experts]}"
                )
                return additional_experts

    return None


def get_best_expert_for_query(query: str) -> ExpertRole:
    """
    질문에 가장 적합한 단일 전문가 반환

    Args:
        query: 사용자 질문

    Returns:
        가장 적합한 전문가 역할
    """
    results = route_to_expert(query, top_k=1)
    if results:
        return results[0][0]
    # 기본값으로 정책 전문가 반환
    return ExpertRole.POLICY_EXPERT


def get_expert_team_for_query(
    query: str,
    category: Optional[str] = None,
) -> List[ExpertRole]:
    """
    질문에 적합한 전문가 팀 구성

    주 전문가를 선정하고 협업이 필요한 경우 추가 전문가를 포함

    Args:
        query: 사용자 질문
        category: 질문 카테고리 (선택)

    Returns:
        전문가 팀 (역할 목록)
    """
    # 상위 1명 선정
    primary_results = route_to_expert(query, category=category, top_k=1)
    if not primary_results:
        return [ExpertRole.POLICY_EXPERT]

    primary_expert = primary_results[0][0]
    team = [primary_expert]

    # 협업 필요 여부 확인
    additional = needs_collaboration(query, primary_expert)
    if additional:
        team.extend(additional)

    # 중복 제거하면서 순서 유지
    seen = set()
    unique_team = []
    for expert in team:
        if expert not in seen:
            seen.add(expert)
            unique_team.append(expert)

    logger.info(f"Expert team for query: {[e.value for e in unique_team]}")
    return unique_team
