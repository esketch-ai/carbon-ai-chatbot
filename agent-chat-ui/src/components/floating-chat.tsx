"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { X, MessageCircle, Maximize2, Minimize2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Thread } from "./thread";
import { ArtifactProvider } from "./thread/artifact";
import { Toaster } from "./ui/sonner";
import { SettingsProvider } from "@/providers/Settings";
import { StreamProvider } from "@/providers/Stream";
import { ThreadProvider } from "@/providers/Thread";
import { ChatConfig } from "@/lib/config";

interface FloatingChatProps {
  isOpen: boolean;
  onClose: () => void;
  initialConfig: ChatConfig;
}

export function FloatingChat({
  isOpen,
  onClose,
  initialConfig,
}: FloatingChatProps) {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [position, setPosition] = useState({ x: 100, y: 100 });
  const [size, setSize] = useState({ width: 800, height: 600 });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [resizeStart, setResizeStart] = useState({ x: 0, y: 0, width: 0, height: 0 });
  const windowRef = useRef<HTMLDivElement>(null);
  const headerRef = useRef<HTMLDivElement>(null);
  const savedStateRef = useRef<{ position: { x: number; y: number }; size: { width: number; height: number } } | null>(null);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  // 전체 화면/플로팅 모드 전환
  const toggleFullscreen = useCallback(() => {
    if (isFullscreen) {
      // 전체 화면 → 플로팅 모드: 저장된 상태 복원
      if (savedStateRef.current) {
        setPosition(savedStateRef.current.position);
        setSize(savedStateRef.current.size);
      }
      setIsFullscreen(false);
    } else {
      // 플로팅 모드 → 전체 화면: 현재 상태 저장
      savedStateRef.current = {
        position: { ...position },
        size: { ...size },
      };
      setIsFullscreen(true);
    }
  }, [isFullscreen, position, size]);

  // 드래그 시작
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (isFullscreen) return; // 전체 화면 모드에서는 드래그 불가
    if (headerRef.current?.contains(e.target as Node)) {
      // 버튼 클릭은 드래그로 처리하지 않음
      const target = e.target as HTMLElement;
      if (target.closest('button')) return;
      
      setIsDragging(true);
      setDragStart({
        x: e.clientX - position.x,
        y: e.clientY - position.y,
      });
    }
  }, [position, isFullscreen]);

  // 리사이즈 시작
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    if (isFullscreen) return; // 전체 화면 모드에서는 리사이즈 불가
    e.stopPropagation();
    setIsResizing(true);
    setResizeStart({
      x: e.clientX,
      y: e.clientY,
      width: size.width,
      height: size.height,
    });
  }, [size, isFullscreen]);

  // 마우스 이동 처리
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging) {
        const newX = e.clientX - dragStart.x;
        const newY = e.clientY - dragStart.y;
        
        // 화면 경계 체크
        const maxX = window.innerWidth - size.width;
        const maxY = window.innerHeight - size.height;
        
        setPosition({
          x: Math.max(0, Math.min(newX, maxX)),
          y: Math.max(0, Math.min(newY, maxY)),
        });
      } else if (isResizing) {
        const deltaX = e.clientX - resizeStart.x;
        const deltaY = e.clientY - resizeStart.y;
        
        const minWidth = 400;
        const minHeight = 300;
        const maxWidth = window.innerWidth - position.x;
        const maxHeight = window.innerHeight - position.y;
        
        setSize({
          width: Math.max(minWidth, Math.min(resizeStart.width + deltaX, maxWidth)),
          height: Math.max(minHeight, Math.min(resizeStart.height + deltaY, maxHeight)),
        });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setIsResizing(false);
    };

    if (isDragging || isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, isResizing, dragStart, resizeStart, size, position]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop - 플로팅 모드에서만 표시 */}
      {!isFullscreen && (
        <div
          className={cn(
            "fixed inset-0 bg-black/50 backdrop-blur-sm z-[9998] transition-opacity duration-300",
            isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
          )}
          onClick={onClose}
        />
      )}

      {/* Chat Window */}
      <div
        ref={windowRef}
        className={cn(
          "fixed z-[9999] bg-white dark:bg-zinc-900 shadow-2xl border border-border transition-all duration-300 flex flex-col",
          isFullscreen
            ? "inset-0 rounded-none"
            : "rounded-2xl",
          !isOpen && "opacity-0 pointer-events-none"
        )}
        style={
          isFullscreen
            ? {}
            : {
                left: `${position.x}px`,
                top: `${position.y}px`,
                width: `${size.width}px`,
                height: `${size.height}px`,
                cursor: isDragging ? "grabbing" : "default",
              }
        }
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          ref={headerRef}
          onMouseDown={handleMouseDown}
          className={cn(
            "flex-shrink-0 bg-gradient-to-r from-teal-600 via-teal-500 to-emerald-500 text-white px-4 sm:px-6 py-4 flex items-center justify-between border-b border-teal-400/30",
            isFullscreen ? "rounded-none" : "rounded-t-2xl",
            !isFullscreen && (isDragging ? "cursor-grabbing" : "cursor-grab")
          )}
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
              <MessageCircle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base sm:text-lg font-bold">후시봇</h3>
              <p className="text-xs text-white/80">AI 탄소배출 전문 상담</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={toggleFullscreen}
              className="w-9 h-9 rounded-lg bg-white/20 backdrop-blur-sm hover:bg-white/30 transition-colors flex items-center justify-center"
              aria-label={isFullscreen ? "플로팅 모드" : "전체 화면"}
            >
              {isFullscreen ? (
                <Minimize2 className="w-5 h-5" />
              ) : (
                <Maximize2 className="w-5 h-5" />
              )}
            </button>
            <button
              onClick={onClose}
              className="w-9 h-9 rounded-lg bg-white/20 backdrop-blur-sm hover:bg-white/30 transition-colors flex items-center justify-center"
              aria-label="닫기"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Chat Content */}
        <div className="flex-1 overflow-hidden relative">
          <Toaster />
          <SettingsProvider initialConfig={initialConfig}>
            <ThreadProvider>
              <StreamProvider>
                <ArtifactProvider>
                  <Thread />
                </ArtifactProvider>
              </StreamProvider>
            </ThreadProvider>
          </SettingsProvider>
        </div>

        {/* Resize Handle - 플로팅 모드에서만 표시 */}
        {!isFullscreen && (
          <div
            onMouseDown={handleResizeStart}
            className={cn(
              "absolute bottom-0 right-0 w-6 h-6 cursor-nwse-resize",
              "bg-transparent hover:bg-teal-500/20 transition-colors",
              "flex items-center justify-end pr-1 pb-1"
            )}
            style={{
              clipPath: "polygon(100% 0, 0 0, 100% 100%)",
            }}
          >
            <div className="w-3 h-3 border-r-2 border-b-2 border-teal-400/50 rounded-br-lg" />
          </div>
        )}
      </div>
    </>
  );
}

