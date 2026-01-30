"use client";
// ai의 마크다운 응답을 파싱하고 적절한 컴포넌트로 렌더링함
import "./markdown-styles.css";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";
import { FC, memo, useState } from "react";
import { CheckIcon, CopyIcon } from "lucide-react";
import { SyntaxHighlighter } from "@/components/thread/syntax-highlighter";
import { AGChart } from "@/components/thread/ag-chart";
import { AGGridTable } from "@/components/thread/ag-grid-table";
import dynamic from "next/dynamic";

// MapRenderer를 클라이언트 전용으로 동적 로드
const MapRenderer = dynamic(
  () => import("@/components/thread/map-renderer").then((mod) => mod.MapRenderer),
  { ssr: false, loading: () => <div className="h-[500px] flex items-center justify-center">맵 로딩 중...</div> }
);

// MermaidDiagram을 클라이언트 전용으로 동적 로드
const MermaidDiagram = dynamic(
  () => import("@/components/thread/mermaid-diagram").then((mod) => mod.MermaidDiagram),
  { ssr: false, loading: () => <div className="flex items-center justify-center p-4">다이어그램 로딩 중...</div> }
);

import { TooltipIconButton } from "@/components/thread/tooltip-icon-button";
import { VisualizationToggle } from "@/components/thread/VisualizationToggle";
import { cn } from "@/lib/utils";

import "katex/dist/katex.min.css";

interface CodeHeaderProps {
  language?: string;
  code: string;
}

const useCopyToClipboard = ({
  copiedDuration = 3000,
}: {
  copiedDuration?: number;
} = {}) => {
  const [isCopied, setIsCopied] = useState<boolean>(false);

  const copyToClipboard = (value: string) => {
    if (!value) return;

    navigator.clipboard.writeText(value).then(() => {
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), copiedDuration);
    });
  };

  return { isCopied, copyToClipboard };
};

const CodeHeader: FC<CodeHeaderProps> = ({ language, code }) => {
  const { isCopied, copyToClipboard } = useCopyToClipboard();
  const onCopy = () => {
    if (!code || isCopied) return;
    copyToClipboard(code);
  };

  return (
    <div className="flex items-center justify-between gap-4 rounded-t-xl bg-muted dark:bg-zinc-800 px-5 py-2.5 text-sm font-medium text-foreground dark:text-white/90 border-b border-border dark:border-zinc-600">
      <span className="lowercase text-xs font-mono">{language}</span>
      <TooltipIconButton
        tooltip="Copy"
        onClick={onCopy}
      >
        {!isCopied && <CopyIcon />}
        {isCopied && <CheckIcon />}
      </TooltipIconButton>
    </div>
  );
};

const defaultComponents: Record<string, unknown> = {
  h1: ({ className, ...props }: { className?: string }) => (
    <h1
      className={cn(
        "mb-8 scroll-m-20 text-4xl font-extrabold tracking-tight last:mb-0",
        className,
      )}
      {...props}
    />
  ),
  h2: ({ className, ...props }: { className?: string }) => (
    <h2
      className={cn(
        "mt-8 mb-4 scroll-m-20 text-3xl font-semibold tracking-tight first:mt-0 last:mb-0",
        className,
      )}
      {...props}
    />
  ),
  h3: ({ className, ...props }: { className?: string }) => (
    <h3
      className={cn(
        "mt-6 mb-4 scroll-m-20 text-2xl font-semibold tracking-tight first:mt-0 last:mb-0",
        className,
      )}
      {...props}
    />
  ),
  h4: ({ className, ...props }: { className?: string }) => (
    <h4
      className={cn(
        "mt-6 mb-4 scroll-m-20 text-xl font-semibold tracking-tight first:mt-0 last:mb-0",
        className,
      )}
      {...props}
    />
  ),
  h5: ({ className, ...props }: { className?: string }) => (
    <h5
      className={cn(
        "my-4 text-lg font-semibold first:mt-0 last:mb-0",
        className,
      )}
      {...props}
    />
  ),
  h6: ({ className, ...props }: { className?: string }) => (
    <h6
      className={cn("my-4 font-semibold first:mt-0 last:mb-0", className)}
      {...props}
    />
  ),
  p: ({ className, ...props }: { className?: string }) => (
    <p
      className={cn("mt-5 mb-5 leading-relaxed text-foreground/90 first:mt-0 last:mb-0", className)}
      {...props}
    />
  ),
  a: ({ className, ...props }: { className?: string }) => (
    <a
      className={cn(
        "text-primary font-medium underline underline-offset-4",
        className,
      )}
      {...props}
    />
  ),
  blockquote: ({ className, ...props }: { className?: string }) => (
    <blockquote
      className={cn("border-l-2 pl-6 italic", className)}
      {...props}
    />
  ),
  ul: ({ className, ...props }: { className?: string }) => (
    <ul
      className={cn("my-5 ml-6 list-disc [&>li]:mt-2 [&>li]:leading-relaxed", className)}
      {...props}
    />
  ),
  ol: ({ className, ...props }: { className?: string }) => (
    <ol
      className={cn("my-5 ml-6 list-decimal [&>li]:mt-2 [&>li]:leading-relaxed", className)}
      {...props}
    />
  ),
  hr: ({ className, ...props }: { className?: string }) => (
    <hr
      className={cn("my-5 border-b", className)}
      {...props}
    />
  ),
  table: ({ className, ...props }: { className?: string }) => (
    <table
      className={cn(
        "my-5 w-full border-separate border-spacing-0 overflow-y-auto",
        className,
      )}
      {...props}
    />
  ),
  th: ({ className, ...props }: { className?: string }) => (
    <th
      className={cn(
        "bg-muted px-4 py-2 text-left font-bold first:rounded-tl-lg last:rounded-tr-lg [&[align=center]]:text-center [&[align=right]]:text-right",
        className,
      )}
      {...props}
    />
  ),
  td: ({ className, ...props }: { className?: string }) => (
    <td
      className={cn(
        "border-b border-l px-4 py-2 text-left last:border-r [&[align=center]]:text-center [&[align=right]]:text-right",
        className,
      )}
      {...props}
    />
  ),
  tr: ({ className, ...props }: { className?: string }) => (
    <tr
      className={cn(
        "m-0 border-b p-0 first:border-t [&:last-child>td:first-child]:rounded-bl-lg [&:last-child>td:last-child]:rounded-br-lg",
        className,
      )}
      {...props}
    />
  ),
  sup: ({ className, ...props }: { className?: string }) => (
    <sup
      className={cn("[&>a]:text-xs [&>a]:no-underline", className)}
      {...props}
    />
  ),
  pre: ({ className, ...props }: { className?: string }) => (
    <pre
      className={cn(
        "w-full overflow-x-auto rounded-xl bg-muted/50 dark:bg-zinc-900 text-foreground dark:text-white shadow-md border border-border/30 dark:border-zinc-700",
        className,
      )}
      {...props}
    />
  ),
  img: ({ className, ...props }: { className?: string; src?: string; alt?: string }) => (
    <img
      className={cn(
        "my-6 rounded-lg border border-border/30 shadow-md max-w-full h-auto",
        className
      )}
      {...props}
    />
  ),
};

const MarkdownTextImpl: FC<{
  children: string;
  isStreaming?: boolean;
}> = ({ children, isStreaming = false }) => {
  // Create components with isStreaming context
  const components = {
    ...defaultComponents,
    code: ({
      className,
      children,
      ...props
    }: {
      className?: string;
      children?: React.ReactNode;
    }) => {
      const match = /language-(\w+)/.exec(className || "");

      if (match) {
        const language = match[1];
        const code = String(children).replace(/\n$/, "");

        // AG Chart with toggle
        if (language === "agchart") {
          return (
            <VisualizationToggle
              code={code}
              language={language}
              visualization={<AGChart config={code} />}
              isStreaming={isStreaming}
            />
          );
        }

        // AG Grid with toggle
        if (language === "aggrid") {
          return (
            <VisualizationToggle
              code={code}
              language={language}
              visualization={<AGGridTable config={code} />}
              isStreaming={isStreaming}
            />
          );
        }

        // Map with toggle
        if (language === "map" || language === "geomap" || language === "deckgl") {
          return (
            <VisualizationToggle
              code={code}
              language={language}
              visualization={<MapRenderer config={code} />}
              isStreaming={isStreaming}
            />
          );
        }

        // Mermaid with toggle
        if (language === "mermaid") {
          return (
            <VisualizationToggle
              code={code}
              language={language}
              visualization={<MermaidDiagram code={code} />}
              isStreaming={isStreaming}
            />
          );
        }

        // Regular code block
        return (
          <>
            <CodeHeader
              language={language}
              code={code}
            />
            <SyntaxHighlighter
              language={language}
              className={className}
            >
              {code}
            </SyntaxHighlighter>
          </>
        );
      }

      return (
        <code
          className={cn("rounded-md bg-muted/60 px-1.5 py-0.5 font-mono text-[0.9em] font-medium border border-border/30 text-foreground", className)}
          {...props}
        >
          {children}
        </code>
      );
    },
  };

  return (
    <div className="markdown-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={components}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
};

export const MarkdownText = memo(MarkdownTextImpl);
