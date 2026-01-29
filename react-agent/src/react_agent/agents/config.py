"""
에이전트 설정 및 레지스트리
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class AgentRole(str, Enum):
    """에이전트 역할 정의"""
    MANAGER = "manager"
    SIMPLE = "simple"
    CARBON_EXPERT = "carbon_expert"
    REGULATION_EXPERT = "regulation_expert"
    SUPPORT_EXPERT = "support_expert"


@dataclass
class AgentConfig:
    """에이전트 설정"""
    role: AgentRole
    name: str
    description: str
    model: str
    temperature: float
    tools: List[str]  # 사용 가능한 도구 이름 목록

    # 복잡도 처리 범위
    min_complexity: str  # simple/medium/complex
    max_complexity: str


# 에이전트 레지스트리

AGENT_REGISTRY = {

    # 매니저 에이전트
    AgentRole.MANAGER: AgentConfig(
        role=AgentRole.MANAGER,
        name="매니저 에이전트",
        description="질문 복잡도 분석 및 에이전트 할당",
        model="claude-haiku-4-5",  # 빠른 라우팅을 위해 Haiku (속도 최적화)
        temperature=0.0,
        tools=[],  # 판단만 하고 도구 사용 안 함
        min_complexity="simple",
        max_complexity="complex"
    ),

    # 간단 답변 에이전트 (Haiku - 빠르고 저렴)
    AgentRole.SIMPLE: AgentConfig(
        role=AgentRole.SIMPLE,
        name="일반 답변 에이전트",
        description="기본 질문 및 간단한 조회 답변",
        model="claude-haiku-4-5",
        temperature=0.1,
        tools=[
            "search_knowledge_base",  # RAG 검색
            "search",  # 웹 검색
            "classify_customer_segment"
        ],
        min_complexity="simple",
        max_complexity="simple"
    ),

    # 탄소배출권 전문가 (Haiku)
    AgentRole.CARBON_EXPERT: AgentConfig(
        role=AgentRole.CARBON_EXPERT,
        name="탄소배출권 전문가",
        description="배출권 거래, NET-Z 플랫폼, 시장 분석",
        model="claude-haiku-4-5",
        temperature=0.1,
        tools=[
            "search_knowledge_base",
            "search",  # 웹 검색 추가 (최신 시장 동향 등)
            "get_transaction_volume",
            "get_market_price",
            "get_emission_allocation",
            "search_carbon_credits",
            "calculate_trading_fee"
        ],
        min_complexity="medium",
        max_complexity="complex"
    ),

    # 규제대응 전문가 (Haiku)
    AgentRole.REGULATION_EXPERT: AgentConfig(
        role=AgentRole.REGULATION_EXPERT,
        name="규제대응 전문가",
        description="Scope 배출량, 법규 준수, 보고서",
        model="claude-haiku-4-5",
        temperature=0.1,
        tools=[
            "search_knowledge_base",
            "search",  # 최신 규제 웹 검색
            "calculate_scope_emissions",
            "get_compliance_report",
            "validate_emission_data"
        ],
        min_complexity="medium",
        max_complexity="complex"
    ),

    # 고객지원 전문가 (Haiku)
    AgentRole.SUPPORT_EXPERT: AgentConfig(
        role=AgentRole.SUPPORT_EXPERT,
        name="고객지원 전문가",
        description="서비스 안내, 문제 해결, 솔루션 제안",
        model="claude-haiku-4-5",
        temperature=0.2,
        tools=[
            "search_knowledge_base",  # RAG 검색
            "search",  # 웹 검색
            "classify_customer_segment",
            "get_customer_history"
        ],
        min_complexity="simple",
        max_complexity="medium"
    )
}


def get_agent_config(role: AgentRole) -> AgentConfig:
    """에이전트 설정 가져오기"""
    return AGENT_REGISTRY[role]


def get_available_agents_for_category(category: str) -> List[AgentRole]:
    """카테고리별 사용 가능한 에이전트 목록"""
    category_agents = {
        "탄소배출권": [AgentRole.SIMPLE, AgentRole.CARBON_EXPERT],
        "규제대응": [AgentRole.SIMPLE, AgentRole.REGULATION_EXPERT],
        "고객상담": [AgentRole.SIMPLE, AgentRole.SUPPORT_EXPERT]
    }
    return category_agents.get(category, [AgentRole.SIMPLE])
