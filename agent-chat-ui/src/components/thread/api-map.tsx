"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";

const MapRenderer = dynamic(
  () => import("./map-renderer").then((mod) => mod.MapRenderer),
  { ssr: false }
);
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function APIMap() {
  const [locations, setLocations] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  // 예제 1: 랜덤 위치 생성? -> 실제 api 필요?
  const loadRandomLocations = () => {
    setIsLoading(true);
    setError("");

    // 서울 근처 랜덤 위치 생성 (너무 많으면 성능 저하)
    const randomLocs = Array.from({ length: 100 }, (_, i) => ({
      position: [
        126.9780 + (Math.random() - 0.5) * 0.3,
        37.5665 + (Math.random() - 0.5) * 0.3,
      ],
      radius: Math.random() * 300 + 100,
      color: [
        Math.floor(Math.random() * 255),
        Math.floor(Math.random() * 255),
        Math.floor(Math.random() * 255),
        180,
      ],
      name: `위치 ${i + 1}`,
      value: Math.random() * 100,
    }));

    setTimeout(() => {
      setLocations(randomLocs);
      setIsLoading(false);
    }, 500);
  };

  // 예제 2: 특정 지역의 POI 로드 (시뮬레이션)
  const loadSeoulPOI = () => {
    setIsLoading(true);
    setError("");

    // 서울 주요 관광지
    const pois = [
      { name: "경복궁", lng: 126.9770, lat: 37.5796 },
      { name: "창덕궁", lng: 126.9910, lat: 37.5794 },
      { name: "덕수궁", lng: 126.9752, lat: 37.5658 },
      { name: "N서울타워", lng: 126.9882, lat: 37.5512 },
      { name: "광화문광장", lng: 126.9769, lat: 37.5720 },
      { name: "명동", lng: 126.9849, lat: 37.5636 },
      { name: "강남역", lng: 127.0276, lat: 37.4979 },
      { name: "홍대입구역", lng: 126.9239, lat: 37.5572 },
      { name: "이태원", lng: 126.9944, lat: 37.5347 },
      { name: "잠실", lng: 127.1000, lat: 37.5133 },
    ];

    const locations = pois.map(poi => ({
      position: [poi.lng, poi.lat],
      radius: 250,
      color: [255, 100, 50, 200],
      name: poi.name,
    }));

    setTimeout(() => {
      setLocations(locations);
      setIsLoading(false);
    }, 500);
  };

  // 예제 3: 외부 GeoJSON API에서 데이터 로드
  const loadGeoJSON = async () => {
    setIsLoading(true);
    setError("");

    try {
      // 공개 GeoJSON API 예제 (실제로는 다른 API를 사용할 수 있습니다)
      const response = await fetch(
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
      );
      const data = await response.json();

      // GeoJSON Feature를 맵 데이터로 변환
      const earthquakes = data.features
        .slice(0, 100) // 최대 100개만
        .map((feature: any) => ({
          position: [
            feature.geometry.coordinates[0],
            feature.geometry.coordinates[1],
          ],
          radius: feature.properties.mag * 50, // 진도에 따른 크기
          color: [255, 0, 0, 150],
          name: `진도 ${feature.properties.mag} - ${feature.properties.place}`,
          magnitude: feature.properties.mag,
        }));

      setLocations(earthquakes);
      setIsLoading(false);
    } catch (err) {
      setError("데이터를 불러오는데 실패했습니다.");
      setIsLoading(false);
    }
  };

  // 예제 4: 실시간 시뮬레이션 (WebSocket 대신 interval 사용)
  const [simulationInterval, setSimulationInterval] = useState<NodeJS.Timeout | null>(null);

  const startRealtimeSimulation = () => {
    // 기존 시뮬레이션 중지
    if (simulationInterval) {
      clearInterval(simulationInterval);
    }

    setError("");
    setIsLoading(true);
    setLocations([]); // 기존 데이터 초기화

    let count = 0;
    const interval = setInterval(() => {
      const newLocation = {
        position: [
          126.9780 + (Math.random() - 0.5) * 0.2,
          37.5665 + (Math.random() - 0.5) * 0.2,
        ],
        radius: 150,
        color: [0, 255, 0, 200],
        name: `실시간 데이터 ${count++}`,
        timestamp: new Date().toLocaleTimeString(),
      };

      setLocations(prev => [...prev.slice(-30), newLocation]); // 최근 30개만 유지

      if (count >= 50) {
        clearInterval(interval);
        setSimulationInterval(null);
        setIsLoading(false);
      }
    }, 1000); // 1초로 늘려서 부하 감소

    setSimulationInterval(interval);
  };

  // 컴포넌트 언마운트 시 interval 정리
  useEffect(() => {
    return () => {
      if (simulationInterval) {
        clearInterval(simulationInterval);
      }
    };
  }, [simulationInterval]);

  const mapConfig = {
    initialViewState: {
      longitude: 126.9780,
      latitude: 37.5665,
      zoom: 11,
    },
    layers: locations.length > 0 ? [
      {
        type: "scatterplot" as const,
        data: locations,
      },
    ] : [],
    tooltip: true,
  };

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">API 연동 맵</h1>
        <p className="text-muted-foreground">
          외부 API나 실시간 데이터를 지도에 표시합니다.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 왼쪽: 컨트롤 */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>데이터 소스</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button
                onClick={loadRandomLocations}
                className="w-full"
                disabled={isLoading}
              >
                랜덤 위치 생성
              </Button>
              <Button
                onClick={loadSeoulPOI}
                className="w-full"
                disabled={isLoading}
                variant="secondary"
              >
                서울 관광지
              </Button>
              <Button
                onClick={loadGeoJSON}
                className="w-full"
                disabled={isLoading}
                variant="secondary"
              >
                지진 데이터 (USGS)
              </Button>
              <Button
                onClick={startRealtimeSimulation}
                className="w-full"
                disabled={isLoading}
                variant="outline"
              >
                실시간 시뮬레이션
              </Button>
              <Button
                onClick={() => setLocations([])}
                className="w-full"
                disabled={locations.length === 0}
                variant="destructive"
              >
                지우기
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>상태</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                <p>
                  <span className="font-semibold">데이터 포인트:</span>{" "}
                  {locations.length}개
                </p>
                <p>
                  <span className="font-semibold">상태:</span>{" "}
                  {isLoading ? "로딩 중..." : "준비됨"}
                </p>
                {error && (
                  <p className="text-red-500 text-xs">{error}</p>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>API 예제</CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              <p className="mb-2">연동 가능한 API:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>서울 열린데이터 광장</li>
                <li>공공데이터 포털</li>
                <li>카카오 로컬 API</li>
                <li>네이버 지도 API</li>
                <li>Google Places API</li>
                <li>OpenStreetMap API</li>
              </ul>
            </CardContent>
          </Card>
        </div>

        {/* 오른쪽: 맵 */}
        <div className="lg:col-span-3">
          {isLoading && locations.length === 0 ? (
            <Card className="h-[600px] flex items-center justify-center">
              <CardContent>
                <p className="text-muted-foreground">데이터 로딩 중...</p>
              </CardContent>
            </Card>
          ) : locations.length === 0 ? (
            <Card className="h-[600px] flex items-center justify-center">
              <CardContent className="text-center">
                <p className="text-muted-foreground">
                  왼쪽에서 데이터 소스를 선택하세요.
                </p>
              </CardContent>
            </Card>
          ) : (
            <MapRenderer config={mapConfig} className="h-[600px]" />
          )}
        </div>
      </div>

      {/* 사용 예제 코드 */}
      <Card>
        <CardHeader>
          <CardTitle>코드 예제: 실제 API 연동</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-xs">
{`// 예: 서울시 공공 와이파이 위치 API
const loadWifiLocations = async () => {
  const response = await fetch(
    'http://openapi.seoul.go.kr:8088/[API_KEY]/json/TbPublicWifiInfo/1/1000/'
  );
  const data = await response.json();

  const locations = data.TbPublicWifiInfo.row.map(item => ({
    position: [
      parseFloat(item.LNG),
      parseFloat(item.LAT)
    ],
    radius: 100,
    color: [0, 150, 255, 180],
    name: item.INST_NM
  }));

  setLocations(locations);
};

// 예: 카카오 로컬 API (장소 검색)
const searchPlaces = async (keyword) => {
  const response = await fetch(
    \`https://dapi.kakao.com/v2/local/search/keyword.json?query=\${keyword}\`,
    {
      headers: {
        'Authorization': 'KakaoAK [YOUR_API_KEY]'
      }
    }
  );
  const data = await response.json();

  const locations = data.documents.map(place => ({
    position: [parseFloat(place.x), parseFloat(place.y)],
    radius: 150,
    name: place.place_name,
    address: place.address_name
  }));

  setLocations(locations);
};`}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}
