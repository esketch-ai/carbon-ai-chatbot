"""멀티 에이전트 ReAct 그래프

기존 단일 에이전트를 매니저 + 전문가 구조로 확장
- Manager: 질문 복잡도 분석 및 에이전트 할당 (Sonnet)
- Simple Agent: 기본 질문 답변 (Haiku)
- Expert Agents: 전문 분야 답변 (Haiku)
"""

import time
import logging
import asyncio
from typing import Dict, List, Literal, Any, Optional

from dotenv import load_dotenv
from langchain_core.messages import ToolMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from react_agent.configuration import Configuration
from react_agent.checkpointer import get_checkpointer
from react_agent.state import InputState, State
from react_agent.tools import get_all_tools

# 멀티 에이전트 노드 임포트
from react_agent.agents import manager_agent, simple_agent, expert_agent

# 기존 graph.py의 함수들 재사용
from react_agent.graph import smart_tool_prefetch, _safe_rag_search

# Ensure .env is loaded
load_dotenv()

import os

logger = logging.getLogger(__name__)

# 신뢰도 기반 라우팅 설정
# 환경변수로 조정 가능 (기본값: 0.7)
CONFIDENCE_THRESHOLD = float(os.getenv("ROUTING_CONFIDENCE_THRESHOLD", "0.7"))


def get_confidence_threshold() -> float:
    """현재 신뢰도 임계값 반환"""
    return CONFIDENCE_THRESHOLD


def route_with_confidence(
    assigned_agent: str,
    confidence: float,
    threshold: float = None
) -> Dict[str, Any]:
    """
    신뢰도 기반 라우팅 결정 헬퍼 함수

    Args:
        assigned_agent: 매니저가 배정한 에이전트 이름
        confidence: 배정 신뢰도 (0.0-1.0)
        threshold: 신뢰도 임계값 (None이면 기본값 사용)

    Returns:
        라우팅 결정 딕셔너리:
        - action: "route" | "clarify"
        - agent: 배정될 에이전트 (action이 "route"일 때만)
        - message: 명확화 요청 메시지 (action이 "clarify"일 때만)
        - suggested_category: 추천 카테고리 (action이 "clarify"일 때만)
    """
    if threshold is None:
        threshold = CONFIDENCE_THRESHOLD

    if confidence < threshold:
        # 신뢰도 낮으면 명확화 요청
        category_names = {
            "simple": "기본 정보",
            "carbon_expert": "탄소배출권",
            "regulation_expert": "규제대응",
            "support_expert": "고객지원"
        }
        friendly_category = category_names.get(assigned_agent, assigned_agent)

        return {
            "action": "clarify",
            "message": f"'{friendly_category}' 관련 질문이 맞나요? 더 정확한 답변을 위해 확인해주세요.",
            "suggested_category": assigned_agent,
            "confidence": confidence,
            "threshold": threshold
        }

    return {
        "action": "route",
        "agent": assigned_agent,
        "confidence": confidence,
        "threshold": threshold
    }


# ==================== 신뢰도 기반 명확화 요청 노드 ====================

async def clarification_agent(state: State) -> Dict[str, Any]:
    """
    [명확화 요청 에이전트] 매니저의 신뢰도가 낮을 때 사용자에게 명확화 요청

    신뢰도가 CONFIDENCE_THRESHOLD 미만일 때 호출되어
    사용자에게 질문의 의도를 명확히 해달라고 요청합니다.
    """
    decision = state.manager_decision
    confidence = decision.get("confidence", 0.5)
    suggested_category = decision.get("assigned_agent", "simple")
    reasoning = decision.get("reasoning", "")

    # 카테고리별 친화적인 이름 매핑
    category_names = {
        "simple": "기본 정보",
        "carbon_expert": "탄소배출권",
        "regulation_expert": "규제대응",
        "support_expert": "고객지원"
    }

    friendly_category = category_names.get(suggested_category, suggested_category)

    # 명확화 요청 메시지 생성
    clarification_message = f"""죄송합니다, 질문의 의도를 정확히 파악하기 어렵습니다.
더 정확한 답변을 드리기 위해 확인하고 싶은 점이 있습니다.

현재 제가 이해한 바로는 **{friendly_category}** 관련 질문으로 보입니다.
(판단 근거: {reasoning})

다음 중 해당하는 항목이 있다면 알려주세요:

🔹 **탄소배출권** 관련 (거래, 시세, NET-Z 플랫폼 등)
🔹 **규제대응** 관련 (배출량 계산, 법규 준수, 보고서 등)
🔹 **고객지원** 관련 (서비스 이용, 계정 관리, 기술 문의 등)
🔹 **기타** - 구체적으로 어떤 정보가 필요하신지 알려주세요

---
💡 **예시로 질문을 다시 해주시면 더 정확한 답변이 가능합니다:**
- "배출권 현재 시세가 어떻게 되나요?"
- "우리 회사 Scope 1 배출량 계산 방법을 알려주세요"
- "NET-Z 회원가입은 어떻게 하나요?"
"""

    response = AIMessage(content=clarification_message)

    logger.info(
        f"[Clarification] 신뢰도 낮음 ({confidence:.2f} < {CONFIDENCE_THRESHOLD}) → "
        f"명확화 요청 (제안: {suggested_category})"
    )

    return {
        "messages": [response],
        "agent_used": "clarification"
    }


# ==================== 도구 호출 노드 (재사용) ====================

async def call_tools(state: State) -> Dict[str, List[ToolMessage]]:
    """동적으로 도구를 로드하고 호출"""
    # 호출된 도구 이름 추출
    last_message = state.messages[-1]
    tool_names = [tc.get('name', 'unknown') for tc in getattr(last_message, 'tool_calls', [])]

    t0 = time.perf_counter()
    all_tools = await get_all_tools()
    tool_node = ToolNode(all_tools)
    result = await tool_node.ainvoke(state)
    elapsed = time.perf_counter() - t0

    logger.info(f"⏱️ [도구 실행] 총 {elapsed:.2f}초 ({', '.join(tool_names)})")
    return result


# ==================== 라우팅 함수 ====================

def route_after_prefetch(state: State) -> Literal["manager_agent", "__end__"]:
    """Prefetch 후 라우팅

    FAQ 캐시 히트면 바로 종료, 아니면 Manager로
    """
    if hasattr(state, 'prefetched_context') and state.prefetched_context:
        if state.prefetched_context.get("source") == "faq_cache":
            logger.info("[ROUTE] FAQ 캐시 히트 → 즉시 종료")
            return "__end__"

    logger.info("[ROUTE] Prefetch 완료 → Manager Agent")
    return "manager_agent"


def route_after_manager(state: State) -> Literal["simple_agent", "expert_agent", "clarification_agent"]:
    """Manager 판단 후 라우팅

    신뢰도 기반 라우팅:
    - 신뢰도 >= CONFIDENCE_THRESHOLD: Simple 또는 Expert 에이전트로 분기
    - 신뢰도 < CONFIDENCE_THRESHOLD: 명확화 요청 에이전트로 분기
    """
    decision = state.manager_decision
    assigned = decision.get("assigned_agent", "simple")
    confidence = decision.get("confidence", 0.5)
    complexity = decision.get("complexity", "unknown")

    # 신뢰도가 낮으면 명확화 요청
    if confidence < CONFIDENCE_THRESHOLD:
        logger.info(
            f"[ROUTE] Manager 신뢰도 낮음 ({confidence:.2f} < {CONFIDENCE_THRESHOLD}) → "
            f"Clarification Agent (제안: {assigned})"
        )
        return "clarification_agent"

    # 신뢰도가 충분하면 원래 라우팅 로직
    if assigned == "simple":
        logger.info(
            f"[ROUTE] Manager 결정: Simple Agent "
            f"(복잡도: {complexity}, 신뢰도: {confidence:.2f})"
        )
        return "simple_agent"
    else:
        logger.info(
            f"[ROUTE] Manager 결정: Expert Agent ({assigned}) "
            f"(복잡도: {complexity}, 신뢰도: {confidence:.2f})"
        )
        return "expert_agent"


def route_after_agent(state: State) -> Literal["tools", "__end__"]:
    """Agent 응답 후 라우팅

    도구 호출 필요하면 tools로, 아니면 종료
    """
    last_message = state.messages[-1]

    if last_message.tool_calls:
        tool_names = [tc.get('name', 'unknown') for tc in last_message.tool_calls]
        logger.info(f"[ROUTE] 도구 호출 필요 → tools ({', '.join(tool_names)})")
        return "tools"

    logger.info("[ROUTE] 답변 완료 → 종료")
    return "__end__"


def route_after_tools(state: State) -> Literal["simple_agent", "expert_agent"]:
    """도구 실행 후 원래 에이전트로 복귀

    agent_used 필드로 어떤 에이전트가 호출했는지 확인
    """
    agent_used = state.agent_used

    if agent_used == "simple":
        logger.info("[ROUTE] 도구 실행 완료 → Simple Agent 복귀")
        return "simple_agent"
    else:
        logger.info(f"[ROUTE] 도구 실행 완료 → Expert Agent ({agent_used}) 복귀")
        return "expert_agent"


# ==================== 그래프 구성 ====================

builder = StateGraph(State, input=InputState, config_schema=Configuration)

# 노드 추가
builder.add_node("smart_prefetch", smart_tool_prefetch)
builder.add_node("manager_agent", manager_agent)
builder.add_node("clarification_agent", clarification_agent)  # 신뢰도 낮을 때 명확화 요청
builder.add_node("simple_agent", simple_agent)
builder.add_node("expert_agent", expert_agent)
builder.add_node("tools", call_tools)

# 엣지 정의
# 시작 → Prefetch
builder.add_edge("__start__", "smart_prefetch")

# Prefetch → Manager or End
builder.add_conditional_edges(
    "smart_prefetch",
    route_after_prefetch,
    {
        "manager_agent": "manager_agent",
        "__end__": "__end__"
    }
)

# Manager → Simple, Expert, or Clarification (신뢰도 기반)
builder.add_conditional_edges(
    "manager_agent",
    route_after_manager,
    {
        "simple_agent": "simple_agent",
        "expert_agent": "expert_agent",
        "clarification_agent": "clarification_agent"
    }
)

# Clarification Agent → End (명확화 요청 후 종료, 사용자 응답 대기)
builder.add_edge("clarification_agent", "__end__")

# Simple Agent → Tools or End
builder.add_conditional_edges(
    "simple_agent",
    route_after_agent,
    {
        "tools": "tools",
        "__end__": "__end__"
    }
)

# Expert Agent → Tools or End
builder.add_conditional_edges(
    "expert_agent",
    route_after_agent,
    {
        "tools": "tools",
        "__end__": "__end__"
    }
)

# Tools → 원래 Agent로 복귀
builder.add_conditional_edges(
    "tools",
    route_after_tools,
    {
        "simple_agent": "simple_agent",
        "expert_agent": "expert_agent"
    }
)

# 컴파일
# Checkpointer factory returns MemorySaver (default) or PostgresSaver (production)
checkpointer = get_checkpointer()
graph = builder.compile(name="Multi-Agent System", checkpointer=checkpointer)
