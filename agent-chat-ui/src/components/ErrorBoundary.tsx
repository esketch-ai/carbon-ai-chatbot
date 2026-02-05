'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home, ChevronDown, ChevronUp } from 'lucide-react';
import { logger } from '@/lib/logger';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
  showDetails: boolean;
}

/**
 * Global Error Boundary component for catching and handling React errors.
 * Provides a user-friendly error UI with retry functionality.
 */
export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    showDetails: false,
  };

  public static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error for debugging
    logger.error('ErrorBoundary caught error:', error, errorInfo);

    // Store error info for display
    this.setState({ errorInfo });

    // Here you can integrate with error tracking services like Sentry
    // Example:
    // if (typeof window !== 'undefined' && window.Sentry) {
    //   window.Sentry.captureException(error, { extra: errorInfo });
    // }
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
    this.props.onReset?.();
  };

  private handleRefresh = () => {
    if (typeof window !== 'undefined') {
      window.location.reload();
    }
  };

  private handleGoHome = () => {
    if (typeof window !== 'undefined') {
      window.location.href = '/';
    }
  };

  private toggleDetails = () => {
    this.setState(prev => ({ showDetails: !prev.showDetails }));
  };

  public render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const { error, errorInfo, showDetails } = this.state;

      return (
        <div className="min-h-screen flex items-center justify-center bg-background p-4">
          <div className="max-w-md w-full">
            {/* Error Card */}
            <div className="bg-card rounded-xl border border-border shadow-lg overflow-hidden">
              {/* Header with warning icon */}
              <div className="bg-destructive/10 dark:bg-destructive/20 p-6 flex flex-col items-center text-center">
                <div className="w-16 h-16 rounded-full bg-destructive/20 dark:bg-destructive/30 flex items-center justify-center mb-4">
                  <AlertTriangle className="w-8 h-8 text-destructive" />
                </div>
                <h2 className="text-xl font-semibold text-foreground">
                  문제가 발생했습니다
                </h2>
                <p className="text-sm text-muted-foreground mt-2">
                  예기치 않은 오류가 발생했습니다. 잠시 후 다시 시도해주세요.
                </p>
              </div>

              {/* Content */}
              <div className="p-6 space-y-4">
                {/* Error message preview */}
                {error?.message && (
                  <div className="bg-muted/50 rounded-lg p-3 border border-border">
                    <p className="text-sm text-muted-foreground font-mono truncate">
                      {error.message}
                    </p>
                  </div>
                )}

                {/* Action buttons */}
                <div className="flex flex-col gap-3">
                  <button
                    onClick={this.handleReset}
                    className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary text-primary-foreground px-4 py-2.5 text-sm font-medium shadow-sm hover:bg-primary/90 transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                  >
                    <RefreshCw className="w-4 h-4" />
                    다시 시도
                  </button>

                  <div className="flex gap-3">
                    <button
                      onClick={this.handleRefresh}
                      className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg border border-input bg-background px-4 py-2.5 text-sm font-medium shadow-sm hover:bg-accent hover:text-accent-foreground transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                    >
                      페이지 새로고침
                    </button>

                    <button
                      onClick={this.handleGoHome}
                      className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg border border-input bg-background px-4 py-2.5 text-sm font-medium shadow-sm hover:bg-accent hover:text-accent-foreground transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                    >
                      <Home className="w-4 h-4" />
                      홈으로
                    </button>
                  </div>
                </div>

                {/* Error details toggle */}
                {(error || errorInfo) && (
                  <div className="pt-2">
                    <button
                      onClick={this.toggleDetails}
                      className="w-full flex items-center justify-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {showDetails ? (
                        <>
                          <ChevronUp className="w-3 h-3" />
                          에러 세부사항 숨기기
                        </>
                      ) : (
                        <>
                          <ChevronDown className="w-3 h-3" />
                          에러 세부사항 보기
                        </>
                      )}
                    </button>

                    {showDetails && (
                      <div className="mt-3 space-y-3">
                        {/* Error stack */}
                        {error?.stack && (
                          <div className="bg-muted/50 rounded-lg p-3 border border-border overflow-hidden">
                            <p className="text-xs font-medium text-muted-foreground mb-2">
                              Error Stack:
                            </p>
                            <pre className="text-xs text-muted-foreground font-mono whitespace-pre-wrap break-all overflow-x-auto max-h-40 overflow-y-auto">
                              {error.stack}
                            </pre>
                          </div>
                        )}

                        {/* Component stack */}
                        {errorInfo?.componentStack && (
                          <div className="bg-muted/50 rounded-lg p-3 border border-border overflow-hidden">
                            <p className="text-xs font-medium text-muted-foreground mb-2">
                              Component Stack:
                            </p>
                            <pre className="text-xs text-muted-foreground font-mono whitespace-pre-wrap break-all overflow-x-auto max-h-40 overflow-y-auto">
                              {errorInfo.componentStack}
                            </pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Help text */}
            <p className="text-center text-xs text-muted-foreground mt-4">
              문제가 지속되면 관리자에게 문의하세요.
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Hook-based error boundary wrapper for functional components.
 * Usage: <ErrorBoundaryWrapper><YourComponent /></ErrorBoundaryWrapper>
 */
export function ErrorBoundaryWrapper({
  children,
  fallback,
  onReset,
}: Props) {
  return (
    <ErrorBoundary fallback={fallback} onReset={onReset}>
      {children}
    </ErrorBoundary>
  );
}

export default ErrorBoundary;
