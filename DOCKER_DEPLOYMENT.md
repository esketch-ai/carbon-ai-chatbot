# Docker 배포 가이드

## 개요

Carbon AI Chatbot을 Synology NAS Docker 환경에서 실행하는 방법입니다.

## 구성 요소

| 서비스 | 설명 | 포트 |
|--------|------|------|
| **backend** | FastAPI + LangGraph 백엔드 API | 7860 |
| **frontend** | Next.js 프론트엔드 | 3000 |
| **redis** | 캐시 서버 (선택) | 6379 |
| **nginx** | 리버스 프록시 (선택) | 80, 443 |

## 빠른 시작

### 1. 환경 설정

```bash
# 환경 변수 파일 생성
cp .env.example .env

# API 키 설정 (필수)
nano .env
```

필수 설정:
- `ANTHROPIC_API_KEY`: Claude API 키
- `TAVILY_API_KEY`: 웹 검색 API 키

### 2. 배포

```bash
# 배포 스크립트 사용
./scripts/deploy.sh deploy

# 또는 Docker Compose 직접 사용
docker-compose up -d --build
```

### 3. 상태 확인

```bash
./scripts/deploy.sh status

# 또는
docker-compose ps
curl http://localhost:7860/health
```

## 서비스 관리

```bash
# 시작
./scripts/deploy.sh start

# 중지
./scripts/deploy.sh stop

# 재시작
./scripts/deploy.sh restart

# 로그 보기
./scripts/deploy.sh logs backend
./scripts/deploy.sh logs frontend

# 모든 로그
docker-compose logs -f
```

## Synology NAS 설정

### Docker 패키지 설치

1. 패키지 센터 → Docker 설치
2. Container Manager 사용 (DSM 7.2+)

### SSH 접속

```bash
ssh admin@your-nas-ip
cd /volume1/docker/carbon-ai-chatbot
```

### 파일 구조

```
/volume1/docker/carbon-ai-chatbot/
├── .env                    # 환경 변수
├── docker-compose.yml
├── data/
│   ├── knowledge_base/     # 지식베이스 문서
│   └── chroma_db/          # 벡터 DB 저장소
└── nginx/
    ├── nginx.conf
    └── ssl/                # SSL 인증서 (선택)
```

## Jenkins CI/CD

### Jenkins 설정

1. **플러그인 설치**
   - Docker Pipeline
   - Git
   - Pipeline

2. **자격 증명 추가**
   - `github-credentials`: GitHub 접근 토큰
   - `docker-registry-url`: Docker 레지스트리 URL (선택)

3. **파이프라인 생성**
   - 새 아이템 → Pipeline
   - Pipeline script from SCM
   - SCM: Git
   - Repository URL: `https://github.com/esketch-ai/carbon-ai-chatbot.git`
   - Script Path: `Jenkinsfile`

### 자동 배포 설정

GitHub Webhook을 설정하여 push 시 자동 빌드:

1. GitHub → Settings → Webhooks
2. Payload URL: `http://your-jenkins:8080/github-webhook/`
3. Content type: `application/json`
4. Events: `Push events`

## 환경 변수 상세

| 변수 | 필수 | 설명 | 기본값 |
|------|------|------|--------|
| `ANTHROPIC_API_KEY` | ✅ | Claude API 키 | - |
| `TAVILY_API_KEY` | ✅ | 웹 검색 API 키 | - |
| `BACKEND_PORT` | ❌ | 백엔드 포트 | 7860 |
| `FRONTEND_PORT` | ❌ | 프론트엔드 포트 | 3000 |
| `ENVIRONMENT` | ❌ | 환경 (production/development) | production |
| `LOG_LEVEL` | ❌ | 로그 레벨 | INFO |
| `USE_REDIS_CACHE` | ❌ | Redis 캐시 사용 | false |
| `ALLOWED_ORIGINS` | ❌ | CORS 허용 도메인 | localhost:3000 |

## 문제 해결

### 컨테이너가 시작되지 않음

```bash
# 로그 확인
docker-compose logs backend
docker-compose logs frontend

# 컨테이너 상태
docker-compose ps
```

### 메모리 부족

```bash
# Docker 리소스 제한 설정
# docker-compose.yml에 추가:
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
```

### 포트 충돌

```bash
# 사용 중인 포트 확인
netstat -tlnp | grep -E '7860|3000'

# .env에서 포트 변경
BACKEND_PORT=7861
FRONTEND_PORT=3001
```

## 업그레이드

```bash
# 최신 코드 가져오기
git pull origin main

# 재배포
./scripts/deploy.sh deploy

# 또는 특정 서비스만
docker-compose up -d --build backend
```

## 백업

```bash
# 데이터 백업
tar -czvf backup_$(date +%Y%m%d).tar.gz data/

# 복원
tar -xzvf backup_20240101.tar.gz
```
