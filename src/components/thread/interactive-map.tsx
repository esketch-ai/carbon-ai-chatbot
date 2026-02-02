"use client";

import { useState } from "react";
import dynamic from "next/dynamic";

const MapRenderer = dynamic(
  () => import("./map-renderer").then((mod) => mod.MapRenderer),
  { ssr: false }
);
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface Location {
  longitude: number;
  latitude: number;
  radius?: number;
  name?: string;
  color?: [number, number, number, number];
}

export function InteractiveMap() {
  const [locations, setLocations] = useState<Location[]>([]);
  const [centerLng, setCenterLng] = useState(126.9780);
  const [centerLat, setCenterLat] = useState(37.5665);
  const [zoom, setZoom] = useState(11);

  // 새 포인트 추가 폼
  const [newLng, setNewLng] = useState("");
  const [newLat, setNewLat] = useState("");
  const [newName, setNewName] = useState("");
  const [newRadius, setNewRadius] = useState("200");

  // JSON 입력
  const [jsonInput, setJsonInput] = useState("");
  const [jsonError, setJsonError] = useState("");

  // 파일 업로드
  const [fileError, setFileError] = useState("");

  // 포인트 추가
  const addLocation = () => {
    const lng = parseFloat(newLng);
    const lat = parseFloat(newLat);
    const radius = parseFloat(newRadius);

    if (isNaN(lng) || isNaN(lat)) {
      alert("경도와 위도를 올바르게 입력해주세요.");
      return;
    }

    const newLocation: Location = {
      longitude: lng,
      latitude: lat,
      radius: isNaN(radius) ? 200 : radius,
      name: newName || `위치 ${locations.length + 1}`,
      color: [
        Math.floor(Math.random() * 255),
        Math.floor(Math.random() * 255),
        Math.floor(Math.random() * 255),
        200,
      ],
    };

    setLocations([...locations, newLocation]);
    setNewLng("");
    setNewLat("");
    setNewName("");
    setNewRadius("200");
  };

  // JSON에서 데이터 로드
  const loadFromJSON = () => {
    try {
      const data = JSON.parse(jsonInput);

      // 배열인지 확인
      if (!Array.isArray(data)) {
        throw new Error("데이터는 배열 형식이어야 합니다.");
      }

      // 각 항목에 longitude, latitude가 있는지 확인
      const validData = data.map((item, index) => {
        const lng = item.longitude ?? item.lng ?? item.lon;
        const lat = item.latitude ?? item.lat;

        if (lng === undefined || lat === undefined) {
          throw new Error(`${index + 1}번째 항목에 경도/위도가 없습니다.`);
        }

        return {
          longitude: parseFloat(lng),
          latitude: parseFloat(lat),
          radius: item.radius ?? 200,
          name: item.name ?? `위치 ${index + 1}`,
          color: item.color ?? [
            Math.floor(Math.random() * 255),
            Math.floor(Math.random() * 255),
            Math.floor(Math.random() * 255),
            200,
          ],
        };
      });

      setLocations(validData);
      setJsonError("");
      setJsonInput("");
    } catch (err) {
      setJsonError(err instanceof Error ? err.message : "JSON 파싱 오류");
    }
  };

  // 파일 업로드
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      let data;

      if (file.name.endsWith(".json") || file.name.endsWith(".geojson")) {
        data = JSON.parse(text);

        // GeoJSON Feature Collection 처리
        if (data.type === "FeatureCollection" && data.features) {
          const points = data.features
            .filter((f: any) => f.geometry.type === "Point")
            .map((f: any, index: number) => ({
              longitude: f.geometry.coordinates[0],
              latitude: f.geometry.coordinates[1],
              radius: f.properties?.radius ?? 200,
              name: f.properties?.name ?? `위치 ${index + 1}`,
              color: f.properties?.color ?? [
                Math.floor(Math.random() * 255),
                Math.floor(Math.random() * 255),
                Math.floor(Math.random() * 255),
                200,
              ],
            }));
          setLocations(points);
        } else if (Array.isArray(data)) {
          // 일반 JSON 배열
          setJsonInput(text);
          loadFromJSON();
        }
      } else if (file.name.endsWith(".csv")) {
        // CSV 파싱
        const lines = text.split("\n");
        const headers = lines[0].toLowerCase().split(",").map(h => h.trim());

        const lngIndex = headers.findIndex(h =>
          h.includes("lng") || h.includes("lon") || h.includes("경도")
        );
        const latIndex = headers.findIndex(h =>
          h.includes("lat") || h.includes("위도")
        );
        const nameIndex = headers.findIndex(h =>
          h.includes("name") || h.includes("이름")
        );

        if (lngIndex === -1 || latIndex === -1) {
          throw new Error("CSV에 경도/위도 열이 없습니다.");
        }

        const points = lines.slice(1)
          .filter(line => line.trim())
          .map((line, index) => {
            const cols = line.split(",").map(c => c.trim());
            return {
              longitude: parseFloat(cols[lngIndex]),
              latitude: parseFloat(cols[latIndex]),
              radius: 200,
              name: nameIndex !== -1 ? cols[nameIndex] : `위치 ${index + 1}`,
              color: [
                Math.floor(Math.random() * 255),
                Math.floor(Math.random() * 255),
                Math.floor(Math.random() * 255),
                200,
              ] as [number, number, number, number],
            };
          });

        setLocations(points);
      }

      setFileError("");
    } catch (err) {
      setFileError(err instanceof Error ? err.message : "파일 로드 오류");
    }
  };

  // 외부 API에서 데이터 가져오기 (예: 공공데이터)
  const loadFromAPI = async () => {
    try {
      // 예제: 서울 열린데이터 광장 - 서울시 공공와이파이 위치
      // 실제로는 API 키가 필요합니다
      const response = await fetch(
        "/api/map-data" // 백엔드 API 엔드포인트
      );
      const data = await response.json();
      setLocations(data);
    } catch (err) {
      alert("API에서 데이터를 가져오는데 실패했습니다.");
    }
  };

  // 맵 설정 생성
  const mapConfig = {
    initialViewState: {
      longitude: centerLng,
      latitude: centerLat,
      zoom: zoom,
    },
    layers: locations.length > 0 ? [
      {
        type: "scatterplot" as const,
        data: locations.map(loc => ({
          position: [loc.longitude, loc.latitude],
          radius: loc.radius ?? 200,
          color: loc.color,
          name: loc.name,
        })),
      },
    ] : [],
    tooltip: true,
  };

  // 데이터 내보내기
  const exportData = () => {
    const dataStr = JSON.stringify(locations, null, 2);
    const blob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "map-data.json";
    a.click();
  };

  // GeoJSON 포맷으로 내보내기
  const exportGeoJSON = () => {
    const geojson = {
      type: "FeatureCollection",
      features: locations.map(loc => ({
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [loc.longitude, loc.latitude],
        },
        properties: {
          name: loc.name,
          radius: loc.radius,
          color: loc.color,
        },
      })),
    };

    const blob = new Blob([JSON.stringify(geojson, null, 2)], {
      type: "application/geo+json"
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "map-data.geojson";
    a.click();
  };

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">인터랙티브 맵 에디터</h1>
        <p className="text-muted-foreground">
          실시간으로 데이터를 추가하고 지도에서 시각화하세요.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 왼쪽: 컨트롤 패널 */}
        <div className="lg:col-span-1 space-y-4">
          {/* 맵 중심 설정 */}
          <Card>
            <CardHeader>
              <CardTitle>맵 설정</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <Label>중심 경도</Label>
                <Input
                  type="number"
                  step="0.0001"
                  value={centerLng}
                  onChange={(e) => setCenterLng(parseFloat(e.target.value))}
                />
              </div>
              <div>
                <Label>중심 위도</Label>
                <Input
                  type="number"
                  step="0.0001"
                  value={centerLat}
                  onChange={(e) => setCenterLat(parseFloat(e.target.value))}
                />
              </div>
              <div>
                <Label>줌 레벨</Label>
                <Input
                  type="number"
                  min="0"
                  max="20"
                  value={zoom}
                  onChange={(e) => setZoom(parseInt(e.target.value))}
                />
              </div>
            </CardContent>
          </Card>

          {/* 포인트 추가 */}
          <Card>
            <CardHeader>
              <CardTitle>포인트 추가</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <Label>경도 (Longitude)</Label>
                <Input
                  type="number"
                  step="0.0001"
                  placeholder="126.9780"
                  value={newLng}
                  onChange={(e) => setNewLng(e.target.value)}
                />
              </div>
              <div>
                <Label>위도 (Latitude)</Label>
                <Input
                  type="number"
                  step="0.0001"
                  placeholder="37.5665"
                  value={newLat}
                  onChange={(e) => setNewLat(e.target.value)}
                />
              </div>
              <div>
                <Label>이름 (선택)</Label>
                <Input
                  placeholder="서울시청"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                />
              </div>
              <div>
                <Label>반지름 (미터)</Label>
                <Input
                  type="number"
                  placeholder="200"
                  value={newRadius}
                  onChange={(e) => setNewRadius(e.target.value)}
                />
              </div>
              <Button onClick={addLocation} className="w-full">
                포인트 추가
              </Button>
            </CardContent>
          </Card>

          {/* JSON 입력 */}
          <Card>
            <CardHeader>
              <CardTitle>JSON 데이터 입력</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Textarea
                placeholder={`[\n  {\n    "longitude": 126.9780,\n    "latitude": 37.5665,\n    "name": "서울시청"\n  }\n]`}
                rows={8}
                value={jsonInput}
                onChange={(e) => setJsonInput(e.target.value)}
                className="font-mono text-xs"
              />
              {jsonError && (
                <p className="text-sm text-red-500">{jsonError}</p>
              )}
              <Button onClick={loadFromJSON} className="w-full" variant="secondary">
                JSON 로드
              </Button>
            </CardContent>
          </Card>

          {/* 파일 업로드 */}
          <Card>
            <CardHeader>
              <CardTitle>파일 업로드</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input
                type="file"
                accept=".json,.geojson,.csv"
                onChange={handleFileUpload}
              />
              <p className="text-xs text-muted-foreground">
                JSON, GeoJSON, CSV 파일 지원
              </p>
              {fileError && (
                <p className="text-sm text-red-500">{fileError}</p>
              )}
            </CardContent>
          </Card>

          {/* 데이터 내보내기 */}
          <Card>
            <CardHeader>
              <CardTitle>데이터 관리</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button
                onClick={exportData}
                className="w-full"
                variant="outline"
                disabled={locations.length === 0}
              >
                JSON 내보내기
              </Button>
              <Button
                onClick={exportGeoJSON}
                className="w-full"
                variant="outline"
                disabled={locations.length === 0}
              >
                GeoJSON 내보내기
              </Button>
              <Button
                onClick={() => setLocations([])}
                className="w-full"
                variant="destructive"
                disabled={locations.length === 0}
              >
                모두 지우기
              </Button>
              <p className="text-xs text-muted-foreground pt-2">
                현재 {locations.length}개의 포인트
              </p>
            </CardContent>
          </Card>
        </div>

        {/* 오른쪽: 맵 */}
        <div className="lg:col-span-2">
          {locations.length === 0 ? (
            <Card className="h-[500px] flex items-center justify-center">
              <CardContent className="text-center">
                <p className="text-muted-foreground">
                  왼쪽에서 데이터를 추가하면 지도에 표시됩니다.
                </p>
              </CardContent>
            </Card>
          ) : (
            <MapRenderer config={mapConfig} />
          )}
        </div>
      </div>
    </div>
  );
}
