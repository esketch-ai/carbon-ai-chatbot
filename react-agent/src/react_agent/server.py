"""FastAPI server for LangGraph agent deployment."""

import os
import uuid
import json
import time
import logging
import asyncio
import psutil
import http
from datetime import datetime
from typing import Any, Dict, Optional, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
import uvicorn
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST, REGISTRY

from react_agent.graph_multi import graph   # 멀티 에이전트 그래프 임포트
from react_agent.configuration import Configuration  # 기존 설정 클래스
from langchain_core.messages import AIMessage, HumanMessage   # 랭체인 메세지 타입 임포트
from react_agent.rag_tool import get_rag_tool  # RAG 도구
from react_agent.input_sanitizer import sanitize_user_input, detect_prompt_injection  # 입력 검증
from react_agent.cache_manager import get_cache_manager  # 캐시 매니저
from react_agent.logging_config import setup_logging, get_logger, LogContext, set_log_context, clear_log_context  # 구조화된 로깅

# Load environment variables
load_dotenv()

# 구조화된 로깅 설정 (JSON for production, human-readable for development)
setup_logging()

logger = get_logger(__name__)

# ============= Prometheus Metrics =============
# Use module-level dict to store metrics and avoid duplicate registration
_METRICS: Dict[str, Any] = {}

def _get_or_create_metric(metric_class, name, description, labelnames=None, **kwargs):
    """Get existing metric or create new one to avoid duplicate registration."""
    # Check module-level cache first
    if name in _METRICS:
        return _METRICS[name]

    # Check if metric exists in registry
    if name in REGISTRY._names_to_collectors:
        _METRICS[name] = REGISTRY._names_to_collectors[name]
        return _METRICS[name]

    # Try to create new metric
    try:
        if labelnames:
            metric = metric_class(name, description, labelnames, **kwargs)
        else:
            metric = metric_class(name, description, **kwargs)
        _METRICS[name] = metric
        return metric
    except ValueError as e:
        if "Duplicated timeseries" in str(e):
            # Metric was registered by another import, find and return it
            for collector in REGISTRY._names_to_collectors.values():
                if hasattr(collector, '_name') and collector._name == name:
                    _METRICS[name] = collector
                    return collector
            # For Counter, the key might be the base name without _total
            base_name = name.replace('_total', '') if name.endswith('_total') else name
            if base_name in REGISTRY._names_to_collectors:
                _METRICS[name] = REGISTRY._names_to_collectors[base_name]
                return _METRICS[name]
        raise

# Request metrics
REQUEST_COUNT = _get_or_create_metric(
    Counter,
    'carbonai_requests',
    'Total number of requests',
    ['endpoint', 'method', 'status']
)
REQUEST_LATENCY = _get_or_create_metric(
    Histogram,
    'carbonai_request_latency_seconds',
    'Request latency in seconds',
    ['endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

# Agent metrics
AGENT_USAGE = _get_or_create_metric(
    Counter,
    'carbonai_agent_usage',
    'Agent usage count by type',
    ['agent_type', 'category']
)

# Error metrics
ERROR_COUNT = _get_or_create_metric(
    Counter,
    'carbonai_errors',
    'Total number of errors',
    ['error_type', 'endpoint']
)

# System metrics
ACTIVE_THREADS = _get_or_create_metric(
    Gauge,
    'carbonai_active_threads',
    'Number of active conversation threads'
)
ACTIVE_REQUESTS = _get_or_create_metric(
    Gauge,
    'carbonai_active_requests',
    'Number of currently active requests'
)


# Helper function to convert LangChain messages to JSON-serializable format
def message_to_dict(msg):  # 랭체인 메세지를 json으로 변환 -> 프론트엔드 sdk 형식 / 호환을 위함

    # CRITICAL: Extract content BEFORE serialization to avoid "complex" conversion
    # LangChain's dict()/model_dump() converts list content to "complex" string
    extracted_content = None
    if hasattr(msg, 'content'):
        raw_content = msg.content
        if isinstance(raw_content, list):
            # Extract text from list of content blocks (multimodal format)
            text_parts = []
            for item in raw_content:
                if isinstance(item, dict):
                    if item.get('type') == 'text':
                        text_parts.append(item.get('text', ''))
                    elif 'text' in item:
                        text_parts.append(item['text'])
                elif isinstance(item, str):
                    text_parts.append(item)
            extracted_content = '\n'.join(text_parts) if text_parts else ''
        elif isinstance(raw_content, str):
            extracted_content = raw_content

    # Now serialize the message
    if hasattr(msg, 'dict'):
        result = msg.dict()
    elif hasattr(msg, 'model_dump'):
        result = msg.model_dump()
    elif hasattr(msg, '__dict__'):
        # Fallback: convert object attributes to dict
        result = {}
        for key, value in msg.__dict__.items():
            if isinstance(value, (str, int, float, bool, type(None))):
                result[key] = value
            elif isinstance(value, dict):
                result[key] = value
            elif isinstance(value, list):
                result[key] = [message_to_dict(item) if hasattr(item, '__dict__') else item for item in value]
            else:
                result[key] = str(value)
    else:
        return str(msg)

    # Replace content with extracted text if we found any
    if extracted_content is not None and isinstance(result, dict):
        # CRITICAL: Convert string content to LangGraph SDK format (array of content blocks)
        # Frontend SDK expects: content: [{ type: "text", text: "..." }]
        result['content'] = [
            {
                "type": "text",
                "text": extracted_content
            }
        ]

    return result


def is_streamable_text_message(msg) -> bool:
    """Check if a message chunk should be streamed as real-time tokens.

    Only AI text content is streamed token-by-token.
    Tool calls, tool results, and human messages are handled via values (node-level).
    """
    # Must be an AI message (AIMessage or AIMessageChunk)
    msg_type = getattr(msg, 'type', None)
    if msg_type != 'ai' and msg_type != 'AIMessageChunk':
        # Also check class name for chunk types
        class_name = type(msg).__name__
        if 'AI' not in class_name:
            return False

    # Skip if this is purely a tool call (no text content)
    content = getattr(msg, 'content', '')
    tool_calls = getattr(msg, 'tool_calls', [])
    tool_call_chunks = getattr(msg, 'tool_call_chunks', [])

    has_text = bool(content) if isinstance(content, str) else False
    if isinstance(content, list):
        has_text = any(
            (isinstance(c, str) and c) or
            (isinstance(c, dict) and c.get('type') == 'text' and c.get('text'))
            for c in content
        )

    has_tool_calls = bool(tool_calls) or bool(tool_call_chunks)

    # Stream only when there's actual text content
    # If it's purely a tool call with no text, let values handle it
    if not has_text and has_tool_calls:
        return False

    return has_text


def serialize_chunk(chunk):
    """Recursively serialize a chunk to JSON-serializable format."""
    if isinstance(chunk, dict):
        return {key: serialize_chunk(value) for key, value in chunk.items()}
    elif isinstance(chunk, list):
        return [serialize_chunk(item) for item in chunk]
    elif hasattr(chunk, 'dict') or hasattr(chunk, 'model_dump') or hasattr(chunk, '__dict__'):
        return message_to_dict(chunk)
    else:
        return chunk

# Thread activity tracking for memory cleanup
thread_last_activity: Dict[str, float] = {}
THREAD_TTL_SECONDS = 90 * 60  # 90 minutes
CLEANUP_INTERVAL_SECONDS = 30 * 60  # 30 minutes


def track_thread_activity(thread_id: str) -> None:
    """Record the last activity time for a thread."""
    thread_last_activity[thread_id] = time.time()


# Initialize FastAPI app
app = FastAPI(
    title="CarbonAI Agent API",
    description="LangGraph-powered chatbot for carbon emission consulting",
    version="1.0.0"
)


# ============= RFC 7807 Problem Details Error Response =============
class ErrorResponse(BaseModel):
    """RFC 7807 Problem Details 기반 에러 응답 모델.

    Provides a standardized error response format across all API endpoints.
    Reference: https://datatracker.ietf.org/doc/html/rfc7807
    """
    type: str = Field(
        default="about:blank",
        description="A URI reference that identifies the problem type"
    )
    title: str = Field(
        ...,
        description="A short, human-readable summary of the problem type"
    )
    status: int = Field(
        ...,
        description="The HTTP status code"
    )
    detail: str = Field(
        ...,
        description="A human-readable explanation specific to this occurrence"
    )
    instance: Optional[str] = Field(
        default=None,
        description="A URI reference that identifies the specific occurrence"
    )
    timestamp: Optional[str] = Field(
        default=None,
        description="ISO 8601 timestamp when the error occurred"
    )
    trace_id: Optional[str] = Field(
        default=None,
        description="Unique identifier for tracing this error"
    )


def create_error_response(
    status_code: int,
    detail: str,
    request: Request,
    error_type: Optional[str] = None,
    title: Optional[str] = None
) -> JSONResponse:
    """Create a standardized RFC 7807 error response.

    Args:
        status_code: HTTP status code
        detail: Detailed error message
        request: FastAPI Request object
        error_type: Optional custom error type URI
        title: Optional custom title (defaults to HTTP status phrase)

    Returns:
        JSONResponse with RFC 7807 compliant error body
    """
    # Generate trace ID for error tracking
    trace_id = str(uuid.uuid4())[:8]

    # Get HTTP status phrase as default title
    try:
        default_title = http.HTTPStatus(status_code).phrase
    except ValueError:
        default_title = "Unknown Error"

    error_response = ErrorResponse(
        type=error_type or f"/errors/{status_code}",
        title=title or default_title,
        status=status_code,
        detail=detail,
        instance=str(request.url),
        timestamp=datetime.now().isoformat(),
        trace_id=trace_id
    )

    # Log error for monitoring
    logger.error(
        f"[ERROR {trace_id}] {status_code} {error_response.title}: {detail} "
        f"(endpoint: {request.url.path})"
    )

    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(),
        headers={"Content-Type": "application/problem+json"}
    )


# ============= Exception Handlers =============
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTPException with RFC 7807 Problem Details format."""
    # Track error metrics
    ERROR_COUNT.labels(error_type="HTTPException", endpoint=request.url.path).inc()

    return create_error_response(
        status_code=exc.status_code,
        detail=str(exc.detail),
        request=request
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors with RFC 7807 Problem Details format."""
    # Track error metrics
    ERROR_COUNT.labels(error_type="ValidationError", endpoint=request.url.path).inc()

    # Format validation errors into readable message
    errors = exc.errors()
    if errors:
        # Create a readable summary of validation errors
        error_messages = []
        for error in errors:
            loc = " -> ".join(str(l) for l in error.get("loc", []))
            msg = error.get("msg", "Validation error")
            error_messages.append(f"{loc}: {msg}")
        detail = "; ".join(error_messages)
    else:
        detail = "Request validation failed"

    return create_error_response(
        status_code=422,
        detail=detail,
        request=request,
        error_type="/errors/validation",
        title="Validation Error"
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions with RFC 7807 Problem Details format.

    This is a catch-all handler for unexpected errors.
    """
    # Track error metrics
    ERROR_COUNT.labels(error_type=type(exc).__name__, endpoint=request.url.path).inc()

    # Log the full exception for debugging
    logger.exception(f"Unhandled exception at {request.url.path}: {exc}")

    # Don't expose internal error details in production
    # Check if we're in debug mode
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"

    if debug_mode:
        detail = f"{type(exc).__name__}: {str(exc)}"
    else:
        detail = "An internal server error occurred. Please try again later."

    return create_error_response(
        status_code=500,
        detail=detail,
        request=request,
        error_type="/errors/internal",
        title="Internal Server Error"
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded with RFC 7807 Problem Details format."""
    # Track error metrics
    ERROR_COUNT.labels(error_type="RateLimitExceeded", endpoint=request.url.path).inc()

    return create_error_response(
        status_code=429,
        detail=f"Rate limit exceeded: {exc.detail}",
        request=request,
        error_type="/errors/rate-limit",
        title="Too Many Requests"
    )


# Rate limiter 설정
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
# Note: RateLimitExceeded handler is defined above with RFC 7807 format

# CORS middleware - 환경변수 기반 origin 제한
_origins_env = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,https://carbon-ai-chatbot.vercel.app,https://esketch-carbon-ai-chatbot-ui.hf.space"
)

# 빈 문자열 및 와일드카드 필터링
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in _origins_env.split(",")
    if origin.strip() and origin.strip() != "*"
]

# 기본값 폴백 (필터링 후 비어있으면)
if not ALLOWED_ORIGINS:
    ALLOWED_ORIGINS = ["http://localhost:3000"]
    logger.warning("ALLOWED_ORIGINS가 비어있어 기본값 사용: http://localhost:3000")

logger.info(f"CORS 허용 origins: {ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)


# Startup event: Pre-load heavy resources (RAG only, MCP loads on first use)
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 무거운 리소스들을 미리 로드하여 첫 요청 지연 감소"""
    logger.info("=" * 60)
    logger.info("🚀 서버 시작: 리소스 사전 로드 시작")
    logger.info("=" * 60)

    startup_tasks = []

    # 1. RAG 도구 초기화 (임베딩 모델 로드)
    async def init_rag():
        try:
            logger.info("[STARTUP] RAG 도구 초기화 중...")
            rag_tool = get_rag_tool()
            if rag_tool.available:
                # Warmup: 더미 검색으로 임베딩 모델 준비
                logger.info("[STARTUP] 임베딩 모델 워밍업 중...")
                _ = rag_tool.search_documents("test warmup", k=1)
                logger.info("[STARTUP] ✓ RAG 도구 준비 완료")
            else:
                logger.warning("[STARTUP] ⚠️ RAG 도구 사용 불가 (지식베이스 없음)")
        except Exception as e:
            logger.warning(f"[STARTUP] ⚠️ RAG 도구 초기화 실패: {e} (첫 요청 시 재시도됨)")

    startup_tasks.append(init_rag())

    # MCP 클라이언트는 startup에서 초기화하지 않음
    # 이유: SSE 연결이 느려서 startup 타임아웃 발생 및 상태 불량
    # 대신 첫 번째 MCP 도구 호출 시 lazy하게 초기화됨 (이전 작동 방식)
    logger.info("[STARTUP] MCP 클라이언트는 첫 사용 시 lazy 초기화됨")

    # 병렬 실행 (전체 타임아웃 10초)
    try:
        await asyncio.wait_for(
            asyncio.gather(*startup_tasks, return_exceptions=True),
            timeout=10.0
        )
    except asyncio.TimeoutError:
        logger.warning("[STARTUP] ⚠️ 일부 초기화 작업이 타임아웃됨 (10초)")

    # Background task: clean up expired threads from MemorySaver
    async def cleanup_expired_threads():
        while True:
            await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
            try:
                now = time.time()
                expired = [
                    tid for tid, last in thread_last_activity.items()
                    if now - last > THREAD_TTL_SECONDS
                ]
                if expired:
                    checkpointer = getattr(graph, "checkpointer", None)
                    for tid in expired:
                        thread_last_activity.pop(tid, None)
                        if checkpointer and hasattr(checkpointer, "storage"):
                            # MemorySaver stores data keyed by thread_id
                            checkpointer.storage.pop(tid, None)
                    logger.info(f"Cleaned up {len(expired)} expired threads")
            except Exception as e:
                logger.warning(f"Thread cleanup error: {e}")

    asyncio.create_task(cleanup_expired_threads())

    logger.info("=" * 60)
    logger.info("✅ 서버 준비 완료")
    logger.info("=" * 60)


# Request/Response models
class Message(BaseModel):
    """Chat message model."""
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User message")
    thread_id: Optional[str] = Field(None, description="Thread ID for conversation continuity")
    category: Optional[str] = Field(None, description="Category: 탄소배출권, 규제대응, 고객상담")
    model: Optional[str] = Field("claude-haiku-4-5", description="Model name")


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str = Field(..., description="Agent response")
    thread_id: str = Field(..., description="Thread ID")


# ============= Health Check Helper Functions =============

async def check_vectordb() -> Dict[str, Any]:
    """VectorDB (ChromaDB) 상태 확인"""
    try:
        rag_tool = get_rag_tool()
        if not rag_tool.available:
            return {
                "status": "unavailable",
                "message": "RAG 라이브러리가 설치되지 않음"
            }

        vectorstore = rag_tool.vectorstore
        if vectorstore is None:
            return {
                "status": "unavailable",
                "message": "벡터 DB가 아직 구축되지 않음"
            }

        # 문서 수 확인
        collection = vectorstore._collection
        doc_count = collection.count()

        return {
            "status": "healthy",
            "document_count": doc_count,
            "db_path": str(rag_tool.chroma_db_path)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_redis() -> Dict[str, Any]:
    """Redis 캐시 상태 확인"""
    try:
        cache_manager = get_cache_manager()
        stats = cache_manager.get_stats()

        if stats.get("backend") == "redis":
            return {
                "status": "healthy",
                "backend": "redis",
                "keys": stats.get("redis_keys", 0),
                "hits": stats.get("redis_hits", 0),
                "misses": stats.get("redis_misses", 0)
            }
        else:
            return {
                "status": "healthy",
                "backend": "memory",
                "cache_size": stats.get("memory_cache_size", 0),
                "message": "Redis가 구성되지 않음, 메모리 캐시 사용 중"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_anthropic_api() -> Dict[str, Any]:
    """Anthropic API 상태 확인"""
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {
                "status": "unavailable",
                "message": "ANTHROPIC_API_KEY가 설정되지 않음"
            }

        # API 키 형식 확인 (실제 호출 없이 기본 검증)
        if not api_key.startswith("sk-ant-"):
            return {
                "status": "warning",
                "message": "API 키 형식이 예상과 다름"
            }

        return {
            "status": "healthy",
            "message": "API 키 구성됨"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_tavily_api() -> Dict[str, Any]:
    """Tavily API (웹 검색) 상태 확인"""
    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return {
                "status": "skipped",
                "message": "TAVILY_API_KEY가 설정되지 않음 (선택적 기능)"
            }

        return {
            "status": "healthy",
            "message": "API 키 구성됨"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def get_memory_usage() -> Dict[str, Any]:
    """시스템 메모리 사용량 확인"""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()

        # 시스템 전체 메모리
        system_memory = psutil.virtual_memory()

        return {
            "process_rss_mb": round(memory_info.rss / 1024 / 1024, 2),
            "process_vms_mb": round(memory_info.vms / 1024 / 1024, 2),
            "system_total_gb": round(system_memory.total / 1024 / 1024 / 1024, 2),
            "system_available_gb": round(system_memory.available / 1024 / 1024 / 1024, 2),
            "system_percent_used": system_memory.percent
        }
    except Exception as e:
        return {
            "error": str(e)
        }


# Health check endpoint (simple)
@app.get("/ok")
async def simple_health_check():
    """간단한 헬스체크 (로드밸런서용)"""
    return {"status": "ok", "service": "carbonai-agent"}


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus 메트릭 엔드포인트"""
    # Update active threads gauge
    ACTIVE_THREADS.set(len(thread_last_activity))
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Detailed health check endpoint
@app.get("/health")
async def health_check():
    """상세 헬스체크 - 모든 컴포넌트 상태 확인"""
    # 컴포넌트 상태 병렬 체크
    vectordb_check, redis_check, anthropic_check, tavily_check = await asyncio.gather(
        check_vectordb(),
        check_redis(),
        check_anthropic_api(),
        check_tavily_api(),
        return_exceptions=True
    )

    # 예외 처리
    def safe_result(result, name: str) -> Dict[str, Any]:
        if isinstance(result, Exception):
            return {"status": "unhealthy", "error": f"{name} 체크 실패: {str(result)}"}
        return result

    components = {
        "api": {"status": "healthy"},
        "vectordb": safe_result(vectordb_check, "vectordb"),
        "cache": safe_result(redis_check, "cache"),
        "anthropic": safe_result(anthropic_check, "anthropic"),
        "tavily": safe_result(tavily_check, "tavily"),
    }

    # 메모리 사용량
    memory = get_memory_usage()

    # 전체 상태 판단
    overall_status = "healthy"
    critical_components = ["api", "anthropic"]  # 필수 컴포넌트

    for name, check in components.items():
        status = check.get("status", "unknown")
        if status == "unhealthy":
            if name in critical_components:
                overall_status = "unhealthy"
            else:
                if overall_status != "unhealthy":
                    overall_status = "degraded"
        elif status == "unavailable" and name in critical_components:
            overall_status = "degraded"

    # 활성 스레드 수
    active_threads = len(thread_last_activity)

    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "service": "carbonai-agent",
        "version": "1.0.0",
        "components": components,
        "memory": memory,
        "active_threads": active_threads,
        "thread_ttl_minutes": THREAD_TTL_SECONDS // 60
    }


# Main chat endpoint (non-streaming)
@app.post("/invoke", response_model=ChatResponse)
@limiter.limit("20/minute")
async def invoke_agent(request: Request, chat_request: ChatRequest):
    """
    Invoke the agent with a message and get a complete response.

    Args:
        request: FastAPI Request object (required for rate limiting)
        chat_request: ChatRequest with message and optional parameters

    Returns:
        ChatResponse with agent's response
    """
    # Generate request ID for tracing
    request_id = str(uuid.uuid4())[:8]
    thread_id = chat_request.thread_id or "default"
    category = chat_request.category or "general"

    # Set log context for this request
    set_log_context(
        request_id=request_id,
        thread_id=thread_id,
        category=category,
        endpoint="/invoke"
    )

    start_time = time.perf_counter()
    ACTIVE_REQUESTS.inc()
    status = "success"
    try:
        logger.info("Invoke request received", extra={"message_length": len(chat_request.message)})

        # 입력 검증
        is_dangerous, pattern = detect_prompt_injection(chat_request.message)
        if is_dangerous:
            logger.warning("Dangerous input detected", extra={"pattern": pattern})

        sanitized_message = sanitize_user_input(chat_request.message)

        # Prepare configuration
        config = {
            "configurable": {
                "model": chat_request.model or "claude-haiku-4-5",
                "category": chat_request.category,
                "thread_id": chat_request.thread_id or "default"
            }
        }

        # Track agent usage
        AGENT_USAGE.labels(agent_type="invoke", category=category).inc()

        # Prepare input
        # IMPORTANT: Create HumanMessage object to avoid "complex" serialization
        input_data = {
            "messages": [HumanMessage(content=sanitized_message)]
        }

        # Invoke the graph
        result = await graph.ainvoke(input_data, config=config)

        # Extract the last message
        if result and "messages" in result and len(result["messages"]) > 0:
            last_message = result["messages"][-1]
            response_content = last_message.content if hasattr(last_message, 'content') else str(last_message)
        else:
            response_content = "No response generated"

        return ChatResponse(
            response=response_content,
            thread_id=config["configurable"]["thread_id"]
        )

    except Exception as e:
        status = "error"
        ERROR_COUNT.labels(error_type=type(e).__name__, endpoint="/invoke").inc()
        logger.error("Invoke request failed", extra={"error": str(e), "error_type": type(e).__name__})
        raise HTTPException(status_code=500, detail=f"Error invoking agent: {str(e)}")
    finally:
        elapsed = time.perf_counter() - start_time
        ACTIVE_REQUESTS.dec()
        REQUEST_COUNT.labels(endpoint="/invoke", method="POST", status=status).inc()
        REQUEST_LATENCY.labels(endpoint="/invoke").observe(elapsed)
        logger.info("Invoke request completed", extra={"status": status, "duration_seconds": round(elapsed, 3)})
        clear_log_context()


# Streaming chat endpoint
@app.post("/stream")
@limiter.limit("10/minute")
async def stream_agent(request: Request, chat_request: ChatRequest):
    """
    Stream the agent's response token by token.

    Args:
        request: FastAPI Request object (required for rate limiting)
        chat_request: ChatRequest with message and optional parameters

    Returns:
        StreamingResponse with agent's response chunks
    """
    # Generate request ID for tracing
    request_id = str(uuid.uuid4())[:8]
    thread_id = chat_request.thread_id or "default"
    category = chat_request.category or "general"

    start_time = time.perf_counter()
    REQUEST_COUNT.labels(endpoint="/stream", method="POST", status="started").inc()

    # Track agent usage
    AGENT_USAGE.labels(agent_type="stream", category=category).inc()

    try:
        # Set log context for this request
        set_log_context(
            request_id=request_id,
            thread_id=thread_id,
            category=category,
            endpoint="/stream"
        )
        logger.info("Stream request received", extra={"message_length": len(chat_request.message)})

        # 입력 검증
        is_dangerous, pattern = detect_prompt_injection(chat_request.message)
        if is_dangerous:
            logger.warning("Dangerous input detected", extra={"pattern": pattern})

        sanitized_message = sanitize_user_input(chat_request.message)

        # Prepare configuration
        config = {
            "configurable": {
                "model": chat_request.model or "claude-haiku-4-5",
                "category": chat_request.category,
                "thread_id": chat_request.thread_id or "default"
            }
        }

        # Prepare input
        # IMPORTANT: Create HumanMessage object to avoid "complex" serialization
        input_data = {
            "messages": [HumanMessage(content=sanitized_message)]
        }

        async def generate():
            """Generate streaming response with hybrid mode."""
            ACTIVE_REQUESTS.inc()
            stream_start = time.perf_counter()
            try:
                # Use hybrid streaming for real-time tokens
                async for event in graph.astream(
                    input_data,
                    config=config,
                    stream_mode=["messages", "values"]
                ):
                    # Unpack (mode, chunk) tuple
                    if isinstance(event, tuple) and len(event) == 2:
                        mode, chunk = event

                        if mode == "messages":
                            # Messages mode: extract message content (tokens)
                            if isinstance(chunk, tuple) and len(chunk) == 2:
                                msg, metadata = chunk
                                if hasattr(msg, 'content') and msg.content:
                                    yield f"data: {msg.content}\n\n"
                            elif hasattr(chunk, 'content') and chunk.content:
                                yield f"data: {chunk.content}\n\n"
                        # Skip values events in simple endpoint

                yield "data: [DONE]\n\n"
                REQUEST_COUNT.labels(endpoint="/stream", method="POST", status="success").inc()

            except Exception as e:
                ERROR_COUNT.labels(error_type=type(e).__name__, endpoint="/stream").inc()
                REQUEST_COUNT.labels(endpoint="/stream", method="POST", status="error").inc()
                yield f"data: Error: {str(e)}\n\n"
            finally:
                ACTIVE_REQUESTS.dec()
                REQUEST_LATENCY.labels(endpoint="/stream").observe(time.perf_counter() - stream_start)

        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )

    except Exception as e:
        ERROR_COUNT.labels(error_type=type(e).__name__, endpoint="/stream").inc()
        REQUEST_COUNT.labels(endpoint="/stream", method="POST", status="error").inc()
        raise HTTPException(status_code=500, detail=f"Error streaming agent: {str(e)}")


# Get available categories
@app.get("/categories")
async def get_categories():
    """Get available conversation categories."""
    return {
        "categories": [
            {
                "id": "탄소배출권",
                "name": "탄소배출권",
                "description": "배출권 거래, 구매, 판매, 관리 전문 상담"
            },
            {
                "id": "규제대응",
                "name": "규제대응",
                "description": "탄소 규제, 법규, 보고서, 컴플라이언스 대응"
            },
            {
                "id": "고객상담",
                "name": "고객상담",
                "description": "1:1 맞춤 상담, 서비스 안내, 문의사항"
            }
        ]
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "CarbonAI Agent API",
        "version": "1.0.0",
        "endpoints": {
            "health_simple": "GET /ok (로드밸런서용)",
            "health_detailed": "GET /health (상세 상태)",
            "metrics": "GET /metrics (Prometheus 메트릭)",
            "invoke": "POST /invoke",
            "stream": "POST /stream",
            "categories": "GET /categories"
        },
        "docs": "/docs"
    }


# ============= LangGraph Cloud API Compatible Endpoints =============

@app.get("/info")
async def get_info():
    """Get server information (LangGraph Cloud API compatible)."""
    return {
        "version": "1.0.0",
        "service": "CarbonAI Agent API"
    }


@app.post("/assistants/search")
async def search_assistants(request: Request):
    """Search for assistants (LangGraph Cloud API compatible)."""
    # Use a fixed UUID for the assistant
    assistant_uuid = "fe096781-5601-53d2-b2f6-0d3403f7e9ca"
    return [
        {
            "assistant_id": assistant_uuid,
            "graph_id": "agent",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "config": {},
            "metadata": {
                "name": "CarbonAI Agent",
                "description": "탄소 배출권 전문 AI 챗봇"
            }
        }
    ]


@app.get("/assistants/{assistant_id}")
async def get_assistant(assistant_id: str):
    """Get assistant by ID (LangGraph Cloud API compatible)."""
    # Always return the same assistant regardless of ID
    return {
        "assistant_id": assistant_id,
        "graph_id": "agent",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "config": {},
        "metadata": {
            "name": "CarbonAI Agent",
            "description": "탄소 배출권 전문 AI 챗봇"
        }
    }


@app.get("/assistants/{assistant_id}/schemas")
async def get_assistant_schemas(assistant_id: str):
    """Get assistant schemas (LangGraph Cloud API compatible)."""
    # Return empty schemas as we don't use custom input/output schemas
    return {
        "input_schema": {},
        "output_schema": {},
        "config_schema": {}
    }


@app.post("/threads")
async def create_thread(request: Request):
    """Create a new thread (LangGraph Cloud API compatible)."""
    thread_id = str(uuid.uuid4())
    return {
        "thread_id": thread_id,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "metadata": {}
    }


@app.get("/threads/{thread_id}/state")
async def get_thread_state(thread_id: str):
    """Get thread state (LangGraph Cloud API compatible)."""
    return {
        "values": {},
        "next": [],
        "config": {
            "configurable": {
                "thread_id": thread_id
            }
        },
        "metadata": {},
        "created_at": "2024-01-01T00:00:00Z",
        "parent_config": None
    }


@app.post("/threads/search")
async def search_threads(request: Request):
    """Search for threads (LangGraph Cloud API compatible)."""
    # Return empty list as we don't persist threads
    return []


@app.post("/threads/{thread_id}/runs")
async def create_run(thread_id: str, request: Request):
    """Create a run in a thread (LangGraph Cloud API compatible)."""
    try:
        track_thread_activity(thread_id)
        body = await request.json()

        # Extract input from body
        input_data = body.get("input", {})
        messages = input_data.get("messages", [])
        context = input_data.get("context", {})

        # Get configuration
        assistant_id = body.get("assistant_id", "agent")
        config = body.get("config", {})
        stream = body.get("stream", False)

        # Prepare user message
        if messages and len(messages) > 0:
            content = messages[-1].get("content", "")
            # content가 리스트 형태인 경우 (LangGraph Cloud 형식)
            if isinstance(content, list):
                # [{'type': 'text', 'text': '...'}, ...] 형태에서 텍스트 추출
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                user_message = " ".join(text_parts)
            else:
                user_message = str(content)
        else:
            user_message = ""

        # 입력 검증
        is_dangerous, pattern = detect_prompt_injection(user_message)
        if is_dangerous:
            logger.warning(f"[보안] 위험한 입력 감지: {pattern}")

        sanitized_message = sanitize_user_input(user_message)

        # Prepare configuration
        # Category can come from either context or config
        category = context.get("category") or config.get("configurable", {}).get("category")

        graph_config = {
            "configurable": {
                "model": config.get("configurable", {}).get("model", "claude-haiku-4-5"),
                "category": category,
                "thread_id": thread_id
            }
        }

        # Prepare input for graph
        # IMPORTANT: Create HumanMessage object to avoid "complex" serialization
        graph_input = {
            "messages": [HumanMessage(content=sanitized_message)]
        }

        if stream:
            # Streaming response with hybrid mode
            # Uses standard SSE format matching LangGraph Cloud protocol
            async def generate():
                """Generate streaming response in LangGraph Cloud SSE format."""
                t_total = time.perf_counter()
                try:
                    run_id = str(uuid.uuid4())

                    # Send metadata event first
                    metadata_payload = json.dumps({"run_id": run_id, "thread_id": thread_id}, ensure_ascii=False)
                    yield f"event: metadata\ndata: {metadata_payload}\n\n"

                    async for event in graph.astream(
                        graph_input,
                        config=graph_config,
                        stream_mode=["messages", "values"]
                    ):
                        if isinstance(event, tuple) and len(event) == 2:
                            mode, chunk = event

                            if mode == "messages":
                                # Extract the raw message for filtering
                                raw_msg = chunk[0] if isinstance(chunk, tuple) and len(chunk) == 2 else chunk

                                # Only stream AI text tokens in real-time
                                # Tool calls, tool results, etc. are handled by values mode
                                if not is_streamable_text_message(raw_msg):
                                    continue

                                if isinstance(chunk, tuple) and len(chunk) == 2:
                                    msg, metadata = chunk
                                    serialized_msg = serialize_chunk(msg)
                                    serialized_metadata = serialize_chunk(metadata) if metadata else {}
                                else:
                                    serialized_msg = serialize_chunk(chunk)
                                    serialized_metadata = {}

                                data_json = json.dumps([serialized_msg, serialized_metadata], ensure_ascii=False)
                                yield f"event: messages\ndata: {data_json}\n\n"

                            elif mode == "values":
                                serialized_data = serialize_chunk(chunk)
                                data_json = json.dumps(serialized_data, ensure_ascii=False)
                                yield f"event: values\ndata: {data_json}\n\n"

                            else:
                                continue
                        else:
                            serialized_chunk = serialize_chunk(event)
                            data_json = json.dumps(serialized_chunk, ensure_ascii=False)
                            yield f"event: values\ndata: {data_json}\n\n"

                    total_elapsed = time.perf_counter() - t_total
                    logger.info(f"⏱️ [전체 요청] {total_elapsed:.2f}초 (thread: {thread_id})")
                    yield f"event: end\ndata: {{}}\n\n"

                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    error_json = json.dumps({"error": str(e), "message": str(e)})
                    yield f"event: error\ndata: {error_json}\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            )
        else:
            # Non-streaming response
            result = await graph.ainvoke(graph_input, config=graph_config)

            return {
                "run_id": str(uuid.uuid4()),
                "thread_id": thread_id,
                "assistant_id": assistant_id,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "status": "success",
                "values": result
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating run: {str(e)}")


@app.post("/threads/{thread_id}/runs/stream")
@limiter.limit("10/minute")
async def create_run_stream(request: Request, thread_id: str):
    """Create a streaming run in a thread (LangGraph Cloud API compatible)."""
    # Generate request ID for tracing
    request_id = str(uuid.uuid4())[:8]
    REQUEST_COUNT.labels(endpoint="/threads/runs/stream", method="POST", status="started").inc()

    try:
        track_thread_activity(thread_id)
        body = await request.json()

        # Set log context early
        set_log_context(
            request_id=request_id,
            thread_id=thread_id,
            endpoint="/threads/runs/stream"
        )
        logger.debug("Stream request body received", extra={"body_keys": list(body.keys())})

        # Extract input from body
        input_data = body.get("input", {})
        messages = input_data.get("messages", [])
        context = input_data.get("context", {})

        # Get configuration
        config = body.get("config", {})

        # Prepare user message
        if messages and len(messages) > 0:
            content = messages[-1].get("content", "")
            # content가 리스트 형태인 경우 (LangGraph Cloud 형식)
            if isinstance(content, list):
                # [{'type': 'text', 'text': '...'}, ...] 형태에서 텍스트 추출
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                user_message = " ".join(text_parts)
            else:
                user_message = str(content)
        else:
            user_message = ""

        # 입력 검증
        is_dangerous, pattern = detect_prompt_injection(user_message)
        if is_dangerous:
            logger.warning("Dangerous input detected", extra={"pattern": pattern})

        sanitized_message = sanitize_user_input(user_message)

        # Prepare configuration
        # Category can come from either context or config
        category = context.get("category") or config.get("configurable", {}).get("category")

        # Update log context with category
        set_log_context(category=category or "general")
        logger.info("LangGraph stream request received", extra={"message_length": len(user_message)})

        # Track agent usage with category
        AGENT_USAGE.labels(agent_type="langgraph_stream", category=category or "general").inc()

        graph_config = {
            "configurable": {
                "model": config.get("configurable", {}).get("model", "claude-haiku-4-5"),
                "category": category,
                "thread_id": thread_id
            }
        }

        # Prepare input for graph
        # IMPORTANT: Create HumanMessage object to avoid "complex" serialization
        graph_input = {
            "messages": [HumanMessage(content=sanitized_message)]
        }

        # Streaming response with hybrid mode (messages + values)
        # Uses standard SSE format: "event: <type>\ndata: <json>\n\n"
        # This matches the LangGraph Cloud protocol expected by @langchain/langgraph-sdk
        async def generate():
            """Generate streaming response with real-time tokens."""
            import asyncio
            ACTIVE_REQUESTS.inc()
            t_total = time.perf_counter()
            stream_status = "success"
            try:
                run_id = str(uuid.uuid4())
                chunk_count = 0

                # Send metadata event first (required by SDK)
                metadata_payload = json.dumps({"run_id": run_id, "thread_id": thread_id}, ensure_ascii=False)
                yield f"event: metadata\ndata: {metadata_payload}\n\n"

                # HYBRID STREAMING: messages (real-time tokens) + values (node updates)
                async for event in graph.astream(
                    graph_input,
                    config=graph_config,
                    stream_mode=["messages", "values"]
                ):
                    chunk_count += 1

                    if isinstance(event, tuple) and len(event) == 2:
                        mode, chunk = event

                        if mode == "messages":
                            # Extract the raw message for filtering
                            raw_msg = chunk[0] if isinstance(chunk, tuple) and len(chunk) == 2 else chunk

                            # Only stream AI text tokens in real-time
                            # Tool calls, MCP results, visualizations → handled by values mode (node-level)
                            if not is_streamable_text_message(raw_msg):
                                continue

                            if isinstance(chunk, tuple) and len(chunk) == 2:
                                msg, metadata = chunk
                                serialized_msg = serialize_chunk(msg)
                                serialized_metadata = serialize_chunk(metadata) if metadata else {}
                            else:
                                serialized_msg = serialize_chunk(chunk)
                                serialized_metadata = {}

                            data_json = json.dumps([serialized_msg, serialized_metadata], ensure_ascii=False)
                            yield f"event: messages\ndata: {data_json}\n\n"

                        elif mode == "values":
                            serialized_data = serialize_chunk(chunk)
                            data_json = json.dumps(serialized_data, ensure_ascii=False)
                            yield f"event: values\ndata: {data_json}\n\n"

                        else:
                            continue
                    else:
                        # Fallback for single mode
                        serialized_chunk = serialize_chunk(event)
                        data_json = json.dumps(serialized_chunk, ensure_ascii=False)
                        yield f"event: values\ndata: {data_json}\n\n"

                # Send end event
                total_elapsed = time.perf_counter() - t_total
                logger.info("Stream completed", extra={"duration_seconds": round(total_elapsed, 3), "chunk_count": chunk_count})
                yield f"event: end\ndata: {{}}\n\n"

            except asyncio.CancelledError:
                # Client disconnected - don't yield error event
                stream_status = "cancelled"
                logger.info("Stream cancelled by client")
                raise
            except Exception as e:
                stream_status = "error"
                ERROR_COUNT.labels(error_type=type(e).__name__, endpoint="/threads/runs/stream").inc()
                logger.error("Streaming error", extra={"error": str(e), "error_type": type(e).__name__})
                import traceback
                traceback.print_exc()
                error_json = json.dumps({"error": str(e), "message": str(e)})
                yield f"event: error\ndata: {error_json}\n\n"
            finally:
                ACTIVE_REQUESTS.dec()
                REQUEST_COUNT.labels(endpoint="/threads/runs/stream", method="POST", status=stream_status).inc()
                REQUEST_LATENCY.labels(endpoint="/threads/runs/stream").observe(time.perf_counter() - t_total)
                clear_log_context()

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable Nginx buffering for streaming
            }
        )

    except Exception as e:
        ERROR_COUNT.labels(error_type=type(e).__name__, endpoint="/threads/runs/stream").inc()
        REQUEST_COUNT.labels(endpoint="/threads/runs/stream", method="POST", status="error").inc()
        logger.error("Stream request failed", extra={"error": str(e), "error_type": type(e).__name__})
        import traceback
        traceback.print_exc()
        clear_log_context()
        raise HTTPException(status_code=500, detail=f"Error creating streaming run: {str(e)}")


@app.post("/threads/{thread_id}/history")
@app.get("/threads/{thread_id}/history")
async def get_thread_history(thread_id: str, request: Request):
    """Get thread history (LangGraph Cloud API compatible)."""
    try:
        # Get the latest state from the checkpointer
        config = {"configurable": {"thread_id": thread_id}}

        # Get state from graph
        state = graph.get_state(config)

        if not state or not state.values:
            return []

        # Extract messages from state
        messages = state.values.get("messages", [])

        # Convert messages to serializable format
        serialized_messages = [message_to_dict(msg) for msg in messages]

        # Return as array of StateSnapshot objects (LangGraph SDK format)
        # SDK expects: [{ values: {...}, next: [...], config: {...}, ... }, ...]
        return [
            {
                "values": {"messages": serialized_messages},
                "next": [],
                "config": config,
                "metadata": {},
                "created_at": None,
                "parent_config": None,
            }
        ]

    except Exception as e:
        print(f"[HISTORY ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return []


# ============= Weekly Pipeline Endpoints =============
@app.post("/admin/pipeline/run")
async def run_weekly_pipeline(request: Request):
    """Run the weekly crawling and analysis pipeline manually.

    This endpoint triggers a full pipeline run:
    1. Crawl configured sources
    2. Preprocess content
    3. Classify and route to experts
    4. Analyze content
    5. Generate report and update knowledge base
    """
    from react_agent.weekly_pipeline.pipeline import WeeklyPipeline

    try:
        logger.info("[Pipeline] 수동 실행 시작")

        pipeline = WeeklyPipeline(
            days_back=7,
            enable_llm_meeting=True
        )

        result = await pipeline.run()

        logger.info(f"[Pipeline] 완료 - 크롤링: {result.crawled_count}, 분석: {result.analyzed_count}, 저장: {result.chunks_created}")

        return {
            "status": "success",
            "start_time": result.start_time.isoformat(),
            "end_time": result.end_time.isoformat(),
            "crawled_count": result.crawled_count,
            "preprocessed_count": result.preprocessed_count,
            "analyzed_count": result.analyzed_count,
            "chunks_created": result.chunks_created,
            "new_experts": result.new_experts,
            "report_path": result.report_path,
            "errors": result.errors
        }

    except Exception as e:
        logger.error(f"[Pipeline] 실행 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")


@app.get("/admin/pipeline/status")
async def get_pipeline_status():
    """Get the status of the weekly pipeline and knowledge base."""
    import os
    from pathlib import Path

    # Use environment variables if set, otherwise fallback to relative paths
    kb_path = Path(os.getenv("KNOWLEDGE_BASE_PATH", str(Path(__file__).parent.parent / "knowledge_base")))
    chroma_path = Path(os.getenv("CHROMA_DB_PATH", str(Path(__file__).parent.parent / "chroma_db")))
    reports_path = Path(__file__).parent.parent / "data" / "weekly_reports"

    # Count documents in knowledge base
    doc_count = 0
    for ext in ['.txt', '.md', '.pdf', '.docx']:
        doc_count += len(list(kb_path.rglob(f"*{ext}"))) if kb_path.exists() else 0

    # Check chroma db
    chroma_exists = chroma_path.exists() and any(chroma_path.iterdir()) if chroma_path.exists() else False

    # Get latest report
    latest_report = None
    if reports_path.exists():
        reports = sorted(reports_path.glob("*.md"), reverse=True)
        if reports:
            latest_report = reports[0].name

    return {
        "knowledge_base": {
            "path": str(kb_path),
            "document_count": doc_count,
            "exists": kb_path.exists()
        },
        "vector_db": {
            "path": str(chroma_path),
            "exists": chroma_exists
        },
        "reports": {
            "path": str(reports_path),
            "latest_report": latest_report
        }
    }


@app.post("/admin/vectordb/rebuild")
async def rebuild_vectordb():
    """Rebuild the vector database from knowledge base documents.

    This endpoint triggers a full rebuild of the ChromaDB vector store:
    1. Load all documents from knowledge_base
    2. Split into chunks
    3. Generate embeddings
    4. Store in ChromaDB
    """
    try:
        logger.info("[VectorDB] 벡터 DB 재구축 시작")

        rag_tool = get_rag_tool()
        if not rag_tool.available:
            raise HTTPException(status_code=500, detail="RAG 도구를 사용할 수 없습니다")

        # Force rebuild
        rag_tool._rebuild_vectorstore()

        # Get stats after rebuild
        doc_count = 0
        if rag_tool.vectorstore is not None:
            doc_count = rag_tool.vectorstore._collection.count()

        stats = {
            "document_count": doc_count,
            "db_path": str(rag_tool.chroma_db_path),
            "kb_path": str(rag_tool.knowledge_base_path)
        }

        logger.info(f"[VectorDB] 재구축 완료: {stats}")

        return {
            "status": "success",
            "message": "벡터 DB 재구축 완료",
            "stats": stats
        }

    except Exception as e:
        logger.error(f"[VectorDB] 재구축 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"VectorDB rebuild failed: {str(e)}")


# Run server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))  # Hugging Face Spaces default
    uvicorn.run(
        "react_agent.server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
        timeout_keep_alive=75,  # Keep connection alive for 75 seconds
        timeout_graceful_shutdown=30,  # Wait 30s for graceful shutdown
    )
