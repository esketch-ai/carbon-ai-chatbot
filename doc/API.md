# API 문서

## 개요

Carbon AI Chatbot 백엔드는 FastAPI 기반의 REST API를 제공합니다. 모든 응답은 JSON 형식이며, 스트리밍 엔드포인트는 SSE(Server-Sent Events)를 사용합니다.

---

## 기본 정보

**Base URL**
- 로컬: `http://localhost:7860`
- 프로덕션: `https://ruffy1601-carbon-ai-chatbot.hf.space`

**인증**
- 현재: 인증 없음 (오픈 액세스)
- 선택적: `X-Api-Key` 헤더

**Content-Type**
- 요청: `application/json`
- 응답: `application/json` 또는 `text/event-stream`

---

## 엔드포인트 목록

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/ok` | 간단한 헬스체크 |
| GET | `/health` | 상세 헬스 상태 |
| GET | `/info` | 서버 정보 |
| GET | `/categories` | 카테고리 목록 |
| POST | `/threads` | 새 스레드 생성 |
| GET | `/threads/{id}/state` | 스레드 상태 조회 |
| GET | `/threads/{id}/history` | 대화 히스토리 |
| POST | `/threads/{id}/history` | 히스토리 추가 |
| POST | `/threads/{id}/runs` | 비스트리밍 실행 |
| POST | `/threads/{id}/runs/stream` | 스트리밍 실행 |
| POST | `/threads/search` | 스레드 검색 |
| POST | `/assistants/search` | 어시스턴트 검색 |

---

## 헬스체크

### GET /ok

간단한 헬스체크 엔드포인트입니다.

**응답**
```json
"OK"
```

### GET /health

상세한 헬스 상태를 반환합니다.

**응답**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "llm": "healthy",
    "vectorstore": "healthy",
    "cache": "healthy"
  }
}
```

### GET /info

서버 정보와 버전을 반환합니다.

**응답**
```json
{
  "name": "Carbon AI Chatbot",
  "version": "1.0.0",
  "langgraph_version": "0.6.10",
  "python_version": "3.11.0",
  "model": "claude-haiku-4-5"
}
```

---

## 카테고리

### GET /categories

사용 가능한 카테고리 목록을 반환합니다.

**응답**
```json
{
  "categories": [
    {
      "id": "carbon_trading",
      "name": "탄소배출권",
      "description": "배출권 거래, 시장 분석"
    },
    {
      "id": "regulation",
      "name": "규제대응",
      "description": "규제, 컴플라이언스"
    },
    {
      "id": "customer_support",
      "name": "고객상담",
      "description": "일반 문의, 지원"
    }
  ]
}
```

---

## 스레드 관리

### POST /threads

새로운 대화 스레드를 생성합니다.

**요청**
```json
{
  "metadata": {
    "user_id": "user123",
    "category": "carbon_trading"
  }
}
```

**응답**
```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2024-01-15T10:30:00Z",
  "metadata": {
    "user_id": "user123",
    "category": "carbon_trading"
  }
}
```

### GET /threads/{thread_id}/state

스레드의 현재 상태를 조회합니다.

**응답**
```json
{
  "values": {
    "messages": [
      {
        "type": "human",
        "content": "배출권 구매 방법 알려주세요"
      },
      {
        "type": "ai",
        "content": "배출권 구매 절차를 안내해 드리겠습니다..."
      }
    ],
    "manager_decision": {
      "complexity": "simple",
      "assigned_agent": "simple"
    }
  },
  "metadata": {
    "thread_id": "550e8400-e29b-41d4-a716-446655440000",
    "checkpoint_id": "abc123"
  }
}
```

### GET /threads/{thread_id}/history

대화 히스토리를 조회합니다.

**쿼리 파라미터**
| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| limit | int | 100 | 최대 메시지 수 |

**응답**
```json
{
  "messages": [
    {
      "id": "msg-001",
      "type": "human",
      "content": "배출권 구매 방법 알려주세요",
      "timestamp": "2024-01-15T10:30:00Z"
    },
    {
      "id": "msg-002",
      "type": "ai",
      "content": "배출권 구매 절차를 안내해 드리겠습니다...",
      "timestamp": "2024-01-15T10:30:05Z",
      "tool_calls": []
    }
  ]
}
```

### POST /threads/{thread_id}/history

히스토리에 메시지를 추가합니다.

**요청**
```json
{
  "messages": [
    {
      "type": "human",
      "content": "추가 질문입니다"
    }
  ]
}
```

**응답**
```json
{
  "success": true
}
```

---

## 스레드 검색

### POST /threads/search

메타데이터로 스레드를 검색합니다.

**요청**
```json
{
  "metadata": {
    "assistant_id": "agent"
  },
  "limit": 100
}
```

**응답**
```json
{
  "threads": [
    {
      "thread_id": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T11:00:00Z",
      "metadata": {
        "assistant_id": "agent",
        "category": "carbon_trading"
      }
    }
  ]
}
```

---

## 어시스턴트 검색

### POST /assistants/search

사용 가능한 어시스턴트를 검색합니다.

**요청**
```json
{
  "graph_id": "agent"
}
```

**응답**
```json
{
  "assistants": [
    {
      "assistant_id": "agent",
      "graph_id": "agent",
      "name": "Carbon AI Chatbot",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

---

## 에이전트 실행

### POST /threads/{thread_id}/runs

비스트리밍 모드로 에이전트를 실행합니다.

**요청**
```json
{
  "assistant_id": "agent",
  "input": {
    "messages": [
      {
        "type": "human",
        "content": "KOC 현재 시세 알려주세요"
      }
    ]
  },
  "config": {
    "configurable": {
      "category": "carbon_trading"
    }
  }
}
```

**응답**
```json
{
  "run_id": "run-001",
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "values": {
    "messages": [
      {
        "type": "human",
        "content": "KOC 현재 시세 알려주세요"
      },
      {
        "type": "ai",
        "content": "현재 KOC 시세는 15,000원입니다...",
        "tool_calls": [
          {
            "name": "get_market_price",
            "args": {"credit_type": "KOC"},
            "result": {"price": 15000, "change": "+2.3%"}
          }
        ]
      }
    ],
    "manager_decision": {
      "complexity": "medium",
      "assigned_agent": "carbon_expert"
    }
  }
}
```

### POST /threads/{thread_id}/runs/stream

SSE 스트리밍 모드로 에이전트를 실행합니다.

**요청**
```json
{
  "assistant_id": "agent",
  "input": {
    "messages": [
      {
        "type": "human",
        "content": "배출권 거래 절차를 다이어그램으로 설명해주세요"
      }
    ]
  },
  "config": {
    "configurable": {
      "category": "carbon_trading"
    }
  },
  "stream_mode": ["messages", "values"],
  "stream_subgraphs": true
}
```

**SSE 응답 스트림**

```
event: metadata
data: {"run_id": "run-001", "thread_id": "550e8400-...", "assistant_id": "agent"}

event: messages
data: {"type": "ai", "content": [{"type": "text", "text": "배출권"}]}

event: messages
data: {"type": "ai", "content": [{"type": "text", "text": " 거래"}]}

event: messages
data: {"type": "ai", "content": [{"type": "text", "text": " 절차를"}]}

...

event: messages
data: {"type": "ai", "content": [{"type": "text", "text": "```mermaid\ngraph TD\n    A[시작] --> B[로그인]\n```"}]}

event: values
data: {"messages": [...], "manager_decision": {...}, "agent_used": "carbon_expert"}

event: end
data: {}
```

---

## SSE 이벤트 타입

### metadata
실행 메타데이터를 전송합니다.

```
event: metadata
data: {
  "run_id": "run-001",
  "thread_id": "550e8400-...",
  "assistant_id": "agent"
}
```

### messages
AI 응답 토큰을 실시간으로 전송합니다.

```
event: messages
data: {
  "type": "ai",
  "content": [
    {
      "type": "text",
      "text": "응답 토큰"
    }
  ]
}
```

### values
노드 완료 시 전체 상태를 전송합니다.

```
event: values
data: {
  "messages": [...],
  "prefetched_context": {...},
  "manager_decision": {...},
  "agent_used": "carbon_expert"
}
```

### end
스트림 종료를 알립니다.

```
event: end
data: {}
```

### error
오류 발생 시 전송합니다.

```
event: error
data: {
  "error": "Internal server error",
  "code": "ERR_INTERNAL"
}
```

---

## 메시지 타입

### HumanMessage
사용자 메시지입니다.

```json
{
  "type": "human",
  "content": "질문 내용",
  "id": "msg-001"
}
```

### AIMessage
AI 응답 메시지입니다.

```json
{
  "type": "ai",
  "content": "응답 내용",
  "id": "msg-002",
  "tool_calls": [
    {
      "id": "call-001",
      "name": "search_knowledge_base",
      "args": {"query": "배출권"}
    }
  ]
}
```

### ToolMessage
도구 실행 결과입니다.

```json
{
  "type": "tool",
  "content": "도구 실행 결과...",
  "tool_call_id": "call-001",
  "name": "search_knowledge_base"
}
```

---

## 에러 응답

### 400 Bad Request
잘못된 요청입니다.

```json
{
  "detail": "Invalid request body",
  "code": "ERR_INVALID_REQUEST"
}
```

### 404 Not Found
리소스를 찾을 수 없습니다.

```json
{
  "detail": "Thread not found",
  "code": "ERR_NOT_FOUND"
}
```

### 429 Too Many Requests
요청 제한을 초과했습니다.

```json
{
  "detail": "Rate limit exceeded",
  "code": "ERR_RATE_LIMIT",
  "retry_after": 60
}
```

### 500 Internal Server Error
서버 오류입니다.

```json
{
  "detail": "Internal server error",
  "code": "ERR_INTERNAL"
}
```

---

## 프론트엔드 클라이언트 예시

### LangGraph SDK 사용

```typescript
import { Client } from "@langchain/langgraph-sdk";

const client = new Client({
  apiUrl: "https://ruffy1601-carbon-ai-chatbot.hf.space",
});

// 스레드 생성
const thread = await client.threads.create({
  metadata: { category: "carbon_trading" }
});

// 스트리밍 실행
const stream = await client.runs.stream(
  thread.thread_id,
  "agent",
  {
    input: {
      messages: [{ type: "human", content: "KOC 시세?" }]
    },
    streamMode: ["messages", "values"]
  }
);

for await (const event of stream) {
  if (event.event === "messages") {
    console.log("Token:", event.data);
  } else if (event.event === "values") {
    console.log("State:", event.data);
  }
}
```

### fetch 사용

```typescript
const response = await fetch(
  "https://ruffy1601-carbon-ai-chatbot.hf.space/threads/xxx/runs/stream",
  {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      assistant_id: "agent",
      input: {
        messages: [{ type: "human", content: "질문" }]
      },
      stream_mode: ["messages", "values"]
    })
  }
);

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const text = decoder.decode(value);
  // SSE 이벤트 파싱
  for (const line of text.split("\n")) {
    if (line.startsWith("data: ")) {
      const data = JSON.parse(line.slice(6));
      console.log(data);
    }
  }
}
```

---

## cURL 예시

### 헬스체크

```bash
curl https://ruffy1601-carbon-ai-chatbot.hf.space/health
```

### 스레드 생성

```bash
curl -X POST https://ruffy1601-carbon-ai-chatbot.hf.space/threads \
  -H "Content-Type: application/json" \
  -d '{"metadata": {"category": "carbon_trading"}}'
```

### 비스트리밍 실행

```bash
curl -X POST https://ruffy1601-carbon-ai-chatbot.hf.space/threads/xxx/runs \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "agent",
    "input": {
      "messages": [{"type": "human", "content": "KOC 시세?"}]
    }
  }'
```

### 스트리밍 실행

```bash
curl -N -X POST https://ruffy1601-carbon-ai-chatbot.hf.space/threads/xxx/runs/stream \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "agent",
    "input": {
      "messages": [{"type": "human", "content": "KOC 시세?"}]
    },
    "stream_mode": ["messages", "values"]
  }'
```
