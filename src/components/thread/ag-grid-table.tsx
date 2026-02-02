"use client";

import { useEffect, useState, useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import { ModuleRegistry, AllCommunityModule, ColDef } from "ag-grid-community";
import { cn } from "@/lib/utils";

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
        parsedConfig = JSON.parse(config);
      } else {
        parsedConfig = config;
      }

      if (!parsedConfig.columnDefs || !parsedConfig.rowData) {
        throw new Error("columnDefs와 rowData가 필요합니다.");
      }

      setGridConfig(parsedConfig);
      setIsLoading(false);
    } catch (err) {
      console.error("AG Grid parsing error:", err);
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
