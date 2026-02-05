"use client";

import { useEffect, useState } from "react";
import { AgCharts } from "ag-charts-react";
import type { AgChartOptions } from "ag-charts-community";
import { cn } from "@/lib/utils";
import { safeParseJSON } from "@/lib/json-sanitizer";
import { logger } from "@/lib/logger";

interface AGChartProps {
  config: string | AgChartOptions;
  className?: string;
}

export function AGChart({ config, className }: AGChartProps) {
  const [chartOptions, setChartOptions] = useState<AgChartOptions | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    setChartOptions(null);

    try {
      let options: AgChartOptions;

      if (typeof config === "string") {
        // 빈 문자열이나 공백만 있는 경우 체크
        const trimmed = config.trim();
        if (!trimmed) {
          throw new Error("차트 설정이 비어있습니다.");
        }

        const { data, error: parseError } = safeParseJSON<AgChartOptions>(trimmed);
        if (!data || parseError) {
          throw new Error(parseError || "차트 JSON을 파싱할 수 없습니다.");
        }
        options = data;
      } else {
        options = config;
      }

      // 데이터 검증
      if (!options.data && !options.series) {
        throw new Error("차트 데이터가 없습니다. 'data' 또는 'series' 속성이 필요합니다.");
      }

      // data가 있는데 빈 배열인 경우
      if (Array.isArray(options.data) && options.data.length === 0) {
        throw new Error("차트 데이터가 비어있습니다.");
      }

      // series 검증
      if (options.series) {
        const seriesArray = Array.isArray(options.series) ? options.series : [options.series];

        // 모든 series가 비어있는지 확인
        const hasData = seriesArray.some((s: any) => {
          if (s.data && Array.isArray(s.data) && s.data.length > 0) {
            return true;
          }
          return false;
        });

        // options.data도 없고 series에도 데이터가 없으면
        if (!hasData && (!options.data || (Array.isArray(options.data) && options.data.length === 0))) {
          throw new Error("차트에 표시할 데이터가 없습니다.");
        }
      }

      // 기본 테마 및 스타일 적용
      const defaultOptions: AgChartOptions = {
        background: {
          fill: "transparent",
        },
        padding: {
          top: 20,
          right: 20,
          bottom: 20,
          left: 20,
        },
        ...options,
      };

      setChartOptions(defaultOptions);
      setIsLoading(false);
    } catch (err) {
      logger.error("AG Chart error:", err);
      logger.error("Config:", typeof config === "string" ? config.substring(0, 200) : config);
      setError(err instanceof Error ? err.message : "차트를 렌더링할 수 없습니다.");
      setIsLoading(false);
    }
  }, [config]);

  if (error) {
    // 친화적인 에러 메시지 매핑
    const userFriendlyError = error.includes("JSON")
      ? "차트 형식이 올바르지 않습니다. JSON 형식을 확인해주세요."
      : error.includes("데이터")
      ? error  // 이미 친화적인 메시지
      : error.includes("Unexpected")
      ? "차트 코드가 완전하지 않습니다. 전체 코드가 생성될 때까지 기다려주세요."
      : error;

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
              차트 오류
            </p>
            <p className="text-sm text-red-600/90 dark:text-red-400/90 mt-1">
              {userFriendlyError}
            </p>
          </div>
        </div>
        <details className="mt-4">
          <summary className="text-xs text-red-600/70 dark:text-red-400/70 cursor-pointer hover:text-red-600 dark:hover:text-red-400 transition-colors">
            상세 정보 보기
          </summary>
          <pre className="mt-2 text-xs text-red-600/60 dark:text-red-400/60 overflow-x-auto bg-red-50/50 dark:bg-red-950/30 p-3 rounded-lg border border-red-200/30 dark:border-red-800/20">
            {typeof config === "string" ? config : JSON.stringify(config, null, 2)}
          </pre>
        </details>
      </div>
    );
  }

  if (isLoading || !chartOptions) {
    return (
      <div
        className={cn(
          "rounded-xl bg-muted/50 dark:bg-zinc-900 p-4 border border-border/30 dark:border-zinc-700",
          className
        )}
      >
        <div className="text-center text-sm text-muted-foreground py-4">
          차트 렌더링 중...
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "ag-chart-container rounded-xl bg-white dark:bg-zinc-900/50 p-6 border border-border/50 dark:border-zinc-700/50 shadow-sm",
        className
      )}
    >
      <div className="w-full h-[400px] min-h-[300px]">
        <AgCharts options={chartOptions} />
      </div>
    </div>
  );
}
