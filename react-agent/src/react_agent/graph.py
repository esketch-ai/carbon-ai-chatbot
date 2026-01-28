"""Define a custom Reasoning and Action agent.

Works with a chat model with tool calling support.
"""
# 카테고리 별 특화 프롬프트 생성 파트


import os
import json
import asyncio
from datetime import UTC, datetime
from typing import Dict, List, Literal, cast, Optional, Any

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from react_agent.configuration import Configuration
from react_agent.state import InputState, State
from react_agent.tools import TOOLS, get_all_tools, search_knowledge_base, search
from react_agent.utils import (
    detect_and_convert_mermaid,
    analyze_conversation_context,
    build_context_aware_prompt_addition,
)
from react_agent.cache_manager import get_cache_manager

# Ensure .env is loaded so ANTHROPIC_API_KEY is available
load_dotenv()

# ==================== 병렬 도구 호출 시스템 ====================

async def smart_tool_prefetch(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """질문을 분석하고 필요한 도구들을 병렬로 미리 실행

    이 노드는 사용자 질문을 분석하여 필요한 도구들을 판단하고,
    병렬로 실행하여 결과를 state에 저장합니다.
    이를 통해 LLM이 여러 번 도구를 호출하는 것을 방지하고 속도를 개선합니다.
    """
    # 마지막 사용자 메시지 추출
    last_human_message = None
    for msg in reversed(state.messages):
        if isinstance(msg, HumanMessage):
            last_human_message = msg.content
            break

    if not last_human_message:
        return {}

    # FAQ 캐시 확인 먼저
    cache_manager = get_cache_manager()
    faq_answer = cache_manager.get_faq(last_human_message)
    if faq_answer:
        print(f"✅ FAQ 캐시 히트")
        return {
            "messages": [AIMessage(content=faq_answer)],
            "prefetched_context": {"source": "faq_cache"}
        }

    # RAG 검색 실행
    tasks = []
    task_names = []

    tasks.append(asyncio.create_task(_safe_rag_search(last_human_message)))
    task_names.append("RAG")

    # 병렬 실행
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 처리
        prefetched_context = {}
        for i, (result, name) in enumerate(zip(results, task_names)):
            if isinstance(result, Exception):
                prefetched_context[name] = {"error": str(result)}
            else:
                prefetched_context[name] = result

        return {
            "prefetched_context": prefetched_context
        }
    else:
        return {}


async def _safe_rag_search(query: str) -> Dict[str, Any]:
    """RAG 검색을 안전하게 실행 (예외 처리 포함)

    RAG에서 문서를 찾지 못하면 웹 검색을 수행합니다.
    단, NET-Z 관련 질문은 MCP 도구를 사용해야 하므로 웹 검색을 스킵합니다.
    """
    try:
        result = search_knowledge_base.invoke({"query": query, "k": 3, "use_hybrid": True})

        # RAG에서 문서를 찾지 못한 경우
        if result.get("status") == "no_results":
            # NET-Z 관련 질문인지 확인
            query_lower = query.lower()
            is_netz_query = any(kw in query_lower for kw in [
                'netz', 'net-z', '넷지', '넷제로',
                '등록된 회사', '기업 목록', '배출량 데이터',
                'enterprise', 'company list'
            ])

            if is_netz_query:
                # NET-Z 질문은 웹 검색 스킵, LLM이 MCP 도구 사용하도록 유도
                print(f"🔧 NET-Z 질문 감지 → MCP 도구 사용 대기")
                return result

            # 일반 질문은 웹 검색 폴백
            print(f"🌐 웹 검색 실행 중...")
            try:
                web_result = await search(query)
                if web_result:
                    print(f"✅ 웹 검색 완료")
                    return {
                        "status": "web_fallback",
                        "message": f"지식베이스에서 관련 문서를 찾지 못해 웹 검색을 수행했습니다.",
                        "rag_results": [],
                        "web_results": web_result,
                        "fallback_used": True
                    }
                else:
                    return result
            except Exception as web_error:
                print(f"❌ 웹 검색 오류: {web_error}")
                return result

        return result
    except Exception as e:
        print(f"[RAG ERROR] {e}")
        return {"status": "error", "message": str(e), "results": []}


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

    # Initialize the model with tool binding
    llm = ChatAnthropic(temperature=0.1, model=configuration.model)
    model = llm.bind_tools(all_tools)

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

    # 🚀 Prefetched context가 있으면 시스템 메시지에 추가
    if hasattr(state, 'prefetched_context') and state.prefetched_context:
        context_info = "\n\n**⚡ 미리 조회된 정보 (도구 재호출 불필요):**\n"

        # RAG 검색 결과
        if "RAG" in state.prefetched_context:
            rag_result = state.prefetched_context["RAG"]
            if rag_result.get("status") == "success":
                context_info += f"\n📚 **지식베이스 검색 완료**: {rag_result.get('message', '')}\n"
                context_info += "검색된 문서:\n"
                for doc in rag_result.get("results", [])[:3]:
                    context_info += f"- {doc.get('metadata', {}).get('source', 'Unknown')}: {doc.get('page_content', '')[:200]}...\n"
            elif rag_result.get("status") == "web_fallback":
                # 웹 검색 폴백이 사용된 경우
                context_info += f"\n🌐 **웹 검색 수행**: {rag_result.get('message', '')}\n"
                web_results = rag_result.get("web_results", {})

                # Tavily returns dict with "results" key containing list
                if isinstance(web_results, dict):
                    results_list = web_results.get("results", [])
                elif isinstance(web_results, list):
                    results_list = web_results
                else:
                    results_list = []

                if results_list:
                    context_info += "웹 검색 결과:\n"
                    for item in results_list[:5]:
                        if isinstance(item, dict):
                            title = item.get("title", "")
                            url = item.get("url", "")
                            content = item.get("content", "")
                            context_info += f"- [{title}]({url})\n  {content[:200]}...\n"
                        else:
                            context_info += f"- {str(item)[:200]}\n"
            else:
                context_info += f"\n📚 지식베이스: {rag_result.get('message', '검색 결과 없음')}\n"

        # MCP 결과 등 추가 가능

        context_info += "\n위 정보를 활용하여 답변하세요. 이미 조회된 정보이므로 동일한 도구를 다시 호출하지 마세요.\n"
        system_message += context_info

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
    try:
        response = cast(
            AIMessage,
            await model.ainvoke(
                [{"role": "system", "content": system_message}, *state.messages]
            ),
        )

        # 도구 호출 로깅
        if response.tool_calls:
            tool_names = [tc.get('name', 'unknown') for tc in response.tool_calls]
            print(f"🔧 도구 호출: {', '.join(tool_names)}")

    except asyncio.CancelledError:
        print(f"❌ 클라이언트 연결 끊김")
        raise
    except Exception as e:
        print(f"❌ 모델 호출 오류: {type(e).__name__}: {e}")
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


# ==================== 라우팅 함수 ====================

def route_after_prefetch(state: State) -> Literal["call_model", "__end__"]:
    """Prefetch 이후 라우팅 결정

    FAQ 캐시에서 답변이 왔으면 바로 종료, 아니면 call_model로 진행
    """
    # FAQ 캐시에서 답변이 왔는지 확인
    if hasattr(state, 'prefetched_context') and state.prefetched_context:
        if state.prefetched_context.get("source") == "faq_cache":
            print("[ROUTE] FAQ 캐시 히트, 즉시 종료")
            return "__end__"

    # 일반적인 경우 call_model로 진행
    return "call_model"


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


# Define a new graph

builder = StateGraph(State, input=InputState, config_schema=Configuration)

# Define the nodes
builder.add_node("smart_prefetch", smart_tool_prefetch)  # 🚀 병렬 도구 미리 실행
builder.add_node(call_model)
builder.add_node("tools", call_tools)  # 동적 도구 로드

# Set the entrypoint as smart_prefetch (병렬 도구 실행부터 시작)
builder.add_edge("__start__", "smart_prefetch")

# Prefetch 이후 조건부 라우팅 (FAQ 캐시 히트면 바로 종료)
builder.add_conditional_edges(
    "smart_prefetch",
    route_after_prefetch,
    {
        "call_model": "call_model",
        "__end__": "__end__"
    }
)

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
