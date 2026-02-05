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

    // 다크모드 확인
    const isDark = document.documentElement.classList.contains('dark');

    // Mermaid 초기화 - 현대적이고 부드러운 스타일
    mermaid.initialize({
      startOnLoad: false,
      theme: "base",  // base 테마로 커스터마이징
      securityLevel: "loose",
      fontFamily: "ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      // 텍스트 잘림 방지 설정
      flowchart: {
        useMaxWidth: true,  // 컨테이너 너비에 맞춤
        htmlLabels: true,
        curve: "basis",  // 부드러운 곡선
        padding: 20,
        wrappingWidth: 150,  // 텍스트 줄바꿈 너비 줄임
        nodeSpacing: 50,
        rankSpacing: 50,
      },
      // 커스텀 테마 변수 - 현대적이고 부드러운 디자인
      themeVariables: {
        // 기본 색상 (라이트 모드)
        primaryColor: isDark ? '#4f46e5' : '#6366f1',
        primaryTextColor: isDark ? '#ffffff' : '#ffffff',
        primaryBorderColor: isDark ? '#6366f1' : '#818cf8',

        // 라인 색상
        lineColor: isDark ? '#64748b' : '#94a3b8',

        // 보조 색상
        secondaryColor: isDark ? '#06b6d4' : '#0ea5e9',
        tertiaryColor: isDark ? '#8b5cf6' : '#a855f7',

        // 배경
        mainBkg: isDark ? '#4f46e5' : '#6366f1',
        secondBkg: isDark ? '#06b6d4' : '#0ea5e9',
        tertiaryBkg: isDark ? '#8b5cf6' : '#a855f7',

        // 노드 테두리
        nodeBorder: isDark ? '#6366f1' : '#818cf8',
        clusterBkg: isDark ? 'rgba(79, 70, 229, 0.1)' : 'rgba(99, 102, 241, 0.1)',
        clusterBorder: isDark ? '#6366f1' : '#818cf8',

        // 폰트
        fontFamily: "ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        fontSize: '15px',

        // 엣지 라벨
        edgeLabelBackground: isDark ? '#1e293b' : '#f8fafc',

        // 활성 상태 색상
        activeTaskBkgColor: isDark ? '#4f46e5' : '#6366f1',
        activeTaskBorderColor: isDark ? '#6366f1' : '#818cf8',

        // 그리드
        gridColor: isDark ? '#334155' : '#e2e8f0',

        // 시퀀스 다이어그램
        actorBkg: isDark ? '#4f46e5' : '#6366f1',
        actorBorder: isDark ? '#6366f1' : '#818cf8',
        actorTextColor: '#ffffff',
        actorLineColor: isDark ? '#64748b' : '#94a3b8',
        signalColor: isDark ? '#cbd5e1' : '#475569',
        signalTextColor: isDark ? '#e2e8f0' : '#1e293b',
        labelBoxBkgColor: isDark ? '#1e293b' : '#f8fafc',
        labelBoxBorderColor: isDark ? '#475569' : '#cbd5e1',
      },
      // 추가 여백 설정
      er: {
        useMaxWidth: true,
      },
      sequence: {
        useMaxWidth: true,
        wrap: true,
        width: 150,
        height: 60,
        boxMargin: 10,
        messageMargin: 35,
        mirrorActors: true,
        bottomMarginAdj: 1,
        actorFontSize: 14,
        noteFontSize: 13,
        messageFontSize: 13,
      },
      gantt: {
        useMaxWidth: true,
        fontSize: 13,
        barHeight: 20,
        barGap: 4,
        topPadding: 50,
        leftPadding: 80,
        gridLineStartPadding: 35,
        numberSectionStyles: 4,
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
        "mermaid-diagram-container",
        "rounded-xl bg-gradient-to-br from-muted/30 to-muted/50",
        "dark:from-zinc-900/50 dark:to-zinc-800/50",
        "backdrop-blur-sm",
        "p-4 sm:p-5 md:p-6",
        "border border-border/40 dark:border-zinc-700/50",
        "overflow-hidden max-w-full",
        "transition-all duration-300 ease-in-out",
        isLoading && "opacity-50 animate-pulse",
        className
      )}
      style={{
        maxWidth: '100%',
        // 부드러운 그라데이션 배경
        backgroundImage: document.documentElement.classList.contains('dark')
          ? 'linear-gradient(135deg, rgba(24, 24, 27, 0.5) 0%, rgba(39, 39, 42, 0.5) 100%)'
          : 'linear-gradient(135deg, rgba(248, 250, 252, 0.5) 0%, rgba(241, 245, 249, 0.5) 100%)',
      }}
    >
      <div
        ref={ref}
        className="flex items-center justify-center min-h-[200px] w-full"
      />
      {isLoading && (
        <div className="text-center text-sm text-muted-foreground py-4 flex items-center justify-center gap-2">
          <svg
            className="animate-spin h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <span>다이어그램 렌더링 중...</span>
        </div>
      )}
    </div>
  );
}

