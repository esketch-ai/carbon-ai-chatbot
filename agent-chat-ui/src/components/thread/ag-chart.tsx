"use client";

import { useEffect, useState } from "react";
import { AgCharts } from "ag-charts-react";
import type { AgChartOptions } from "ag-charts-community";
import { cn } from "@/lib/utils";

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
        // AI가 생성한 JSON은 비표준일 수 있으므로 전처리
        let sanitized = config
          // 쉼표가 포함된 숫자 (예: 80,000 → 80000)
          .replace(/:\s*(\d{1,3}(,\d{3})+)(\s*[,}\]])/g, (_, num, __, tail) => {
            return `: ${num.replace(/,/g, "")}${tail}`;
          })
          // 작은따옴표를 큰따옴표로 (프로퍼티명/값)
          .replace(/'/g, '"')
          // 후행 쉼표 제거 (예: [1, 2,] → [1, 2])
          .replace(/,\s*([}\]])/g, "$1");
        options = JSON.parse(sanitized);
      } else {
        options = config;
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
      console.error("AG Chart parsing error:", err);
      setError(err instanceof Error ? err.message : "차트를 렌더링할 수 없습니다.");
      setIsLoading(false);
    }
  }, [config]);

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
