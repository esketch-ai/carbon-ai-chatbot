"""FastAPI server for LangGraph agent deployment."""

import os
import uuid
import json
from typing import Any, Dict, Optional, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

from react_agent.graph import graph   # 기존 langgraph 그래프 임포트
from react_agent.configuration import Configuration  # 기존 설정 클래스
from langchain_core.messages import AIMessage, HumanMessage   # 랭체인 메세지 타입 임포트

# Load environment variables
load_dotenv()


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
        print(f"[SERIALIZE] Extracted content: {extracted_content[:200]}...")
    elif isinstance(result, dict) and result.get('content') == 'complex':
        # Fallback: if content is still "complex", log warning
        print(f"[SERIALIZE WARNING] Content is 'complex' - extraction may have failed")
        print(f"[SERIALIZE WARNING] Message type: {type(msg)}, has content: {hasattr(msg, 'content')}")

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


def normalize_stream_mode(raw_mode: Any, default: str = "values") -> str:
    """Normalize stream mode from request body to a single mode string."""
    if raw_mode is None:
        return default
    if isinstance(raw_mode, list) and raw_mode:
        # SDK sends an array; we currently support a single mode at a time.
        return str(raw_mode[0])
    if isinstance(raw_mode, str):
        return raw_mode
    return default

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
            """Generate streaming response."""
            try:
                async for chunk in graph.astream(input_data, config=config):
                    # Extract message content from chunk
                    if "messages" in chunk and len(chunk["messages"]) > 0:
                        message = chunk["messages"][-1]
                        if hasattr(message, 'content'):
                            yield f"data: {message.content}\n\n"

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
        requested_stream_mode = body.get("stream_mode") or body.get("streamMode")
        stream_mode = normalize_stream_mode(requested_stream_mode, default="values")

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
            # Streaming response
            async def generate():
                """Generate streaming response in LangGraph Cloud format."""
                try:
                    async for chunk in graph.astream(
                        graph_input,
                        config=graph_config,
                        stream_mode=stream_mode
                    ):
                        # Serialize chunk to JSON-serializable format
                        serialized_chunk = serialize_chunk(chunk)
                        # Format as LangGraph Cloud stream event
                        event = {
                            "event": stream_mode,
                            "data": serialized_chunk
                        }
                        yield f"data: {json.dumps(event)}\n\n"

                    # Send end event
                    end_event = {
                        "event": "end"
                    }
                    yield f"data: {json.dumps(end_event)}\n\n"

                except Exception as e:
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
        print(f"[STREAM] Messages: {messages}")
        print(f"[STREAM] Context: {context}")

        # Get configuration
        config = body.get("config", {})
        requested_stream_mode = body.get("stream_mode") or body.get("streamMode")
        stream_mode = normalize_stream_mode(requested_stream_mode, default="messages")

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

        print(f"[STREAM] User message: {user_message}")

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
        print(f"[STREAM] Graph config: {graph_config}")
        print(f"[STREAM] Stream mode: {stream_mode}")

        # Prepare input for graph
        # IMPORTANT: Create HumanMessage object to avoid "complex" serialization
        graph_input = {
            "messages": [HumanMessage(content=user_message)]
        }

        print(f"[STREAM] Starting token-level streaming...")

        # Token-level streaming using astream_events
        async def generate():
            """Generate streaming response with real-time token updates."""
            import asyncio
            event_count = 0
            token_buffer = []

            try:
                # Try astream_events for token-level streaming first
                print(f"[STREAM] Using astream_events for token-level streaming")
                async for event in graph.astream_events(
                    graph_input,
                    config=graph_config,
                    version="v2"
                ):
                    event_count += 1
                    event_type = event.get("event")
                    event_name = event.get("name", "")

                    print(f"[STREAM] Event {event_count}: type={event_type}, name={event_name}")

                    # Handle token streaming from chat model
                    if event_type == "on_chat_model_stream":
                        # Extract token from the chunk
                        chunk_data = event.get("data", {})
                        chunk_obj = chunk_data.get("chunk")

                        if chunk_obj and hasattr(chunk_obj, "content"):
                            token = chunk_obj.content
                            if token:  # Only send non-empty tokens
                                token_buffer.append(token)
                                print(f"[STREAM] Token: {token}")

                                # Send token as custom event for real-time display
                                token_event = {
                                    "event": "messages",
                                    "data": {
                                        "messages": [{
                                            "type": "ai",
                                            "content": [{"type": "text", "text": token}],
                                            "id": f"token-{event_count}"
                                        }]
                                    }
                                }
                                yield f"data: {json.dumps(token_event, ensure_ascii=False)}\n\n"

                    # Handle final message completion
                    elif event_type == "on_chat_model_end":
                        print(f"[STREAM] Chat model completed. Total tokens: {len(token_buffer)}")

                        # Send complete message
                        full_text = "".join(token_buffer)
                        complete_event = {
                            "event": "values",
                            "data": {
                                "messages": [{
                                    "type": "ai",
                                    "content": [{"type": "text", "text": full_text}],
                                    "id": f"complete-{event_count}"
                                }]
                            }
                        }
                        yield f"data: {json.dumps(complete_event, ensure_ascii=False)}\n\n"
                        token_buffer = []

                    # Handle tool calls and other node updates
                    elif event_type == "on_chain_end" and event_name:
                        result_data = event.get("data", {})
                        output = result_data.get("output", {})

                        # Send node completion event
                        if output:
                            serialized_output = serialize_chunk(output)
                            node_event = {
                                "event": "values",
                                "data": serialized_output
                            }
                            yield f"data: {json.dumps(node_event, ensure_ascii=False)}\n\n"

                print(f"[STREAM] Stream completed with {event_count} events")

                # Send end event
                end_event = {"event": "end"}
                yield f"data: {json.dumps(end_event)}\n\n"

            except asyncio.CancelledError:
                print(f"[STREAM] Client disconnected (CancelledError) after {event_count} events")
                return
            except GeneratorExit:
                print(f"[STREAM] Client disconnected (GeneratorExit) after {event_count} events")
                return
            except Exception as e:
                print(f"[STREAM ERROR] {type(e).__name__}: {e}")
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
