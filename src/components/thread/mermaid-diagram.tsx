"use client";

import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import { cn } from "@/lib/utils";

interface MermaidDiagramProps {
  code: string;
  className?: string;
}

// Mermaid 코드 정리 함수
function cleanMermaidCode(code: string): string {
  if (!code) return code;
  
  let cleaned = code.trim();
  
  // 1. HTML 태그 제거 (<br/>, <br>, <div> 등) - 가장 먼저 처리
  // 따옴표 안의 <br/> 태그를 공백으로 변경
  cleaned = cleaned.replace(/"([^"]*)"/g, (match, content) => {
    // 따옴표 안의 내용에서 <br/> 태그를 공백으로 변경
    let cleanContent = content
      .replace(/<br\s*\/?>/gi, ' ')  // <br/> 제거
      .replace(/<[^>]+>/g, '')        // 다른 HTML 태그도 제거
      .replace(/\s+/g, ' ')           // 연속된 공백을 하나로
      .trim();
    // 빈 따옴표 방지
    if (!cleanContent) {
      cleanContent = ' ';
    }
    return `"${cleanContent}"`;
  });
  
  // 1-1. 따옴표 밖에 남아있는 <br/> 태그도 제거 (혹시 모를 경우를 대비)
  cleaned = cleaned.replace(/<br\s*\/?>/gi, ' ');
  cleaned = cleaned.replace(/<[^>]+>/g, '');
  
  // 2. 따옴표 밖의 HTML 태그도 제거
  cleaned = cleaned.replace(/<br\s*\/?>/gi, ' ');
  cleaned = cleaned.replace(/<[^>]+>/g, '');
  
  // 3. style 구문 오류 수정 (줄바꿈 문제)
  // style A fill:#c8e6c9\n    style 같은 잘못된 줄바꿈 수정
  cleaned = cleaned.replace(/style\s+(\w+)\s+fill:([^\n]+)\s*\n\s*style/g, 'style $1 fill:$2\n    style');
  // style이 줄바꿈으로 분리된 경우 수정
  cleaned = cleaned.replace(/style\s+(\w+)\s*\n\s+fill:([^\n]+)/g, 'style $1 fill:$2');
  
  // 4. 이모지 제거 (Mermaid가 이모지를 제대로 처리하지 못할 수 있음)
  cleaned = cleaned.replace(/[\u{1F300}-\u{1F9FF}]/gu, '');
  cleaned = cleaned.replace(/[\u{2600}-\u{26FF}]/gu, '');
  cleaned = cleaned.replace(/[\u{2700}-\u{27BF}]/gu, '');
  
  // 5. 빈 줄 정리 (3개 이상 연속된 빈 줄을 2개로)
  cleaned = cleaned.replace(/\n\s*\n\s*\n+/g, '\n\n');
  
  // 6. 따옴표가 제대로 닫히지 않은 경우 수정
  const quoteCount = (cleaned.match(/"/g) || []).length;
  if (quoteCount % 2 !== 0) {
    // 따옴표가 홀수 개면 마지막에 추가
    cleaned = cleaned + '"';
  }
  
  return cleaned;
}

export function MermaidDiagram({ code, className }: MermaidDiagramProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [svg, setSvg] = useState<string | null>(null);

  useEffect(() => {
    if (!code) return;

    setIsLoading(true);
    setError(null);
    setSvg(null);

    // Mermaid 코드 정리
    const cleanedCode = cleanMermaidCode(code);
    
    // 정리된 코드가 비어있으면 에러
    if (!cleanedCode.trim()) {
      setError("다이어그램 코드가 비어있습니다.");
      setIsLoading(false);
      return;
    }

    // Mermaid 초기화
    mermaid.initialize({
      startOnLoad: false,
      theme: "default",
      securityLevel: "loose",
      fontFamily: "inherit",
      // 렌더링 안정성을 위한 추가 설정
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: "basis",
      },
    });

    const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;

    // Mermaid 렌더링
    mermaid
      .render(id, cleanedCode)
      .then((result) => {
        // SVG 검증
        if (result.svg && !result.svg.includes('viewBox="0 0 -Infinity')) {
          setSvg(result.svg);
          setIsLoading(false);
        } else {
          throw new Error("렌더링된 SVG가 유효하지 않습니다.");
        }
      })
      .catch((err) => {
        console.error("Mermaid rendering error:", err);
        console.error("Original code:", code);
        console.error("Cleaned code:", cleanedCode);
        setError(err.message || "다이어그램을 렌더링할 수 없습니다.");
        setIsLoading(false);
      });
  }, [code]);

  useEffect(() => {
    if (svg && ref.current) {
      ref.current.innerHTML = svg;
    }
  }, [svg]);

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
          {code}
        </pre>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "mermaid-diagram-container rounded-xl bg-muted/50 dark:bg-zinc-900 p-4 border border-border/30 dark:border-zinc-700 overflow-auto",
        isLoading && "opacity-50",
        className
      )}
    >
      <div
        ref={ref}
        className="flex items-center justify-center min-h-[200px]"
      />
      {isLoading && (
        <div className="text-center text-sm text-muted-foreground py-4">
          다이어그램 렌더링 중...
        </div>
      )}
    </div>
  );
}

