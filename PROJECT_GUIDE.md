# CarbonAI 프로젝트 가이드

## 한줄 요약

사용자가 탄소배출권/규제/고객상담 질문을 하면, **매니저 에이전트**가 복잡도를 판단하고 적합한 **전문가 에이전트**에게 라우팅하여 답변을 생성하는 AI 챗봇.

---

## 프로젝트 구조

```
carbon-ai-chatbot/
├── agent-chat-ui/          ← 프론트엔드 (Next.js + React)
├── react-agent/            ← 백엔드 (FastAPI + LangGraph)
├── Dockerfile              ← Hugging Face Spaces 배포용
└── Makefile                ← 빌드 자동화
```

- **프론트엔드**: Vercel에 배포 (GitHub `github` 리모트 → 자동 배포)
- **백엔드**: Hugging Face Spaces에 배포 (HF `origin` 리모트 → 자동 배포)

---

## 요청 흐름 (전체 그림)

```
사용자 입력 (메시지 + 카테고리 선택)
    ↓
[프론트엔드] POST /threads/{threadId}/runs/stream
    ↓
[백엔드 server.py] create_run_stream() → HumanMessage 생성
    ↓
[LangGraph 그래프] graph.astream()
    ↓
┌─────────────────────────────────────────────┐
│  1. smart_tool_prefetch                     │
│     ├ FAQ 캐시 확인 (있으면 바로 종료)       │
│     ├ RAG 지식베이스 검색 (병렬)             │
│     └ 웹 검색 (병렬)                        │
│                                             │
│  2. manager_agent (라우팅 판단)              │
│     → tool_choice로 JSON 강제 출력          │
│     → {assigned_agent, complexity, ...}     │
│                                             │
│  3. simple_agent 또는 expert_agent          │
│     → 카테고리별 전문 프롬프트              │
│     → 필요시 도구 호출 (MCP, 웹검색 등)     │
│     → 도구 결과로 재호출 (루프)             │
│                                             │
│  4. 최종 응답 반환                          │
└─────────────────────────────────────────────┘
    ↓
[백엔드] SSE 스트리밍 이벤트 전송
    ├ event: metadata  → {run_id, thread_id}
    ├ event: messages  → AI 텍스트 토큰 (실시간)
    ├ event: values    → 상태 업데이트 (도구 결과 등)
    └ event: end       → 완료
    ↓
[프론트엔드] 토큰 실시간 렌더링 + 시각화(차트/표/지도) 감지 및 렌더링
```

---

## 프론트엔드 구조 (agent-chat-ui/)

### Provider 계층 (위에서 아래로 감싸는 순서)

```
StreamProvider          ← API 연결, 스트리밍 관리
  └ SessionContext      ← 세션 타이머 (60분 비활동 만료)
    └ AssistantConfig   ← 어시스턴트 설정
      └ ThreadProvider  ← 대화 히스토리
        └ Settings      ← 테마, UI 설정
```

### 주요 컴포넌트

| 컴포넌트 | 위치 | 역할 |
|---------|------|------|
| `Thread` | `components/thread/index.tsx` | 메인 채팅 화면 (입력, 메시지 목록, 전송) |
| `ThreadHistory` | `components/thread/history/` | 사이드바 대화 목록 |
| `AssistantMessage` | `components/thread/messages/ai.tsx` | AI 응답 렌더링 (마크다운, 시각화) |
| `HumanMessage` | `components/thread/messages/human.tsx` | 사용자 메시지 |
| `SettingsDialog` | `components/settings/` | 설정 다이얼로그 |
| `CategorySelectors` | `components/thread/CategorySelectors.tsx` | 카테고리 선택 UI |

### 주요 Hook

| Hook | 역할 |
|------|------|
| `useStreamContext` | 스트리밍 데이터 접근 (messages, isLoading, submit 등) |
| `useSession` | 세션 타이머 리셋 함수 (`resetSessionTimer`) |
| `useSessionTimeout` | 60분 비활동 감지 → 토스트 알림 → 새 대화 |
| `useThreads` | 대화 목록 CRUD |
| `useSettings` | 테마/UI 설정 읽기/쓰기 |

### 데이터 흐름 예시: 메시지 전송

```
1. 사용자가 텍스트 입력 + Enter
2. thread/index.tsx handleSubmit()
   → stream.submit({messages: [...], context: {category}})
   → resetSessionTimer()  (세션 타이머 리셋)
3. StreamProvider가 POST /threads/{id}/runs/stream 호출
4. SSE 이벤트 수신
   → messages 이벤트: 실시간 토큰 → 화면에 글자 하나씩 표시
   → values 이벤트: 도구 호출 결과 → 시각화 렌더링
5. end 이벤트 → isLoading = false
```

---

## 백엔드 구조 (react-agent/)

### 파일 역할 맵

```
src/react_agent/
├── server.py              ← FastAPI 서버 (API 엔드포인트, SSE 스트리밍)
├── graph_multi.py         ← LangGraph 그래프 정의 (노드 연결, 라우팅 조건)
├── agents/
│   ├── config.py          ← 에이전트별 설정 (모델, 도구, 복잡도 범위)
│   ├── nodes.py           ← 에이전트 실행 로직 (manager, simple, expert)
│   └── prompts.py         ← 프롬프트 템플릿 (시스템 프롬프트, 시각화 가이드)
├── state.py               ← LangGraph 상태 정의 (messages, manager_decision 등)
├── configuration.py       ← 런타임 설정 (model, category, system_prompt)
├── tools.py               ← 도구 정의 (search, RAG, classify 등)
├── rag_tool.py            ← RAG 시스템 (ChromaDB + 하이브리드 검색)
├── sse_mcp_client.py      ← NET-Z MCP 클라이언트 (외부 API 도구)
├── cache_manager.py       ← 캐시 (FAQ 캐시 + LLM 응답 캐시)
└── utils.py               ← 유틸리티 (Mermaid 변환, 대화 컨텍스트 추출)
```

### 멀티 에이전트 시스템

#### 에이전트 구성

| 에이전트 | 모델 | 역할 | 도구 |
|---------|------|------|------|
| **Manager** | Haiku 4.5 | 질문 복잡도 판단 + 라우팅 | 없음 (tool_choice로 JSON 판단만) |
| **Simple** | Haiku 4.5 | 기본 질문 답변 | RAG, 웹검색, 고객분류 |
| **Carbon Expert** | Haiku 4.5 | 배출권 전문 | RAG, 웹검색, NET-Z MCP 도구 |
| **Regulation Expert** | Haiku 4.5 | 규제 전문 | RAG, 웹검색, NET-Z MCP 도구 |
| **Support Expert** | Haiku 4.5 | 고객지원 | RAG, 웹검색, 고객분류 |

#### 라우팅 흐름 (graph_multi.py)

```
START → smart_tool_prefetch
            ↓
        FAQ 캐시 히트? ──YES──→ END (즉시 응답)
            │NO
            ↓
        manager_agent
            ↓
        complexity 판단
            ├── simple → simple_agent
            └── medium/complex → expert_agent (카테고리별)
                    ↓
                도구 호출 필요? ──YES──→ tools → 다시 에이전트로 (루프)
                    │NO
                    ↓
                   END
```

#### Manager의 tool_choice (JSON 파싱 실패 방지)

```python
# 이전: 프롬프트로 "JSON으로 응답해줘" → 자유 텍스트 반환 → json.loads() 실패
# 현재: tool_choice로 구조화 출력 강제 → 항상 정확한 JSON 반환

route_tool = {
    "name": "route_decision",
    "input_schema": {
        "properties": {
            "complexity": {"enum": ["simple", "medium", "complex"]},
            "assigned_agent": {"enum": ["simple", "carbon_expert"]},  # 카테고리별 동적
            "reasoning": {"type": "string"},
            "confidence": {"type": "number"}
        }
    }
}
model = llm.bind_tools([route_tool], tool_choice={"type": "tool", "name": "route_decision"})
# → response.tool_calls[0]["args"]에서 바로 dict 추출
```

### RAG 시스템 (rag_tool.py)

```
지식베이스 문서 (knowledge_base/)
    ↓ 청킹 (800자, 150자 오버랩)
    ↓ 임베딩 (BGE-m3-ko 한국어 모델)
    ↓
ChromaDB 벡터 저장소
    ↓
검색 요청 시:
    ├ 벡터 유사도 검색 (코사인)
    ├ BM25 키워드 검색
    └ RRF (Reciprocal Rank Fusion)로 결합
    ↓
상위 3개 문서 반환 (유사도 0.7 이상)
```

### 캐시 시스템 (cache_manager.py)

```
요청 → FAQ 캐시 확인 (정확 매칭)
         ├ HIT → 즉시 반환
         └ MISS → LLM 응답 캐시 확인
                    ├ HIT → 캐시된 응답 반환
                    └ MISS → LLM 호출 → 응답 캐시 저장
```

- **백엔드**: Redis (가능 시) 또는 인메모리 딕셔너리
- **TTL**: 24시간

---

## 세션 관리

### 프론트엔드: 60분 비활동 자동 만료

```
useSessionTimeout 훅 (Stream.tsx에서 초기화)
    ↓
타이머 시작 (60분)
    ↓
아래 동작 시 타이머 리셋:
    - 메시지 전송
    - 새 채팅 버튼
    - 로고 클릭
    - 스레드 삭제
    ↓
60분 비활동 시:
    → 토스트: "세션이 만료되어 새 대화가 시작됩니다"
    → threadId = null (새 대화 화면)
```

### 백엔드: 만료 스레드 메모리 정리

```
30분 주기로 실행 (background task)
    ↓
90분 이상 비활동 스레드
    → MemorySaver 체크포인트 삭제
    → 로그: "Cleaned up N expired threads"
```

---

## API 엔드포인트 요약

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/ok`, `/health` | 헬스체크 |
| GET | `/info` | 서버 정보 |
| POST | `/threads` | 새 스레드 생성 |
| POST | `/threads/{id}/runs/stream` | **메인**: 스트리밍 응답 |
| POST | `/threads/{id}/runs` | 비스트리밍 응답 |
| GET/POST | `/threads/{id}/history` | 대화 히스토리 |
| POST | `/threads/search` | 스레드 검색 |
| POST | `/assistants/search` | 어시스턴트 검색 |
| GET | `/categories` | 카테고리 목록 |

---

## 환경 변수

### 프론트엔드 (.env)
```
NEXT_PUBLIC_API_URL=https://ruffy1601-carbon-ai-chatbot.hf.space
NEXT_PUBLIC_ASSISTANT_ID=agent
```

### 백엔드 (.env)
```
ANTHROPIC_API_KEY=...          # Claude API 키
TAVILY_API_KEY=...             # 웹 검색
NETZ_MCP_ENABLED=true          # NET-Z MCP 연동
NETZ_MCP_URL=http://...        # MCP 서버 주소
USE_REDIS_CACHE=true           # Redis 캐시 사용
REDIS_URL=redis://localhost:6379/0
```

---

## 최근 변경 이력

| 커밋 | 변경 내용 |
|------|----------|
| `af42cf6` | `logging.basicConfig()` 추가 → 성능 측정 로그 출력 활성화 |
| `68ad2bc` | Manager에 `tool_choice` 적용 → JSON 파싱 실패 원천 차단 |
| `8bfaef8` | 세션 60분 자동 만료 + 백엔드 90분 스레드 정리 |
| `a130ac1` | 파이프라인 단계별 소요 시간 측정 로그 |
| `5e84145` | SSE end 이벤트 빈 JSON 객체 전송 (파싱 에러 해결) |

---

## 시각화 지원

AI 응답에 코드 블록이 포함되면 자동으로 시각화 컴포넌트로 렌더링:

| 코드 블록 | 렌더링 | 용도 |
|-----------|--------|------|
| ` ```agchart ` | AG Charts | 파이/바/라인 차트 |
| ` ```aggrid ` | AG Grid | 인터랙티브 테이블 |
| ` ```mermaid ` | Mermaid SVG | 플로우차트, 다이어그램 |
| ` ```map ` | Deck.gl/Leaflet | 지도 시각화 |

---

## 로컬 개발

### 프론트엔드
```bash
cd agent-chat-ui
pnpm install
pnpm dev          # http://localhost:3000
```

### 백엔드
```bash
cd react-agent
pip install -e .
python -m react_agent.server   # http://localhost:7860
```

### 배포
```bash
git push origin main    # → Hugging Face Spaces (백엔드)
git push github main    # → GitHub → Vercel (프론트엔드)
```
