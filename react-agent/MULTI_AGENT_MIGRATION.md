# 멀티 에이전트 마이그레이션 가이드

## 📋 개요

기존 단일 에이전트 구조를 멀티 에이전트 구조로 전환하는 가이드입니다.

---

## 🎯 변경 사항 요약

### 1. State 확장 ✅ (완료)
- `manager_decision`: 매니저의 판단 결과
- `agent_used`: 사용된 에이전트 이름

### 2. 새 디렉토리/파일 ✅ (완료)
```
react-agent/src/react_agent/agents/
├── __init__.py          # 에이전트 모듈 초기화
├── config.py            # 에이전트 설정 및 레지스트리
├── prompts.py           # 프롬프트 템플릿
└── nodes.py             # 에이전트 노드 구현
```

### 3. Graph 수정 (필요)
기존 `graph.py`에 새 노드 및 라우팅 추가

---

## 🔧 Graph.py 수정 방법

### Option A: 기존 파일 수정

#### 1. Import 추가

```python
# graph.py 상단에 추가
from react_agent.agents import (
    AgentRole,
    manager_agent,
    simple_agent,
    expert_agent
)
```

#### 2. 노드 추가 (기존 builder 수정)

```python
# 기존 노드
builder.add_node("smart_prefetch", smart_tool_prefetch)

# 새 노드 추가
builder.add_node("manager_agent", manager_agent)
builder.add_node("simple_agent", simple_agent)
builder.add_node("expert_agent", expert_agent)

# 기존 도구 노드
builder.add_node("tools", call_tools)
```

#### 3. 라우팅 함수 추가

```python
def route_after_prefetch(state: State) -> Literal["manager_agent", "__end__"]:
    """Prefetch 후 라우팅"""
    # FAQ 캐시 히트면 바로 종료
    if state.prefetched_context.get("source") == "faq_cache":
        return "__end__"

    # Manager로 라우팅
    return "manager_agent"


def route_after_manager(state: State) -> Literal["simple_agent", "expert_agent"]:
    """Manager 판단 후 라우팅"""
    decision = state.manager_decision
    assigned = decision.get("assigned_agent", "simple")

    if assigned == "simple":
        return "simple_agent"
    else:
        # carbon_expert, regulation_expert, support_expert
        return "expert_agent"


def route_after_agent(state: State) -> Literal["tools", "__end__"]:
    """Agent 응답 후 라우팅"""
    last_message = state.messages[-1]

    # 도구 호출 필요
    if last_message.tool_calls:
        return "tools"

    # 답변 완료
    return "__end__"
```

#### 4. 엣지 재구성

```python
# 기존 엣지 삭제하고 새로 구성

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

# Tools → 원래 에이전트로 돌아가기
def route_after_tools(state: State) -> Literal["simple_agent", "expert_agent"]:
    """도구 실행 후 원래 에이전트로"""
    agent_used = state.agent_used
    if agent_used == "simple":
        return "simple_agent"
    else:
        return "expert_agent"

builder.add_conditional_edges(
    "tools",
    route_after_tools,
    {
        "simple_agent": "simple_agent",
        "expert_agent": "expert_agent"
    }
)
```

---

### Option B: 새 파일 생성 (추천)

기존 `graph.py`를 `graph_single.py`로 백업하고 새로 작성

```python
# graph_multi.py (새 파일)

"""멀티 에이전트 그래프"""

from typing import Literal, Dict, Any
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

from react_agent.state import State, InputState
from react_agent.configuration import Configuration
from react_agent.agents import manager_agent, simple_agent, expert_agent

# 기존 함수 재사용
from react_agent.graph import smart_tool_prefetch, call_tools


# ============ 라우팅 로직 ============

def route_after_prefetch(state: State) -> Literal["manager_agent", "__end__"]:
    """Prefetch 후 라우팅"""
    if state.prefetched_context.get("source") == "faq_cache":
        return "__end__"
    return "manager_agent"


def route_after_manager(state: State) -> Literal["simple_agent", "expert_agent"]:
    """Manager 판단 후 라우팅"""
    assigned = state.manager_decision.get("assigned_agent", "simple")
    return "simple_agent" if assigned == "simple" else "expert_agent"


def route_after_agent(state: State) -> Literal["tools", "__end__"]:
    """Agent 응답 후 라우팅"""
    last_message = state.messages[-1]
    return "tools" if last_message.tool_calls else "__end__"


def route_after_tools(state: State) -> Literal["simple_agent", "expert_agent"]:
    """도구 실행 후 원래 에이전트로"""
    return "simple_agent" if state.agent_used == "simple" else "expert_agent"


# ============ 그래프 구성 ============

builder = StateGraph(State, input=InputState, config_schema=Configuration)

# 노드 추가
builder.add_node("smart_prefetch", smart_tool_prefetch)
builder.add_node("manager_agent", manager_agent)
builder.add_node("simple_agent", simple_agent)
builder.add_node("expert_agent", expert_agent)
builder.add_node("tools", call_tools)

# 엣지 정의
builder.add_edge("__start__", "smart_prefetch")

builder.add_conditional_edges(
    "smart_prefetch",
    route_after_prefetch,
    {"manager_agent": "manager_agent", "__end__": "__end__"}
)

builder.add_conditional_edges(
    "manager_agent",
    route_after_manager,
    {"simple_agent": "simple_agent", "expert_agent": "expert_agent"}
)

builder.add_conditional_edges(
    "simple_agent",
    route_after_agent,
    {"tools": "tools", "__end__": "__end__"}
)

builder.add_conditional_edges(
    "expert_agent",
    route_after_agent,
    {"tools": "tools", "__end__": "__end__"}
)

builder.add_conditional_edges(
    "tools",
    route_after_tools,
    {"simple_agent": "simple_agent", "expert_agent": "expert_agent"}
)

# 컴파일
checkpointer = MemorySaver()
graph = builder.compile(name="Multi-Agent System", checkpointer=checkpointer)
```

---

## 🧪 테스트 방법

### 1. 간단한 질문 (Simple Agent)

```python
from react_agent.graph_multi import graph

result = await graph.ainvoke(
    {"messages": [{"role": "user", "content": "배출권이 뭐에요?"}]},
    config={"configurable": {"category": "탄소배출권"}}
)

# 예상 흐름:
# smart_prefetch → manager (simple 할당) → simple_agent → END
```

### 2. 전문가 필요 질문 (Expert Agent)

```python
result = await graph.ainvoke(
    {"messages": [{"role": "user", "content": "오늘 NET-Z 거래량 조회해줘"}]},
    config={"configurable": {"category": "탄소배출권"}}
)

# 예상 흐름:
# smart_prefetch → manager (carbon_expert 할당) → expert_agent → tools → expert_agent → END
```

---

## 📊 성능 비교

### 단일 에이전트 (기존)
- API 호출: 1-2회
- 비용: Sonnet 1-2회
- 속도: 3-5초

### 멀티 에이전트 (신규)
- API 호출: 2-4회
  - Manager (Sonnet) 1회
  - Agent (Haiku) 1-3회
- 비용: Sonnet 1회 + Haiku 1-3회 (약 30% 절감)
- 속도: 4-6초 (약간 느림)

---

## 🎯 추천 전환 순서

1. **Phase 1: A/B 테스트 준비**
   - 기존 `graph.py` 백업
   - `graph_multi.py` 작성
   - 환경변수로 선택 가능하게

2. **Phase 2: 테스트**
   - 간단한 질문 → Simple Agent 정확도
   - 복잡한 질문 → Expert Agent 정확도
   - Manager 판단 정확도 측정

3. **Phase 3: 점진적 전환**
   - 특정 카테고리만 멀티 에이전트
   - 성과 좋으면 전체 전환

---

## ⚠️ 주의사항

1. **Manager 판단 오류**
   - Simple로 잘못 할당 → Expert 필요한 질문 실패
   - Expert로 잘못 할당 → 비용 낭비
   → 로그 분석 및 프롬프트 개선 필요

2. **도구 필터링**
   - 각 에이전트는 허용된 도구만 사용
   - tools.py의 도구 이름과 정확히 일치해야 함

3. **캐시 무효화**
   - 에이전트 구조 변경 시 LLM 캐시 클리어 필요

---

## 📝 다음 단계

1. ✅ State 확장 (완료)
2. ✅ 에이전트 모듈 생성 (완료)
3. ⬜ Graph 수정/생성
4. ⬜ 테스트 및 검증
5. ⬜ 프롬프트 튜닝
6. ⬜ 성능 측정 및 최적화
