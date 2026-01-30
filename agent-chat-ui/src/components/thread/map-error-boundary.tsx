"use client";

import React from "react";

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class MapErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("Map rendering error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="rounded-xl bg-muted/50 dark:bg-zinc-900 p-4 border border-yellow-500/30">
          <p className="text-sm text-yellow-600 dark:text-yellow-400">
            지도를 렌더링하는 중 문제가 발생했습니다.
          </p>
          <p className="text-xs text-muted-foreground mt-2">
            페이지를 새로고침하거나 다른 브라우저를 사용해보세요.
          </p>
          <details className="mt-2 text-xs text-muted-foreground">
            <summary className="cursor-pointer">에러 세부사항</summary>
            <pre className="mt-2 overflow-x-auto">
              {this.state.error?.message}
            </pre>
          </details>
        </div>
      );
    }

    return this.props.children;
  }
}
