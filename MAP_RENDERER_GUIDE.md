# MapRenderer 사용 가이드

deck.gl + OSM을 활용한 GIS 지도 시각화 컴포넌트입니다.

## 설치된 패키지

- `deck.gl` - 고성능 WebGL 기반 데이터 시각화
- `@deck.gl/layers` - 다양한 레이어 타입
- `@deck.gl/geo-layers` - GIS 특화 레이어
- `react-map-gl` - React 맵 래퍼
- `maplibre-gl` - 오픈소스 맵 렌더링

## 기본 사용법

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
        { position: [126.9780, 37.5665], radius: 200, color: [255, 0, 0, 200] },
      ],
    },
  ],
};

<MapRenderer config={mapConfig} />
```

## 지원하는 레이어 타입

### 1. Scatterplot (포인트 맵)
```js
{
  type: "scatterplot",
  data: [
    {
      position: [longitude, latitude],  // 또는 longitude, latitude 속성
      radius: 200,                      // 반지름 (미터)
      color: [R, G, B, A],             // RGBA 색상
    }
  ],
  radiusMinPixels: 5,                  // 최소 반지름 (픽셀)
  radiusMaxPixels: 30,                 // 최대 반지름 (픽셀)
}
```

**사용 사례**: 매장 위치, 센서 위치, 이벤트 발생 지점

### 2. Path (경로 맵)
```js
{
  type: "path",
  data: [
    {
      path: [[lng1, lat1], [lng2, lat2], ...],  // 경로 좌표 배열
      color: [R, G, B, A],
      width: 5,                                 // 선 두께
    }
  ],
  widthMinPixels: 2,
}
```

**사용 사례**: 배송 경로, 이동 패턴, 도로 네트워크

### 3. Polygon (폴리곤 맵)
```js
{
  type: "polygon",
  data: [
    {
      polygon: [[[lng1, lat1], [lng2, lat2], ...]],  // 폴리곤 좌표
      fillColor: [R, G, B, A],
      lineColor: [R, G, B, A],
      elevation: 100,                                // 3D 높이 (선택)
    }
  ],
  extruded: false,  // 3D 활성화
  lineWidth: 1,
}
```

**사용 사례**: 행정구역, 토지 이용, 건물

### 4. Hexagon (히트맵)
```js
{
  type: "hexagon",
  data: [
    {
      position: [longitude, latitude],
      weight: 1,  // 가중치
    }
  ],
  radius: 500,           // 육각형 반지름 (미터)
  elevationScale: 10,    // 높이 스케일
  coverage: 0.8,         // 커버리지 (0-1)
  extruded: true,        // 3D 활성화
}
```

**사용 사례**: 인구 밀도, 범죄율, 트래픽 히트맵

### 5. GeoJSON
```js
{
  type: "geojson",
  data: {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: { type: "Polygon", coordinates: [...] },
        properties: {
          fillColor: [R, G, B, A],
          lineColor: [R, G, B, A],
        }
      }
    ]
  },
  lineWidth: 1,
}
```

**사용 사례**: 표준 GIS 데이터 로드

## 설정 옵션

### initialViewState
```js
{
  longitude: 126.9780,  // 중심 경도
  latitude: 37.5665,    // 중심 위도
  zoom: 11,             // 줌 레벨 (0-20)
  pitch: 0,             // 기울기 (0-60)
  bearing: 0,           // 회전 (0-360)
}
```

### 맵 스타일
```js
{
  style: "https://your-custom-map-style.json",  // 커스텀 맵 스타일 URL
}
```

기본값:
- 라이트 모드: CartoDB Positron
- 다크 모드: CartoDB Dark Matter

### 툴팁
```js
{
  tooltip: true,  // false로 설정하면 툴팁 비활성화
}
```

## 예제 보기

개발 서버를 실행한 후 다음 URL에 접속하세요:

```bash
cd agent-chat-ui
pnpm dev
```

브라우저에서: http://localhost:3000/map-examples

## 고급 기능 아이디어

### 1. 시계열 애니메이션
```js
// TripsLayer를 사용하여 시간에 따른 이동 표시
```

### 2. 클러스터링
```js
// 많은 포인트를 자동으로 클러스터링
```

### 3. 실시간 데이터
```js
// WebSocket으로 실시간 위치 업데이트
```

### 4. 인터랙션
```js
// 클릭 이벤트, 필터링, 검색
```

## AI 에이전트와 통합

MapRenderer는 AI 에이전트가 자동으로 맵을 생성할 수 있도록 설계되었습니다:

```
사용자: "서울의 카페 분포를 지도로 보여줘"
AI: [데이터를 가져와서 MapRenderer config 생성]
    <MapRenderer config={generatedConfig} />
```

## 트러블슈팅

### 맵이 표시되지 않는 경우
1. maplibre-gl CSS가 로드되었는지 확인
2. 브라우저 콘솔에서 에러 확인
3. config의 데이터 형식 확인

### 성능 문제
1. 데이터 포인트가 너무 많으면 클러스터링 사용
2. 3D 레이어는 성능에 영향을 줄 수 있음
3. extruded: false로 설정하여 2D 사용

## 참고 자료

- [deck.gl 공식 문서](https://deck.gl/)
- [react-map-gl 문서](https://visgl.github.io/react-map-gl/)
- [MapLibre GL JS](https://maplibre.org/)
