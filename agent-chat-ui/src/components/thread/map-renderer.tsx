"use client";

import { useEffect, useState, useMemo, useRef, useCallback } from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import { DeckLayer } from "@deck.gl-community/leaflet";
import { ScatterplotLayer, PathLayer, PolygonLayer, GeoJsonLayer } from "@deck.gl/layers";
import { HexagonLayer } from "@deck.gl/aggregation-layers";
import type { Layer } from "@deck.gl/core";
import { cn } from "@/lib/utils";
import "leaflet/dist/leaflet.css";

// 전역 활성 맵 관리 
const activeMapInstances = new Set<string>();
const MAX_ACTIVE_MAPS = 8; // Leaflet은 WebGL을 1개만 사용하므로 더 많이 허용
// map libre -> deck.gl + leaflet 으로 변경
const registerMap = (id: string): boolean => {
  if (activeMapInstances.size >= MAX_ACTIVE_MAPS && !activeMapInstances.has(id)) {
    return false;
  }
  activeMapInstances.add(id);
  return true;
};

const unregisterMap = (id: string) => {
  activeMapInstances.delete(id);
};

interface MapConfig {
  initialViewState?: {
    longitude?: number;
    latitude?: number;
    zoom?: number;
    pitch?: number;
    bearing?: number;
  };
  layers?: Array<{
    type: "scatterplot" | "path" | "polygon" | "hexagon" | "geojson";
    data: any;
    [key: string]: any;
  }>;
  style?: string;
  tooltip?: boolean;
}

interface MapRendererProps {
  config: string | MapConfig;
  className?: string;
}

// 기본은 서울 중심 좌표
const DEFAULT_VIEW_STATE = {
  longitude: 126.9780,
  latitude: 37.5665,
  zoom: 11,
  pitch: 0,
  bearing: 0,
};

// Carto 래스터 타일 (Leaflet 호환)
const LIGHT_TILE_URL = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";
const DARK_TILE_URL = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";

// 개선된 색상 팔레트
const COLOR_PALETTES = {
  light: {
    scatterplot: [59, 130, 246, 200],
    path: [239, 68, 68, 200],
    polygon: [34, 197, 94, 150],
    hexagon: [168, 85, 247, 180],
    geojson: [249, 115, 22, 180],
  },
  dark: {
    scatterplot: [96, 165, 250, 220],
    path: [248, 113, 113, 220],
    polygon: [74, 222, 128, 170],
    hexagon: [196, 181, 253, 200],
    geojson: [251, 146, 60, 200],
  },
};

// DeckGL 레이어를 Leaflet에 통합하는 컴포넌트
function DeckGLOverlay({
  layers,
  onHover,
  mapLoaded
}: {
  layers: Layer[];
  onHover: (info: any) => void;
  mapLoaded: boolean;
}) {
  const map = useMap();
  const deckLayerRef = useRef<any>(null);

  useEffect(() => {
    if (!mapLoaded || !map) return;

    // DeckLayer 생성
    const deckLayer = new DeckLayer({
      layers: layers,
      onHover: onHover,
      getTooltip: () => null,
      _typedArrayManagerProps: {
        overAlloc: 1,
        poolSize: 0
      }
    });

    deckLayerRef.current = deckLayer;
    deckLayer.addTo(map);

    return () => {
      if (deckLayerRef.current) {
        map.removeLayer(deckLayerRef.current);
        deckLayerRef.current = null;
      }
    };
  }, [layers, onHover, mapLoaded, map]);

  return null;
}

// 맵 컨트롤 버튼 컴포넌트
function MapControls({
  onZoomIn,
  onZoomOut,
  onResetView,
  onToggleLegend
}: {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetView: () => void;
  onToggleLegend: () => void;
}) {
  const map = useMap();

  useEffect(() => {
    // 맵 인스턴스를 통해 줌 제어
    const handleZoomIn = () => map.zoomIn();
    const handleZoomOut = () => map.zoomOut();

    return () => {};
  }, [map]);

  return (
    <div className="leaflet-top leaflet-right" style={{ top: '10px', right: '10px' }}>
      <div className="leaflet-control flex flex-col gap-2">
        <button
          onClick={() => map.zoomIn()}
          className="bg-white dark:bg-zinc-800 hover:bg-gray-100 dark:hover:bg-zinc-700 p-2 rounded-lg shadow-lg border border-border/50 dark:border-zinc-700/50 transition-colors"
          title="Zoom In"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        </button>
        <button
          onClick={() => map.zoomOut()}
          className="bg-white dark:bg-zinc-800 hover:bg-gray-100 dark:hover:bg-zinc-700 p-2 rounded-lg shadow-lg border border-border/50 dark:border-zinc-700/50 transition-colors"
          title="Zoom Out"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
          </svg>
        </button>
        <button
          onClick={onResetView}
          className="bg-white dark:bg-zinc-800 hover:bg-gray-100 dark:hover:bg-zinc-700 p-2 rounded-lg shadow-lg border border-border/50 dark:border-zinc-700/50 transition-colors"
          title="Reset View"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
        </button>
        <button
          onClick={onToggleLegend}
          className="bg-white dark:bg-zinc-800 hover:bg-gray-100 dark:hover:bg-zinc-700 p-2 rounded-lg shadow-lg border border-border/50 dark:border-zinc-700/50 transition-colors"
          title="Toggle Legend"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>
    </div>
  );
}

// 뷰 리셋 핸들러
function ViewResetHandler({
  resetTrigger,
  initialViewState
}: {
  resetTrigger: number;
  initialViewState: any;
}) {
  const map = useMap();

  useEffect(() => {
    if (resetTrigger > 0) {
      map.setView(
        [initialViewState.latitude, initialViewState.longitude],
        initialViewState.zoom
      );
    }
  }, [resetTrigger, initialViewState, map]);

  return null;
}

export function MapRenderer({ config, className }: MapRendererProps) {
  const [mapConfig, setMapConfig] = useState<MapConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hoveredObject, setHoveredObject] = useState<any>(null);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [dataSamplingInfo, setDataSamplingInfo] = useState<{
    original: number;
    sampled: number;
  } | null>(null);
  const [layersVisible, setLayersVisible] = useState<boolean[]>([]);
  const [showLegend, setShowLegend] = useState(true);
  const [isInView, setIsInView] = useState(false);
  const [canActivate, setCanActivate] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [resetTrigger, setResetTrigger] = useState(0);

  const containerRef = useRef<HTMLDivElement>(null);
  const instanceId = useRef(`map-${Math.random().toString(36).substr(2, 9)}`).current;

  // Intersection Observer
  useEffect(() => {
    if (!containerRef.current) return;

    let retryInterval: NodeJS.Timeout | null = null;
    let retryTimeout: NodeJS.Timeout | null = null;
    let initialCheckDone = false;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const isVisible = entry.isIntersecting;

          if (isVisible) {
            setIsInView(true);
            const activationDelay = initialCheckDone ? 0 : Math.random() * 300;

            setTimeout(() => {
              const canRegister = registerMap(instanceId);

              if (canRegister) {
                setCanActivate(true);
                requestAnimationFrame(() => {
                  setIsReady(true);
                });
              } else {
                setCanActivate(false);
                setIsReady(true);

                retryInterval = setInterval(() => {
                  const retry = registerMap(instanceId);
                  if (retry) {
                    setCanActivate(true);
                    requestAnimationFrame(() => {
                      setIsReady(true);
                    });
                    if (retryInterval) clearInterval(retryInterval);
                  }
                }, 500);

                retryTimeout = setTimeout(() => {
                  if (retryInterval) clearInterval(retryInterval);
                }, 5000);
              }
            }, activationDelay);

            initialCheckDone = true;
          } else {
            setIsInView(false);
            unregisterMap(instanceId);
            setCanActivate(false);
            setIsReady(true);

            if (retryInterval) clearInterval(retryInterval);
            if (retryTimeout) clearTimeout(retryTimeout);
          }
        });
      },
      {
        rootMargin: '50px',
        threshold: 0.1,
      }
    );

    const startDelay = setTimeout(() => {
      if (containerRef.current) {
        observer.observe(containerRef.current);
      }
    }, 50);

    return () => {
      clearTimeout(startDelay);
      observer.disconnect();
      unregisterMap(instanceId);
      if (retryInterval) clearInterval(retryInterval);
      if (retryTimeout) clearTimeout(retryTimeout);
    };
  }, [instanceId]);

  // 클라이언트 마운트
  useEffect(() => {
    setIsMounted(true);
  }, []);

  // 다크 모드 감지
  useEffect(() => {
    const checkDarkMode = () => {
      const isDark = document.documentElement.classList.contains("dark");
      setIsDarkMode(isDark);
    };

    checkDarkMode();
    const observer = new MutationObserver(checkDarkMode);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });

    return () => observer.disconnect();
  }, []);

  // Config 파싱
  useEffect(() => {
    setIsLoading(true);
    setError(null);
    setMapConfig(null);
    setMapLoaded(false);

    try {
      let parsedConfig: MapConfig;

      if (typeof config === "string") {
        parsedConfig = JSON.parse(config);
      } else {
        parsedConfig = config;
      }

      setMapConfig(parsedConfig);
      if (parsedConfig.layers) {
        setLayersVisible(new Array(parsedConfig.layers.length).fill(true));
      }
      setIsLoading(false);
    } catch (err) {
      console.error("Map config parsing error:", err);
      setError(err instanceof Error ? err.message : "맵을 렌더링할 수 없습니다.");
      setIsLoading(false);
    }
  }, [config]);

  // 데이터 샘플링
  const sampleData = (data: any[], maxPoints: number = 5000) => {
    if (!Array.isArray(data) || data.length <= maxPoints) return data;
    const step = Math.ceil(data.length / maxPoints);
    return data.filter((_, i) => i % step === 0);
  };

  // DeckGL 레이어 생성
  const layers: Layer[] = useMemo(() => {
    if (!mapConfig?.layers) return [];

    let totalOriginal = 0;
    let totalSampled = 0;

    const palette = isDarkMode ? COLOR_PALETTES.dark : COLOR_PALETTES.light;

    const createdLayers = mapConfig.layers.map((layerConfig, index) => {
      if (!layersVisible[index]) return null;

      const { type, data, ...otherProps } = layerConfig;

      const originalCount = Array.isArray(data) ? data.length : 0;
      totalOriginal += originalCount;

      const sampledData = sampleData(data);
      const sampledCount = Array.isArray(sampledData) ? sampledData.length : 0;
      totalSampled += sampledCount;

      const commonProps = {
        id: `layer-${index}`,
        data: sampledData,
        pickable: true,
        ...otherProps,
      };

      switch (type) {
        case "scatterplot":
          return new ScatterplotLayer({
            ...commonProps,
            getPosition: (d: any) => d.position || [d.longitude, d.latitude],
            getRadius: (d: any) => d.radius || 100,
            getFillColor: (d: any) => d.color || palette.scatterplot,
            radiusMinPixels: layerConfig.radiusMinPixels || 5,
            radiusMaxPixels: layerConfig.radiusMaxPixels || 30,
          });

        case "path":
          return new PathLayer({
            ...commonProps,
            getPath: (d: any) => d.path,
            getColor: (d: any) => d.color || palette.path,
            getWidth: (d: any) => d.width || 5,
            widthMinPixels: layerConfig.widthMinPixels || 2,
          });

        case "polygon":
          return new PolygonLayer({
            ...commonProps,
            getPolygon: (d: any) => d.polygon,
            getFillColor: (d: any) => d.fillColor || palette.polygon,
            getLineColor: (d: any) => d.lineColor || (isDarkMode ? [255, 255, 255, 100] : [0, 0, 0, 100]),
            getLineWidth: layerConfig.lineWidth || 1,
            filled: true,
            extruded: layerConfig.extruded || false,
            getElevation: (d: any) => d.elevation || 0,
          });

        case "hexagon":
          return new HexagonLayer({
            ...commonProps,
            getPosition: (d: any) => d.position || [d.longitude, d.latitude],
            getColorWeight: (d: any) => d.weight || 1,
            getElevationWeight: (d: any) => d.weight || 1,
            colorAggregation: 'SUM',
            elevationAggregation: 'SUM',
            elevationScale: layerConfig.elevationScale || 10,
            radius: layerConfig.radius || 500,
            coverage: layerConfig.coverage || 0.8,
            extruded: layerConfig.extruded !== undefined ? layerConfig.extruded : true,
          });

        case "geojson":
          return new GeoJsonLayer({
            ...commonProps,
            filled: true,
            stroked: true,
            getFillColor: (d: any) => d.properties?.fillColor || palette.geojson,
            getLineColor: (d: any) => d.properties?.lineColor || (isDarkMode ? [255, 255, 255, 100] : [0, 0, 0, 100]),
            getLineWidth: layerConfig.lineWidth || 1,
            pointRadiusMinPixels: 3,
            pointRadiusMaxPixels: 10,
          });

        default:
          return null;
      }
    }).filter(Boolean) as Layer[];

    if (totalOriginal > totalSampled) {
      setDataSamplingInfo({ original: totalOriginal, sampled: totalSampled });
    } else {
      setDataSamplingInfo(null);
    }

    return createdLayers;
  }, [mapConfig, isDarkMode, layersVisible]);

  const handleHover = useCallback((info: any) => {
    setHoveredObject(info.object);
  }, []);

  const handleResetView = useCallback(() => {
    setResetTrigger(prev => prev + 1);
  }, []);

  const toggleLayer = useCallback((index: number) => {
    setLayersVisible(prev => {
      const newVisible = [...prev];
      newVisible[index] = !newVisible[index];
      return newVisible;
    });
  }, []);

  const formatTooltipData = useCallback((obj: any) => {
    if (!obj) return null;
    const entries = Object.entries(obj).filter(([key]) =>
      !key.startsWith('_') && key !== 'index'
    );
    if (entries.length === 0) return null;
    return entries.slice(0, 8);
  }, []);

  const tileUrl = useMemo(() =>
    isDarkMode ? DARK_TILE_URL : LIGHT_TILE_URL,
    [isDarkMode]
  );

  const initialViewState = useMemo(() => ({
    ...DEFAULT_VIEW_STATE,
    ...mapConfig?.initialViewState,
  }), [mapConfig?.initialViewState]);

  if (error) {
    return (
      <div
        className={cn(
          "rounded-xl bg-muted/50 dark:bg-zinc-900 p-4 border border-red-500/30",
          className
        )}
      >
        <p className="text-sm text-red-500">오류: {error}</p>
        <pre className="mt-2 text-xs text-muted-foreground overflow-x-auto">
          {typeof config === "string" ? config : JSON.stringify(config, null, 2)}
        </pre>
      </div>
    );
  }

  if (!isMounted || isLoading || !mapConfig) {
    return (
      <div
        ref={containerRef}
        className={cn(
          "rounded-xl bg-muted/50 dark:bg-zinc-900 p-4 border border-border/30 dark:border-zinc-700",
          className
        )}
      >
        <div className="text-center text-sm text-muted-foreground py-4">
          맵 렌더링 중...
        </div>
      </div>
    );
  }

  if (!isReady) {
    return (
      <div
        ref={containerRef}
        className={cn(
          "rounded-xl bg-muted/50 dark:bg-zinc-900 p-4 border border-border/30 dark:border-zinc-700",
          className
        )}
      >
        <div className="relative w-full h-[500px] flex items-center justify-center">
          <div className="text-center">
            <div className="text-sm text-muted-foreground mb-2">
              🗺️ 지도 준비 중...
            </div>
            <div className="text-xs text-muted-foreground/70">
              WebGL 리소스 최적화를 위해 순차적으로 로드됩니다
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!isInView || !canActivate) {
    const message = !isInView
      ? "🗺️ 지도 (스크롤하여 활성화)"
      : "⏳ 대기 중 (다른 지도 닫으면 활성화)";
    const subMessage = !isInView
      ? "WebGL 리소스 절약을 위해 뷰포트 내에서만 렌더링됩니다"
      : `최대 ${MAX_ACTIVE_MAPS}개 지도만 동시 활성화 가능 (현재: ${activeMapInstances.size}/${MAX_ACTIVE_MAPS})`;

    return (
      <div
        ref={containerRef}
        className={cn(
          "rounded-xl bg-muted/50 dark:bg-zinc-900 p-4 border border-border/30 dark:border-zinc-700",
          className
        )}
      >
        <div className="relative w-full h-[500px] flex items-center justify-center">
          <div className="text-center">
            <div className="text-sm text-muted-foreground mb-2">
              {message}
            </div>
            <div className="text-xs text-muted-foreground/70">
              {subMessage}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn(
        "map-container rounded-xl overflow-hidden border border-border/50 dark:border-zinc-700/50 shadow-sm",
        className
      )}
    >
      <div className="relative w-full h-[500px]">
        <MapContainer
          center={[initialViewState.latitude, initialViewState.longitude]}
          zoom={initialViewState.zoom}
          style={{ width: '100%', height: '100%' }}
          zoomControl={false}
          whenReady={() => {
            setTimeout(() => setMapLoaded(true), 100);
          }}
        >
          <TileLayer
            url={tileUrl}
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          />

          <DeckGLOverlay
            layers={layers}
            onHover={handleHover}
            mapLoaded={mapLoaded}
          />

          <MapControls
            onZoomIn={() => {}}
            onZoomOut={() => {}}
            onResetView={handleResetView}
            onToggleLegend={() => setShowLegend(!showLegend)}
          />

          <ViewResetHandler
            resetTrigger={resetTrigger}
            initialViewState={initialViewState}
          />
        </MapContainer>

        {/* 툴팁 */}
        {mapConfig.tooltip !== false && hoveredObject && (() => {
          const tooltipData = formatTooltipData(hoveredObject);
          return tooltipData && (
            <div
              className="absolute bottom-4 left-4 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-sm p-4 rounded-xl shadow-2xl border border-border/50 dark:border-zinc-700/50 max-w-sm animate-in fade-in slide-in-from-bottom-2 duration-200 z-[1000]"
              style={{ pointerEvents: "none" }}
            >
              <div className="space-y-2">
                {tooltipData.map(([key, value], idx) => (
                  <div key={idx} className="flex justify-between gap-4 text-sm">
                    <span className="font-medium text-muted-foreground capitalize">
                      {key.replace(/([A-Z])/g, ' $1').trim()}:
                    </span>
                    <span className="text-foreground font-semibold text-right">
                      {typeof value === 'number' ? value.toLocaleString() : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          );
        })()}

        {/* 레이어 범례 */}
        {showLegend && mapConfig.layers && mapConfig.layers.length > 0 && (
          <div className="absolute top-4 left-4 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-sm p-4 rounded-xl shadow-lg border border-border/50 dark:border-zinc-700/50 max-w-xs z-[1000]">
            <h3 className="text-sm font-semibold mb-3 text-foreground">Layers</h3>
            <div className="space-y-2">
              {mapConfig.layers.map((layer, index) => {
                const palette = isDarkMode ? COLOR_PALETTES.dark : COLOR_PALETTES.light;
                const color = palette[layer.type as keyof typeof palette] || [128, 128, 128, 200];
                const rgbaColor = `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${color[3] / 255})`;

                return (
                  <label
                    key={index}
                    className="flex items-center gap-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-zinc-800 p-2 rounded-lg transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={layersVisible[index]}
                      onChange={() => toggleLayer(index)}
                      className="rounded border-gray-300"
                    />
                    <div
                      className="w-4 h-4 rounded-sm border border-border/50"
                      style={{ backgroundColor: rgbaColor }}
                    />
                    <span className="text-xs text-foreground capitalize">
                      {layer.type} ({Array.isArray(layer.data) ? layer.data.length : 0})
                    </span>
                  </label>
                );
              })}
            </div>
          </div>
        )}

        {/* 샘플링 경고 */}
        {dataSamplingInfo && (
          <div className="absolute bottom-4 right-4 bg-yellow-50/95 dark:bg-yellow-900/30 backdrop-blur-sm text-yellow-900 dark:text-yellow-100 p-3 rounded-xl shadow-lg border border-yellow-500/30 dark:border-yellow-500/20 text-xs max-w-[240px] z-[1000]">
            <div className="flex items-start gap-2">
              <span className="text-base">⚠️</span>
              <div className="flex-1">
                <p className="font-semibold mb-1">데이터 샘플링됨</p>
                <p className="text-[11px] opacity-90">
                  {dataSamplingInfo.original.toLocaleString()}개 → {dataSamplingInfo.sampled.toLocaleString()}개 표시
                </p>
                <p className="mt-1 text-[10px] opacity-70">
                  성능 최적화를 위해 샘플링됨
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
