# Carbon AI Chatbot 종합 개선 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 인증/인가를 제외한 28개의 개선사항을 구현하여 프로덕션 준비 상태로 업그레이드

**Architecture:** 백엔드(FastAPI/LangGraph), 프론트엔드(Next.js/React), DevOps(CI/CD) 전반에 걸친 개선. 보안, 성능, 안정성, 모니터링 강화.

**Tech Stack:** Python 3.11+, FastAPI, LangGraph, Next.js 15, React 19, TypeScript, GitHub Actions

---

## Phase 1: 즉시 수정 (Critical - 보안/안정성)

### Task 1: CORS 설정 보안 강화

**Files:**
- Modify: `react-agent/src/react_agent/server.py:161-168`

**Step 1: CORS 설정 수정**

```python
# server.py 162-168번 줄 수정
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,https://carbon-ai-chatbot.vercel.app"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)
```

**Step 2: 환경변수 문서화**

`.env.example`에 추가:
```bash
# CORS 설정 (쉼표로 구분)
ALLOWED_ORIGINS=http://localhost:3000,https://your-domain.com
```

**Step 3: 커밋**

```bash
git add react-agent/src/react_agent/server.py
git commit -m "fix(security): restrict CORS to allowed origins only"
```

---

### Task 2: Rate Limiting 구현

**Files:**
- Modify: `react-agent/src/react_agent/server.py`
- Modify: `react-agent/pyproject.toml`

**Step 1: slowapi 의존성 추가**

`pyproject.toml`에 추가:
```toml
dependencies = [
    # ... existing
    "slowapi>=0.1.9",
]
```

**Step 2: Rate Limiter 구현**

`server.py` 상단에 추가:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**Step 3: 엔드포인트에 Rate Limit 적용**

```python
@app.post("/invoke", response_model=ChatResponse)
@limiter.limit("20/minute")
async def invoke_agent(request: Request, chat_request: ChatRequest):
    # ... existing code

@app.post("/stream")
@limiter.limit("10/minute")
async def stream_agent(request: Request, chat_request: ChatRequest):
    # ... existing code

@app.post("/threads/{thread_id}/runs/stream")
@limiter.limit("10/minute")
async def create_run_stream(request: Request, thread_id: str):
    # ... existing code
```

**Step 4: 커밋**

```bash
git add react-agent/src/react_agent/server.py react-agent/pyproject.toml
git commit -m "feat(security): add rate limiting to API endpoints"
```

---

### Task 3: Prompt Injection 방어

**Files:**
- Create: `react-agent/src/react_agent/input_sanitizer.py`
- Modify: `react-agent/src/react_agent/server.py`

**Step 1: Input Sanitizer 모듈 생성**

```python
# react-agent/src/react_agent/input_sanitizer.py
"""사용자 입력 검증 및 정제"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# 위험한 패턴 목록
DANGEROUS_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+(instructions?|prompts?)",
    r"disregard\s+(all\s+)?previous",
    r"override\s+(system|instructions?)",
    r"you\s+are\s+now\s+a",
    r"pretend\s+(to\s+be|you\s+are)",
    r"system\s*:\s*",
    r"assistant\s*:\s*",
    r"\[INST\]",
    r"\[/INST\]",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
]

# 컴파일된 패턴
COMPILED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in DANGEROUS_PATTERNS
]


def detect_prompt_injection(message: str) -> Tuple[bool, str]:
    """
    프롬프트 인젝션 시도 감지

    Args:
        message: 사용자 입력 메시지

    Returns:
        (is_dangerous, matched_pattern): 위험 여부와 매칭된 패턴
    """
    for pattern in COMPILED_PATTERNS:
        match = pattern.search(message)
        if match:
            logger.warning(f"[보안] 프롬프트 인젝션 시도 감지: '{match.group()}'")
            return True, match.group()
    return False, ""


def sanitize_user_input(message: str, strict: bool = False) -> str:
    """
    사용자 입력 정제

    Args:
        message: 사용자 입력 메시지
        strict: 엄격 모드 (위험 패턴 발견 시 예외 발생)

    Returns:
        정제된 메시지

    Raises:
        ValueError: strict 모드에서 위험 패턴 발견 시
    """
    is_dangerous, pattern = detect_prompt_injection(message)

    if is_dangerous:
        if strict:
            raise ValueError(f"잠재적으로 위험한 입력이 감지되었습니다: {pattern}")
        # 로그만 남기고 계속 진행 (비엄격 모드)
        logger.warning(f"[보안] 위험 패턴 감지됨 (비엄격 모드): {pattern}")

    # 기본 정제: 연속 공백 제거, 앞뒤 공백 제거
    sanitized = re.sub(r'\s+', ' ', message).strip()

    # 최대 길이 제한 (10,000자)
    max_length = 10000
    if len(sanitized) > max_length:
        logger.warning(f"[보안] 입력이 너무 깁니다: {len(sanitized)}자 → {max_length}자로 자름")
        sanitized = sanitized[:max_length]

    return sanitized
```

**Step 2: server.py에 sanitizer 적용**

```python
# server.py 상단에 추가
from react_agent.input_sanitizer import sanitize_user_input, detect_prompt_injection

# invoke_agent 함수 내에 추가 (graph 호출 전)
# 사용자 입력 검증
is_dangerous, pattern = detect_prompt_injection(request.message)
if is_dangerous:
    logger.warning(f"[보안] 위험한 입력 감지: {pattern}")
    # 경고만 하고 계속 진행 (또는 거부하려면 HTTPException 발생)

sanitized_message = sanitize_user_input(request.message)
input_data = {
    "messages": [HumanMessage(content=sanitized_message)]
}
```

**Step 3: 커밋**

```bash
git add react-agent/src/react_agent/input_sanitizer.py react-agent/src/react_agent/server.py
git commit -m "feat(security): add prompt injection detection and input sanitization"
```

---

### Task 4: Vector DB 백업 전략 구현

**Files:**
- Modify: `react-agent/src/react_agent/rag_tool.py:410-419`

**Step 1: 백업 로직 추가**

```python
# rag_tool.py의 _rebuild_vectorstore 메서드 수정
def _rebuild_vectorstore(self):
    """기존 벡터 DB를 백업 후 재구축"""
    import shutil
    from datetime import datetime

    if self.chroma_db_path.exists():
        # 백업 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = Path(f"{self.chroma_db_path}.backup.{timestamp}")

        try:
            logger.info(f"벡터 DB 백업 생성 중: {backup_path}")
            shutil.copytree(self.chroma_db_path, backup_path)
            logger.info(f"✓ 백업 완료: {backup_path}")
        except Exception as e:
            logger.error(f"백업 생성 실패: {e}")
            raise RuntimeError(f"벡터 DB 백업 실패: {e}")

        # 기존 DB 삭제
        try:
            logger.info("기존 벡터 DB 삭제 중...")
            shutil.rmtree(str(self.chroma_db_path))
            logger.info("기존 벡터 DB 삭제 완료")
        except Exception as e:
            logger.error(f"벡터 DB 삭제 실패: {e}")
            # 백업에서 복구
            logger.info("백업에서 복구 시도 중...")
            shutil.copytree(backup_path, self.chroma_db_path)
            raise RuntimeError(f"벡터 DB 삭제 실패, 복구됨: {e}")

        # 오래된 백업 정리 (최근 3개만 유지)
        self._cleanup_old_backups(keep_count=3)


def _cleanup_old_backups(self, keep_count: int = 3):
    """오래된 백업 파일 정리"""
    import shutil

    parent_dir = self.chroma_db_path.parent
    backup_pattern = f"{self.chroma_db_path.name}.backup.*"

    backups = sorted(
        parent_dir.glob(backup_pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    # 최근 keep_count개 제외하고 삭제
    for old_backup in backups[keep_count:]:
        try:
            shutil.rmtree(old_backup)
            logger.info(f"오래된 백업 삭제: {old_backup}")
        except Exception as e:
            logger.warning(f"백업 삭제 실패: {old_backup} - {e}")
```

**Step 2: 커밋**

```bash
git add react-agent/src/react_agent/rag_tool.py
git commit -m "feat(data): add vector DB backup before rebuild"
```

---

### Task 5: HNSW search_ef 값 조정

**Files:**
- Modify: `react-agent/src/react_agent/rag_tool.py:462-467`

**Step 1: search_ef 값 수정**

```python
# rag_tool.py의 Chroma 생성 시 collection_metadata 수정
self._vectorstore = Chroma.from_documents(
    documents=documents,
    embedding=self.embeddings,
    persist_directory=str(self.chroma_db_path),
    collection_metadata={
        "hnsw:space": "cosine",
        "hnsw:construction_ef": 200,
        "hnsw:search_ef": 300,  # 100 → 300으로 증가 (검색 정확도 향상)
        "hnsw:M": 32,
    }
)
```

**Step 2: 커밋**

```bash
git add react-agent/src/react_agent/rag_tool.py
git commit -m "perf(rag): increase HNSW search_ef for better recall"
```

---

### Task 6: 캐시 키 충돌 수정

**Files:**
- Modify: `react-agent/src/react_agent/cache_manager.py:93-105`

**Step 1: 해시 길이 증가**

```python
# cache_manager.py의 _generate_cache_key 메서드 수정
def _generate_cache_key(self, prefix: str, content: str) -> str:
    """
    캐시 키 생성 (해시 기반)

    Args:
        prefix: 키 접두사 (예: "rag", "llm")
        content: 해시할 콘텐츠

    Returns:
        캐시 키
    """
    # 전체 SHA256 해시 사용 (64자) - 충돌 확률 최소화
    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
    return f"{prefix}:{content_hash}"
```

**Step 2: 커밋**

```bash
git add react-agent/src/react_agent/cache_manager.py
git commit -m "fix(cache): use full SHA256 hash to prevent key collisions"
```

---

### Task 7: CI/CD 파이프라인 구축

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/deploy-backend.yml`
- Create: `.github/workflows/deploy-frontend.yml`

**Step 1: CI 워크플로우 생성**

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-lint-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: react-agent

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Lint with ruff
        run: |
          pip install ruff
          ruff check src/

      - name: Type check with mypy
        run: |
          pip install mypy
          mypy src/ --ignore-missing-imports || true

      - name: Run tests
        run: |
          pytest tests/ -v --tb=short
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

  frontend-lint-build:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: agent-chat-ui

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Setup pnpm
        uses: pnpm/action-setup@v2
        with:
          version: 8

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Lint
        run: pnpm lint

      - name: Type check
        run: pnpm tsc --noEmit

      - name: Build
        run: pnpm build
        env:
          NEXT_PUBLIC_API_URL: https://ruffy1601-carbon-ai-chatbot.hf.space
          NEXT_PUBLIC_ASSISTANT_ID: agent
```

**Step 2: 백엔드 배포 워크플로우**

```yaml
# .github/workflows/deploy-backend.yml
name: Deploy Backend

on:
  push:
    branches: [main]
    paths:
      - 'react-agent/**'
      - '.github/workflows/deploy-backend.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    needs: [ci]

    steps:
      - uses: actions/checkout@v4
        with:
          lfs: true

      - name: Push to HuggingFace Spaces
        env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
        run: |
          git remote add space https://user:$HF_TOKEN@huggingface.co/spaces/ruffy1601/carbon-ai-chatbot || true
          git push space main --force
```

**Step 3: 프론트엔드 배포 워크플로우**

```yaml
# .github/workflows/deploy-frontend.yml
name: Deploy Frontend

on:
  push:
    branches: [main]
    paths:
      - 'agent-chat-ui/**'
      - '.github/workflows/deploy-frontend.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: ./agent-chat-ui
          vercel-args: '--prod'
```

**Step 4: 커밋**

```bash
git add .github/workflows/
git commit -m "feat(devops): add CI/CD pipelines for backend and frontend"
```

---

## Phase 2: 단기 수정 (High Priority)

### Task 8: 상세 헬스체크 구현

**Files:**
- Modify: `react-agent/src/react_agent/server.py:261-266`

**Step 1: 상세 헬스체크 엔드포인트 추가**

```python
# server.py의 health_check 수정 및 추가 엔드포인트

@app.get("/ok")
async def simple_health():
    """간단한 헬스체크 (로드밸런서용)"""
    return "OK"


@app.get("/health")
async def health_check():
    """기본 헬스체크"""
    return {"status": "ok", "service": "carbonai-agent"}


@app.get("/health/ready")
async def readiness_check():
    """준비 상태 체크 (Kubernetes readiness probe)"""
    checks = {}
    all_healthy = True

    # RAG 도구 체크
    try:
        rag_tool = get_rag_tool()
        checks["rag"] = {
            "status": "healthy" if rag_tool.available else "unavailable",
            "vectorstore": rag_tool.vectorstore is not None
        }
        if not rag_tool.available:
            all_healthy = False
    except Exception as e:
        checks["rag"] = {"status": "error", "message": str(e)}
        all_healthy = False

    # LLM 연결 체크 (Anthropic)
    try:
        import anthropic
        client = anthropic.Anthropic()
        # 간단한 연결 테스트
        checks["anthropic"] = {"status": "healthy"}
    except Exception as e:
        checks["anthropic"] = {"status": "error", "message": str(e)}
        # Anthropic은 핵심이므로 실패 시 not ready
        all_healthy = False

    # Redis 체크 (선택적)
    cache_manager = get_cache_manager()
    if cache_manager._redis_client:
        try:
            cache_manager._redis_client.ping()
            checks["redis"] = {"status": "healthy"}
        except Exception as e:
            checks["redis"] = {"status": "degraded", "message": str(e)}
            # Redis는 선택적이므로 실패해도 계속 진행
    else:
        checks["redis"] = {"status": "not_configured"}

    status_code = 200 if all_healthy else 503
    return JSONResponse(
        content={
            "status": "ready" if all_healthy else "not_ready",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        },
        status_code=status_code
    )


@app.get("/health/live")
async def liveness_check():
    """생존 상태 체크 (Kubernetes liveness probe)"""
    import time
    return {
        "status": "alive",
        "uptime_seconds": time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
    }
```

**Step 2: 시작 시간 기록 (startup event에 추가)**

```python
# startup_event 함수 시작 부분에 추가
import time
app.state.start_time = time.time()
```

**Step 3: 커밋**

```bash
git add react-agent/src/react_agent/server.py
git commit -m "feat(monitoring): add detailed health check endpoints"
```

---

### Task 9: 토큰 비용 최적화 (Anthropic 캐싱)

**Files:**
- Modify: `react-agent/src/react_agent/agents/nodes.py` (또는 해당 에이전트 파일)

**Step 1: RAG 컨텍스트에 cache_control 적용**

에이전트에서 RAG 결과를 LLM에 전달할 때 캐시 제어 적용:

```python
# 에이전트 노드에서 RAG 컨텍스트 구성 시
def build_rag_context_message(rag_results: list) -> dict:
    """RAG 결과를 캐시 가능한 형식으로 구성"""
    context_text = "\n\n---\n\n".join([
        f"[출처: {r['filename']}]\n{r['content']}"
        for r in rag_results
    ])

    return {
        "type": "text",
        "text": f"<context>\n{context_text}\n</context>",
        "cache_control": {"type": "ephemeral"}  # 5분 캐시, 90% 비용 절감
    }
```

**Step 2: 커밋**

```bash
git add react-agent/src/react_agent/agents/
git commit -m "perf(ai): add Anthropic cache_control for RAG context"
```

---

### Task 10: Error Boundary 컴포넌트 구현

**Files:**
- Create: `agent-chat-ui/src/components/ErrorBoundary.tsx`
- Modify: `agent-chat-ui/src/app/layout.tsx`

**Step 1: ErrorBoundary 컴포넌트 생성**

```tsx
// agent-chat-ui/src/components/ErrorBoundary.tsx
"use client";

import React, { Component, ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    this.setState({ errorInfo });

    // 에러 리포팅 서비스에 전송 (예: Sentry)
    // reportError(error, errorInfo);
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-8 text-center">
          <AlertTriangle className="w-16 h-16 text-yellow-500 mb-4" />
          <h2 className="text-xl font-semibold mb-2">문제가 발생했습니다</h2>
          <p className="text-muted-foreground mb-4 max-w-md">
            예기치 않은 오류가 발생했습니다. 페이지를 새로고침하거나 잠시 후 다시 시도해 주세요.
          </p>
          {process.env.NODE_ENV === "development" && this.state.error && (
            <pre className="text-xs text-left bg-muted p-4 rounded-md mb-4 max-w-full overflow-auto">
              {this.state.error.toString()}
              {this.state.errorInfo?.componentStack}
            </pre>
          )}
          <div className="flex gap-2">
            <Button onClick={this.handleReset} variant="outline">
              <RefreshCw className="w-4 h-4 mr-2" />
              다시 시도
            </Button>
            <Button onClick={() => window.location.reload()}>
              페이지 새로고침
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
```

**Step 2: layout.tsx에 적용**

```tsx
// layout.tsx에서 ErrorBoundary로 감싸기
import { ErrorBoundary } from "@/components/ErrorBoundary";

// ... existing code

<ErrorBoundary>
  {children}
</ErrorBoundary>
```

**Step 3: 커밋**

```bash
git add agent-chat-ui/src/components/ErrorBoundary.tsx agent-chat-ui/src/app/layout.tsx
git commit -m "feat(frontend): add ErrorBoundary for graceful error handling"
```

---

### Task 11: console.log 제거 및 로깅 설정

**Files:**
- Create: `agent-chat-ui/src/lib/logger.ts`
- Modify: `agent-chat-ui/next.config.mjs`
- Modify: `agent-chat-ui/.eslintrc.json`

**Step 1: Logger 유틸리티 생성**

```typescript
// agent-chat-ui/src/lib/logger.ts
type LogLevel = "debug" | "info" | "warn" | "error";

const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

const currentLevel: LogLevel =
  process.env.NODE_ENV === "production" ? "warn" : "debug";

function shouldLog(level: LogLevel): boolean {
  return LOG_LEVELS[level] >= LOG_LEVELS[currentLevel];
}

export const logger = {
  debug: (...args: unknown[]) => {
    if (shouldLog("debug")) {
      console.debug("[DEBUG]", ...args);
    }
  },
  info: (...args: unknown[]) => {
    if (shouldLog("info")) {
      console.info("[INFO]", ...args);
    }
  },
  warn: (...args: unknown[]) => {
    if (shouldLog("warn")) {
      console.warn("[WARN]", ...args);
    }
  },
  error: (...args: unknown[]) => {
    if (shouldLog("error")) {
      console.error("[ERROR]", ...args);
    }
  },
};

export default logger;
```

**Step 2: next.config.mjs에 console 제거 설정**

```javascript
// next.config.mjs
const nextConfig = {
  // ... existing config

  compiler: {
    // 프로덕션 빌드에서 console.log 제거
    removeConsole: process.env.NODE_ENV === "production" ? {
      exclude: ["error", "warn"],
    } : false,
  },
};
```

**Step 3: ESLint 규칙 추가**

```json
// .eslintrc.json에 추가
{
  "rules": {
    "no-console": ["warn", { "allow": ["warn", "error"] }]
  }
}
```

**Step 4: 커밋**

```bash
git add agent-chat-ui/src/lib/logger.ts agent-chat-ui/next.config.mjs agent-chat-ui/.eslintrc.json
git commit -m "feat(frontend): add structured logging and remove console.log in production"
```

---

### Task 12: Hallucination 방지 프롬프트 강화

**Files:**
- Modify: `react-agent/src/react_agent/prompts.py` 또는 `agents/prompts.py`

**Step 1: 불확실성 처리 프롬프트 추가**

```python
# prompts.py에 추가
UNCERTAINTY_GUIDELINES = """
## 불확실성 처리 지침

당신은 정확한 정보만 제공해야 합니다. 다음 규칙을 반드시 준수하세요:

### 반드시 금지
- RAG 검색 결과 없이 답변 생성 금지
- 가상의 URL, 전화번호, 이메일 주소 생성 금지
- 과거 데이터로 미래 예측 금지 (예: "2024년 가격은 X원이었으니 2026년에는...")
- 출처 없이 통계, 수치 제공 금지

### 불확실할 때 응답 방식
불확실하거나 RAG 결과가 없을 때는 다음 중 하나로 응답하세요:

1. "해당 정보는 현재 지식베이스에서 찾을 수 없습니다. 더 정확한 정보를 위해 [담당 부서/공식 웹사이트]를 확인해 주세요."

2. "이 부분은 확인이 필요합니다. 최신 정보를 위해 웹 검색을 진행할까요?"

3. "제가 가진 정보만으로는 정확한 답변이 어렵습니다. 전문가 상담을 권장드립니다."

### 인용 규칙
- 모든 정보에는 출처를 명시하세요: [출처: 파일명]
- RAG 결과의 파일명을 그대로 사용하세요
- 여러 출처가 있으면 모두 나열하세요
"""

# 기존 시스템 프롬프트에 추가
SYSTEM_PROMPT = f"""
{EXISTING_SYSTEM_PROMPT}

{UNCERTAINTY_GUIDELINES}
"""
```

**Step 2: 인용 검증 함수 추가**

```python
# utils.py 또는 적절한 파일에 추가
import re
from typing import List, Tuple

def validate_citations(response_text: str, rag_sources: List[str]) -> Tuple[bool, List[str]]:
    """
    응답의 인용이 실제 RAG 소스와 일치하는지 검증

    Args:
        response_text: AI 응답 텍스트
        rag_sources: RAG에서 검색된 실제 소스 파일명 목록

    Returns:
        (is_valid, invalid_citations): 유효 여부와 잘못된 인용 목록
    """
    # [출처: xxx] 패턴 추출
    citation_pattern = r'\[출처:\s*([^\]]+)\]'
    citations = re.findall(citation_pattern, response_text)

    invalid_citations = []
    for citation in citations:
        citation = citation.strip()
        if citation not in rag_sources:
            invalid_citations.append(citation)

    return len(invalid_citations) == 0, invalid_citations
```

**Step 3: 커밋**

```bash
git add react-agent/src/react_agent/prompts.py react-agent/src/react_agent/utils.py
git commit -m "feat(ai): add hallucination prevention guidelines and citation validation"
```

---

### Task 13: 메모리 캐시 크기 제한 개선

**Files:**
- Modify: `react-agent/src/react_agent/cache_manager.py`

**Step 1: LRU 캐시 로직 개선**

```python
# cache_manager.py의 CacheManager 클래스 수정

from collections import OrderedDict

class CacheManager:
    MAX_MEMORY_CACHE_SIZE = 10000  # 최대 캐시 항목 수

    def __init__(self, ...):
        # ... existing code
        # OrderedDict로 변경하여 LRU 구현
        self._memory_cache: OrderedDict[str, tuple[Any, datetime]] = OrderedDict()

    def get(self, prefix: str, content: str) -> Optional[Any]:
        cache_key = self._generate_cache_key(prefix, content)

        # ... Redis 캐시 코드 ...

        # 메모리 캐시 확인 (LRU: 접근 시 맨 뒤로 이동)
        if cache_key in self._memory_cache:
            cached_value, expiry_time = self._memory_cache[cache_key]
            if datetime.now() < expiry_time:
                # LRU: 접근한 항목을 맨 뒤로 이동
                self._memory_cache.move_to_end(cache_key)
                logger.info(f"[캐시 HIT] 메모리: {prefix} - {content[:50]}...")
                return cached_value
            else:
                # 만료된 캐시 제거
                del self._memory_cache[cache_key]
                logger.debug(f"[캐시 만료] {prefix} - {content[:50]}...")

        return None

    def set(self, prefix: str, content: str, value: Any, ttl: Optional[int] = None) -> bool:
        cache_key = self._generate_cache_key(prefix, content)
        ttl = ttl or self.default_ttl

        # ... Redis 캐시 코드 ...

        # 메모리 캐시 저장
        expiry_time = datetime.now() + timedelta(seconds=ttl)

        # 기존 키가 있으면 먼저 삭제 (순서 유지를 위해)
        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]

        self._memory_cache[cache_key] = (value, expiry_time)

        # LRU: 새 항목은 맨 뒤에 추가됨

        # 크기 제한 초과 시 LRU 정리
        while len(self._memory_cache) > self.MAX_MEMORY_CACHE_SIZE:
            # 가장 오래된 항목(맨 앞) 제거
            oldest_key = next(iter(self._memory_cache))
            del self._memory_cache[oldest_key]
            logger.debug(f"[캐시 LRU 제거] {oldest_key}")

        return True
```

**Step 2: 커밋**

```bash
git add react-agent/src/react_agent/cache_manager.py
git commit -m "feat(cache): implement proper LRU eviction with max size limit"
```

---

## Phase 3: 중기 수정 (Medium Priority)

### Task 14: Prometheus 메트릭 추가

**Files:**
- Modify: `react-agent/src/react_agent/server.py`
- Modify: `react-agent/pyproject.toml`

**Step 1: prometheus-client 의존성 추가**

```toml
# pyproject.toml
dependencies = [
    # ... existing
    "prometheus-client>=0.19.0",
]
```

**Step 2: 메트릭 정의 및 엔드포인트 추가**

```python
# server.py 상단에 추가
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# 메트릭 정의
REQUEST_COUNT = Counter(
    'carbonai_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status']
)

REQUEST_LATENCY = Histogram(
    'carbonai_request_latency_seconds',
    'Request latency in seconds',
    ['endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

ACTIVE_STREAMS = Gauge(
    'carbonai_active_streams',
    'Number of active SSE streams'
)

CACHE_HITS = Counter(
    'carbonai_cache_hits_total',
    'Cache hit count',
    ['cache_type']  # rag, llm, faq
)

RAG_SEARCH_LATENCY = Histogram(
    'carbonai_rag_search_seconds',
    'RAG search latency',
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

# 메트릭 엔드포인트
@app.get("/metrics")
async def metrics():
    """Prometheus 메트릭 엔드포인트"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# 미들웨어로 요청 메트릭 수집
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    # 메트릭 기록
    latency = time.time() - start_time
    endpoint = request.url.path

    REQUEST_COUNT.labels(
        endpoint=endpoint,
        method=request.method,
        status=response.status_code
    ).inc()

    REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency)

    return response
```

**Step 3: 커밋**

```bash
git add react-agent/src/react_agent/server.py react-agent/pyproject.toml
git commit -m "feat(monitoring): add Prometheus metrics endpoint"
```

---

### Task 15: 접근성(a11y) 개선

**Files:**
- Modify: Various component files in `agent-chat-ui/src/components/`

**Step 1: 공통 접근성 유틸리티 생성**

```tsx
// agent-chat-ui/src/lib/a11y.ts
export const srOnly = "sr-only"; // Tailwind class for screen reader only

export function getAriaLabel(action: string, context?: string): string {
  return context ? `${action} - ${context}` : action;
}

export const a11yAttributes = {
  loading: {
    role: "status" as const,
    "aria-busy": true,
    "aria-live": "polite" as const,
  },
  button: (label: string, pressed?: boolean) => ({
    "aria-label": label,
    ...(pressed !== undefined && { "aria-pressed": pressed }),
  }),
  expandable: (expanded: boolean, controlsId: string) => ({
    "aria-expanded": expanded,
    "aria-controls": controlsId,
  }),
};
```

**Step 2: 주요 컴포넌트에 ARIA 속성 추가**

예시 - Thread.tsx의 입력 영역:
```tsx
<textarea
  aria-label="메시지 입력"
  aria-describedby="message-helper-text"
  placeholder="메시지를 입력하세요..."
/>
<span id="message-helper-text" className="sr-only">
  Enter 키를 눌러 메시지를 전송합니다
</span>
```

예시 - 로딩 상태:
```tsx
<div
  role="status"
  aria-busy={isLoading}
  aria-live="polite"
  aria-label={isLoading ? "응답 생성 중" : "응답 완료"}
>
  {isLoading ? <Spinner /> : content}
</div>
```

**Step 3: 커밋**

```bash
git add agent-chat-ui/src/
git commit -m "feat(a11y): add ARIA attributes and screen reader support"
```

---

### Task 16: MemorySaver → PostgreSQL 체크포인터 마이그레이션 준비

**Files:**
- Modify: `react-agent/src/react_agent/graph_multi.py`
- Modify: `react-agent/pyproject.toml`

**Step 1: PostgreSQL 체크포인터 조건부 사용**

```python
# graph_multi.py 수정
import os
from langgraph.checkpoint.memory import MemorySaver

def get_checkpointer():
    """환경에 따라 적절한 체크포인터 반환"""
    database_url = os.getenv("DATABASE_URL")

    if database_url and os.getenv("ENVIRONMENT") == "production":
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
            checkpointer = PostgresSaver.from_conn_string(database_url)
            logger.info("✓ PostgreSQL 체크포인터 사용")
            return checkpointer
        except ImportError:
            logger.warning("langgraph-checkpoint-postgres 미설치, MemorySaver 사용")
        except Exception as e:
            logger.warning(f"PostgreSQL 연결 실패: {e}, MemorySaver 사용")

    logger.info("MemorySaver 체크포인터 사용 (개발/로컬 환경)")
    return MemorySaver()

# 그래프 생성 시
checkpointer = get_checkpointer()
graph = workflow.compile(checkpointer=checkpointer)
```

**Step 2: 의존성 추가 (선택적)**

```toml
# pyproject.toml
[project.optional-dependencies]
postgres = [
    "langgraph-checkpoint-postgres>=0.1.0",
    "psycopg2-binary>=2.9.0",
]
```

**Step 3: 커밋**

```bash
git add react-agent/src/react_agent/graph_multi.py react-agent/pyproject.toml
git commit -m "feat(persistence): add PostgreSQL checkpointer support for production"
```

---

### Task 17: 에러 응답 표준화

**Files:**
- Create: `react-agent/src/react_agent/exceptions.py`
- Modify: `react-agent/src/react_agent/server.py`

**Step 1: 표준 에러 응답 모델 생성**

```python
# react-agent/src/react_agent/exceptions.py
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """표준 에러 응답 모델"""
    error: str
    message: str
    code: str
    details: Optional[Any] = None


class AppException(Exception):
    """애플리케이션 커스텀 예외"""
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Any] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


# 에러 코드 정의
class ErrorCodes:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    THREAD_NOT_FOUND = "THREAD_NOT_FOUND"
    RAG_SEARCH_FAILED = "RAG_SEARCH_FAILED"
    LLM_ERROR = "LLM_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    PROMPT_INJECTION_DETECTED = "PROMPT_INJECTION_DETECTED"


def create_error_response(
    status_code: int,
    message: str,
    code: str,
    details: Optional[Any] = None
) -> JSONResponse:
    """표준 에러 응답 생성"""
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=code,
            message=message,
            code=code,
            details=details
        ).model_dump()
    )
```

**Step 2: 글로벌 예외 핸들러 등록**

```python
# server.py에 추가
from react_agent.exceptions import AppException, create_error_response, ErrorCodes

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.error(f"AppException: {exc.code} - {exc.message}")
    return create_error_response(
        status_code=exc.status_code,
        message=exc.message,
        code=exc.code,
        details=exc.details
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc}")
    return create_error_response(
        status_code=500,
        message="내부 서버 오류가 발생했습니다.",
        code=ErrorCodes.INTERNAL_ERROR
    )
```

**Step 3: 커밋**

```bash
git add react-agent/src/react_agent/exceptions.py react-agent/src/react_agent/server.py
git commit -m "feat(api): standardize error response format"
```

---

### Task 18: 구조화된 로깅 (JSON 형식)

**Files:**
- Create: `react-agent/src/react_agent/logging_config.py`
- Modify: `react-agent/src/react_agent/server.py`

**Step 1: 구조화된 로깅 설정**

```python
# react-agent/src/react_agent/logging_config.py
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """JSON 형식 로그 포매터"""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 추가 필드
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "thread_id"):
            log_data["thread_id"] = record.thread_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        # 예외 정보
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(json_format: bool = True, level: str = "INFO"):
    """로깅 설정 초기화"""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 새 핸들러 추가
    handler = logging.StreamHandler(sys.stdout)

    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))

    root_logger.addHandler(handler)

    # 노이즈 로거 레벨 조정
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
```

**Step 2: server.py에서 로깅 설정 적용**

```python
# server.py 시작 부분
import os
from react_agent.logging_config import setup_logging

# 환경변수로 JSON 로깅 제어
use_json_logs = os.getenv("LOG_FORMAT", "json").lower() == "json"
log_level = os.getenv("LOG_LEVEL", "INFO")
setup_logging(json_format=use_json_logs, level=log_level)
```

**Step 3: 커밋**

```bash
git add react-agent/src/react_agent/logging_config.py react-agent/src/react_agent/server.py
git commit -m "feat(logging): add structured JSON logging support"
```

---

### Task 19: 에이전트 라우팅 신뢰도 활용

**Files:**
- Modify: `react-agent/src/react_agent/graph_multi.py`

**Step 1: 신뢰도 기반 라우팅 로직 개선**

```python
# graph_multi.py의 route_after_manager 함수 수정
def route_after_manager(state: State) -> str:
    """Manager 결정에 따라 다음 에이전트 라우팅 (신뢰도 고려)"""
    manager_decision = state.get("manager_decision", {})

    assigned_agent = manager_decision.get("assigned_agent", "simple")
    confidence = manager_decision.get("confidence", 0.5)

    logger.info(f"Manager 결정: {assigned_agent} (신뢰도: {confidence:.2f})")

    # 신뢰도 기반 라우팅
    if confidence >= 0.8:
        # 높은 신뢰도: 바로 해당 에이전트로
        return assigned_agent
    elif confidence >= 0.5:
        # 중간 신뢰도: 에이전트 실행 후 결과 검증 필요
        # (현재는 동일하게 처리, 추후 검증 로직 추가 가능)
        logger.info(f"중간 신뢰도({confidence:.2f}), 결과 검증 권장")
        return assigned_agent
    else:
        # 낮은 신뢰도: 명확화 질문 또는 기본 에이전트
        logger.warning(f"낮은 신뢰도({confidence:.2f}), 명확화 필요")
        # 명확화 노드가 있다면 "clarify" 반환
        # 없다면 기본 에이전트로 fallback
        return "simple"
```

**Step 2: 커밋**

```bash
git add react-agent/src/react_agent/graph_multi.py
git commit -m "feat(routing): utilize confidence score in agent routing"
```

---

### Task 20: 백엔드 테스트 추가 (핵심 API)

**Files:**
- Create: `react-agent/tests/test_api.py`
- Create: `react-agent/tests/conftest.py`

**Step 1: pytest fixtures 설정**

```python
# react-agent/tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from react_agent.server import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """테스트용 비동기 클라이언트"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

**Step 2: API 테스트 작성**

```python
# react-agent/tests/test_api.py
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """헬스체크 엔드포인트 테스트"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.anyio
async def test_simple_ok(client: AsyncClient):
    """간단한 OK 엔드포인트 테스트"""
    response = await client.get("/ok")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_categories(client: AsyncClient):
    """카테고리 목록 테스트"""
    response = await client.get("/categories")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert len(data["categories"]) > 0


@pytest.mark.anyio
async def test_create_thread(client: AsyncClient):
    """스레드 생성 테스트"""
    response = await client.post("/threads", json={})
    assert response.status_code == 200
    data = response.json()
    assert "thread_id" in data


@pytest.mark.anyio
async def test_invoke_requires_message(client: AsyncClient):
    """invoke 엔드포인트 필수 파라미터 검증"""
    response = await client.post("/invoke", json={})
    assert response.status_code == 422  # Validation error


@pytest.mark.anyio
async def test_assistants_search(client: AsyncClient):
    """어시스턴트 검색 테스트"""
    response = await client.post("/assistants/search", json={})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "assistant_id" in data[0]
```

**Step 3: pytest.ini 설정**

```ini
# react-agent/pytest.ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_functions = test_*
```

**Step 4: 커밋**

```bash
git add react-agent/tests/
git commit -m "test(api): add core API endpoint tests"
```

---

## 완료 체크리스트

### Phase 1 (즉시 수정)
- [ ] Task 1: CORS 설정 보안 강화
- [ ] Task 2: Rate Limiting 구현
- [ ] Task 3: Prompt Injection 방어
- [ ] Task 4: Vector DB 백업 전략
- [ ] Task 5: HNSW search_ef 조정
- [ ] Task 6: 캐시 키 충돌 수정
- [ ] Task 7: CI/CD 파이프라인

### Phase 2 (단기 수정)
- [ ] Task 8: 상세 헬스체크
- [ ] Task 9: 토큰 비용 최적화
- [ ] Task 10: Error Boundary
- [ ] Task 11: console.log 제거
- [ ] Task 12: Hallucination 방지
- [ ] Task 13: 메모리 캐시 LRU

### Phase 3 (중기 수정)
- [ ] Task 14: Prometheus 메트릭
- [ ] Task 15: 접근성 개선
- [ ] Task 16: PostgreSQL 체크포인터
- [ ] Task 17: 에러 응답 표준화
- [ ] Task 18: 구조화된 로깅
- [ ] Task 19: 라우팅 신뢰도 활용
- [ ] Task 20: 백엔드 테스트

---

**Note:** 인증/인가(원본 #2, #4)는 이 계획에서 제외되었습니다.
