"use client";

import dynamic from "next/dynamic";
import { MapErrorBoundary } from "./map-error-boundary";

// MapRenderer를 클라이언트 전용으로 로드 (SSR 비활성화)
const MapRenderer = dynamic(
  () => import("./map-renderer").then((mod) => mod.MapRenderer),
  {
    ssr: false,
    loading: () => (
      <div className="h-[500px] flex items-center justify-center border rounded-xl">
        <p className="text-muted-foreground">지도 로딩 중...</p>
      </div>
    )
  }
);

// 예제 1: 서울 주요 지점 (Scatterplot)
const seoulLocations = {
  initialViewState: {
    longitude: 126.9780,
    latitude: 37.5665,
    zoom: 11,
  },
  layers: [
    {
      type: "scatterplot" as const,
      data: [
        { position: [126.9780, 37.5665], radius: 200, color: [255, 0, 0, 200], name: "서울시청" },
        { position: [127.0276, 37.4979], radius: 300, color: [0, 255, 0, 200], name: "강남역" },
        { position: [127.0495, 37.5142], radius: 250, color: [0, 0, 255, 200], name: "코엑스" },
        { position: [126.9910, 37.5511], radius: 180, color: [255, 255, 0, 200], name: "경복궁" },
        { position: [126.9996, 37.5800], radius: 220, color: [255, 0, 255, 200], name: "창경궁" },
      ],
    },
  ],
  tooltip: true,
};

// 예제 2: 경로 표시 (Path)
const deliveryRoutes = {
  initialViewState: {
    longitude: 126.9780,
    latitude: 37.5665,
    zoom: 12,
  },
  layers: [
    {
      type: "path" as const,
      data: [
        {
          path: [
            [126.9780, 37.5665],
            [127.0276, 37.4979],
            [127.0495, 37.5142],
          ],
          color: [255, 0, 0, 200],
          width: 5,
        },
        {
          path: [
            [126.9910, 37.5511],
            [126.9780, 37.5665],
            [126.9996, 37.5800],
          ],
          color: [0, 0, 255, 200],
          width: 5,
        },
      ],
    },
  ],
};

// 예제 3: 히트맵 (Hexagon)
const populationDensity = {
  initialViewState: {
    longitude: 126.9780,
    latitude: 37.5665,
    zoom: 11,
    pitch: 45,
  },
  layers: [
    {
      type: "hexagon" as const,
      data: Array.from({ length: 200 }, () => ({
        position: [
          126.9780 + (Math.random() - 0.5) * 0.2,
          37.5665 + (Math.random() - 0.5) * 0.2,
        ],
        weight: Math.random() * 10,
      })),
      radius: 300,
      elevationScale: 20,
      extruded: true,
    },
  ],
};

// 예제 4: GeoJSON (구역 표시)
const districtBoundaries = {
  initialViewState: {
    longitude: 126.9780,
    latitude: 37.5665,
    zoom: 11,
  },
  layers: [
    {
      type: "geojson" as const,
      data: {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            geometry: {
              type: "Polygon",
              coordinates: [
                [
                  [126.9, 37.5],
                  [127.0, 37.5],
                  [127.0, 37.6],
                  [126.9, 37.6],
                  [126.9, 37.5],
                ],
              ],
            },
            properties: {
              name: "강북구",
              fillColor: [255, 100, 100, 100],
              lineColor: [255, 0, 0, 255],
            },
          },
          {
            type: "Feature",
            geometry: {
              type: "Polygon",
              coordinates: [
                [
                  [127.0, 37.5],
                  [127.1, 37.5],
                  [127.1, 37.6],
                  [127.0, 37.6],
                  [127.0, 37.5],
                ],
              ],
            },
            properties: {
              name: "강남구",
              fillColor: [100, 100, 255, 100],
              lineColor: [0, 0, 255, 255],
            },
          },
        ],
      },
    },
  ],
};

export function MapExamples() {
  return (
    <div className="space-y-8 p-8">
      <div>
        <h2 className="text-2xl font-bold mb-4">맵 시각화 예제</h2>
        <p className="text-muted-foreground mb-6">
          deck.gl + OSM을 활용한 다양한 GIS 시각화 예제입니다.
        </p>
      </div>

      <div className="space-y-6">
        <div>
          <h3 className="text-xl font-semibold mb-2">1. 포인트 맵 (Scatterplot)</h3>
          <p className="text-sm text-muted-foreground mb-3">
            서울 주요 지점을 표시합니다. 각 포인트에 마우스를 올려보세요.
          </p>
          <MapErrorBoundary>
            <MapRenderer config={seoulLocations} />
          </MapErrorBoundary>
        </div>

        <div>
          <h3 className="text-xl font-semibold mb-2">2. 경로 맵 (Path)</h3>
          <p className="text-sm text-muted-foreground mb-3">
            배송 경로나 이동 패턴을 시각화합니다.
          </p>
          <MapErrorBoundary>
            <MapRenderer config={deliveryRoutes} />
          </MapErrorBoundary>
        </div>

        <div>
          <h3 className="text-xl font-semibold mb-2">3. 히트맵 (Hexagon)</h3>
          <p className="text-sm text-muted-foreground mb-3">
            인구 밀도나 데이터 집중도를 3D로 표현합니다. 마우스로 회전할 수 있습니다.
          </p>
          <MapErrorBoundary>
            <MapRenderer config={populationDensity} />
          </MapErrorBoundary>
        </div>

        <div>
          <h3 className="text-xl font-semibold mb-2">4. 구역 맵 (GeoJSON)</h3>
          <p className="text-sm text-muted-foreground mb-3">
            행정구역이나 토지 이용 구역을 표시합니다.
          </p>
          <MapErrorBoundary>
            <MapRenderer config={districtBoundaries} />
          </MapErrorBoundary>
        </div>
      </div>
    </div>
  );
}
