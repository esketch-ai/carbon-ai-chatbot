"use client";

import React from "react";
import { MessageCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatBannerProps {
  onClick: () => void;
  className?: string;
}

export function ChatBanner({ onClick, className }: ChatBannerProps) {
  return (
    <div
      className={cn(
        "fixed bottom-0 left-0 right-0 z-[9997] bg-gradient-to-r from-teal-600 via-teal-500 to-emerald-500 shadow-2xl border-t border-teal-400/30",
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 py-4 sm:py-5">
        <button
          onClick={onClick}
          className="w-full flex items-center justify-between gap-4 p-4 sm:p-5 rounded-2xl bg-white/10 backdrop-blur-md hover:bg-white/20 transition-all duration-300 border border-white/20 hover:border-white/30 group cursor-pointer"
        >
          <div className="flex items-center gap-4 flex-1">
            <div className="flex-shrink-0 w-12 h-12 sm:w-14 sm:h-14 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center group-hover:bg-white/30 transition-colors">
              <MessageCircle className="w-6 h-6 sm:w-7 sm:h-7 text-white" />
            </div>
            <div className="flex-1 text-left">
              <h3 className="text-base sm:text-lg font-bold text-white mb-1">
                AI 탄소배출 전문 상담
              </h3>
              <p className="text-xs sm:text-sm text-white/90">
                궁금한 점을 물어보세요. 24시간 언제든지 도와드립니다.
              </p>
            </div>
          </div>
          <div className="flex-shrink-0">
            <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center group-hover:bg-white/30 transition-colors">
              <svg
                className="w-4 h-4 sm:w-5 sm:h-5 text-white transform group-hover:translate-x-1 transition-transform"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </div>
          </div>
        </button>
      </div>
    </div>
  );
}

