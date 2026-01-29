"""
멀티 에이전트 노드 구현
"""

import json
import logging
from typing import Dict, Any, List
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from react_agent.state import State
from react_agent.configuration import Configuration
from react_agent.utils import detect_and_convert_mermaid
from .config import AgentRole, get_agent_config
from .prompts import get_agent_prompt

logger = logging.getLogger(__name__)


async def manager_agent(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """
    [매니저 에이전트] 복잡도 분석 및 에이전트 할당

    Sonnet 4.5 사용 - 정확한 판단
    """
    configuration = Configuration.from_runnable_config(config)

    # 매니저 프롬프트 생성
    system_prompt = get_agent_prompt(
        AgentRole.MANAGER,
        configuration.category or "탄소배출권",
        state.prefetched_context
    )

    # Sonnet 모델로 판단
    llm = ChatAnthropic(
        temperature=0,
        model="claude-sonnet-4-5"
    )

    try:
        response = await llm.ainvoke([
            {"role": "system", "content": system_prompt},
            *state.messages
        ])

        # JSON 파싱
        content = response.content.strip()

        # JSON 블록 추출 (```json ... ``` 형식 처리)
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.find("```", json_start)
            content = content[json_start:json_end].strip()
        elif "```" in content:
            json_start = content.find("```") + 3
            json_end = content.find("```", json_start)
            content = content[json_start:json_end].strip()

        decision = json.loads(content)

        logger.info(
            f"[Manager] 복잡도: {decision['complexity']}, "
            f"할당: {decision['assigned_agent']}, "
            f"이유: {decision['reasoning']}"
        )

        return {
            "manager_decision": decision
        }

    except json.JSONDecodeError as e:
        logger.error(f"[Manager] JSON 파싱 실패: {e}, 응답: {response.content}")
        # 기본값으로 폴백
        return {
            "manager_decision": {
                "complexity": "simple",
                "assigned_agent": "simple",
                "reasoning": "파싱 오류로 기본 에이전트 할당",
                "confidence": 0.5
            }
        }
    except Exception as e:
        logger.error(f"[Manager] 오류: {e}", exc_info=True)
        return {
            "manager_decision": {
                "complexity": "simple",
                "assigned_agent": "simple",
                "reasoning": "오류 발생으로 기본 에이전트 할당",
                "confidence": 0.5
            }
        }


async def simple_agent(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """
    [일반 답변 에이전트] 기본 질문 답변

    Haiku 4.5 사용 - 빠르고 저렴
    도구 사용 가능: search_knowledge_base, classify_customer_segment
    """
    configuration = Configuration.from_runnable_config(config)

    # 일반 답변 프롬프트
    system_prompt = get_agent_prompt(
        AgentRole.SIMPLE,
        configuration.category or "탄소배출권",
        state.prefetched_context
    )

    # Simple 에이전트 설정
    agent_config = get_agent_config(AgentRole.SIMPLE)

    # 도구 로드 (simple 에이전트용)
    from react_agent.tools import get_all_tools
    all_tools = await get_all_tools()

    # 허용된 도구만 필터링
    allowed_tools = [
        tool for tool in all_tools
        if tool.name in agent_config.tools
    ]

    # Haiku 모델 + 도구 바인딩
    llm = ChatAnthropic(
        temperature=agent_config.temperature,
        model=agent_config.model
    )
    model = llm.bind_tools(allowed_tools) if allowed_tools else llm

    # LLM 호출
    response = await model.ainvoke([
        {"role": "system", "content": system_prompt},
        *state.messages
    ])

    # 도구 호출 로깅
    if response.tool_calls:
        tool_names = [tc.get('name', 'unknown') for tc in response.tool_calls]
        logger.info(f"[Simple Agent] 도구 호출: {', '.join(tool_names)}")

    # Mermaid 코드 블록을 이미지로 자동 변환
    if response.content and isinstance(response.content, str):
        converted_content = detect_and_convert_mermaid(response.content)
        if converted_content != response.content:
            response = AIMessage(
                id=response.id,
                content=converted_content,
                tool_calls=response.tool_calls if hasattr(response, 'tool_calls') else [],
                additional_kwargs=response.additional_kwargs,
            )

    return {
        "messages": [response],
        "agent_used": "simple"
    }


async def expert_agent(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """
    [전문가 에이전트] 전문 분야 답변

    Haiku 4.5 사용 - 비용 최적화
    카테고리별 전문 도구 사용
    """
    configuration = Configuration.from_runnable_config(config)

    # 매니저가 할당한 에이전트 역할 가져오기
    assigned_agent = state.manager_decision.get("assigned_agent", "carbon_expert")

    try:
        agent_role = AgentRole(assigned_agent)
    except ValueError:
        logger.warning(f"[Expert] 알 수 없는 에이전트: {assigned_agent}, carbon_expert 사용")
        agent_role = AgentRole.CARBON_EXPERT

    # 전문가 프롬프트
    system_prompt = get_agent_prompt(
        agent_role,
        configuration.category or "탄소배출권",
        state.prefetched_context
    )

    # 전문가 설정
    agent_config = get_agent_config(agent_role)

    # 도구 로드 (전문가용)
    from react_agent.tools import get_all_tools
    all_tools = await get_all_tools()

    # 허용된 도구만 필터링
    allowed_tools = [
        tool for tool in all_tools
        if tool.name in agent_config.tools
    ]

    logger.info(
        f"[Expert: {agent_config.name}] "
        f"도구 {len(allowed_tools)}개: {', '.join([t.name for t in allowed_tools])}"
    )

    # Haiku 모델 + 도구 바인딩
    llm = ChatAnthropic(
        temperature=agent_config.temperature,
        model=agent_config.model
    )
    model = llm.bind_tools(allowed_tools) if allowed_tools else llm

    # LLM 호출
    response = await model.ainvoke([
        {"role": "system", "content": system_prompt},
        *state.messages
    ])

    # 도구 호출 로깅
    if response.tool_calls:
        tool_names = [tc.get('name', 'unknown') for tc in response.tool_calls]
        logger.info(f"[Expert: {agent_config.name}] 도구 호출: {', '.join(tool_names)}")

    # Mermaid 코드 블록을 이미지로 자동 변환
    if response.content and isinstance(response.content, str):
        converted_content = detect_and_convert_mermaid(response.content)
        if converted_content != response.content:
            response = AIMessage(
                id=response.id,
                content=converted_content,
                tool_calls=response.tool_calls if hasattr(response, 'tool_calls') else [],
                additional_kwargs=response.additional_kwargs,
            )

    return {
        "messages": [response],
        "agent_used": agent_role.value
    }
