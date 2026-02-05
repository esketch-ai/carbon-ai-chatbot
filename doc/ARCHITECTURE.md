# 시스템 아키텍처

## 개요

Carbon AI Chatbot은 **멀티 에이전트 AI 챗봇 시스템**으로, 프론트엔드와 백엔드가 분리된 마이크로서비스 아키텍처를 채택하고 있습니다.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         사용자 (브라우저)                            │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    프론트엔드 (Vercel)                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │  Next.js    │  │   React     │  │  LangGraph  │                  │
│  │  App Router │  │   Context   │  │    SDK      │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │ SSE Streaming
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    백엔드 (HuggingFace Spaces)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │   FastAPI   │  │  LangGraph  │  │   Claude    │                  │
│  │   Server    │  │    Agent    │  │  Haiku 4.5  │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │  Chroma DB  │  │   Tavily    │  │   NET-Z     │                  │
│  │  (Vector)   │  │  (Search)   │  │    MCP      │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 프론트엔드 아키텍처

### 기술 스택

| 기술 | 버전 | 용도 |
|------|------|------|
| **Next.js** | 15.5.9 | React 프레임워크 (App Router) |
| **React** | 19.0.0 | UI 라이브러리 |
| **TypeScript** | ~5.7.2 | 타입 안정성 |
| **Tailwind CSS** | 4.0.13 | 스타일링 |
| **LangGraph SDK** | 0.2.63 | 에이전트 통신 |
| **Shadcn/UI** | Latest | UI 컴포넌트 |

### 디렉토리 구조

```
agent-chat-ui/src/
├── app/                    # Next.js App Router
│   ├── page.tsx            # 메인 페이지
│   ├── layout.tsx          # 루트 레이아웃
│   ├── ClientApp.tsx       # 클라이언트 래퍼
│   └── api/[..._path]/     # API 프록시
│
├── components/
│   ├── ui/                 # Shadcn/UI 기본 컴포넌트
│   ├── thread/             # 채팅 관련 컴포넌트
│   │   ├── index.tsx       # 메인 채팅 인터페이스
│   │   ├── messages/       # 메시지 렌더링
│   │   ├── history/        # 대화 히스토리 사이드바
│   │   └── agent-inbox/    # 에이전트 응답 표시
│   ├── charts/             # AG Charts 시각화
│   └── settings/           # 설정 다이얼로그
│
├── providers/
│   ├── Stream.tsx          # SSE 스트리밍 Provider
│   ├── Thread.tsx          # 스레드/대화 Provider
│   ├── Session.tsx         # 세션 타임아웃 Provider
│   ├── AssistantConfig.tsx # 어시스턴트 설정
│   └── Settings.tsx        # 테마/UI 설정
│
├── hooks/                  # Custom React Hooks
├── lib/                    # 유틸리티 라이브러리
└── types/                  # TypeScript 타입 정의
```

### Provider 구조

```tsx
<ThemeProvider>
  <SettingsProvider>
    <AssistantConfigProvider>
      <SessionProvider>
        <StreamProvider>
          <ThreadProvider>
            <App />
          </ThreadProvider>
        </StreamProvider>
      </SessionProvider>
    </AssistantConfigProvider>
  </SettingsProvider>
</ThemeProvider>
```

---

## 백엔드 아키텍처

### 기술 스택

| 기술 | 버전 | 용도 |
|------|------|------|
| **Python** | 3.11+ | 코어 언어 |
| **FastAPI** | Latest | REST API 프레임워크 |
| **LangGraph** | 0.6.10+ | 에이전트 오케스트레이션 |
| **LangChain** | 0.3.27+ | LLM 프레임워크 |
| **Claude API** | Haiku 4.5 | LLM 추론 |
| **Chroma DB** | 0.4.0+ | 벡터 데이터베이스 |

### 디렉토리 구조

```
react-agent/src/react_agent/
├── server.py               # FastAPI 서버 + SSE 스트리밍
├── graph_multi.py          # 멀티에이전트 라우팅 그래프
├── state.py                # LangGraph 상태 정의
├── configuration.py        # 런타임 설정
│
├── agents/
│   ├── config.py           # 에이전트 레지스트리 및 역할
│   ├── nodes.py            # Manager/Simple/Expert 에이전트
│   └── prompts.py          # 에이전트별 프롬프트
│
├── tools.py                # 도구 정의
├── rag_tool.py             # RAG/벡터 검색 (Chroma DB)
├── sse_mcp_client.py       # MCP 도구 클라이언트
├── cache_manager.py        # Redis/메모리 캐싱
├── faq_rules.py            # FAQ 데이터베이스
├── utils.py                # Mermaid 변환, 헬퍼
└── prompts.py              # 시스템 프롬프트
```

---

## 멀티 에이전트 시스템

### 에이전트 구성

```
┌──────────────────────────────────────────────────────────────┐
│                    Manager Agent (라우터)                     │
│                     Claude Haiku 4.5                         │
│                     Temperature: 0.0                         │
└──────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   Simple Agent   │ │  Expert Agents   │ │  Support Agent   │
│   (일반 질문)     │ │  (전문 질문)      │ │  (고객 상담)      │
│   Temp: 0.1      │ │  Temp: 0.1       │ │  Temp: 0.2       │
└──────────────────┘ └──────────────────┘ └──────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│     Carbon Expert        │   │   Regulation Expert      │
│   (탄소배출권 거래)       │   │   (규제 대응/컴플라이언스) │
└──────────────────────────┘   └──────────────────────────┘
```

### 에이전트별 역할

| 에이전트 | 역할 | 도구 |
|---------|------|------|
| **Manager** | 질문 분석 및 라우팅 | - |
| **Simple** | 일반 질문, FAQ | RAG, Web Search |
| **Carbon Expert** | 배출권 거래, 시장 분석 | MCP (거래량, 시세) |
| **Regulation Expert** | 규제, 컴플라이언스 | MCP (Scope 계산) |
| **Support Expert** | 고객 상담, 온보딩 | 고객 분류, 히스토리 |

### 라우팅 플로우

```
사용자 질문
     │
     ▼
┌─────────────┐
│ FAQ 캐시    │ ── HIT ──> 즉시 응답
└─────────────┘
     │ MISS
     ▼
┌─────────────┐
│ 전처리      │
│ (RAG+검색)  │  ← 병렬 실행
└─────────────┘
     │
     ▼
┌─────────────┐
│ Manager     │ → 복잡도 분석 (simple/medium/complex)
│ Agent       │ → 전문가 선택
└─────────────┘
     │
     ▼
┌─────────────┐
│ 전문가      │ → 도구 사용
│ Agent       │ → 응답 생성
└─────────────┘
     │
     ▼
SSE 스트리밍 응답
```

---

## 데이터 흐름

### 요청-응답 사이클

```
1. 프론트엔드
   └─> POST /threads/{id}/runs/stream
       └─> messages: [HumanMessage]
       └─> context: {category: "탄소배출권"}

2. FastAPI 서버
   └─> 스레드 상태 로드
   └─> LangGraph 그래프 실행

3. LangGraph 노드 실행
   └─> smart_tool_prefetch (FAQ, RAG, 웹검색)
   └─> manager_agent (라우팅)
   └─> expert_agent (응답 생성)
   └─> call_tools (도구 실행)

4. SSE 스트리밍
   └─> event: metadata
   └─> event: messages (토큰별)
   └─> event: values (도구 결과)
   └─> event: end

5. 프론트엔드 렌더링
   └─> 실시간 텍스트 표시
   └─> 시각화 감지 및 렌더링
   └─> 스레드 상태 저장
```

### 상태 관리

```python
@dataclass
class State:
    messages: Sequence[BaseMessage]      # 대화 메시지
    conversation_context: dict           # 대화 컨텍스트
    prefetched_context: dict             # 전처리 결과
    manager_decision: dict               # 라우팅 결정
    agent_used: str                      # 사용된 에이전트
```

---

## 캐싱 전략

### 3단계 캐싱

```
Level 1: FAQ 캐시
├── 정확히 일치하는 질문 → 즉시 응답
└── TTL: 영구

Level 2: RAG 캐시
├── 유사 질문 벡터 검색
└── TTL: 24시간

Level 3: LLM 응답 캐시
├── 동일 질문 해시 매칭
└── TTL: 24시간
└── Storage: Redis (또는 메모리)
```

### 캐시 키 구조

```python
# FAQ 캐시
faq_key = normalize(question)

# LLM 캐시
llm_key = f"llm:{sha256(question + category)}"

# RAG 캐시
rag_key = f"rag:{sha256(query)}"
```

---

## 배포 아키텍처

### 프로덕션 환경

```
┌─────────────────────────────────────────────────────────────┐
│                        Vercel CDN                           │
│  - 정적 자산 캐싱                                            │
│  - Edge 함수                                                 │
│  - SSL/TLS                                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   HuggingFace Spaces                         │
│  - Docker 컨테이너                                           │
│  - GPU (선택)                                                │
│  - Auto-scaling                                              │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         Anthropic        Tavily         NET-Z MCP
         (Claude)         (Search)       (데이터)
```

### 대체 배포 옵션

- **Railway**: `railway.json` 설정 제공
- **Docker Compose**: 로컬/온프레미스 배포
- **Kubernetes**: 대규모 배포 (수동 설정 필요)

---

## 보안 고려사항

### API 키 관리

```
프론트엔드:
- localStorage에 저장 (선택적)
- X-Api-Key 헤더로 전송

백엔드:
- 환경변수로 관리
- .env 파일 (버전 관리 제외)
```

### 인증 흐름

```
현재: API 키 기반 (선택적)

1. 사용자 설정에서 API 키 입력
2. localStorage에 저장
3. 모든 요청에 X-Api-Key 헤더 첨부
4. 백엔드에서 검증 (선택적)
```

### 데이터 보호

- HTTPS 전용 통신
- 민감 데이터 로깅 제외
- 세션 자동 만료 (60분)
