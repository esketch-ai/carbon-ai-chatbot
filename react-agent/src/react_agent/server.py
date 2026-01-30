"""FastAPI server for LangGraph agent deployment."""

import os
import uuid
import json
import logging
import asyncio
from typing import Any, Dict, Optional, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

from react_agent.graph_multi import graph   # 멀티 에이전트 그래프 임포트
from react_agent.configuration import Configuration  # 기존 설정 클래스
from langchain_core.messages import AIMessage, HumanMessage   # 랭체인 메세지 타입 임포트
from react_agent.rag_tool import get_rag_tool  # RAG 도구

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


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

# Initialize FastAPI app
app = FastAPI(
    title="CarbonAI Agent API",
    description="LangGraph-powered chatbot for carbon emission consulting",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


# Health check endpoint
@app.get("/ok")
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "carbonai-agent"}


# Main chat endpoint (non-streaming)
@app.post("/invoke", response_model=ChatResponse)
async def invoke_agent(request: ChatRequest):
    """
    Invoke the agent with a message and get a complete response.

    Args:
        request: ChatRequest with message and optional parameters

    Returns:
        ChatResponse with agent's response
    """
    try:
        # Prepare configuration
        config = {
            "configurable": {
                "model": request.model or "claude-haiku-4-5",
                "category": request.category,
                "thread_id": request.thread_id or "default"
            }
        }

        # Prepare input
        # IMPORTANT: Create HumanMessage object to avoid "complex" serialization
        input_data = {
            "messages": [HumanMessage(content=request.message)]
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
        raise HTTPException(status_code=500, detail=f"Error invoking agent: {str(e)}")


# Streaming chat endpoint
@app.post("/stream")
async def stream_agent(request: ChatRequest):
    """
    Stream the agent's response token by token.

    Args:
        request: ChatRequest with message and optional parameters

    Returns:
        StreamingResponse with agent's response chunks
    """
    try:
        # Prepare configuration
        config = {
            "configurable": {
                "model": request.model or "claude-haiku-4-5",
                "category": request.category,
                "thread_id": request.thread_id or "default"
            }
        }

        # Prepare input
        # IMPORTANT: Create HumanMessage object to avoid "complex" serialization
        input_data = {
            "messages": [HumanMessage(content=request.message)]
        }

        async def generate():
            """Generate streaming response with hybrid mode."""
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

            except Exception as e:
                yield f"data: Error: {str(e)}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )

    except Exception as e:
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
            "health": "/ok or /health",
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
            "messages": [HumanMessage(content=user_message)]
        }

        if stream:
            # Streaming response with hybrid mode
            async def generate():
                """Generate streaming response in LangGraph Cloud format with hybrid mode."""
                try:
                    # Use hybrid streaming for real-time tokens + node updates
                    async for event in graph.astream(
                        graph_input,
                        config=graph_config,
                        stream_mode=["messages", "values"]
                    ):
                        # Unpack (mode, chunk) tuple
                        if isinstance(event, tuple) and len(event) == 2:
                            mode, chunk = event

                            if mode == "messages":
                                # Messages mode: (message, metadata) tuple
                                if isinstance(chunk, tuple) and len(chunk) == 2:
                                    msg, metadata = chunk
                                    serialized_data = serialize_chunk([msg])
                                else:
                                    serialized_data = serialize_chunk([chunk])

                                stream_event = {
                                    "event": "messages",
                                    "data": serialized_data
                                }
                            elif mode == "values":
                                # Values mode: full state
                                serialized_data = serialize_chunk(chunk)
                                stream_event = {
                                    "event": "values",
                                    "data": serialized_data
                                }
                            else:
                                continue

                            yield f"data: {json.dumps(stream_event)}\n\n"
                        else:
                            # Fallback: single mode
                            serialized_chunk = serialize_chunk(event)
                            stream_event = {
                                "event": "values",
                                "data": serialized_chunk
                            }
                            yield f"data: {json.dumps(stream_event)}\n\n"

                    # Send end event
                    end_event = {
                        "event": "end"
                    }
                    yield f"data: {json.dumps(end_event)}\n\n"

                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    error_event = {
                        "event": "error",
                        "data": {"error": str(e)}
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream"
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
async def create_run_stream(thread_id: str, request: Request):
    """Create a streaming run in a thread (LangGraph Cloud API compatible)."""
    try:
        body = await request.json()
        print(f"[STREAM] Request body: {body}")

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
            "messages": [HumanMessage(content=user_message)]
        }

        # Streaming response with hybrid mode (messages + values)
        # Reference: https://docs.langchain.com/oss/python/langgraph/streaming
        async def generate():
            """Generate streaming response with real-time tokens."""
            import asyncio
            try:
                chunk_count = 0

                # HYBRID STREAMING: messages (real-time tokens) + values (node updates)
                # When using multiple modes, astream returns (mode, chunk) tuples
                async for event in graph.astream(
                    graph_input,
                    config=graph_config,
                    stream_mode=["messages", "values"]
                ):
                    chunk_count += 1

                    # Unpack (mode, chunk) tuple
                    if isinstance(event, tuple) and len(event) == 2:
                        mode, chunk = event

                        if mode == "messages":
                            # Messages mode returns (message, metadata) tuple
                            if isinstance(chunk, tuple) and len(chunk) == 2:
                                msg, metadata = chunk
                                # Stream only message content (tokens)
                                serialized_data = serialize_chunk([msg])
                            else:
                                # Fallback: chunk is already a message
                                serialized_data = serialize_chunk([chunk])

                            stream_event = {
                                "event": "messages",
                                "data": serialized_data
                            }
                        elif mode == "values":
                            # Values mode returns full state
                            serialized_data = serialize_chunk(chunk)
                            stream_event = {
                                "event": "values",
                                "data": serialized_data
                            }
                        else:
                            # Unknown mode - skip
                            continue

                        event_json = json.dumps(stream_event, ensure_ascii=False)
                        yield f"data: {event_json}\n\n"
                    else:
                        # Fallback for single mode (backward compatibility)
                        serialized_chunk = serialize_chunk(event)
                        stream_event = {
                            "event": "values",
                            "data": serialized_chunk
                        }
                        event_json = json.dumps(stream_event, ensure_ascii=False)
                        yield f"data: {event_json}\n\n"

                # Send end event
                end_event = {
                    "event": "end"
                }
                yield f"data: {json.dumps(end_event)}\n\n"

            except asyncio.CancelledError:
                # Client disconnected - don't yield error event
                raise
            except Exception as e:
                print(f"❌ 스트리밍 오류: {e}")
                import traceback
                traceback.print_exc()
                error_event = {
                    "event": "error",
                    "data": {"error": str(e)}
                }
                yield f"data: {json.dumps(error_event)}\n\n"

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
        print(f"[STREAM OUTER ERROR] {e}")
        import traceback
        traceback.print_exc()
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
