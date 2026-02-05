"use client";

import { useEffect, useState, useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import { ModuleRegistry, AllCommunityModule, ColDef } from "ag-grid-community";
import { cn } from "@/lib/utils";
import { safeParseJSON } from "@/lib/json-sanitizer";
import { logger } from "@/lib/logger";

import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";

// Register AG Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

interface AGGridTableProps {
  config: string | { columnDefs: ColDef[]; rowData: any[] };
  className?: string;
}

export function AGGridTable({ config, className }: AGGridTableProps) {
  const [gridConfig, setGridConfig] = useState<{
    columnDefs: ColDef[];
    rowData: any[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    setGridConfig(null);

    try {
      let parsedConfig: { columnDefs: ColDef[]; rowData: any[] };

      if (typeof config === "string") {
        // 빈 문자열이나 공백만 있는 경우 체크
        const trimmed = config.trim();
        if (!trimmed) {
          throw new Error("테이블 설정이 비어있습니다.");
        }

        const { data, error: parseError } = safeParseJSON<{ columnDefs: ColDef[]; rowData: any[] }>(trimmed);
        if (!data || parseError) {
          throw new Error(parseError || "테이블 JSON을 파싱할 수 없습니다.");
        }
        parsedConfig = data;
      } else {
        parsedConfig = config;
      }

      // 데이터 검증
      if (!parsedConfig.columnDefs || !parsedConfig.rowData) {
        throw new Error("columnDefs와 rowData가 필요합니다.");
      }

      // columnDefs가 빈 배열인 경우
      if (!Array.isArray(parsedConfig.columnDefs) || parsedConfig.columnDefs.length === 0) {
        throw new Error("컬럼 정의가 비어있습니다. 최소 1개 이상의 컬럼이 필요합니다.");
      }

      // rowData가 배열이 아닌 경우
      if (!Array.isArray(parsedConfig.rowData)) {
        throw new Error("rowData는 배열이어야 합니다.");
      }

      // rowData가 빈 배열인 경우 (경고만, 에러는 아님)
      if (parsedConfig.rowData.length === 0) {
        logger.warn("AG Grid: rowData가 비어있습니다. 빈 테이블이 표시됩니다.");
      }

      setGridConfig(parsedConfig);
      setIsLoading(false);
    } catch (err) {
      logger.error("AG Grid error:", err);
      logger.error("Config:", typeof config === "string" ? config.substring(0, 200) : config);
      setError(err instanceof Error ? err.message : "테이블을 렌더링할 수 없습니다.");
      setIsLoading(false);
    }
  }, [config]);

  const defaultColDef = useMemo<ColDef>(
    () => ({
      sortable: true,
      filter: true,
      resizable: true,
      flex: 1,
      minWidth: 100,
    }),
    []
  );

  if (error) {
    // 친화적인 에러 메시지 매핑
    const userFriendlyError = error.includes("JSON")
      ? "테이블 형식이 올바르지 않습니다. JSON 형식을 확인해주세요."
      : error.includes("columnDefs") || error.includes("rowData")
      ? error  // 이미 친화적한 메시지
      : error.includes("Unexpected")
      ? "테이블 코드가 완전하지 않습니다. 전체 코드가 생성될 때까지 기다려주세요."
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
              테이블 오류
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

  if (isLoading || !gridConfig) {
    return (
      <div
        className={cn(
          "rounded-xl bg-muted/50 dark:bg-zinc-900 p-4 border border-border/30 dark:border-zinc-700",
          className
        )}
      >
        <div className="text-center text-sm text-muted-foreground py-4">
          테이블 렌더링 중...
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "ag-grid-container rounded-xl bg-white dark:bg-zinc-900/50 p-6 border border-border/50 dark:border-zinc-700/50 shadow-sm",
        className
      )}
    >
      <div className="ag-theme-quartz w-full" style={{ width: "100%" }}>
        <AgGridReact
          columnDefs={gridConfig.columnDefs}
          rowData={gridConfig.rowData}
          defaultColDef={defaultColDef}
          pagination={true}
          paginationPageSize={10}
          paginationPageSizeSelector={[10, 20, 50, 100]}
          domLayout="autoHeight"
          theme="legacy"
        />
      </div>
    </div>
  );
}
