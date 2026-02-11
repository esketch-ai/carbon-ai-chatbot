"""Expert Panel 노드 구현 - LangGraph 노드"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from react_agent.state import State
from react_agent.configuration import Configuration
from react_agent.utils import detect_and_convert_mermaid, get_message_text
from react_agent.tools import get_all_tools

from .config import ExpertRole, EXPERT_REGISTRY, get_expert_by_role
from .prompts import get_expert_prompt
from .router import route_to_expert, needs_collaboration
from .collaboration import collaborate_experts, format_expert_header

logger = logging.getLogger(__name__)


async def expert_panel_router(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """
    [Expert Panel 라우터] 전문가 선정 및 협업 필요 여부 결정

    마지막 사용자 메시지를 분석하여:
    1. 가장 적합한 전문가를 선정
    2. 협업이 필요한 경우 추가 전문가 목록 반환

    Returns:
        {"expert_panel_decision": {
            "primary_expert": ExpertRole,
            "primary_score": float,
            "additional_experts": List[ExpertRole] or None,
            "needs_collaboration": bool,
            "query": str
        }}
    """
    configuration = Configuration.from_runnable_config(config)
    category = configuration.category or "탄소배출권"

    # 마지막 사용자 메시지 추출
    last_user_message = ""
    for msg in reversed(state.messages):
        if isinstance(msg, HumanMessage):
            last_user_message = get_message_text(msg)
            break

    if not last_user_message:
        logger.warning("[Expert Panel Router] 사용자 메시지를 찾을 수 없습니다")
        return {
            "expert_panel_decision": {
                "primary_expert": ExpertRole.POLICY_EXPERT,
                "primary_score": 0.0,
                "additional_experts": None,
                "needs_collaboration": False,
                "query": "",
            }
        }

    logger.info(f"[Expert Panel Router] 질문 분석 중: '{last_user_message[:50]}...'")

    # 1. 가장 적합한 전문가 선정
    t0 = time.perf_counter()
    expert_results = route_to_expert(last_user_message, category=category, top_k=1)
    routing_elapsed = time.perf_counter() - t0

    if not expert_results:
        logger.warning("[Expert Panel Router] 전문가 선정 실패, 기본 전문가 사용")
        primary_expert = ExpertRole.POLICY_EXPERT
        primary_score = 0.0
    else:
        primary_expert, primary_score = expert_results[0]

    logger.info(
        f"⏱️ [Expert Panel Router] {routing_elapsed:.2f}초 → "
        f"{primary_expert.value} (score: {primary_score:.2f})"
    )

    # 2. 협업 필요 여부 확인
    additional_experts = needs_collaboration(last_user_message, primary_expert)
    needs_collab = additional_experts is not None and len(additional_experts) > 0

    if needs_collab:
        expert_names = [e.value for e in additional_experts]
        logger.info(f"[Expert Panel Router] 협업 필요: {expert_names}")
    else:
        logger.info("[Expert Panel Router] 단일 전문가 모드")

    # 결정 반환
    decision = {
        "primary_expert": primary_expert,
        "primary_score": primary_score,
        "additional_experts": additional_experts,
        "needs_collaboration": needs_collab,
        "query": last_user_message,
    }

    return {"expert_panel_decision": decision}


async def expert_panel_agent(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """
    [Expert Panel 에이전트] 전문가 패널 응답 생성

    expert_panel_decision을 기반으로:
    1. 단일 전문가인 경우: 해당 전문가가 직접 응답
    2. 다중 전문가인 경우: 병렬로 응답 후 통합

    Returns:
        {"messages": [AIMessage], "agent_used": "expert_panel:..."}
    """
    configuration = Configuration.from_runnable_config(config)
    category = configuration.category or "탄소배출권"

    # expert_panel_decision에서 결정 가져오기
    # state에 expert_panel_decision이 없으면 manager_decision 사용
    panel_decision = getattr(state, 'expert_panel_decision', None)

    if panel_decision is None:
        # state에 직접 없으면 dict 접근 시도 (State가 dataclass인 경우)
        panel_decision = state.__dict__.get('expert_panel_decision', {})

    if not panel_decision:
        logger.warning("[Expert Panel Agent] panel_decision이 없습니다. 기본 전문가 사용")
        panel_decision = {
            "primary_expert": ExpertRole.POLICY_EXPERT,
            "needs_collaboration": False,
            "query": "",
        }

    primary_expert = panel_decision.get("primary_expert", ExpertRole.POLICY_EXPERT)
    needs_collab = panel_decision.get("needs_collaboration", False)
    additional_experts = panel_decision.get("additional_experts", [])
    query = panel_decision.get("query", "")

    logger.info(
        f"[Expert Panel Agent] 모드: {'다중 전문가' if needs_collab else '단일 전문가'}, "
        f"주 전문가: {primary_expert.value}"
    )

    try:
        if needs_collab and additional_experts:
            # 다중 전문가 병렬 실행
            all_experts = [primary_expert] + additional_experts
            response_content = await _run_multiple_experts(
                all_experts, state, category, query
            )
            agent_used = f"expert_panel:{'+'.join([e.value for e in all_experts])}"
        else:
            # 단일 전문가 실행
            response_content = await _run_single_expert(
                primary_expert, state, category
            )
            agent_used = f"expert_panel:{primary_expert.value}"

        # Mermaid 코드 블록을 이미지로 자동 변환
        if response_content and isinstance(response_content, str):
            converted_content = detect_and_convert_mermaid(response_content)
            if converted_content != response_content:
                logger.info("[Expert Panel Agent] Mermaid 다이어그램 변환 완료")
                response_content = converted_content

        # AIMessage 생성
        response = AIMessage(content=response_content)

        logger.info(f"[Expert Panel Agent] 응답 생성 완료: {agent_used}")

        return {
            "messages": [response],
            "agent_used": agent_used,
        }

    except Exception as e:
        logger.error(f"[Expert Panel Agent] 오류 발생: {e}", exc_info=True)

        # 오류 발생 시 기본 응답
        error_response = AIMessage(
            content=f"죄송합니다. 전문가 패널 응답 생성 중 오류가 발생했습니다. "
                    f"다시 시도해 주시거나, 질문을 다시 작성해 주세요."
        )

        return {
            "messages": [error_response],
            "agent_used": "expert_panel:error",
        }


async def _run_single_expert(
    expert_role: ExpertRole,
    state: State,
    category: str,
) -> str:
    """
    단일 전문가 실행

    Args:
        expert_role: 전문가 역할
        state: 현재 상태
        category: 질문 카테고리

    Returns:
        전문가 응답 문자열
    """
    expert_config = get_expert_by_role(expert_role)

    logger.info(
        f"[Expert: {expert_config.name}] 응답 생성 시작 "
        f"(역할: {expert_role.value})"
    )

    # 전문가 프롬프트 생성
    system_prompt = get_expert_prompt(
        expert_role,
        category,
        state.prefetched_context
    )

    # 도구 로드 및 필터링
    all_tools = await get_all_tools()

    # 전문가에게 허용된 도구만 필터링
    # 기본 도구 이름들 (MCP 도구는 별도로 모두 허용)
    base_tool_names = [
        "search_knowledge_base", "search", "classify_customer_segment",
        "geocode_location"
    ]

    allowed_tools = [
        tool for tool in all_tools
        if tool.name in expert_config.tools or tool.name not in base_tool_names
    ]

    logger.info(
        f"[Expert: {expert_config.name}] "
        f"도구 {len(allowed_tools)}개: {[t.name for t in allowed_tools]}"
    )

    # Claude Sonnet 모델 사용 (전문가는 고품질 응답 필요)
    llm = ChatAnthropic(
        temperature=0.3,
        model="claude-sonnet-4-20250514"
    )
    model = llm.bind_tools(allowed_tools) if allowed_tools else llm

    # LLM 호출
    t0 = time.perf_counter()
    response = await model.ainvoke([
        {"role": "system", "content": system_prompt},
        *state.messages
    ])
    llm_elapsed = time.perf_counter() - t0

    # 도구 호출이 있는 경우 처리
    if response.tool_calls:
        tool_names = [tc.get('name', 'unknown') for tc in response.tool_calls]
        logger.info(
            f"⏱️ [Expert {expert_config.name}] {llm_elapsed:.2f}초 "
            f"(도구 호출: {', '.join(tool_names)})"
        )
        # 도구 호출이 있으면 tool_calls를 포함한 응답 반환
        # 이 경우 graph.py에서 도구 실행 노드로 라우팅됨
        # 여기서는 content만 반환하므로 도구 호출 결과가 필요하면 추가 처리 필요
        logger.warning(
            f"[Expert {expert_config.name}] 도구 호출 응답 - 현재 구현에서는 "
            f"content만 반환합니다. 도구 실행은 별도 노드에서 처리됩니다."
        )
    else:
        logger.info(
            f"⏱️ [Expert {expert_config.name}] {llm_elapsed:.2f}초 (최종 응답)"
        )

    # 응답 내용 추출
    content = response.content
    if isinstance(content, str):
        response_text = content
    elif isinstance(content, list):
        # content가 리스트인 경우 (멀티모달 응답)
        response_text = "\n".join(
            c.get("text", str(c)) if isinstance(c, dict) else str(c)
            for c in content
        )
    else:
        response_text = str(content)

    # 전문가 헤더 추가
    expert_header = format_expert_header(expert_role)
    formatted_response = f"{expert_header}\n\n{response_text}"

    return formatted_response


async def _run_multiple_experts(
    experts: List[ExpertRole],
    state: State,
    category: str,
    query: str,
) -> str:
    """
    다중 전문가 병렬 실행 및 응답 통합

    Args:
        experts: 전문가 역할 리스트
        state: 현재 상태
        category: 질문 카테고리
        query: 사용자 질문

    Returns:
        통합된 전문가 응답 문자열
    """
    logger.info(
        f"[Expert Panel] 다중 전문가 병렬 실행: "
        f"{[e.value for e in experts]}"
    )

    t0 = time.perf_counter()

    # 각 전문가 응답을 병렬로 수집
    async def run_expert(expert_role: ExpertRole) -> tuple:
        """개별 전문가 실행 래퍼"""
        try:
            response = await _run_single_expert_raw(expert_role, state, category)
            return (expert_role, response)
        except Exception as e:
            logger.error(f"[Expert {expert_role.value}] 실행 오류: {e}")
            return (expert_role, f"[{expert_role.value}] 응답 생성 실패: {str(e)}")

    # 병렬 실행
    results = await asyncio.gather(*[run_expert(expert) for expert in experts])

    parallel_elapsed = time.perf_counter() - t0
    logger.info(f"⏱️ [Expert Panel] 병렬 실행 완료: {parallel_elapsed:.2f}초")

    # 결과를 딕셔너리로 변환
    expert_responses: Dict[ExpertRole, str] = {}
    for expert_role, response in results:
        expert_responses[expert_role] = response

    # 응답 통합
    t1 = time.perf_counter()
    integrated_response = await collaborate_experts(
        expert_responses, query, category
    )
    integration_elapsed = time.perf_counter() - t1

    logger.info(f"⏱️ [Expert Panel] 응답 통합 완료: {integration_elapsed:.2f}초")

    return integrated_response


async def _run_single_expert_raw(
    expert_role: ExpertRole,
    state: State,
    category: str,
) -> str:
    """
    단일 전문가 실행 (헤더 없이 순수 응답만)

    collaborate_experts에서 헤더를 추가하므로 여기서는 순수 응답만 반환

    Args:
        expert_role: 전문가 역할
        state: 현재 상태
        category: 질문 카테고리

    Returns:
        전문가 응답 문자열 (헤더 없음)
    """
    expert_config = get_expert_by_role(expert_role)

    logger.debug(
        f"[Expert: {expert_config.name}] 순수 응답 생성 시작"
    )

    # 전문가 프롬프트 생성
    system_prompt = get_expert_prompt(
        expert_role,
        category,
        state.prefetched_context
    )

    # 도구 로드 및 필터링
    all_tools = await get_all_tools()

    base_tool_names = [
        "search_knowledge_base", "search", "classify_customer_segment",
        "geocode_location"
    ]

    allowed_tools = [
        tool for tool in all_tools
        if tool.name in expert_config.tools or tool.name not in base_tool_names
    ]

    # Claude Sonnet 모델 사용
    llm = ChatAnthropic(
        temperature=0.3,
        model="claude-sonnet-4-20250514"
    )
    model = llm.bind_tools(allowed_tools) if allowed_tools else llm

    # LLM 호출
    t0 = time.perf_counter()
    response = await model.ainvoke([
        {"role": "system", "content": system_prompt},
        *state.messages
    ])
    llm_elapsed = time.perf_counter() - t0

    logger.debug(
        f"[Expert: {expert_config.name}] 응답 생성 완료: {llm_elapsed:.2f}초"
    )

    # 응답 내용 추출
    content = response.content
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        return "\n".join(
            c.get("text", str(c)) if isinstance(c, dict) else str(c)
            for c in content
        )
    else:
        return str(content)
