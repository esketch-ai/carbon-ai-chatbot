"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { cn } from "@/lib/utils";
import { safeParseJSON } from "@/lib/json-sanitizer";

const KAKAO_API_KEY = "ac3864d73fb04009cd4bfc502c9c19a4";

// 카카오 지도 스크립트 로드 함수
const loadKakaoMapScript = (): Promise<void> => {
  return new Promise((resolve, reject) => {
    // 이미 로드되었는지 확인
    if (window.kakao && window.kakao.maps) {
      resolve();
      return;
    }

    // 기존 스크립트가 있는지 확인
    const existingScript = document.querySelector(
      'script[src*="dapi.kakao.com"]'
    );

    if (existingScript) {
      existingScript.addEventListener("load", () => {
        if (window.kakao && window.kakao.maps) {
          window.kakao.maps.load(() => resolve());
        } else {
          reject(new Error("카카오 지도 객체를 찾을 수 없습니다."));
        }
      });
      return;
    }

    // 새 스크립트 생성
    const script = document.createElement("script");
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${KAKAO_API_KEY}&autoload=false`;
    script.async = true;
    script.type = "text/javascript";

    script.onload = () => {
      if (window.kakao && window.kakao.maps) {
        window.kakao.maps.load(() => {
          console.log("카카오 지도 로드 완료");
          resolve();
        });
      } else {
        reject(new Error("카카오 지도 객체를 찾을 수 없습니다."));
      }
    };

    script.onerror = () => {
      reject(new Error("카카오 지도 스크립트 로드 실패"));
    };

    document.head.appendChild(script);
  });
};

interface KakaoMapMarker {
  position: {
    lat: number;
    lng: number;
  };
  title?: string;
  content?: string;
  icon?: string;
  color?: string;
}

interface KakaoMapConfig {
  center?: {
    lat: number;
    lng: number;
  };
  zoom?: number;
  markers?: KakaoMapMarker[];
  style?: "default" | "skyview" | "hybrid";
  showControls?: boolean;
}

interface KakaoMapProps {
  config: string | KakaoMapConfig;
  className?: string;
}

// 기본값 - 서울시청
const DEFAULT_CENTER = {
  lat: 37.5665,
  lng: 126.978,
};

const DEFAULT_ZOOM = 13;

export function KakaoMap({ config, className }: KakaoMapProps) {
  const [mapConfig, setMapConfig] = useState<KakaoMapConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isScriptLoaded, setIsScriptLoaded] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [activeMarker, setActiveMarker] = useState<number | null>(null);

  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const overlaysRef = useRef<any[]>([]);

  // 다크모드 감지
  useEffect(() => {
    const checkDarkMode = () => {
      setIsDarkMode(document.documentElement.classList.contains("dark"));
    };

    checkDarkMode();
    const observer = new MutationObserver(checkDarkMode);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });

    return () => observer.disconnect();
  }, []);

  // 카카오 지도 스크립트 로드
  useEffect(() => {
    let isMounted = true;

    loadKakaoMapScript()
      .then(() => {
        if (isMounted) {
          console.log("카카오 지도 스크립트 로드 성공");
          setIsScriptLoaded(true);
        }
      })
      .catch((err) => {
        console.error("카카오 지도 로드 에러:", err);
        if (isMounted) {
          setError(err.message || "카카오 지도를 로드할 수 없습니다.");
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Config 파싱
  useEffect(() => {
    setIsLoading(true);
    setError(null);

    try {
      let parsedConfig: KakaoMapConfig;

      if (typeof config === "string") {
        const trimmed = config.trim();
        if (!trimmed) {
          throw new Error("지도 설정이 비어있습니다.");
        }

        const { data, error: parseError } = safeParseJSON<KakaoMapConfig>(trimmed);
        if (!data || parseError) {
          throw new Error(parseError || "지도 JSON을 파싱할 수 없습니다.");
        }
        parsedConfig = data;
      } else {
        parsedConfig = config;
      }

      setMapConfig(parsedConfig);
      setIsLoading(false);
    } catch (err) {
      console.error("Kakao Map config error:", err);
      setError(err instanceof Error ? err.message : "지도를 렌더링할 수 없습니다.");
      setIsLoading(false);
    }
  }, [config]);

  // 지도 초기화
  const initializeMap = useCallback(() => {
    if (!isScriptLoaded || !mapRef.current || !mapConfig || !window.kakao?.maps) {
      return;
    }

    const { kakao } = window;

    try {
      // 기존 마커 및 오버레이 제거
      markersRef.current.forEach(marker => marker.setMap(null));
      overlaysRef.current.forEach(overlay => overlay.setMap(null));
      markersRef.current = [];
      overlaysRef.current = [];

      const center = mapConfig.center || DEFAULT_CENTER;
      const zoom = mapConfig.zoom || DEFAULT_ZOOM;

      const options = {
        center: new kakao.maps.LatLng(center.lat, center.lng),
        level: zoom,
      };

      const map = new kakao.maps.Map(mapRef.current, options);
      mapInstanceRef.current = map;

      // 지도 타입 설정
      if (mapConfig.style === "skyview") {
        map.setMapTypeId(kakao.maps.MapTypeId.SKYVIEW);
      } else if (mapConfig.style === "hybrid") {
        map.setMapTypeId(kakao.maps.MapTypeId.HYBRID);
      }

      // 컨트롤 추가
      if (mapConfig.showControls !== false) {
        const zoomControl = new kakao.maps.ZoomControl();
        map.addControl(zoomControl, kakao.maps.ControlPosition.RIGHT);

        const mapTypeControl = new kakao.maps.MapTypeControl();
        map.addControl(mapTypeControl, kakao.maps.ControlPosition.TOPRIGHT);
      }

      // 마커 추가
      if (mapConfig.markers && mapConfig.markers.length > 0) {
        mapConfig.markers.forEach((markerConfig, index) => {
          const markerPosition = new kakao.maps.LatLng(
            markerConfig.position.lat,
            markerConfig.position.lng
          );

          // 커스텀 마커 생성
          const markerContent = createMarkerContent(markerConfig, index);

          const customOverlay = new kakao.maps.CustomOverlay({
            position: markerPosition,
            content: markerContent,
            yAnchor: 1.2,
          });

          customOverlay.setMap(map);
          markersRef.current.push(customOverlay);

          // 인포윈도우 (클릭 시)
          if (markerConfig.content || markerConfig.title) {
            const infoContent = createInfoWindow(markerConfig);
            const infoWindow = new kakao.maps.CustomOverlay({
              content: infoContent,
              position: markerPosition,
              yAnchor: 2.3,
            });

            overlaysRef.current.push(infoWindow);

            // 마커 클릭 이벤트
            const markerElement = markerContent.querySelector('.kakao-marker');
            if (markerElement) {
              markerElement.addEventListener('click', () => {
                // 다른 인포윈도우 숨기기
                overlaysRef.current.forEach(overlay => overlay.setMap(null));

                // 현재 인포윈도우 토글
                if (activeMarker === index) {
                  setActiveMarker(null);
                } else {
                  infoWindow.setMap(map);
                  setActiveMarker(index);

                  // 지도 중심을 마커로 이동
                  map.panTo(markerPosition);
                }
              });
            }
          }
        });
      }
    } catch (err) {
      console.error("Kakao Map initialization error:", err);
      setError("지도를 초기화할 수 없습니다.");
    }
  }, [isScriptLoaded, mapConfig, activeMarker]);

  // 스크립트 로드 후 지도 초기화
  useEffect(() => {
    if (isScriptLoaded && mapConfig) {
      initializeMap();
    }
  }, [isScriptLoaded, mapConfig, initializeMap]);

  // 커스텀 마커 HTML 생성
  const createMarkerContent = (marker: KakaoMapMarker, index: number): HTMLDivElement => {
    const container = document.createElement('div');
    container.className = 'kakao-marker-container';

    const color = marker.color || '#6366f1';

    container.innerHTML = `
      <div class="kakao-marker" style="cursor: pointer; transition: all 0.3s ease;">
        <div style="
          position: relative;
          width: 48px;
          height: 48px;
          background: linear-gradient(135deg, ${color} 0%, ${adjustColor(color, -20)} 100%);
          border-radius: 50% 50% 50% 0;
          transform: rotate(-45deg);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15), 0 0 0 3px white;
          display: flex;
          align-items: center;
          justify-content: center;
          animation: markerBounce 0.6s ease-out;
        ">
          <div style="
            transform: rotate(45deg);
            font-size: 20px;
            color: white;
            font-weight: bold;
          ">
            ${marker.icon || '📍'}
          </div>
        </div>
        <div style="
          position: absolute;
          bottom: -8px;
          left: 50%;
          transform: translateX(-50%);
          width: 0;
          height: 0;
          border-left: 6px solid transparent;
          border-right: 6px solid transparent;
          border-top: 8px solid ${color};
          filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
        "></div>
      </div>
    `;

    return container;
  };

  // 인포윈도우 HTML 생성
  const createInfoWindow = (marker: KakaoMapMarker): HTMLDivElement => {
    const container = document.createElement('div');
    container.className = 'kakao-infowindow';

    const bgColor = isDarkMode ? '#18181b' : '#ffffff';
    const textColor = isDarkMode ? '#f4f4f5' : '#18181b';
    const borderColor = isDarkMode ? '#3f3f46' : '#e4e4e7';

    container.innerHTML = `
      <div style="
        background: ${bgColor};
        backdrop-filter: blur(10px);
        padding: 16px 20px;
        border-radius: 16px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15), 0 0 0 1px ${borderColor};
        min-width: 200px;
        max-width: 320px;
        animation: infoWindowSlide 0.3s ease-out;
      ">
        ${marker.title ? `
          <div style="
            font-size: 16px;
            font-weight: 600;
            color: ${textColor};
            margin-bottom: ${marker.content ? '8px' : '0'};
            line-height: 1.4;
          ">
            ${marker.title}
          </div>
        ` : ''}
        ${marker.content ? `
          <div style="
            font-size: 14px;
            color: ${isDarkMode ? '#a1a1aa' : '#71717a'};
            line-height: 1.6;
          ">
            ${marker.content}
          </div>
        ` : ''}
        <div style="
          position: absolute;
          bottom: -8px;
          left: 50%;
          transform: translateX(-50%);
          width: 0;
          height: 0;
          border-left: 10px solid transparent;
          border-right: 10px solid transparent;
          border-top: 10px solid ${bgColor};
          filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
        "></div>
      </div>
    `;

    return container;
  };

  // 색상 조정 헬퍼
  const adjustColor = (hex: string, amount: number): string => {
    const num = parseInt(hex.replace('#', ''), 16);
    const r = Math.max(0, Math.min(255, (num >> 16) + amount));
    const g = Math.max(0, Math.min(255, ((num >> 8) & 0x00FF) + amount));
    const b = Math.max(0, Math.min(255, (num & 0x0000FF) + amount));
    return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
  };

  if (error) {
    return (
      <div
        className={cn(
          "rounded-2xl bg-gradient-to-br from-red-50/50 to-red-100/50",
          "dark:from-red-950/20 dark:to-red-900/20",
          "backdrop-blur-sm p-6 border border-red-200/50 dark:border-red-800/30",
          "shadow-sm",
          className
        )}
      >
        <div className="flex items-start gap-3">
          <svg
            className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <div className="flex-1">
            <p className="text-sm font-medium text-red-600 dark:text-red-400">
              지도 오류
            </p>
            <p className="text-sm text-red-600/90 dark:text-red-400/90 mt-1">
              {error}
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!isScriptLoaded) {
    return (
      <div
        className={cn(
          "rounded-2xl bg-gradient-to-br from-muted/30 to-muted/50",
          "dark:from-zinc-900/50 dark:to-zinc-800/50",
          "backdrop-blur-sm p-6 border border-border/40 dark:border-zinc-700/50",
          "min-h-[500px]",
          className
        )}
      >
        <div className="h-full flex flex-col items-center justify-center gap-3 text-center">
          <svg
            className="animate-spin h-8 w-8 text-primary"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <div>
            <p className="text-sm font-medium text-foreground">카카오 지도 로드 중...</p>
            <p className="text-xs text-muted-foreground mt-1">지도 스크립트를 불러오고 있습니다</p>
          </div>
        </div>
      </div>
    );
  }

  if (isLoading || !mapConfig) {
    return (
      <div
        className={cn(
          "rounded-2xl bg-gradient-to-br from-muted/30 to-muted/50",
          "dark:from-zinc-900/50 dark:to-zinc-800/50",
          "backdrop-blur-sm p-6 border border-border/40 dark:border-zinc-700/50",
          "min-h-[500px]",
          className
        )}
      >
        <div className="h-full flex items-center justify-center gap-2">
          <svg
            className="animate-spin h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <span className="text-sm text-muted-foreground">지도 설정 중...</span>
        </div>
      </div>
    );
  }

  return (
    <>
      <style jsx global>{`
        @keyframes markerBounce {
          0% {
            transform: rotate(-45deg) translateY(-100px);
            opacity: 0;
          }
          60% {
            transform: rotate(-45deg) translateY(10px);
            opacity: 1;
          }
          80% {
            transform: rotate(-45deg) translateY(-5px);
          }
          100% {
            transform: rotate(-45deg) translateY(0);
          }
        }

        @keyframes infoWindowSlide {
          from {
            transform: translateY(-10px);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }

        .kakao-marker:hover {
          transform: scale(1.1) !important;
        }
      `}</style>

      <div
        className={cn(
          "kakao-map-container",
          "rounded-2xl overflow-hidden",
          "border border-border/50 dark:border-zinc-700/50",
          "shadow-lg",
          "transition-all duration-300",
          className
        )}
      >
        <div
          ref={mapRef}
          className="w-full h-[500px]"
          style={{
            background: isDarkMode
              ? "linear-gradient(135deg, #18181b 0%, #27272a 100%)"
              : "linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)",
          }}
        />
      </div>
    </>
  );
}
