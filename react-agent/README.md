# CarbonAI Backend (LangGraph)

탄소 배출권 전문 AI 챗봇의 백엔드 서버입니다.

## 🚀 로컬 실행

### 1. 환경 변수 설정

`.env` 파일 생성:
```env
ANTHROPIC_API_KEY=your_api_key_here
LANGSMITH_API_KEY=your_langsmith_key
NETZ_MCP_URL=https://hooxi.shinssy.com
NETZ_MCP_ENABLED=true
NETZ_ENTERPRISE_ID=1
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 서버 실행

```bash
langgraph up --host 0.0.0.0 --port 2024
```

서버가 `http://localhost:2024`에서 실행됩니다.

## 📦 배포

Railway, Render, 또는 다른 플랫폼에 배포 가능합니다.

자세한 내용은 프로젝트 루트의 `deployment/` 폴더를 참고하세요.

## 🔧 주요 기능

- **RAG 검색**: 지식베이스 문서 검색 (하이브리드: BM25 + 벡터)
- **MCP 통합**: NETZ MCP 서버 연동
- **대화 맥락 유지**: 이전 대화 기반 맞춤 답변
- **자동 시각화**: Mermaid 다이어그램 자동 변환

## 📁 주요 파일

- `src/react_agent/graph.py`: 메인 그래프 정의
- `src/react_agent/rag_tool.py`: RAG 검색 도구
- `src/react_agent/tools.py`: 도구 정의
- `src/react_agent/prompts.py`: 시스템 프롬프트
- `langgraph.json`: LangGraph 설정

## 🌐 API 엔드포인트

- `POST /threads/{thread_id}/runs/stream`: 스트리밍 채팅
- `GET /threads/{thread_id}/state`: 대화 상태 조회
- `GET /threads`: 스레드 목록

## 📞 문의

문제가 발생하면 이슈를 등록해주세요.
