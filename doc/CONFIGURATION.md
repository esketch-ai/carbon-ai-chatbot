# 설정 가이드

## 개요

Carbon AI Chatbot의 설정은 환경변수와 설정 파일을 통해 관리됩니다.

---

## 환경변수

### 프론트엔드 환경변수

**파일**: `agent-chat-ui/.env.local`

```bash
# === 필수 설정 ===

# 백엔드 API URL
NEXT_PUBLIC_API_URL=https://ruffy1601-carbon-ai-chatbot.hf.space

# 어시스턴트 ID (LangGraph 그래프 ID)
NEXT_PUBLIC_ASSISTANT_ID=agent
```

### 백엔드 환경변수

**파일**: `react-agent/.env`

```bash
# === 필수 API 키 ===

# Anthropic Claude API 키
ANTHROPIC_API_KEY=sk-ant-api03-...

# Tavily 웹 검색 API 키
TAVILY_API_KEY=tvly-...


# === 선택적 설정 ===

# HuggingFace 토큰 (임베딩 모델 다운로드)
HF_TOKEN=hf_...

# LangSmith 트레이싱 (디버깅용)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=ls-...
LANGSMITH_PROJECT=Carbon-AI-Chatbot


# === 캐시 설정 ===

# Redis 캐시 사용 여부
USE_REDIS_CACHE=true

# Redis 연결 URL
REDIS_URL=redis://localhost:6379/0

# 캐시 TTL (초) - 기본 24시간
CACHE_TTL=86400


# === 지식베이스 설정 ===

# 지식베이스 문서 경로
KNOWLEDGE_BASE_PATH=./knowledge_base

# Chroma DB 저장 경로
CHROMA_DB_PATH=./chroma_db


# === NET-Z MCP 설정 ===

# MCP 서버 활성화
NETZ_MCP_ENABLED=true

# MCP 서버 URL
NETZ_MCP_URL=http://10.177.198.46:3662


# === RAG 설정 ===

# 검색 모드: vector_only | bm25 | graph
RAG_SEARCH_MODE=vector_only


# === 서버 설정 ===

# 서버 포트
PORT=7860

# 로그 레벨
LOG_LEVEL=INFO
```

---

## 설정 파일

### langgraph.json (LangGraph 배포)

```json
{
  "graphs": {
    "agent": {
      "path": "./src/react_agent/graph_multi.py:graph",
      "description": "Carbon AI Chatbot Multi-Agent Graph"
    }
  },
  "env": ".env",
  "dependencies": ["./pyproject.toml"],
  "store": {
    "type": "memory"
  }
}
```

### pyproject.toml (Python 프로젝트)

```toml
[project]
name = "react-agent"
version = "0.1.0"
description = "Carbon AI Chatbot Backend"
requires-python = ">=3.11"

dependencies = [
    "langgraph>=0.6.10",
    "langchain>=0.3.27",
    "langchain-anthropic",
    "langchain-community",
    "tavily-python>=0.2.12",
    "chromadb>=0.4.0",
    "sentence-transformers>=2.2.0",
    "fastapi",
    "uvicorn",
    "pypdf",
    "python-docx",
    "redis",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
    "black",
    "ruff",
]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

### next.config.mjs (Next.js)

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // 엄격 모드
  reactStrictMode: true,

  // 이미지 도메인 허용
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },

  // 웹팩 설정 (Mermaid 등)
  webpack: (config) => {
    config.resolve.fallback = {
      ...config.resolve.fallback,
      fs: false,
    };
    return config;
  },

  // 실험적 기능
  experimental: {
    serverActions: true,
  },
};

export default nextConfig;
```

### tailwind.config.js

```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        // ... 더 많은 색상
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
```

---

## 에이전트 설정

### agents/config.py

```python
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional

class AgentRole(Enum):
    """에이전트 역할"""
    MANAGER = "manager"
    SIMPLE = "simple"
    CARBON_EXPERT = "carbon_expert"
    REGULATION_EXPERT = "regulation_expert"
    SUPPORT_EXPERT = "support_expert"

@dataclass
class AgentConfig:
    """에이전트 설정"""
    role: AgentRole
    name: str
    model: str
    temperature: float
    description: str
    tools: List[str]
    system_prompt_key: Optional[str] = None

# 에이전트 레지스트리
AGENT_REGISTRY = {
    AgentRole.MANAGER: AgentConfig(
        role=AgentRole.MANAGER,
        name="Manager Agent",
        model="claude-haiku-4-5",
        temperature=0.0,
        description="질문 분석 및 전문가 라우팅",
        tools=[],
        system_prompt_key="manager"
    ),
    AgentRole.SIMPLE: AgentConfig(
        role=AgentRole.SIMPLE,
        name="Simple Agent",
        model="claude-haiku-4-5",
        temperature=0.1,
        description="일반 질문, FAQ, 기본 정보",
        tools=["search_knowledge_base", "search"],
        system_prompt_key="simple"
    ),
    AgentRole.CARBON_EXPERT: AgentConfig(
        role=AgentRole.CARBON_EXPERT,
        name="Carbon Expert",
        model="claude-haiku-4-5",
        temperature=0.1,
        description="배출권 거래, 시장 분석",
        tools=[
            "search_knowledge_base",
            "search",
            "get_transaction_volume",
            "get_market_price",
            "search_carbon_credits",
            "calculate_trading_fee"
        ],
        system_prompt_key="carbon_expert"
    ),
    AgentRole.REGULATION_EXPERT: AgentConfig(
        role=AgentRole.REGULATION_EXPERT,
        name="Regulation Expert",
        model="claude-haiku-4-5",
        temperature=0.1,
        description="규제 대응, 컴플라이언스",
        tools=[
            "search_knowledge_base",
            "search",
            "calculate_scope_emissions",
            "get_compliance_report",
            "validate_emission_data"
        ],
        system_prompt_key="regulation_expert"
    ),
    AgentRole.SUPPORT_EXPERT: AgentConfig(
        role=AgentRole.SUPPORT_EXPERT,
        name="Support Expert",
        model="claude-haiku-4-5",
        temperature=0.2,
        description="고객 상담, 문제 해결",
        tools=[
            "search_knowledge_base",
            "search",
            "classify_customer_segment",
            "get_customer_history"
        ],
        system_prompt_key="support_expert"
    ),
}

# 카테고리별 기본 에이전트 매핑
CATEGORY_AGENT_MAP = {
    "탄소배출권": AgentRole.CARBON_EXPERT,
    "규제대응": AgentRole.REGULATION_EXPERT,
    "고객상담": AgentRole.SUPPORT_EXPERT,
}
```

---

## RAG 설정

### rag_tool.py

```python
# 임베딩 모델 설정
EMBEDDING_CONFIG = {
    "model_name": "dragonkue/BGE-m3-ko",
    "model_kwargs": {"device": "cpu"},
    "encode_kwargs": {"normalize_embeddings": True},
}

# 청킹 설정
CHUNK_CONFIG = {
    "chunk_size": 800,
    "chunk_overlap": 150,
    "separators": ["\n\n", "\n", ".", " "],
}

# 검색 설정
SEARCH_CONFIG = {
    "k": 3,                    # 반환 문서 수
    "score_threshold": 0.7,    # 유사도 임계값
    "fetch_k": 10,            # 초기 검색 수 (MMR용)
    "lambda_mult": 0.5,       # MMR 다양성 가중치
}

# Chroma 설정
CHROMA_CONFIG = {
    "collection_name": "knowledge_base",
    "distance_fn": "cosine",
}
```

---

## 캐시 설정

### cache_manager.py

```python
# 캐시 키 프리픽스
CACHE_PREFIXES = {
    "faq": "faq:",
    "rag": "rag:",
    "llm": "llm:",
    "mcp": "mcp:",
}

# TTL 설정 (초)
CACHE_TTL = {
    "faq": None,      # 영구
    "rag": 86400,     # 24시간
    "llm": 86400,     # 24시간
    "mcp": 3600,      # 1시간
}

# 메모리 캐시 제한
MEMORY_CACHE_MAX_SIZE = 10000
```

---

## 로깅 설정

### 로거 설정

```python
import logging

# 로그 레벨 설정
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log"),
    ]
)

# 모듈별 로거
logger = logging.getLogger("react_agent")
```

### LangSmith 트레이싱

```python
# 환경변수로 활성화
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = "ls-..."
os.environ["LANGSMITH_PROJECT"] = "Carbon-AI-Chatbot"
```

---

## 프론트엔드 설정

### src/lib/config-server.ts

```typescript
interface ServerConfig {
  apiUrl: string;
  assistantId: string;
}

export function getServerConfig(): ServerConfig {
  return {
    apiUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:7860",
    assistantId: process.env.NEXT_PUBLIC_ASSISTANT_ID || "agent",
  };
}
```

### src/providers/Settings.tsx

```typescript
interface Settings {
  // UI 설정
  chatWidth: "narrow" | "medium" | "wide";
  showToolCalls: boolean;
  enableAnimations: boolean;

  // 시각화 설정
  autoRenderCharts: boolean;
  autoRenderTables: boolean;
  autoRenderMermaid: boolean;
  autoRenderMaps: boolean;

  // 세션 설정
  sessionTimeout: number; // 분
}

const DEFAULT_SETTINGS: Settings = {
  chatWidth: "medium",
  showToolCalls: true,
  enableAnimations: true,
  autoRenderCharts: true,
  autoRenderTables: true,
  autoRenderMermaid: true,
  autoRenderMaps: true,
  sessionTimeout: 60,
};
```

---

## 보안 설정

### API 키 관리

```bash
# 개발 환경
# .env 파일 사용 (버전 관리 제외)
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore

# 프로덕션 환경
# 환경변수 또는 시크릿 매니저 사용
```

### CORS 설정

```python
# server.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://your-app.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/threads/{thread_id}/runs/stream")
@limiter.limit("10/minute")
async def stream_run(request: Request, thread_id: str):
    ...
```

---

## 환경별 설정 예시

### 개발 환경

```bash
# .env.local (프론트엔드)
NEXT_PUBLIC_API_URL=http://localhost:7860
NEXT_PUBLIC_ASSISTANT_ID=agent

# .env (백엔드)
ANTHROPIC_API_KEY=sk-ant-dev-...
TAVILY_API_KEY=tvly-dev-...
USE_REDIS_CACHE=false
LOG_LEVEL=DEBUG
```

### 프로덕션 환경

```bash
# .env.local (프론트엔드)
NEXT_PUBLIC_API_URL=https://ruffy1601-carbon-ai-chatbot.hf.space
NEXT_PUBLIC_ASSISTANT_ID=agent

# .env (백엔드)
ANTHROPIC_API_KEY=sk-ant-prod-...
TAVILY_API_KEY=tvly-prod-...
USE_REDIS_CACHE=true
REDIS_URL=redis://production-redis:6379/0
LOG_LEVEL=INFO
LANGSMITH_TRACING=true
```
