# 🗺️ 맵 시각화 빠른 시작 가이드

## 🚀 개발 서버 실행

```bash
cd agent-chat-ui
pnpm dev
```

서버 실행 후 브라우저에서 접속:
- **메인 데모**: http://localhost:3000/map-demos
- **예제 갤러리**: http://localhost:3000/map-examples
- **인터랙티브 에디터**: http://localhost:3000/map-editor
- **API 연동**: http://localhost:3000/map-api

## 📁 샘플 데이터

`public/sample-data/` 폴더에 테스트용 파일이 있습니다:

- `seoul-cafes.json` - 서울 카페 위치
- `delivery-routes.json` - 배송 경로 데이터
- `seoul-locations.csv` - 서울 주요 지점 (CSV)

이 파일들을 `/map-editor` 페이지에서 업로드하여 테스트할 수 있습니다.

## 💡 3가지 사용 방법

### 1. 수동으로 데이터 입력

`/map-editor` 페이지에서:
1. 경도/위도 입력
2. "포인트 추가" 버튼 클릭
3. 지도에서 실시간으로 확인

### 2. 파일 업로드

`/map-editor` 페이지에서:
1. "파일 업로드" 섹션으로 이동
2. JSON, GeoJSON, 또는 CSV 파일 선택
3. 자동으로 파싱되어 지도에 표시

**JSON 예제:**
```json
[
  {
    "longitude": 126.9780,
    "latitude": 37.5665,
    "name": "서울시청",
    "radius": 200
  }
]
```

**CSV 예제:**
```csv
name,longitude,latitude
서울시청,126.9780,37.5665
강남역,127.0276,37.4979
```

### 3. API 연동

`/map-api` 페이지에서:
- 랜덤 위치 생성
- 서울 관광지 로드
- 실시간 지진 데이터 (USGS API)
- 실시간 시뮬레이션

## 🎨 컴포넌트 사용법

```tsx
import { MapRenderer } from "@/components/thread/map-renderer";

const mapConfig = {
  initialViewState: {
    longitude: 126.9780,
    latitude: 37.5665,
    zoom: 11,
  },
  layers: [
    {
      type: "scatterplot",
      data: [
        {
          position: [126.9780, 37.5665],
          radius: 200,
          color: [255, 0, 0, 200],
          name: "서울시청"
        }
      ]
    }
  ]
};

<MapRenderer config={mapConfig} />
```

## 🔥 실전 사용 예제

### 예제 1: 카페 찾기 앱

```tsx
const [cafes, setCafes] = useState([]);

// 카카오 로컬 API로 카페 검색
const searchCafes = async (keyword) => {
  const response = await fetch(
    `https://dapi.kakao.com/v2/local/search/keyword.json?query=${keyword}`,
    { headers: { 'Authorization': 'KakaoAK YOUR_KEY' }}
  );
  const data = await response.json();

  const locations = data.documents.map(place => ({
    position: [parseFloat(place.x), parseFloat(place.y)],
    radius: 150,
    name: place.place_name
  }));

  setCafes(locations);
};

<MapRenderer config={{
  initialViewState: { longitude: 126.9780, latitude: 37.5665, zoom: 12 },
  layers: [{ type: "scatterplot", data: cafes }]
}} />
```

### 예제 2: 배송 추적

```tsx
const [deliveryPath, setDeliveryPath] = useState([]);

// WebSocket으로 실시간 위치 수신
useEffect(() => {
  const ws = new WebSocket('ws://your-server.com');
  ws.onmessage = (msg) => {
    const location = JSON.parse(msg.data);
    setDeliveryPath(prev => [...prev, [location.lng, location.lat]]);
  };
}, []);

<MapRenderer config={{
  layers: [{
    type: "path",
    data: [{ path: deliveryPath, color: [255, 0, 0, 200], width: 5 }]
  }]
}} />
```

### 예제 3: 인구 밀도 히트맵

```tsx
const populationData = [
  { position: [126.9780, 37.5665], weight: 1500 },
  { position: [127.0276, 37.4979], weight: 2000 },
  // ... more data
];

<MapRenderer config={{
  initialViewState: { pitch: 45 },
  layers: [{
    type: "hexagon",
    data: populationData,
    radius: 500,
    elevationScale: 20,
    extruded: true
  }]
}} />
```

## 📊 데이터 포맷

### Scatterplot (포인트)
```js
{
  position: [longitude, latitude],  // 또는 별도의 longitude, latitude 속성
  radius: 200,                      // 선택사항
  color: [R, G, B, A],             // 선택사항
  name: "이름"                      // 선택사항
}
```

### Path (경로)
```js
{
  path: [[lng1, lat1], [lng2, lat2], ...],
  color: [R, G, B, A],
  width: 5
}
```

### GeoJSON
```js
{
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      geometry: { type: "Point", coordinates: [lng, lat] },
      properties: { name: "이름" }
    }
  ]
}
```

## 🛠️ 고급 기능

### 다크 모드
맵은 자동으로 시스템 다크 모드를 감지하여 테마를 변경합니다.

### 커스텀 맵 스타일
```tsx
<MapRenderer config={{
  style: "https://your-custom-map-style.json",
  // ...
}} />
```

### 툴팁 비활성화
```tsx
<MapRenderer config={{
  tooltip: false,
  // ...
}} />
```

## 🌐 공공 API 활용

### 서울 열린데이터 광장
```js
// 서울시 공공 와이파이
http://openapi.seoul.go.kr:8088/[API_KEY]/json/TbPublicWifiInfo/1/1000/

// 서울시 대기 오염 정보
http://openapi.seoul.go.kr:8088/[API_KEY]/json/TimeAverageAirQuality/1/25/
```

### 공공데이터 포털
https://www.data.go.kr/

### 기타 유용한 API
- 카카오 로컬 API
- 네이버 지도 API
- Google Places API
- OpenStreetMap Overpass API

## 📝 다음 단계

1. `/map-demos` 페이지 방문
2. 각 데모 탐색
3. 샘플 데이터로 테스트
4. 실제 API 연동
5. 프로덕션 배포

## 🔗 참고 자료

- [deck.gl 공식 문서](https://deck.gl/)
- [react-map-gl 문서](https://visgl.github.io/react-map-gl/)
- [MapLibre GL JS](https://maplibre.org/)
- [GeoJSON 스펙](https://geojson.org/)

## ❓ 문제 해결

### 맵이 표시되지 않음
- 브라우저 콘솔에서 에러 확인
- 데이터 형식이 올바른지 확인
- 경도/위도 값이 유효한지 확인

### 성능 문제
- 데이터 포인트가 너무 많으면 샘플링
- 3D 레이어는 `extruded: false`로 설정
- 불필요한 레이어 제거

### CORS 에러
- 백엔드에 프록시 API 추가
- 또는 서버에서 CORS 헤더 설정
