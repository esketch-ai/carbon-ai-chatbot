# 배포 가이드

## 개요

Carbon AI Chatbot은 프론트엔드와 백엔드가 분리되어 별도로 배포됩니다.

| 컴포넌트 | 플랫폼 | URL |
|---------|--------|-----|
| 프론트엔드 | Vercel | `https://your-app.vercel.app` |
| 백엔드 | HuggingFace Spaces | `https://ruffy1601-carbon-ai-chatbot.hf.space` |

---

## 프론트엔드 배포 (Vercel)

### 사전 요구사항

- Vercel 계정
- GitHub/GitLab 연동 (선택)
- Node.js 18+

### 1. Vercel CLI 설치

```bash
npm install -g vercel
```

### 2. 프로젝트 설정

```bash
cd agent-chat-ui
vercel login
```

### 3. 환경변수 설정

Vercel 대시보드 또는 CLI에서 환경변수를 설정합니다.

```bash
vercel env add NEXT_PUBLIC_API_URL
# 값: https://ruffy1601-carbon-ai-chatbot.hf.space

vercel env add NEXT_PUBLIC_ASSISTANT_ID
# 값: agent
```

### 4. 배포

```bash
# 프리뷰 배포
vercel

# 프로덕션 배포
vercel --prod
```

### 5. vercel.json 설정

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs",
  "installCommand": "pnpm install",
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://ruffy1601-carbon-ai-chatbot.hf.space/:path*"
    }
  ]
}
```

### GitHub 자동 배포

1. Vercel 대시보드에서 "Import Project" 선택
2. GitHub 저장소 연결
3. 환경변수 설정
4. "Deploy" 클릭

이후 `main` 브랜치에 푸시하면 자동 배포됩니다.

---

## 백엔드 배포 (HuggingFace Spaces)

### 사전 요구사항

- HuggingFace 계정
- API 키 (Anthropic, Tavily)

### 1. Space 생성

1. [HuggingFace Spaces](https://huggingface.co/spaces)에서 "Create Space" 클릭
2. 설정:
   - SDK: Docker
   - Hardware: CPU (또는 GPU)
   - Visibility: Public/Private

### 2. Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY react-agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드
COPY react-agent/src ./src
COPY react-agent/knowledge_base ./knowledge_base

# 환경 설정
ENV PORT=7860
ENV PYTHONPATH=/app/src

# 서버 실행
CMD ["python", "-m", "react_agent.server"]
```

### 3. Secrets 설정

HuggingFace Spaces 설정에서 Secrets 추가:

```
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
HF_TOKEN=hf_...
```

### 4. 배포

```bash
# Git LFS 설치 (대용량 파일용)
git lfs install

# HuggingFace Hub에 푸시
git remote add space https://huggingface.co/spaces/username/carbon-ai-chatbot
git push space main
```

### Space 설정 파일

`README.md` (Space 루트):

```yaml
---
title: Carbon AI Chatbot
emoji: 🌿
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---
```

---

## 백엔드 배포 (Railway)

### 사전 요구사항

- Railway 계정
- Railway CLI (선택)

### 1. railway.json

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "watchPatterns": ["src/**", "pyproject.toml"]
  },
  "deploy": {
    "startCommand": "python -m react_agent.server",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 300,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### 2. Railway 배포

```bash
# CLI 설치
npm install -g @railway/cli

# 로그인
railway login

# 프로젝트 생성 및 배포
cd react-agent
railway init
railway up
```

### 3. 환경변수 설정

Railway 대시보드에서 Variables 추가:

```
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
PORT=7860
```

---

## Docker 로컬 배포

### 1. 이미지 빌드

```bash
docker build -t carbon-ai-chatbot .
```

### 2. 컨테이너 실행

```bash
docker run -d \
  --name carbon-chatbot \
  -p 7860:7860 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e TAVILY_API_KEY=tvly-... \
  -v $(pwd)/knowledge_base:/app/knowledge_base \
  -v $(pwd)/chroma_db:/app/chroma_db \
  carbon-ai-chatbot
```

### 3. Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "7860:7860"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - TAVILY_API_KEY=${TAVILY_API_KEY}
      - USE_REDIS_CACHE=true
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./knowledge_base:/app/knowledge_base
      - ./chroma_db:/app/chroma_db
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  frontend:
    build:
      context: ./agent-chat-ui
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:7860
      - NEXT_PUBLIC_ASSISTANT_ID=agent

volumes:
  redis_data:
```

### 4. 실행

```bash
# .env 파일 생성
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
echo "TAVILY_API_KEY=tvly-..." >> .env

# 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

---

## 환경별 설정

### 개발 환경

```bash
# 프론트엔드
cd agent-chat-ui
cp .env.example .env.local
# NEXT_PUBLIC_API_URL=http://localhost:7860
pnpm dev

# 백엔드
cd react-agent
cp .env.example .env
# ANTHROPIC_API_KEY=sk-ant-...
python -m react_agent.server
```

### 스테이징 환경

```bash
# 환경변수
NEXT_PUBLIC_API_URL=https://staging-api.example.com
ANTHROPIC_API_KEY=sk-ant-staging-...
```

### 프로덕션 환경

```bash
# 환경변수
NEXT_PUBLIC_API_URL=https://ruffy1601-carbon-ai-chatbot.hf.space
ANTHROPIC_API_KEY=sk-ant-production-...
USE_REDIS_CACHE=true
REDIS_URL=redis://production-redis:6379/0
```

---

## CI/CD 파이프라인

### GitHub Actions (프론트엔드)

```yaml
# .github/workflows/frontend.yml
name: Frontend CI/CD

on:
  push:
    branches: [main]
    paths:
      - 'agent-chat-ui/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install pnpm
        uses: pnpm/action-setup@v2
        with:
          version: 8

      - name: Install dependencies
        run: |
          cd agent-chat-ui
          pnpm install

      - name: Build
        run: |
          cd agent-chat-ui
          pnpm build
        env:
          NEXT_PUBLIC_API_URL: ${{ secrets.API_URL }}

      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: ./agent-chat-ui
          vercel-args: '--prod'
```

### GitHub Actions (백엔드)

```yaml
# .github/workflows/backend.yml
name: Backend CI/CD

on:
  push:
    branches: [main]
    paths:
      - 'react-agent/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd react-agent
          pip install -e .
          pip install pytest

      - name: Run tests
        run: |
          cd react-agent
          pytest tests/

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          lfs: true

      - name: Push to HuggingFace
        env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
        run: |
          git remote add space https://user:$HF_TOKEN@huggingface.co/spaces/ruffy1601/carbon-ai-chatbot
          git push space main --force
```

---

## 모니터링

### 헬스체크

```bash
# 프론트엔드
curl https://your-app.vercel.app

# 백엔드
curl https://ruffy1601-carbon-ai-chatbot.hf.space/health
```

### 로그 확인

```bash
# HuggingFace Spaces
# 대시보드에서 "Logs" 탭 확인

# Railway
railway logs

# Docker
docker logs carbon-chatbot -f
```

### 알림 설정

- **Vercel**: 대시보드에서 Deployment 알림 설정
- **HuggingFace**: Discussions 알림
- **Railway**: Slack/Discord 웹훅 연동

---

## 롤백

### Vercel 롤백

```bash
# 이전 배포로 롤백
vercel rollback [deployment-url]
```

### HuggingFace 롤백

```bash
# 이전 커밋으로 리셋
git reset --hard <commit-hash>
git push space main --force
```

### Docker 롤백

```bash
# 이전 이미지로 실행
docker run -d carbon-ai-chatbot:previous-tag
```

---

## 트러블슈팅

### 프론트엔드 빌드 실패

```bash
# 캐시 삭제
rm -rf .next node_modules
pnpm install
pnpm build
```

### 백엔드 메모리 부족

```bash
# HuggingFace Spaces
# Hardware 업그레이드 (CPU → GPU)

# Docker
docker run --memory=4g carbon-ai-chatbot
```

### API 연결 실패

```bash
# CORS 확인
curl -I https://ruffy1601-carbon-ai-chatbot.hf.space/health

# 환경변수 확인
echo $NEXT_PUBLIC_API_URL
```

### 벡터 DB 재구축

```bash
# Chroma DB 삭제 후 재시작
rm -rf chroma_db
python -m react_agent.server
# 서버 시작 시 자동 재구축
```
