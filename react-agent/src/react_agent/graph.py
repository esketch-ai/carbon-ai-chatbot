"""Define a custom Reasoning and Action agent.

Works with a chat model with tool calling support.
"""
# 카테고리 별 특화 프롬프트 생성 파트


import os
import json
from datetime import UTC, datetime
from typing import Dict, List, Literal, cast

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from react_agent.configuration import Configuration
from react_agent.state import InputState, State
from react_agent.tools import TOOLS, get_all_tools
from react_agent.utils import (
    detect_and_convert_mermaid,
    analyze_conversation_context,
    build_context_aware_prompt_addition,
)
from react_agent.cache_manager import get_cache_manager

# Ensure .env is loaded so ANTHROPIC_API_KEY is available
load_dotenv()

# Define the function that calls the model

def _get_category_prompt(base_prompt: str, category: str) -> str:
    """카테고리별 특화 프롬프트 생성"""
    category_prompts = {
        "탄소배출권": """
**카테고리: 탄소배출권 전문 상담**

이 카테고리는 배출권 거래, 구매, 판매, 관리에 특화되어 있습니다.

**특화 답변 포인트:**
- 배출권 유형별 상세 설명 (KOC, KCU, KAU 등)
- 배출권 거래 절차 및 시장 동향
- NET-Z 플랫폼 사용법 및 기능
- 배출권 가격 정보 및 시장 분석
- 배출권 보유 관리 전략
- 구매/판매 시 주의사항 및 절차

**답변 시 중점:**
- 구체적인 절차와 단계를 명확히 설명
- 시장 가격 및 동향 정보 제공
- 실제 거래 사례 및 활용 방법 제시
- 프로세스나 절차는 Mermaid 다이어그램으로 시각화하면 효과적입니다
""",
        "규제대응": """
**카테고리: 규제대응 전문 상담**

이 카테고리는 탄소 규제, 법규, 보고서, 컴플라이언스 대응에 특화되어 있습니다.

**특화 답변 포인트:**
- Scope 1, 2, 3 배출량 측정 방법
- 탄소 배출량 보고 의무 및 절차
- 규제 변경사항 및 대응 방안
- ESG 보고서 작성 가이드
- 탄소 중립 목표 달성 전략
- 규제 미준수 시 제재 내용
- 탄소 배출량 인증 절차

**답변 시 중점:**
- 법규 및 규제 내용을 정확히 설명
- 컴플라이언스 체크리스트 제공
- 보고서 작성 가이드 및 템플릿 안내
- 규제 변경사항에 대한 대응 전략 제시
- 프로세스나 타임라인은 Mermaid 다이어그램으로 시각화하면 효과적입니다
""",
        "고객상담": """
**카테고리: 고객상담 전문 상담**

이 카테고리는 1:1 맞춤 상담, 서비스 안내, 문의사항에 특화되어 있습니다.

**특화 답변 포인트:**
- 후시파트너스 서비스 소개
- 기업 규모별 추천 솔루션
- 서비스 이용 절차 안내
- 비용 및 요금제 정보
- 전문가 상담 예약 안내
- 맞춤형 솔루션 제안

**답변 시 중점:**
- 친절하고 상세한 서비스 안내
- 고객 상황에 맞는 솔루션 제안
- 다음 단계 및 연락처 안내
- FAQ 및 일반적인 문의사항 해결
- 비교나 프로세스는 Mermaid 다이어그램으로 시각화하면 효과적입니다
"""
    }
    
    category_prompt = category_prompts.get(category, "")
    if category_prompt:
        return base_prompt + "\n\n" + category_prompt
    return base_prompt


def _serialize_messages_for_cache(messages: List, system_message: str, category: str) -> str:
    """메시지 히스토리를 캐시 키로 직렬화"""
    # 메시지를 간단한 형태로 변환 (content만 추출)
    simplified = []
    for msg in messages:
        if isinstance(msg, (HumanMessage, AIMessage, SystemMessage)):
            simplified.append({
                "type": msg.__class__.__name__,
                "content": str(msg.content)[:500]  # 너무 긴 메시지는 자름
            })
        elif isinstance(msg, ToolMessage):
            # 툴 메시지는 캐싱하지 않음 (동적 결과)
            return None

    cache_data = {
        "system": system_message[:200],  # 시스템 메시지 일부
        "category": category,
        "messages": simplified
    }
    return json.dumps(cache_data, ensure_ascii=False, sort_keys=True)


async def call_model(
    state: State, config: RunnableConfig
) -> Dict[str, List[AIMessage]]:
    """Call the LLM powering our "agent".

    This function prepares the prompt, initializes the model, and processes the response.

    Args:
        state (State): The current state of the conversation.
        config (RunnableConfig): Configuration for the model run.

    Returns:
        dict: A dictionary containing the model's response message.
    """
    configuration = Configuration.from_runnable_config(config)

    # MCP 도구를 포함한 전체 도구 목록 가져오기
    all_tools = await get_all_tools()
    # Safely get tool names (handle both Tool objects and functions)
    tool_names = []
    for tool in all_tools:
        if hasattr(tool, 'name'):
            tool_names.append(tool.name)
        elif hasattr(tool, '__name__'):
            tool_names.append(tool.__name__)
        else:
            tool_names.append(str(type(tool).__name__))
    print(f"[CALL_MODEL] Loaded {len(all_tools)} tools: {tool_names}")

    # Initialize the model with tool binding. Change the model or add more tools here.
    # ChatAnthropic 객체 생성
    # Enable streaming so LangGraph can emit token chunks during astream
    llm = ChatAnthropic(
        temperature=0.1,
        model=configuration.model,
        streaming=True
    )
    model = llm.bind_tools(all_tools)
    print(f"[CALL_MODEL] Model initialized with tools bound")

    # Format the system prompt. Customize this to change the agent's behavior.
    # 카테고리별 프롬프트 커스터마이징
    base_prompt = configuration.system_prompt
    if configuration.category:
        base_prompt = _get_category_prompt(base_prompt, configuration.category)

    # 🔥 대화 맥락 분석 및 프롬프트 추가
    conversation_context = analyze_conversation_context(state.messages)
    context_prompt_addition = build_context_aware_prompt_addition(conversation_context)

    # 시스템 메시지 생성 (맥락 정보 포함)
    system_message = base_prompt.format(
        system_time=datetime.now(tz=UTC).isoformat()
    )

    # 맥락 정보가 있으면 시스템 메시지에 추가
    if context_prompt_addition:
        system_message += context_prompt_addition

    # LLM 응답 캐싱 (오프너 질문 등 반복적인 질문에 대해)
    cache_manager = get_cache_manager()
    cache_key_content = _serialize_messages_for_cache(
        state.messages,
        system_message,
        configuration.category or ""
    )

    # 캐시 확인 (툴 호출이 있는 경우는 제외)
    cached_response = None
    if cache_key_content and not state.is_last_step:
        cached_response = cache_manager.get("llm", cache_key_content)
        if cached_response:
            # 캐시된 응답을 AIMessage로 복원
            return {
                "messages": [AIMessage(
                    content=cached_response.get("content", ""),
                    additional_kwargs=cached_response.get("additional_kwargs", {}),
                    id=cached_response.get("id", "cached")
                )]
            }

    # Get the model's response
    import asyncio
    try:
        response = cast(  # 전체 대화 히스토리를 펼쳐서 ai에게 전달
            AIMessage,
            await model.ainvoke(
                [{"role": "system", "content": system_message}, *state.messages]
            ),
        ) # ainvoke는 모델을 비동기적으로 호출하고 그 결과를 반환받는 함수
    except asyncio.CancelledError:
        print(f"[CALL_MODEL] Client disconnected during model invocation - propagating cancellation")
        # Re-raise to properly cleanup the entire chain
        # Don't return a message as the client has already disconnected
        raise
    except Exception as e:
        print(f"[CALL_MODEL ERROR] {type(e).__name__}: {e}")
        raise

    # Handle the case when it's the last step and the model still wants to use a tool
    # 툴을 사용해야 한다고 판단할 경우
    if state.is_last_step and response.tool_calls:
        return {
            "messages": [
                AIMessage(
                    id=response.id,
                    content="Sorry, I could not find an answer to your question in the specified number of steps.",
                )
            ]
        }

    # Mermaid 코드 블록을 이미지로 자동 변환
    # (Claude가 MCP 도구 대신 mermaid를 출력한 경우 처리)
    if response.content and isinstance(response.content, str):
        converted_content = detect_and_convert_mermaid(response.content)
        if converted_content != response.content:
            # 새로운 AIMessage 생성 (content가 변경된 경우)
            response = AIMessage(
                id=response.id,
                content=converted_content,
                tool_calls=response.tool_calls if hasattr(response, 'tool_calls') else [],
                additional_kwargs=response.additional_kwargs,
            )
    elif response.content and isinstance(response.content, list):
        # content가 리스트인 경우 (멀티모달 등)
        new_content = []
        content_changed = False
        for item in response.content:
            if isinstance(item, str):
                converted = detect_and_convert_mermaid(item)
                if converted != item:
                    content_changed = True
                new_content.append(converted)
            elif isinstance(item, dict) and 'text' in item:
                converted = detect_and_convert_mermaid(item['text'])
                if converted != item['text']:
                    content_changed = True
                new_content.append({**item, 'text': converted})
            else:
                new_content.append(item)

        if content_changed:
            response = AIMessage(
                id=response.id,
                content=new_content,
                tool_calls=response.tool_calls if hasattr(response, 'tool_calls') else [],
                additional_kwargs=response.additional_kwargs,
            )

    # LLM 응답 캐싱 (툴 호출이 없는 최종 응답만)
    if cache_key_content and not response.tool_calls:
        cache_data = {
            "content": response.content,
            "additional_kwargs": response.additional_kwargs,
            "id": response.id
        }
        cache_manager.set("llm", cache_key_content, cache_data)

    # Return the model's response as a list to be added to existing messages
    # 🔥 대화 맥락도 함께 업데이트
    return {
        "messages": [response],
        "conversation_context": conversation_context
    }


async def call_tools(state: State) -> Dict[str, List[ToolMessage]]:
    """동적으로 도구를 로드하고 호출"""
    # MCP 도구를 포함한 전체 도구 목록 가져오기
    all_tools = await get_all_tools()

    # ToolNode와 동일하게 동작
    tool_node = ToolNode(all_tools)
    return await tool_node.ainvoke(state)


# Define a new graph

builder = StateGraph(State, input=InputState, config_schema=Configuration)

# Define the two nodes we will cycle between
builder.add_node(call_model)
builder.add_node("tools", call_tools)  # 동적 도구 로드

# Set the entrypoint as `call_model`
# This means that this node is the first one called
builder.add_edge("__start__", "call_model")


def route_model_output(state: State) -> Literal["__end__", "tools"]:
    """Determine the next node based on the model's output.

    This function checks if the model's last message contains tool calls.

    Args:
        state (State): The current state of the conversation.

    Returns:
        str: The name of the next node to call ("__end__" or "tools").
    """
    last_message = state.messages[-1]
    if not isinstance(last_message, AIMessage):
        raise ValueError(
            f"Expected AIMessage in output edges, but got {type(last_message).__name__}"
        )
    # If there is no tool call, then we finish
    if not last_message.tool_calls:
        return "__end__"
    # Otherwise we execute the requested actions
    return "tools"


# Add a conditional edge to determine the next step after `call_model`
builder.add_conditional_edges(
    "call_model",
    # After call_model finishes running, the next node(s) are scheduled
    # based on the output from route_model_output
    route_model_output,
)

# Add a normal edge from `tools` to `call_model`
# This creates a cycle: after using tools, we always return to the model
builder.add_edge("tools", "call_model")

# Compile the builder into an executable graph with checkpointer
# MemorySaver allows the graph to store and retrieve conversation history
checkpointer = MemorySaver()
graph = builder.compile(name="ReAct Agent", checkpointer=checkpointer)
