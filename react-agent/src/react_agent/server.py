"""FastAPI server for LangGraph agent deployment."""

import os
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

from react_agent.graph import graph
from react_agent.configuration import Configuration

# Load environment variables
load_dotenv()

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
    model: Optional[str] = Field("claude-3-5-sonnet-20241022", description="Model name")


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
                "model": request.model or "claude-3-5-sonnet-20241022",
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
                "model": request.model or "claude-3-5-sonnet-20241022",
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
