"use client";

import React, { useState, useEffect } from "react";
import { FloatingChat } from "@/components/floating-chat";
import { ChatConfig } from "@/lib/config";

interface HomePageProps {
  initialConfig: ChatConfig;
}

export function HomePage({ initialConfig }: HomePageProps) {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [splineLoaded, setSplineLoaded] = useState(false);

  // Spline 스크립트 동적 로드
  useEffect(() => {
    const existingScript = document.querySelector('script[src*="splinetool/viewer"]');

    if (existingScript) {
      setSplineLoaded(true);
      return;
    }

    const script = document.createElement("script");
    script.type = "module";
    script.src = "https://unpkg.com/@splinetool/viewer@1.9.48/build/spline-viewer.js";
    script.onload = () => setSplineLoaded(true);
    document.head.appendChild(script);
  }, []);

  const handleStartClick = () => {
    if (!isChatOpen) {
      setIsChatOpen(true);
    }
  };

  return (
    <div className="relative w-full h-screen overflow-hidden">
      {/* Spline 3D 배경 - 인터랙티브 */}
      <div className="absolute inset-0 z-0">
        {!splineLoaded ? (
          <div className="w-full h-full bg-gradient-to-br from-slate-900 via-teal-900 to-emerald-900 flex items-center justify-center">
            <div className="text-white/60 text-lg animate-pulse">Loading 3D Scene...</div>
          </div>
        ) : (
          // @ts-expect-error - spline-viewer is a web component
          <spline-viewer
            url="https://prod.spline.design/2YTWwBKDt94Jth9t/scene.splinecode"
            style={{ width: "100%", height: "100%" }}
          />
        )}
      </div>

      {/* 시작 버튼 - Spline과 별도로 클릭 가능 */}
      {!isChatOpen && (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10 text-center">
          <button
            onClick={handleStartClick}
            className="px-6 py-3 bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/30 rounded-full text-white text-sm font-medium transition-all duration-300 hover:scale-105 cursor-pointer shadow-lg"
          >
            채팅 시작하기
          </button>
        </div>
      )}

      {/* Floating Chat */}
      <FloatingChat
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        initialConfig={initialConfig}
      />
    </div>
  );
}
