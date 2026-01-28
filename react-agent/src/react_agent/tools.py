"""CarbonAI 챗봇 도구 모듈

RAG 기반 문서 검색 및 고객 세그먼트 분류 기능을 제공합니다.
"""

import os
import asyncio
import logging
import json
from typing import Any, Callable, Dict, List, Optional, cast

from langchain_tavily import TavilySearch
from langchain_core.tools import tool

from react_agent.configuration import Configuration
from react_agent.rag_tool import get_rag_tool
from react_agent.sse_mcp_client import SSEMCPClient

logger = logging.getLogger(__name__)


async def search(query: str) -> Optional[dict[str, Any]]:
    """Search for general web results.

    This function performs a search using the Tavily search engine, which is designed
    to provide comprehensive, accurate, and trusted results. It's particularly useful
    for answering questions about current events.
    """
    configuration = Configuration.from_context()
    wrapped = TavilySearch(max_results=configuration.max_search_results)
    return cast(dict[str, Any], await wrapped.ainvoke({"query": query}))


@tool
def search_knowledge_base(query: str, k: int = 3, use_hybrid: bool = True) -> dict[str, Any]:
    """회사 지식베이스에서 관련 문서를 검색합니다.

    이 도구는 하이브리드 검색(BM25 + 벡터)을 사용하여 탄소 배출권 관련 문서를 찾습니다.
    배출권 거래, 구매/판매 절차, NET-Z 플랫폼 사용법 등에 대한 질문에 사용하세요.

    **검색 방식**:
    - **하이브리드 검색 (기본)**: BM25 키워드 검색 + 벡터 의미 검색을 결합하여 정확도 향상
      - BM25: 키워드 매칭 기반 검색 (정확한 용어 검색에 강함)
      - 벡터: 의미 기반 검색 (문맥 이해에 강함)
      - alpha=0.5: 두 방식을 50:50으로 결합
    - **벡터 검색 전용**: use_hybrid=False로 설정 시 기존 벡터 검색만 사용
    - LLM을 사용하여 쿼리에서 핵심 키워드를 추출합니다.
    - 중복된 문서는 자동으로 제거됩니다.

    **중요**:
    - query 파라미터에는 사용자의 전체 질문을 그대로 전달하세요.
    - 키워드만이 아닌 전체 질문을 전달하면 더 정확한 검색이 가능합니다.
    - 질문의 맥락, 의도, 세부사항을 모두 포함해야 합니다.

    Args:
        query: 검색할 사용자의 전체 질문 (예: "배출권을 구매하려면 어떤 절차를 거쳐야 하나요?")
            - 키워드만이 아닌 전체 질문을 그대로 전달해야 합니다.
            - 질문의 맥락, 의도, 세부사항을 모두 포함해야 합니다.
        k: 반환할 문서 수 (기본값: 3)
        use_hybrid: 하이브리드 검색 사용 여부 (기본값: True, 더 정확한 검색)

    Returns:
        검색된 문서들의 정보를 포함한 딕셔너리
        - 관련 문서가 없으면 빈 결과를 반환합니다.
    """
    rag_tool = get_rag_tool()

    if use_hybrid:
        # 하이브리드 검색 (BM25 + 벡터)
        results = rag_tool.search_documents_hybrid(
            query,
            k=k,
            alpha=0.5,  # 벡터 50% + BM25 50%
            similarity_threshold=0.6  # 품질과 커버리지 균형
        )
        threshold_msg = "하이브리드 점수 0.6"
    else:
        # 벡터 검색 전용
        results = rag_tool.search_documents(query, k=k, similarity_threshold=0.7)
        threshold_msg = "유사도 0.7"

    if not results:
        return {
            "status": "no_results",
            "message": f"{threshold_msg} 이상인 관련 문서를 찾을 수 없습니다. 지식베이스 없이 답변하겠습니다.",
            "results": []
        }

    search_type = "하이브리드" if use_hybrid else "벡터"
    return {
        "status": "success",
        "message": f"{len(results)}개의 관련 문서를 찾았습니다 ({search_type} 검색, {threshold_msg} 이상).",
        "results": results
    }


@tool
def classify_customer_segment(question: str) -> dict[str, Any]:
    """사용자 질문을 분석하여 고객 세그먼트를 분류합니다.

    가능한 세그먼트:
    - 배출권_보유자: 배출권을 보유하고 활용 방법을 찾는 고객
    - 배출권_구매자: 배출권을 구매하고자 하는 고객
    - 배출권_판매자: 배출권을 판매하고자 하는 고객
    - 배출권_생성_희망자: 배출권을 생성하고자 하는 고객
    - 일반: 일반적인 정보를 찾는 고객

    Args:
        question: 사용자의 질문이나 요청

    Returns:
        분류된 세그먼트 정보
    """
    question_lower = question.lower()

    # 키워드 기반 분류 -> 데이터 수집 후 추가 필요
    if any(kw in question_lower for kw in ['보유', '가지고', '소유', '활용', '어떻게 할']):
        segment = "배출권_보유자"
    elif any(kw in question_lower for kw in ['구매', '사고 싶', '매수', '어디서', '어떻게']):
        segment = "배출권_구매자"
    elif any(kw in question_lower for kw in ['판매', '팔고 싶', '매도', '처분', '수익']):
        segment = "배출권_판매자"
    elif any(kw in question_lower for kw in ['생성', '만들', '프로젝트', '개발']):
        segment = "배출권_생성_희망자"
    else:
        segment = "일반"

    return {
        "segment": segment,
        "confidence": "high" if segment != "일반" else "medium",
        "question": question
    }


# ==================== MCP 통합 ====================

# NET-Z MCP 클라이언트 (전역, lazy 초기화)
_netz_mcp_client: Optional[SSEMCPClient] = None


async def _get_mcp_client() -> Optional[SSEMCPClient]:
    """MCP 클라이언트를 lazy하게 초기화 (자동 재연결 지원)"""
    global _netz_mcp_client

    # 환경 변수 확인
    netz_enabled = os.getenv("NETZ_MCP_ENABLED", "false").lower() == "true"
    netz_url = os.getenv("NETZ_MCP_URL")
    netz_enterprise_id = os.getenv("NETZ_ENTERPRISE_ID", "1")  # 기본값 1

    if not netz_enabled:
        logger.info("[NET-Z MCP] 비활성화됨 (NETZ_MCP_ENABLED=false)")
        return None

    if not netz_url:
        logger.warning("[NET-Z MCP] URL이 설정되지 않았습니다")
        return None

    # 이미 초기화되어 있으면 상태 확인
    if _netz_mcp_client is not None:
        # 연결 상태 확인 (더 엄격하게)
        is_healthy = (
            _netz_mcp_client.running and
            _netz_mcp_client.sse_task and
            not _netz_mcp_client.sse_task.done() and
            _netz_mcp_client.session_id is not None
        )

        if is_healthy:
            logger.debug("[NET-Z MCP] 기존 연결 사용 (정상)")
            return _netz_mcp_client
        else:
            logger.warning("[NET-Z MCP] 연결 상태 불량, 재초기화 중...")
            logger.debug(f"  running={_netz_mcp_client.running}, "
                        f"sse_task_done={_netz_mcp_client.sse_task.done() if _netz_mcp_client.sse_task else 'None'}, "
                        f"session_id={_netz_mcp_client.session_id}, "
                        f"reconnect_attempts={_netz_mcp_client.reconnect_attempts}")
            try:
                await _netz_mcp_client.close()
            except Exception as e:
                logger.error(f"[NET-Z MCP] 기존 연결 종료 실패: {e}")
            _netz_mcp_client = None

    # 새로운 클라이언트 생성
    try:
        logger.info(f"[NET-Z MCP] 클라이언트 초기화 시작: {netz_url} (Enterprise ID: {netz_enterprise_id})")
        _netz_mcp_client = SSEMCPClient(
            base_url=netz_url,
            enterprise_id=netz_enterprise_id
        )
        await _netz_mcp_client.initialize()
        logger.info("[NET-Z MCP] ✅ 클라이언트 초기화 완료")
        return _netz_mcp_client
    except Exception as e:
        logger.error(f"[NET-Z MCP] 초기화 실패: {e}", exc_info=True)
        _netz_mcp_client = None
        return None


def _create_mcp_tool(mcp_tool_def: Dict[str, Any]) -> Callable:
    """MCP 도구 정의를 LangChain 도구로 변환

    Args:
        mcp_tool_def: MCP 서버에서 받은 도구 정의
    """
    from pydantic import BaseModel, Field, create_model
    from typing import Any as AnyType

    tool_name = mcp_tool_def["name"]
    tool_description = mcp_tool_def.get("description", "")
    input_schema = mcp_tool_def.get("inputSchema", {})

    # 동적 함수 생성
    async def mcp_tool_wrapper(**kwargs):
        max_retries = 2
        for attempt in range(max_retries):
            try:
                client = await _get_mcp_client()

                if client is None:
                    # 오류 시 문자열 직접 반환
                    return "오류: NET-Z MCP 서버에 연결할 수 없습니다."

                logger.info(f"[NET-Z MCP] 도구 호출: {tool_name} (시도 {attempt + 1}/{max_retries})")
                logger.debug(f"[NET-Z MCP] 인자: {kwargs}")

                # MCP 도구 호출
                result = await client.call_tool(tool_name, kwargs)

                logger.info(f"[NET-Z MCP] 도구 호출 성공: {tool_name}")

                # 결과 파싱 - LangChain에 data만 직접 반환
                content = result.get("content", [])
                if content and len(content) > 0:
                    text_content = content[0].get("text", "{}")
                    try:
                        # JSON 파싱 시도
                        data = json.loads(text_content) if isinstance(text_content, str) else text_content
                        # data만 반환 (status 래핑 제거)
                        return data
                    except json.JSONDecodeError:
                        # 파싱 실패 시 문자열 그대로 반환
                        return text_content

                # content가 없으면 전체 result 반환
                return result

            except Exception as e:
                logger.error(f"[NET-Z MCP 오류] {tool_name} (시도 {attempt + 1}/{max_retries}): {e}")

                # 연결 오류면 클라이언트 초기화 해제하고 재시도
                if attempt < max_retries - 1:
                    global _netz_mcp_client
                    if _netz_mcp_client:
                        logger.info(f"[NET-Z MCP] 클라이언트 재설정 후 재시도...")
                        try:
                            await _netz_mcp_client.close()
                        except:
                            pass
                        _netz_mcp_client = None
                    await asyncio.sleep(0.5)  # 재시도 전 대기
                else:
                    logger.error(f"[NET-Z MCP 최종 실패] {tool_name}: {e}", exc_info=True)
                    # 오류 시 문자열 직접 반환
                    return f"오류: MCP 도구 호출 실패 - {str(e)}"

    # 함수 메타데이터 설정
    mcp_tool_wrapper.__name__ = tool_name
    mcp_tool_wrapper.__doc__ = tool_description

    # Pydantic 모델 생성 (inputSchema 기반)
    properties = input_schema.get("properties", {})
    required_fields = input_schema.get("required", [])

    # 파라미터 필드 생성
    fields = {}
    for param_name, param_info in properties.items():
        param_type = param_info.get("type", "string")
        param_desc = param_info.get("description", "")

        # JSON Schema 타입을 Python 타입으로 변환
        python_type = AnyType
        if param_type == "string":
            python_type = str
        elif param_type == "integer":
            python_type = int
        elif param_type == "number":
            python_type = float
        elif param_type == "boolean":
            python_type = bool

        # 필수 여부 결정
        if param_name in required_fields:
            fields[param_name] = (python_type, Field(description=param_desc))
        else:
            fields[param_name] = (python_type, Field(default=None, description=param_desc))

    # 동적 Pydantic 모델 생성
    if fields:
        ArgsSchema = create_model(
            f"{tool_name}Schema",
            **fields
        )
    else:
        ArgsSchema = None

    # LangChain tool 데코레이터 적용 (args_schema 포함)
    if ArgsSchema:
        return tool(args_schema=ArgsSchema)(mcp_tool_wrapper)
    else:
        return tool(mcp_tool_wrapper)


# MCP 도구 캐시
_mcp_tools_cache: Optional[List[Callable]] = None
_mcp_tools_loaded = False


async def _load_mcp_tools() -> List[Callable]:
    """MCP 서버에서 도구 목록을 가져와 LangChain 도구로 변환"""
    global _mcp_tools_cache, _mcp_tools_loaded

    # 이미 로드되었으면 캐시 반환
    if _mcp_tools_loaded and _mcp_tools_cache is not None:
        return _mcp_tools_cache

    mcp_tools = []

    try:
        # MCP 클라이언트 초기화
        client = await _get_mcp_client()

        if client is None:
            logger.warning("[NET-Z MCP] 클라이언트를 초기화할 수 없어 MCP 도구를 로드하지 않습니다")
            _mcp_tools_loaded = True
            _mcp_tools_cache = []
            return []

        # MCP 서버에서 도구 목록 가져오기
        logger.info("[NET-Z MCP] 도구 목록 조회 중...")
        tools_list = await client.list_tools()

        logger.info(f"[NET-Z MCP] {len(tools_list)}개 도구 발견")

        # 각 MCP 도구를 LangChain 도구로 변환
        for mcp_tool in tools_list:
            try:
                langchain_tool = _create_mcp_tool(mcp_tool)
                mcp_tools.append(langchain_tool)
                logger.info(f"  ✓ {mcp_tool['name']} - {mcp_tool.get('description', '')[:50]}...")
            except Exception as e:
                logger.error(f"  ✗ {mcp_tool['name']} 로드 실패: {e}")

        _mcp_tools_cache = mcp_tools
        _mcp_tools_loaded = True

        logger.info(f"[NET-Z MCP] ✓ {len(mcp_tools)}개 도구 로드 완료")

    except Exception as e:
        logger.error(f"[NET-Z MCP] 도구 로드 실패: {e}", exc_info=True)
        _mcp_tools_loaded = True
        _mcp_tools_cache = []

    return mcp_tools


# ==================== 도구 목록 ====================

# 기본 도구
_BASE_TOOLS: List[Callable[..., Any]] = [
    search,
    search_knowledge_base,
    classify_customer_segment,
]

# 초기 TOOLS (MCP 도구는 첫 요청 시 동적 로드됨)
TOOLS: List[Callable[..., Any]] = _BASE_TOOLS.copy()

logger.info(f"[도구 초기화] 기본 {len(_BASE_TOOLS)}개 툴 등록")
logger.info("  ✓ search - 일반 웹 검색")
logger.info("  ✓ search_knowledge_base - 지식베이스 검색")
logger.info("  ✓ classify_customer_segment - 고객 세그먼트 분류")
logger.info("  → NET-Z MCP 도구는 첫 요청 시 자동으로 로드됩니다")


async def get_all_tools() -> List[Callable[..., Any]]:
    
    global TOOLS

    # MCP 도구 로드
    mcp_tools = await _load_mcp_tools()

    # 전체 도구 목록
    all_tools = _BASE_TOOLS + mcp_tools

    # TOOLS 전역 변수 업데이트 (graph.py에서 사용)
    TOOLS = all_tools

    logger.info(f"[도구 목록] 총 {len(all_tools)}개 도구 사용 가능:")
    logger.info(f"  - 기본 도구: {len(_BASE_TOOLS)}개")
    logger.info(f"  - NET-Z MCP 도구: {len(mcp_tools)}개")

    return all_tools
