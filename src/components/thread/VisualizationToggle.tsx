"use client";

import { useState, ReactNode } from "react";
import { Code2, Eye, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { SyntaxHighlighter } from "@/components/thread/syntax-highlighter";

interface VisualizationToggleProps {
  code: string;
  language: string;
  visualization: ReactNode;
  isStreaming?: boolean;
  className?: string;
}

export function VisualizationToggle({
  code,
  language,
  visualization,
  isStreaming = false,
  className,
}: VisualizationToggleProps) {
  const [activeTab, setActiveTab] = useState<"preview" | "code">("preview");

  return (
    <div className={cn("relative", className)}>
      {/* Tab buttons */}
      <div className="flex items-center gap-2 mb-3">
        <button
          onClick={() => setActiveTab("preview")}
          disabled={isStreaming}
          className={cn(
            "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all",
            activeTab === "preview"
              ? "bg-primary text-primary-foreground shadow-sm"
              : "bg-muted hover:bg-muted/80 text-muted-foreground",
            isStreaming && "opacity-50 cursor-not-allowed"
          )}
        >
          {isStreaming ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Eye className="h-4 w-4" />
          )}
          <span>{isStreaming ? "생성 중..." : "미리보기"}</span>
        </button>

        <button
          onClick={() => setActiveTab("code")}
          className={cn(
            "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all",
            activeTab === "code"
              ? "bg-primary text-primary-foreground shadow-sm"
              : "bg-muted hover:bg-muted/80 text-muted-foreground"
          )}
        >
          <Code2 className="h-4 w-4" />
          <span>코드</span>
        </button>

        <span className="ml-auto text-xs text-muted-foreground font-mono">
          {language}
        </span>
      </div>

      {/* Content */}
      <div className="relative">
        {activeTab === "preview" ? (
          <div
            className={cn(
              "transition-opacity duration-200",
              isStreaming && "opacity-50 pointer-events-none"
            )}
          >
            {visualization}
          </div>
        ) : (
          <div className="rounded-xl bg-muted/50 dark:bg-zinc-900 border border-border/30 dark:border-zinc-700 overflow-hidden">
            <div className="flex items-center justify-between gap-4 bg-muted dark:bg-zinc-800 px-5 py-2.5 text-sm font-medium text-foreground dark:text-white/90 border-b border-border dark:border-zinc-600">
              <span className="lowercase text-xs font-mono">{language}</span>
            </div>
            <SyntaxHighlighter language={language}>
              {code}
            </SyntaxHighlighter>
          </div>
        )}
      </div>
    </div>
  );
}
