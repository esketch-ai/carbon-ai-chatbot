# 🤖 AI 챗봇 + 지도 시각화 통합 가이드

## 개요

이제 AI 에이전트가 사용자의 요청에 따라 자동으로 지도를 생성하고 표시할 수 있습니다!

## 작동 원리

1. **사용자**: "서울의 카페 위치를 지도로 보여줘"
2. **AI**: 요청 분석 → 데이터 수집 → 지도 생성
3. **채팅창**: 인터랙티브 지도 표시

## AI가 지도를 생성하는 방법

AI는 마크다운 코드 블록으로 지도를 생성합니다:

````markdown
```map
{
  "initialViewState": {
    "longitude": 126.9780,
    "latitude": 37.5665,
    "zoom": 11
  },
  "layers": [
    {
      "type": "scatterplot",
      "data": [
        {
          "position": [126.9780, 37.5665],
          "radius": 200,
          "name": "서울시청"
        }
      ]
    }
  ]
}
```
````

## 사용 예시

### 예제 1: 포인트 맵

**사용자 질문:**
> "전국 주요 배출권 거래소 위치를 지도로 보여줘"

**AI 응답:**
```map
{
  "initialViewState": {
    "longitude": 127.5,
    "latitude": 36.5,
    "zoom": 7
  },
  "layers": [
    {
      "type": "scatterplot",
      "data": [
        {"position": [126.9780, 37.5665], "name": "서울 거래소", "radius": 250, "color": [255, 0, 0, 200]},
        {"position": [129.0756, 35.1796], "name": "부산 거래소", "radius": 250, "color": [0, 0, 255, 200]},
        {"position": [126.7052, 37.4563], "name": "인천 거래소", "radius": 250, "color": [0, 255, 0, 200]}
      ]
    }
  ]
}
```

### 예제 2: 히트맵

**사용자 질문:**
> "지역별 탄소 배출량을 히트맵으로 보여줘"

**AI 응답:**
```map
{
  "initialViewState": {
    "longitude": 127.5,
    "latitude": 36.5,
    "zoom": 7,
    "pitch": 45
  },
  "layers": [
    {
      "type": "hexagon",
      "data": [
        {"position": [126.9780, 37.5665], "weight": 150},
        {"position": [129.0756, 35.1796], "weight": 100},
        {"position": [127.3845, 36.3504], "weight": 80}
      ],
      "radius": 50000,
      "elevationScale": 20,
      "extruded": true
    }
  ]
}
```

### 예제 3: 경로 맵

**사용자 질문:**
> "배송 차량 이동 경로를 지도로 보여줘"

**AI 응답:**
```map
{
  "initialViewState": {
    "longitude": 126.9780,
    "latitude": 37.5665,
    "zoom": 12
  },
  "layers": [
    {
      "type": "path",
      "data": [
        {
          "path": [
            [126.9780, 37.5665],
            [127.0276, 37.4979],
            [127.0495, 37.5142]
          ],
          "color": [255, 0, 0, 200],
          "width": 5,
          "name": "배송 경로 1"
        }
      ]
    }
  ]
}
```

## AI 프롬프트에 포함된 가이드

AI는 다음과 같은 상황에서 자동으로 지도를 생성합니다:

- 위치 정보 요청
- 지리적 분포 표시
- 경로/이동 패턴 시각화
- 지역별 데이터 비교
- 시설 분포 표시

## 지원하는 레이어 타입

### 1. Scatterplot (포인트)
- **용도**: 특정 위치 표시 (매장, 시설, 이벤트 등)
- **데이터**: `position`, `radius`, `color`, `name`

### 2. Path (경로)
- **용도**: 이동 경로, 도로, 라인 표시
- **데이터**: `path` (좌표 배열), `color`, `width`

### 3. Polygon (구역)
- **용도**: 행정구역, 토지, 영역 표시
- **데이터**: `polygon` (좌표 배열), `fillColor`, `lineColor`

### 4. Hexagon (히트맵)
- **용도**: 밀도, 집중도, 분포 시각화
- **데이터**: `position`, `weight`

### 5. GeoJSON
- **용도**: 표준 GIS 데이터 로드
- **데이터**: GeoJSON FeatureCollection

## 좌표 시스템

- **경도 (Longitude)**: 동서 방향 (-180 ~ 180)
  - 서울: 126.9780
  - 부산: 129.0756

- **위도 (Latitude)**: 남북 방향 (-90 ~ 90)
  - 서울: 37.5665
  - 부산: 35.1796

## 색상 포맷

RGBA 배열: `[Red, Green, Blue, Alpha]`
- R, G, B: 0-255
- Alpha: 0-255 (투명도)

예시:
- 빨강: `[255, 0, 0, 200]`
- 파랑: `[0, 0, 255, 200]`
- 초록: `[0, 255, 0, 200]`

## 테스트 방법

### 1. 개발 서버 실행
```bash
cd agent-chat-ui
pnpm dev
```

### 2. 채팅 테스트
브라우저에서 http://localhost:3000 접속 후:

**테스트 질문들:**
- "서울 시청 위치를 지도로 보여줘"
- "강남역과 홍대입구역 위치를 지도에 표시해줘"
- "서울에서 부산까지 경로를 보여줘"
- "전국 주요 도시 분포를 지도로 보여줘"

### 3. 예제 페이지
직접 테스트하려면:
- http://localhost:3000/map-examples (하드코딩 예제)
- http://localhost:3000/map-editor (수동 입력 테스트)
- http://localhost:3000/map-api (API 연동 테스트)

## 문제 해결

### 지도가 표시되지 않음
1. 브라우저 콘솔 확인
2. JSON 형식이 올바른지 확인
3. 좌표 값이 유효한지 확인 (경도: -180~180, 위도: -90~90)

### AI가 지도를 생성하지 않음
1. `react-agent/src/react_agent/prompts.py` 업데이트 확인
2. AI 에이전트 재시작
3. 더 명확한 질문 시도 ("지도로 보여줘" 명시)

### 성능 문제
1. 데이터 포인트 수 제한 (1000개 이하 권장)
2. 3D 레이어는 `extruded: false`로 설정
3. 줌 레벨 적절히 조정

## 고급 기능

### 실시간 데이터 연동
AI가 외부 API에서 데이터를 가져와 지도 생성:

```python
# tools.py에서 외부 API 호출
def get_store_locations():
    response = requests.get('https://api.example.com/stores')
    return response.json()
```

### 동적 업데이트
WebSocket으로 실시간 위치 추적

### 사용자 인터랙션
클릭 이벤트, 필터링, 검색 기능 추가 가능

## 관련 문서

- `MAP_RENDERER_GUIDE.md` - MapRenderer 전체 API 문서
- `MAP_QUICK_START.md` - 빠른 시작 가이드
- [deck.gl 공식 문서](https://deck.gl/)

## 예상 시나리오

### 탄소 배출 관련
- "전국 배출권 거래소 위치"
- "지역별 탄소 배출량 분포"
- "우리 회사 사업장 위치"

### 물류/배송
- "배송 경로 최적화"
- "물류 센터 위치"
- "배송 차량 실시간 추적"

### 비즈니스
- "매장 분포도"
- "고객 밀집 지역"
- "경쟁사 위치 분석"

## 다음 단계

1. ✅ MapRenderer 컴포넌트 작성
2. ✅ markdown-text.tsx 통합
3. ✅ AI 프롬프트 업데이트
4. 🔄 실제 데이터 API 연동
5. 📊 더 많은 레이어 타입 추가
6. 🎨 커스텀 맵 스타일
7. 📱 모바일 최적화
