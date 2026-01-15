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

from react_agent.graph import graph
from react_agent.configuration import Configuration
from langchain_core.messages import AIMessage, HumanMessage

# Load environment variables
load_dotenv()


# Helper function to convert LangChain messages to JSON-serializable format
def message_to_dict(msg):
    """Convert a LangChain message to a JSON-serializable dictionary."""
    if hasattr(msg, 'dict'):
        return msg.dict()
    elif hasattr(msg, 'model_dump'):
        return msg.model_dump()
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
        return result
    else:
        return str(msg)


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
        input_data = {
            "messages": [{"role": "user", "content": request.message}]
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
        input_data = {
            "messages": [{"role": "user", "content": request.message}]
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
        graph_config = {
            "configurable": {
                "model": config.get("configurable", {}).get("model", "claude-haiku-4-5"),
                "category": config.get("configurable", {}).get("category"),
                "thread_id": thread_id
            }
        }

        # Prepare input for graph
        graph_input = {
            "messages": [{"role": "user", "content": user_message}]
        }

        if stream:
            # Streaming response
            async def generate():
                """Generate streaming response in LangGraph Cloud format."""
                try:
                    async for chunk in graph.astream(graph_input, config=graph_config):
                        # Serialize chunk to JSON-serializable format
                        serialized_chunk = serialize_chunk(chunk)
                        # Format as LangGraph Cloud stream event
                        event = {
                            "event": "values",
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
        print(f"[STREAM] Messages: {messages}")

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

        print(f"[STREAM] User message: {user_message}")

        # Prepare configuration
        graph_config = {
            "configurable": {
                "model": config.get("configurable", {}).get("model", "claude-haiku-4-5"),
                "category": config.get("configurable", {}).get("category"),
                "thread_id": thread_id
            }
        }

        # Prepare input for graph
        graph_input = {
            "messages": [{"role": "user", "content": user_message}]
        }

        print(f"[STREAM] Starting graph stream with astream_events...")

        # Streaming response using astream_events for token-level streaming
        async def generate():
            """Generate streaming response with token-level granularity."""
            try:
                chunk_count = 0
                accumulated_content = ""

                # Initialize with user message
                user_msg = HumanMessage(content=user_message, id=str(uuid.uuid4()))
                current_messages = [user_msg]

                # Use astream_events for fine-grained streaming
                async for event in graph.astream_events(graph_input, config=graph_config, version="v2"):
                    event_type = event.get("event")

                    # Track LLM token streaming
                    if event_type == "on_chat_model_stream":
                        chunk_count += 1
                        chunk_data = event.get("data", {})
                        chunk_content = chunk_data.get("chunk", {})

                        # Extract content from AIMessageChunk
                        token = ""
                        if hasattr(chunk_content, "content"):
                            content = chunk_content.content
                            # Content can be string or list
                            if isinstance(content, str):
                                token = content
                            elif isinstance(content, list):
                                # Extract text from list format
                                for item in content:
                                    if isinstance(item, str):
                                        token += item
                                    elif isinstance(item, dict) and item.get("type") == "text":
                                        token += item.get("text", "")
                        elif isinstance(chunk_content, dict):
                            content = chunk_content.get("content", "")
                            if isinstance(content, str):
                                token = content
                            elif isinstance(content, list):
                                for item in content:
                                    if isinstance(item, str):
                                        token += item
                                    elif isinstance(item, dict) and item.get("type") == "text":
                                        token += item.get("text", "")
                        else:
                            token = str(chunk_content) if chunk_content else ""

                        if token:
                            accumulated_content += token

                            # Create intermediate message with accumulated content
                            # LangGraph SDK expects messages at the root level
                            intermediate_msg = AIMessage(
                                content=accumulated_content,
                                id=event.get("run_id", "temp")
                            )

                            # Include both user message and streaming AI response
                            all_messages = current_messages + [intermediate_msg]

                            # Send as values event with messages at root
                            stream_event = {
                                "event": "values",
                                "data": {
                                    "messages": [message_to_dict(msg) for msg in all_messages]
                                }
                            }

                            yield f"data: {json.dumps(stream_event)}\n\n"

                            if chunk_count % 10 == 0:
                                print(f"[STREAM] Tokens streamed: {chunk_count}, Length: {len(accumulated_content)}")

                    # Track node completion (call_model, tools, etc.)
                    elif event_type == "on_chain_end":
                        name = event.get("name", "")
                        if name == "call_model":
                            # Final message from call_model node
                            output = event.get("data", {}).get("output", {})
                            if "messages" in output:
                                current_messages = output["messages"]

                                # Serialize and send with messages at root level
                                serialized_messages = [message_to_dict(msg) for msg in current_messages]
                                stream_event = {
                                    "event": "values",
                                    "data": {
                                        "messages": serialized_messages
                                    }
                                }
                                yield f"data: {json.dumps(stream_event)}\n\n"
                                print(f"[STREAM] Node 'call_model' completed with {len(current_messages)} messages")

                    # Track tool calls
                    elif event_type == "on_tool_start":
                        tool_name = event.get("name", "unknown")
                        print(f"[STREAM] Tool '{tool_name}' started")

                    elif event_type == "on_tool_end":
                        tool_name = event.get("name", "unknown")
                        print(f"[STREAM] Tool '{tool_name}' completed")

                print(f"[STREAM] Stream completed - Total tokens: {chunk_count}, Final length: {len(accumulated_content)}")

                # Send end event
                end_event = {
                    "event": "end"
                }
                yield f"data: {json.dumps(end_event)}\n\n"

            except Exception as e:
                print(f"[STREAM ERROR] {e}")
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
    # Return empty array directly (frontend expects array, not object)
    return []


# Run server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))  # Hugging Face Spaces default
    uvicorn.run(
        "react_agent.server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
