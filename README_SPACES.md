# CarbonAI - Hugging Face Spaces

탄소 배출권 전문 AI 챗봇

## 🚀 Hugging Face Spaces 배포 가이드

### 1단계: Hugging Face 계정 생성

1. https://huggingface.co/ 접속
2. "Sign Up" 클릭
3. 계정 생성 (GitHub 연동 가능)

### 2단계: New Space 생성

1. https://huggingface.co/new-space 접속
2. 다음 정보 입력:
   - **Space name**: `carbon-ai-chatbot` (원하는 이름)
   - **License**: MIT
   - **Space SDK**: **Docker** 선택 ⚠️ 중요!
   - **Space hardware**: CPU basic (무료)
   - **Visibility**: Public

3. "Create Space" 클릭

### 3단계: GitHub 저장소 연동

Space가 생성되면:

1. **Settings** 탭 클릭
2. **Repository** 섹션에서:
   - **"Link to GitHub"** 클릭
   - GitHub 저장소 선택: `hyunbin1601/carbonAI`
   - 브랜치: `master`

3. **Environment Variables** 섹션에서 다음 추가:
   ```
   ANTHROPIC_API_KEY=your-anthropic-api-key-here
   TAVILY_API_KEY=your-tavily-api-key-here
   LANGSMITH_API_KEY=your-langsmith-api-key-here
   LANGSMITH_TRACING=true
   LANGSMITH_PROJECT=CarbonAI-Production
   NETZ_MCP_URL=https://hooxi.shinssy.com
   NETZ_MCP_ENABLED=true
   NETZ_ENTERPRISE_ID=1
   PORT=7860
   ```

4. **Save** 클릭

### 4단계: 자동 배포 시작

- GitHub 연동 후 자동으로 빌드 시작
- 약 10-15분 소요
- **Logs** 탭에서 진행 상황 확인

### 5단계: 배포 완료 확인

배포가 완료되면:
- Space URL: `https://huggingface.co/spaces/YOUR_USERNAME/carbon-ai-chatbot`
- API URL: `https://YOUR_USERNAME-carbon-ai-chatbot.hf.space`

## 📡 API 엔드포인트

배포 후 다음 엔드포인트 사용 가능:

- `GET /ok` - 헬스 체크
- `POST /invoke` - 일반 채팅
- `POST /stream` - 스트리밍 채팅
- `GET /categories` - 카테고리 목록

### API 사용 예시

```bash
# 헬스 체크
curl https://YOUR_USERNAME-carbon-ai-chatbot.hf.space/ok

# 채팅
curl -X POST https://YOUR_USERNAME-carbon-ai-chatbot.hf.space/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "message": "배출권 거래 방법 알려줘",
    "category": "탄소배출권"
  }'
```

## ⚠️ 주의사항

- **콜드 스타트**: 비활성 시 슬립 모드 진입, 첫 요청 시 ~30초 소요
- **타임아웃**: 60초 이상 요청은 타임아웃될 수 있음
- **동시 접속**: 무료 티어는 제한적 (유료 업그레이드 가능)

## 🔧 문제 해결

### 빌드 실패
- Logs 탭에서 오류 확인
- Dockerfile 문제 → GitHub 이슈 등록

### 서버 시작 실패
- Environment Variables 확인
- PORT=7860 설정 확인

### API 응답 없음
- Space가 Running 상태인지 확인
- 콜드 스타트 중일 수 있음 (30초 대기)

## 📞 지원

문제 발생 시:
1. Hugging Face Spaces Logs 확인
2. GitHub Issues: https://github.com/hyunbin1601/carbonAI/issues
