# 상태 관리

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from langgraph.managed import IsLastStep
from typing_extensions import Annotated


@dataclass
class InputState:
    """Defines the input state for the agent, representing a narrower interface to the outside world.

    This class is used to define the initial state and structure of incoming data.
    """

    messages: Annotated[Sequence[AnyMessage], add_messages] = field(
        default_factory=list
    )
    """
    Messages tracking the primary execution state of the agent.

    Typically accumulates a pattern of:
    1. HumanMessage - user input
    2. AIMessage with .tool_calls - agent picking tool(s) to use to collect information 에이전트가 툴 고름
    3. ToolMessage(s) - the responses (or errors) from the executed tools 툴 실행결과
    4. AIMessage without .tool_calls - agent responding in unstructured format to the user 에이전트가 비구조화된 형식으로 사용자에게 응답
    5. HumanMessage - user responds with the next conversational turn 사용자가 다음 대화 턴에 응답

    Steps 2-5 may repeat as needed.

    The `add_messages` annotation ensures that new messages are merged with existing ones,
    updating by ID to maintain an "append-only" state unless a message with the same ID is provided.
    """

# 기본 메세지 히스토리
@dataclass
class State(InputState):
    """Represents the complete state of the agent, extending InputState with additional attributes.

    This class can be used to store any information needed throughout the agent's lifecycle.
    """

    is_last_step: IsLastStep = field(default=False)
    """
    Indicates whether the current step is the last one before the graph raises an error.

    This is a 'managed' variable, controlled by the state machine rather than user code.
    It is set to 'True' when the step count reaches recursion_limit - 1.
    """

    # 대화 맥락 유지를 위한 필드 (주제, 사용자 유형 등)
    conversation_context: dict = field(default_factory=dict)
    """
    대화 이력에서 추출한 맥락 정보

    포함 내용:
    - recent_topics: 최근 3개 주제
    - user_type: 감지된 사용자 유형
    - mentioned_entities: 언급된 주요 엔티티 (회사명, 제품명 등)
    - conversation_stage: 대화 단계 (초기/진행/심화)
    """

    # 병렬 도구 호출 결과 캐시
    # 미리 실행된 도구 결과 (RAG, 웹 검색)
    prefetched_context: dict = field(default_factory=dict)
    """
    질문 분석 후 미리 실행된 도구들의 결과

    포함 내용:
    - RAG: 지식베이스 검색 결과
    - MCP_*: MCP 도구 호출 결과
    - source: 결과 출처 (예: "faq_cache")
    """

    # 🎯 멀티 에이전트: 매니저 결정
    manager_decision: dict = field(default_factory=dict)
    """
    매니저 에이전트의 복잡도 분석 및 라우팅 결정

    포함 내용:
    - complexity: "simple" | "medium" | "complex"
    - assigned_agent: "simple" | "carbon_expert" | "regulation_expert" | "support_expert"
    - reasoning: 선택 이유
    - confidence: 판단 신뢰도 (0.0-1.0)
    """

    # 🎯 멀티 에이전트: 사용된 에이전트
    agent_used: str = field(default="")
    """
    실제로 답변을 생성한 에이전트 이름
    추적 및 분석용
    """

    # Additional attributes can be added here as needed.
    # Common examples include:
    # retrieved_documents: List[Document] = field(default_factory=list)
    # extracted_entities: Dict[str, Any] = field(default_factory=dict)
    # api_connections: Dict[str, Any] = field(default_factory=dict)
