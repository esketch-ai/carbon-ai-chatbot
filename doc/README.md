# Carbon AI Chatbot - 프로젝트 문서

> 멀티 에이전트 AI 챗봇 시스템 - 탄소배출권 거래 전문

## 문서 목차

| 문서 | 설명 |
|------|------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 시스템 아키텍처 및 전체 구조 |
| [FRONTEND.md](./FRONTEND.md) | 프론트엔드 기술 스택 및 컴포넌트 |
| [BACKEND.md](./BACKEND.md) | 백엔드 서버 및 에이전트 시스템 |
| [AI_FEATURES.md](./AI_FEATURES.md) | AI 통합, 멀티에이전트, 스트리밍 |
| [DATABASE.md](./DATABASE.md) | 데이터베이스 스키마 및 저장소 |
| [API.md](./API.md) | REST API 엔드포인트 문서 |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | 배포 가이드 (Vercel, HuggingFace) |
| [CONFIGURATION.md](./CONFIGURATION.md) | 환경변수 및 설정 가이드 |

---

## 프로젝트 개요

**Carbon AI Chatbot**은 탄소배출권 거래 플랫폼(NET-Z)을 위한 AI 기반 고객 상담 시스템입니다.

### 핵심 기능

- **멀티 에이전트 라우팅**: 질문 복잡도에 따른 자동 전문가 배정
- **실시간 스트리밍**: SSE 기반 토큰 단위 응답 스트리밍
- **RAG 지식베이스**: 문서 기반 벡터 검색 및 답변 생성
- **시각화 지원**: 차트, 테이블, 다이어그램, 지도 자동 렌더링
- **FAQ 캐싱**: 자주 묻는 질문 즉시 응답

### 기술 스택 요약

| 영역 | 기술 |
|------|------|
| **프론트엔드** | Next.js 15, React 19, TypeScript, Tailwind CSS 4 |
| **백엔드** | FastAPI, LangGraph, Python 3.11+ |
| **LLM** | Anthropic Claude (Haiku 4.5) |
| **벡터 DB** | Chroma DB (BGE-m3-ko 임베딩) |
| **시각화** | AG Charts, AG Grid, Mermaid, Kakao Maps |
| **배포** | Vercel (Frontend), HuggingFace Spaces (Backend) |

---

## 빠른 시작

### 1. 프론트엔드 실행

```bash
cd agent-chat-ui
pnpm install
pnpm dev
```

### 2. 백엔드 실행

```bash
cd react-agent
pip install -e .
python -m react_agent.server
```

### 3. 환경변수 설정

**프론트엔드** (`agent-chat-ui/.env.local`):
```
NEXT_PUBLIC_API_URL=http://localhost:7860
NEXT_PUBLIC_ASSISTANT_ID=agent
```

**백엔드** (`react-agent/.env`):
```
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
```

---

## 프로젝트 구조

```
carbon-ai-chatbot/
├── agent-chat-ui/          # Next.js 프론트엔드
│   ├── src/
│   │   ├── app/            # App Router 페이지
│   │   ├── components/     # React 컴포넌트
│   │   ├── providers/      # Context Providers
│   │   └── lib/            # 유틸리티
│   └── package.json
│
├── react-agent/            # Python 백엔드
│   ├── src/react_agent/
│   │   ├── server.py       # FastAPI 서버
│   │   ├── graph_multi.py  # 멀티에이전트 그래프
│   │   ├── agents/         # 에이전트 정의
│   │   ├── rag_tool.py     # RAG 도구
│   │   └── tools.py        # 도구 모음
│   ├── knowledge_base/     # 지식베이스 문서
│   └── pyproject.toml
│
├── doc/                    # 프로젝트 문서
└── Dockerfile              # 컨테이너 이미지
```

---

## 라이선스

이 프로젝트는 내부 사용 목적으로 개발되었습니다.
