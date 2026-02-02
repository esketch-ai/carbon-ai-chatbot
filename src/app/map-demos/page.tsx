"use client";

import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { MapIcon, Edit3Icon, GlobeIcon, FileTextIcon } from "lucide-react";

export default function MapDemosPage() {
  const demos = [
    {
      title: "예제 갤러리",
      description: "다양한 레이어 타입과 시각화 방법을 미리 만들어진 예제로 확인하세요.",
      href: "/map-examples",
      icon: MapIcon,
      color: "text-blue-500",
      features: ["Scatterplot", "Path", "Hexagon", "GeoJSON"],
    },
    {
      title: "인터랙티브 에디터",
      description: "직접 데이터를 입력하거나 파일을 업로드하여 실시간으로 지도를 편집하세요.",
      href: "/map-editor",
      icon: Edit3Icon,
      color: "text-green-500",
      features: ["수동 입력", "JSON/CSV 업로드", "데이터 내보내기"],
    },
    {
      title: "API 연동",
      description: "외부 API나 실시간 데이터를 지도에 연동하는 방법을 확인하세요.",
      href: "/map-api",
      icon: GlobeIcon,
      color: "text-purple-500",
      features: ["공공 API", "실시간 데이터", "GeoJSON 로드"],
    },
  ];

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* 헤더 */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold tracking-tight">
            GIS 맵 시각화 데모
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
            deck.gl + OpenStreetMap을 활용한 인터랙티브 지도 시각화 플랫폼
          </p>
        </div>

        {/* 데모 카드들 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {demos.map((demo) => {
            const Icon = demo.icon;
            return (
              <Card key={demo.href} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-center gap-3 mb-2">
                    <Icon className={`h-6 w-6 ${demo.color}`} />
                    <CardTitle>{demo.title}</CardTitle>
                  </div>
                  <CardDescription>{demo.description}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex flex-wrap gap-2">
                    {demo.features.map((feature) => (
                      <span
                        key={feature}
                        className="text-xs px-2 py-1 rounded-full bg-muted"
                      >
                        {feature}
                      </span>
                    ))}
                  </div>
                  <Link href={demo.href}>
                    <Button className="w-full">데모 보기</Button>
                  </Link>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* 기능 소개 */}
        <Card>
          <CardHeader>
            <CardTitle>주요 기능</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-3">
                <h3 className="font-semibold">지원하는 레이어 타입</h3>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>✓ <strong>Scatterplot</strong> - 포인트 데이터 시각화</li>
                  <li>✓ <strong>Path</strong> - 경로 및 라인 데이터</li>
                  <li>✓ <strong>Polygon</strong> - 구역 및 영역 표시</li>
                  <li>✓ <strong>Hexagon</strong> - 히트맵 시각화</li>
                  <li>✓ <strong>GeoJSON</strong> - 표준 GIS 데이터</li>
                </ul>
              </div>
              <div className="space-y-3">
                <h3 className="font-semibold">데이터 소스</h3>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>✓ 수동 데이터 입력</li>
                  <li>✓ JSON/CSV/GeoJSON 파일 업로드</li>
                  <li>✓ 외부 API 연동</li>
                  <li>✓ 실시간 데이터 스트림</li>
                  <li>✓ 공공 데이터 포털 연동</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 사용 사례 */}
        <Card>
          <CardHeader>
            <CardTitle>활용 사례</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 border rounded-lg">
                <h4 className="font-semibold mb-2">부동산 분석</h4>
                <p className="text-sm text-muted-foreground">
                  매물 분포, 시세 분석, 인프라 시각화
                </p>
              </div>
              <div className="p-4 border rounded-lg">
                <h4 className="font-semibold mb-2">물류 관리</h4>
                <p className="text-sm text-muted-foreground">
                  배송 경로, 차량 추적, 거점 최적화
                </p>
              </div>
              <div className="p-4 border rounded-lg">
                <h4 className="font-semibold mb-2">도시 계획</h4>
                <p className="text-sm text-muted-foreground">
                  인구 밀도, 교통량, 토지 이용 분석
                </p>
              </div>
              <div className="p-4 border rounded-lg">
                <h4 className="font-semibold mb-2">재난 관리</h4>
                <p className="text-sm text-muted-foreground">
                  재난 위치, 대피소, 구조대 이동
                </p>
              </div>
              <div className="p-4 border rounded-lg">
                <h4 className="font-semibold mb-2">비즈니스 분석</h4>
                <p className="text-sm text-muted-foreground">
                  매장 분포, 상권 분석, 경쟁사 위치
                </p>
              </div>
              <div className="p-4 border rounded-lg">
                <h4 className="font-semibold mb-2">환경 모니터링</h4>
                <p className="text-sm text-muted-foreground">
                  대기질, 수질, 센서 데이터 시각화
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 문서 링크 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileTextIcon className="h-5 w-5" />
              문서 및 가이드
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <h4 className="font-semibold">MapRenderer 사용 가이드</h4>
                <p className="text-sm text-muted-foreground">
                  전체 API 문서 및 사용 예제
                </p>
              </div>
              <Button variant="outline" asChild>
                <a href="/MAP_RENDERER_GUIDE.md" target="_blank">
                  보기
                </a>
              </Button>
            </div>
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <h4 className="font-semibold">deck.gl 공식 문서</h4>
                <p className="text-sm text-muted-foreground">
                  고급 기능 및 레이어 옵션
                </p>
              </div>
              <Button variant="outline" asChild>
                <a href="https://deck.gl/" target="_blank" rel="noopener">
                  보기
                </a>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
