import { AIMessage, ToolMessage } from "@langchain/langgraph-sdk";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useSettings } from "@/hooks/useSettings";

function isComplexValue(value: unknown): boolean {
  return Array.isArray(value) || (typeof value === "object" && value !== null);
}

// 도구 이름을 읽기 쉽게 변환
function formatToolName(name: string): string {
  // mcp__netz__get_total_emission -> "총 배출량 조회"
  if (name.startsWith("mcp__netz__")) {
    const toolName = name.replace("mcp__netz__", "");
    const nameMap: Record<string, string> = {
      "get_total_emission": "총 배출량 조회",
      "get_emission_type_ratio": "배출종류 비율 조회",
      "get_scope_emission_comparison": "Scope 배출량 비교",
      "get_top10_facilities_by_scope": "Top10 시설 조회",
      "get_dashboard_emission_comparison": "대시보드 배출량 비교",
      "get_dashboard_emission_type_ratio": "대시보드 배출종류 비율",
      "get_dashboard_input_status": "입력 현황 조회",
      "search_knowledge_base": "지식베이스 검색",
    };
    return nameMap[toolName] || toolName.replace(/_/g, " ");
  }

  // 일반 도구 이름 처리
  return name
    .replace(/^(search|web_search|tavily_search).*/, "웹 검색")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function ToolCalls({
  toolCalls,
  isLoading,
}: {
  toolCalls: AIMessage["tool_calls"];
  isLoading?: boolean;
}) {
  const { userSettings } = useSettings();
  const [isExpanded, setIsExpanded] = useState(true);

  if (!toolCalls || toolCalls.length === 0) return null;

  return (
    <div className={`mx-auto ${userSettings.chatWidth === "default" ? "max-w-3xl" : "max-w-5xl"}`}>
      <div className="overflow-hidden rounded-xl border-2 border-blue-200 dark:border-blue-800 bg-gradient-to-br from-blue-50 to-white dark:from-blue-950/30 dark:to-zinc-900 shadow-lg">
        {/* 헤더 */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full border-b-2 border-blue-200 dark:border-blue-800 bg-blue-100/50 dark:bg-blue-900/30 px-5 py-4 text-left transition-all duration-200 hover:bg-blue-100 dark:hover:bg-blue-900/50"
        >
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-500 dark:bg-blue-600">
                <svg
                  className="h-4 w-4 text-white"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 10V3L4 14h7v7l9-11h-7z"
                  />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-blue-900 dark:text-blue-100 text-base">
                  🔧 Tool Use History
                </h3>
                <p className="text-xs text-blue-700 dark:text-blue-300">
                  {toolCalls.length}개의 도구 사용됨
                </p>
              </div>
            </div>
            <motion.div
              animate={{ rotate: isExpanded ? 0 : -90 }}
              transition={{ duration: 0.25, ease: "easeInOut" }}
            >
              <ChevronDown className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </motion.div>
          </div>
        </button>

        {/* 도구 목록 */}
        <AnimatePresence initial={false}>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
              className="overflow-hidden"
            >
              <div className="divide-y divide-blue-100 dark:divide-blue-900/50">
                {toolCalls.map((tc, idx) => {
                  return <ToolCallItem key={idx} toolCall={tc} isLoading={isLoading} compact={true} />;
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function ToolCallItem({
  toolCall,
  isLoading,
  compact = false
}: {
  toolCall: NonNullable<AIMessage["tool_calls"]>[number];
  isLoading?: boolean;
  compact?: boolean;
}) {
  const { userSettings } = useSettings();
  const [isExpanded, setIsExpanded] = useState(!compact);

  useEffect(() => {
    if (userSettings.autoCollapseToolCalls && isLoading === false) {
      setIsExpanded(false);
    }
  }, [isLoading, userSettings.autoCollapseToolCalls]);

  const args = toolCall.args as Record<string, unknown>;
  const hasArgs = Object.keys(args).length > 0;
  const argEntries = Object.entries(args);

  return (
    <div className={compact ? "" : "overflow-hidden rounded-xl border border-border/50 dark:border-border bg-card shadow-sm transition-all duration-200 hover:shadow-md hover:border-border dark:hover:border-border/80"}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={compact
          ? "w-full px-5 py-3 text-left transition-all duration-200 hover:bg-blue-50 dark:hover:bg-blue-900/20"
          : "w-full border-b border-border/50 dark:border-border bg-muted/30 dark:bg-muted/50 px-5 py-3.5 text-left transition-all duration-200 hover:bg-muted/50 dark:hover:bg-muted/70"
        }
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            {!compact && (
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-foreground/8 ring-1 ring-foreground/5">
                <svg
                  className="h-3.5 w-3.5 text-foreground/70"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 10V3L4 14h7v7l9-11h-7z"
                  />
                </svg>
              </div>
            )}
            <div>
              <h3 className={compact ? "font-semibold text-blue-900 dark:text-blue-100 text-sm" : "font-medium text-foreground text-sm"}>
                {compact && "📌 "}{formatToolName(toolCall.name)}
              </h3>
              {toolCall.name !== formatToolName(toolCall.name) && !compact && (
                <code className="ml-2 rounded-md bg-muted/70 px-2 py-0.5 text-xs font-mono text-muted-foreground/60 border border-border/30">
                  {toolCall.name}
                </code>
              )}
            </div>
          </div>
          <motion.div
            animate={{ rotate: isExpanded ? 0 : -90 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
          >
            <ChevronDown className={compact ? "h-4 w-4 text-blue-600 dark:text-blue-400" : "h-4 w-4 text-muted-foreground/70"} />
          </motion.div>
        </div>
      </button>
      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
            className="overflow-hidden"
          >
            {hasArgs ? (
              <div className="bg-card">
                <table className="min-w-full">
                  <tbody className="divide-y divide-border/40">
                    {argEntries.map(([key, value], argIdx) => (
                      <tr
                        key={argIdx}
                        className="transition-colors duration-150 hover:bg-muted/30"
                      >
                        <td className="px-5 py-3 text-xs font-semibold whitespace-nowrap text-foreground/70 bg-muted/20 w-1/4">
                          {key}
                        </td>
                        <td className="px-5 py-3 text-sm text-foreground/85">
                          {(() => {
                            if (value === null || value === undefined) {
                              return <span className="font-normal text-muted-foreground italic">null</span>;
                            }
                            if (typeof value === 'object') {
                              return (
                                <code className="block rounded-lg bg-muted/40 px-3 py-2 font-mono text-xs break-all border border-border/30 whitespace-pre-wrap">
                                  {JSON.stringify(value, null, 2)}
                                </code>
                              );
                            }
                            return <span className="font-normal">{String(value)}</span>;
                          })()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="bg-card px-5 py-4">
                <code className="text-xs text-muted-foreground/60 italic">
                  No arguments
                </code>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function ToolResult({
  message,
  isLoading
}: {
  message: ToolMessage;
  isLoading?: boolean;
}) {
  const { userSettings } = useSettings();
  const [isExpanded, setIsExpanded] = useState(true);

  useEffect(() => {
    if (userSettings.autoCollapseToolCalls && isLoading === false) {
      setIsExpanded(false);
    }
  }, [isLoading, userSettings.autoCollapseToolCalls]);

  let parsedContent: unknown;
  let isJsonContent = false;
  let chartUrl: string | null = null;
  let infographicUrl: string | null = null;
  let mapUrl: string | null = null;
  let visualizationType: string | null = null;
  let visualizationTitle: string | null = null;
  let mcpError: string | null = null;
  let mcpSuggestion: string | null = null;
  let isMcpResult = false;
  let isSearchResult = false;
  let searchStatus: string | null = null;
  let searchMessage: string | null = null;
  let searchResults: unknown[] | null = null;

  try {
    if (typeof message.content === "string") {
      parsedContent = JSON.parse(message.content);
      isJsonContent = isComplexValue(parsedContent);

      // MCP 차트/인포그래픽/지도 결과 확인
      if (typeof parsedContent === "object" && parsedContent !== null) {
        const content = parsedContent as Record<string, unknown>;

        // 지식베이스 검색 결과 확인
        if ("status" in content && "results" in content && Array.isArray(content.results)) {
          isSearchResult = true;
          searchStatus = content.status as string;
          searchMessage = (content.message as string) || null;
          searchResults = content.results as unknown[];
        }
        // 차트 결과
        else if ("chart_url" in content && typeof content.chart_url === "string") {
          chartUrl = content.chart_url;
          visualizationType = "chart";
          visualizationTitle = (content.title as string) || (content.chart_type as string) || "Chart";
          isMcpResult = true;
        }
        // 인포그래픽 결과
        else if ("infographic_url" in content && typeof content.infographic_url === "string") {
          infographicUrl = content.infographic_url;
          visualizationType = "infographic";
          visualizationTitle = (content.title as string) || (content.infographic_type as string) || "Infographic";
          isMcpResult = true;
        }
        // 지도 결과
        else if ("map_url" in content && typeof content.map_url === "string") {
          mapUrl = content.map_url;
          visualizationType = "map";
          visualizationTitle = (content.title as string) || (content.map_type as string) || "Map";
          isMcpResult = true;
        }
        // MCP 에러 결과
        else if ("status" in content && content.status === "error" && "error" in content) {
          isMcpResult = true;
          mcpError = content.error as string;
          mcpSuggestion = (content.suggestion as string) || null;
          visualizationType = (content.chart_type as string) || (content.infographic_type as string) || (content.map_type as string) || "visualization";
          visualizationTitle = `${visualizationType} 생성 실패`;
        }
      }
    }
  } catch {
    // Content is not JSON, use as is
    parsedContent = message.content;
  }

  // 지식베이스 검색 결과 특별 렌더링
  if (isSearchResult && searchResults) {
    return (
      <div className="mx-auto w-full max-w-5xl my-4">
        <div className="rounded-xl bg-muted/50 dark:bg-zinc-900 p-4 border border-border/30">
          <div className="mb-3 flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900/50">
              <svg
                className="h-4 w-4 text-blue-600 dark:text-blue-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </div>
            <span className="text-sm font-semibold text-foreground/70">
              지식베이스 검색 결과
            </span>
          </div>
          {searchMessage && (
            <p className="text-sm text-foreground/80 mb-3">
              {searchMessage}
            </p>
          )}
          {searchStatus === "success" && searchResults.length > 0 && (
            <div className="space-y-3">
              {searchResults.map((result: any, idx: number) => (
                <div
                  key={idx}
                  className="rounded-lg bg-card border border-border/30 p-3"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <p className="text-xs font-semibold text-foreground/70 mb-1">
                        {result.filename || "문서"}
                      </p>
                      {result.similarity !== undefined && (
                        <p className="text-xs text-muted-foreground">
                          유사도: {(result.similarity * 100).toFixed(1)}%
                        </p>
                      )}
                    </div>
                  </div>
                  <p className="text-sm text-foreground/90 line-clamp-3">
                    {result.content}
                  </p>
                </div>
              ))}
            </div>
          )}
          {searchStatus === "no_results" && (
            <p className="text-sm text-muted-foreground">
              관련 문서를 찾을 수 없습니다.
            </p>
          )}
        </div>
      </div>
    );
  }

  // MCP 에러 결과인 경우 특별 렌더링
  if (isMcpResult && mcpError) {
    return (
      <div className="mx-auto w-full max-w-5xl my-4">
        <div className="rounded-xl bg-red-50 dark:bg-red-950/30 p-5 border-2 border-red-200 dark:border-red-800">
          <div className="flex items-start gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/50 flex-shrink-0 mt-0.5">
              <svg
                className="h-5 w-5 text-red-600 dark:text-red-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="text-base font-semibold text-red-900 dark:text-red-100 mb-2">
                {visualizationTitle}
              </h3>
              <p className="text-sm text-red-800 dark:text-red-200 mb-3">
                {mcpError}
              </p>
              {mcpSuggestion && (
                <div className="mt-3 p-3 rounded-lg bg-red-100/50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/50">
                  <p className="text-xs font-medium text-red-900 dark:text-red-100 mb-1">
                    해결 방법:
                  </p>
                  <pre className="text-xs text-red-800 dark:text-red-200 whitespace-pre-wrap font-sans">
                    {mcpSuggestion}
                  </pre>
                </div>
              )}
              {typeof parsedContent === "object" && parsedContent !== null && "technical_error" in parsedContent && (
                <details className="mt-3">
                  <summary className="text-xs font-medium text-red-700 dark:text-red-300 cursor-pointer hover:underline">
                    기술적 상세 정보 보기
                  </summary>
                  <pre className="mt-2 text-xs text-red-600 dark:text-red-400 p-2 rounded bg-red-50 dark:bg-red-950/50 overflow-x-auto">
                    {String((parsedContent as { technical_error?: unknown }).technical_error)}
                  </pre>
                </details>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 차트/인포그래픽/지도 성공 결과인 경우 특별 렌더링
  const imageUrl = chartUrl || infographicUrl || mapUrl;
  if (imageUrl && visualizationType) {
    return (
      <div className="mx-auto w-full max-w-5xl my-4">
        <div className="rounded-xl bg-muted/50 dark:bg-zinc-900 p-4 border border-border/30">
          <div className="mb-3 flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/50">
              <svg
                className="h-4 w-4 text-green-600 dark:text-green-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <span className="text-sm font-semibold text-foreground/70">
              {visualizationTitle}
            </span>
          </div>
          <div className="rounded-lg overflow-hidden border border-border/30">
            <img
              src={imageUrl}
              alt={visualizationTitle || "Visualization"}
              className="w-full h-auto"
              onError={(e) => {
                // 이미지 로드 실패 시 대체 메시지
                const target = e.target as HTMLImageElement;
                target.style.display = "none";
                const parent = target.parentElement;
                if (parent) {
                  const errorDiv = document.createElement("div");
                  errorDiv.className = "p-6 text-center";
                  errorDiv.innerHTML = `
                    <div class="text-red-600 dark:text-red-400 mb-2">
                      <svg class="h-12 w-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <p class="text-sm text-muted-foreground">이미지를 불러올 수 없습니다.</p>
                    <p class="text-xs text-muted-foreground mt-1">URL: ${imageUrl}</p>
                  `;
                  parent.appendChild(errorDiv);
                }
              }}
            />
          </div>
          {typeof parsedContent === "object" && parsedContent !== null && "description" in parsedContent && (
            <p className="mt-3 text-xs text-muted-foreground">
              {String((parsedContent as { description?: unknown }).description)}
            </p>
          )}
        </div>
      </div>
    );
  }

  const contentStr = isJsonContent
    ? JSON.stringify(parsedContent, null, 2)
    : String(message.content);
  const contentLines = contentStr.split("\n");
  const shouldTruncate = contentLines.length > 4 || contentStr.length > 500;
  const displayedContent =
    shouldTruncate && !isExpanded
      ? contentStr.length > 500
        ? contentStr.slice(0, 500) + "..."
        : contentLines.slice(0, 4).join("\n") + "\n..."
      : contentStr;

  return (
    <div className={`mx-auto grid ${userSettings.chatWidth === "default" ? "max-w-3xl" : "max-w-5xl"} grid-rows-[1fr_auto] gap-0`}>
      <div className="overflow-hidden rounded-xl border border-border/50 dark:border-border bg-card shadow-sm transition-all duration-200 hover:shadow-md hover:border-border dark:hover:border-border/80">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full border-b border-border/50 dark:border-border bg-muted/30 dark:bg-muted/50 px-5 py-3.5 text-left transition-all duration-200 hover:bg-muted/50 dark:hover:bg-muted/70 cursor-pointer"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-foreground/8 ring-1 ring-foreground/5">
                <svg
                  className="h-3.5 w-3.5 text-foreground/70"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
              {message.name ? (
                <h3 className="font-medium text-foreground text-sm flex gap-2 items-center flex-wrap">
                  <span className="text-green-600 dark:text-green-400">✓</span>
                  {formatToolName(message.name)}
                  {message.name !== formatToolName(message.name) && (
                    <code className="rounded-md bg-muted/70 px-2 py-0.5 text-xs font-mono text-muted-foreground/60 border border-border/30">
                      {message.name}
                    </code>
                  )}
                </h3>
              ) : (
                <h3 className="font-medium text-foreground text-sm">
                  <span className="text-green-600 dark:text-green-400">✓</span> 결과
                </h3>
              )}
            </div>
            <div className="flex items-center gap-2">
              {message.tool_call_id && (
                <code className="rounded-md bg-muted/70 px-2 py-0.5 text-xs font-mono text-muted-foreground/80 border border-border/30">
                  {message.tool_call_id.slice(0, 8)}...
                </code>
              )}
              <motion.div
                animate={{ rotate: isExpanded ? 0 : -90 }}
                transition={{ duration: 0.25, ease: "easeInOut" }}
              >
                <ChevronDown className="h-4 w-4 text-muted-foreground/70" />
              </motion.div>
            </div>
          </div>
        </button>
        <AnimatePresence initial={false}>
          {isExpanded && (
            <motion.div
              className="min-w-full bg-card overflow-hidden"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
            >
              <div className="p-3">
                <AnimatePresence
                  mode="wait"
                  initial={false}
                >
                  <motion.div
                    key={isExpanded ? "expanded" : "collapsed"}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
                  >
                    {isJsonContent ? (
                      <table className="min-w-full">
                        <tbody className="divide-y divide-border/40">
                          {(Array.isArray(parsedContent)
                            ? isExpanded
                              ? parsedContent
                              : parsedContent.slice(0, 5)
                            : Object.entries(parsedContent as Record<string, unknown>)
                          ).map((item, argIdx) => {
                            const [key, value] = Array.isArray(parsedContent)
                              ? [argIdx, item]
                              : [item[0], item[1]];
                            return (
                              <tr
                                key={argIdx}
                                className="transition-colors duration-150 hover:bg-muted/30"
                              >
                                <td className="px-5 py-3 text-xs font-semibold whitespace-nowrap text-foreground/70 bg-muted/20 w-1/4">
                                  {key}
                                </td>
                                <td className="px-5 py-3 text-sm text-foreground/85">
                                  {(() => {
                                    if (value === null || value === undefined) {
                                      return <span className="font-normal text-muted-foreground italic">null</span>;
                                    }
                                    if (typeof value === 'object') {
                                      return (
                                        <code className="block rounded-lg bg-muted/40 px-3 py-2 font-mono text-xs break-all border border-border/30 whitespace-pre-wrap">
                                          {JSON.stringify(value, null, 2)}
                                        </code>
                                      );
                                    }
                                    return <span className="font-normal">{String(value)}</span>;
                                  })()}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    ) : (
                      <code className="block rounded-lg bg-muted/40 px-3 py-2.5 text-sm font-mono border border-border/30 leading-relaxed whitespace-pre-wrap">
                        {displayedContent}
                      </code>
                    )}
                  </motion.div>
                </AnimatePresence>
              </div>
              {((shouldTruncate && !isJsonContent) ||
                (isJsonContent &&
                  Array.isArray(parsedContent) &&
                  parsedContent.length > 5)) && (
                <motion.button
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsExpanded(!isExpanded);
                  }}
                  className="flex w-full cursor-pointer items-center justify-center gap-2 border-t border-border/40 bg-muted/20 py-2.5 text-xs font-medium text-foreground/70 transition-all duration-150 ease-in-out hover:bg-muted/40"
                  initial={{ scale: 1 }}
                  whileHover={{ scale: 1.002 }}
                  whileTap={{ scale: 0.998 }}
                >
                  {isExpanded ? (
                    <>
                      <ChevronUp className="h-3.5 w-3.5" />
                      <span>Show less</span>
                    </>
                  ) : (
                    <>
                      <ChevronDown className="h-3.5 w-3.5" />
                      <span>Show more</span>
                    </>
                  )}
                </motion.button>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
