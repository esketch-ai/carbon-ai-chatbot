"""멀티 에이전트 ReAct 그래프

기존 단일 에이전트를 매니저 + 전문가 구조로 확장
- Manager: 질문 복잡도 분석 및 에이전트 할당 (Sonnet)
- Simple Agent: 기본 질문 답변 (Haiku)
- Expert Agents: 전문 분야 답변 (Haiku)
"""

import asyncio
from typing import Dict, List, Literal, Any

from dotenv import load_dotenv
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from react_agent.configuration import Configuration
from react_agent.state import InputState, State
from react_agent.tools import get_all_tools

# 멀티 에이전트 노드 임포트
from react_agent.agents import manager_agent, simple_agent, expert_agent

# 기존 graph.py의 함수들 재사용
from react_agent.graph import smart_tool_prefetch, _safe_rag_search

# Ensure .env is loaded
load_dotenv()


# ==================== 도구 호출 노드 (재사용) ====================

async def call_tools(state: State) -> Dict[str, List[ToolMessage]]:
    """동적으로 도구를 로드하고 호출"""
    all_tools = await get_all_tools()
    tool_node = ToolNode(all_tools)
    return await tool_node.ainvoke(state)


# ==================== 라우팅 함수 ====================

def route_after_prefetch(state: State) -> Literal["manager_agent", "__end__"]:
    """Prefetch 후 라우팅

    FAQ 캐시 히트면 바로 종료, 아니면 Manager로
    """
    if hasattr(state, 'prefetched_context') and state.prefetched_context:
        if state.prefetched_context.get("source") == "faq_cache":
            print("[ROUTE] FAQ 캐시 히트 → 즉시 종료")
            return "__end__"

    print("[ROUTE] Prefetch 완료 → Manager Agent")
    return "manager_agent"


def route_after_manager(state: State) -> Literal["simple_agent", "expert_agent"]:
    """Manager 판단 후 라우팅

    Simple 또는 Expert 에이전트로 분기
    """
    decision = state.manager_decision
    assigned = decision.get("assigned_agent", "simple")

    if assigned == "simple":
        print(f"[ROUTE] Manager 결정: Simple Agent (복잡도: {decision.get('complexity')})")
        return "simple_agent"
    else:
        print(f"[ROUTE] Manager 결정: Expert Agent ({assigned}) (복잡도: {decision.get('complexity')})")
        return "expert_agent"


def route_after_agent(state: State) -> Literal["tools", "__end__"]:
    """Agent 응답 후 라우팅

    도구 호출 필요하면 tools로, 아니면 종료
    """
    last_message = state.messages[-1]

    if last_message.tool_calls:
        tool_names = [tc.get('name', 'unknown') for tc in last_message.tool_calls]
        print(f"[ROUTE] 도구 호출 필요 → tools ({', '.join(tool_names)})")
        return "tools"

    print("[ROUTE] 답변 완료 → 종료")
    return "__end__"


def route_after_tools(state: State) -> Literal["simple_agent", "expert_agent"]:
    """도구 실행 후 원래 에이전트로 복귀

    agent_used 필드로 어떤 에이전트가 호출했는지 확인
    """
    agent_used = state.agent_used

    if agent_used == "simple":
        print("[ROUTE] 도구 실행 완료 → Simple Agent 복귀")
        return "simple_agent"
    else:
        print(f"[ROUTE] 도구 실행 완료 → Expert Agent ({agent_used}) 복귀")
        return "expert_agent"


# ==================== 그래프 구성 ====================

builder = StateGraph(State, input=InputState, config_schema=Configuration)

# 노드 추가
builder.add_node("smart_prefetch", smart_tool_prefetch)
builder.add_node("manager_agent", manager_agent)
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

# Manager → Simple or Expert
builder.add_conditional_edges(
    "manager_agent",
    route_after_manager,
    {
        "simple_agent": "simple_agent",
        "expert_agent": "expert_agent"
    }
)

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
checkpointer = MemorySaver()
graph = builder.compile(name="Multi-Agent System", checkpointer=checkpointer)
