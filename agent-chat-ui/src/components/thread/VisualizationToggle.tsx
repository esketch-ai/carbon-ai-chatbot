"use client";

import { useState, useEffect, useRef, ReactNode } from "react";
import { Code2, Eye } from "lucide-react";
import { cn } from "@/lib/utils";
import { SyntaxHighlighter } from "@/components/thread/syntax-highlighter";

interface VisualizationToggleProps {
  code: string;
  language: string;
  /** 시각화 컴포넌트를 lazy로 생성하는 함수. 미리보기 탭 활성화 시에만 호출됨. */
  renderVisualization: () => ReactNode;
  isStreaming?: boolean;
  className?: string;
}

export function VisualizationToggle({
  code,
  language,
  renderVisualization,
  isStreaming = false,
  className,
}: VisualizationToggleProps) {
  const [activeTab, setActiveTab] = useState<"preview" | "code">("code");
  const isReady = !isStreaming;
  const showPreview = activeTab === "preview" && isReady;

  return (
    <div className={cn("relative", className)}>
      {/* 코드 헤더 + 탭 버튼 (시각화 준비 완료 후에만 탭 표시) */}
      <div className="flex items-center justify-between gap-4 rounded-t-xl bg-muted dark:bg-zinc-800 px-5 py-2.5 text-sm font-medium text-foreground dark:text-white/90 border-b border-border dark:border-zinc-600">
        <span className="lowercase text-xs font-mono">{language}</span>

        {isReady && (
          <div className="flex items-center gap-1">
            <button
              onClick={() => setActiveTab("preview")}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all",
                activeTab === "preview"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "hover:bg-muted-foreground/10 text-muted-foreground",
              )}
            >
              <Eye className="h-3.5 w-3.5" />
              <span>미리보기</span>
            </button>
            <button
              onClick={() => setActiveTab("code")}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all",
                activeTab === "code"
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "hover:bg-muted-foreground/10 text-muted-foreground",
              )}
            >
              <Code2 className="h-3.5 w-3.5" />
              <span>코드</span>
            </button>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="relative">
        {showPreview ? (
          <div className="transition-opacity duration-200">
            {renderVisualization()}
          </div>
        ) : (
          <div className="rounded-b-xl bg-muted/50 dark:bg-zinc-900 border-x border-b border-border/30 dark:border-zinc-700 overflow-hidden">
            <SyntaxHighlighter language={language}>
              {code}
            </SyntaxHighlighter>
          </div>
        )}
      </div>
    </div>
  );
}
