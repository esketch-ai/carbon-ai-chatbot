"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";

const Map = dynamic(
  () => import("react-map-gl/maplibre").then((mod) => mod.default),
  { ssr: false }
);

export default function TestMapPage() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div className="p-8">로딩 중...</div>;
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">맵 테스트 (deck.gl 없이)</h1>
      <div className="w-full h-[500px] border rounded-xl overflow-hidden">
        <Map
          initialViewState={{
            longitude: 126.9780,
            latitude: 37.5665,
            zoom: 11,
          }}
          mapStyle="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
        />
      </div>
    </div>
  );
}
