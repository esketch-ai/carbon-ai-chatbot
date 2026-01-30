import { useState, useMemo } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

interface ChatOpenersProps {
  chatOpeners: string[];
  onSelectOpener: (opener: string) => void;
  disabled: boolean;
}

// CarbonAI 웰컴 옵션 정의
const WELCOME_OPTIONS = [
  {
    icon: "🏢",
    text: "배출권 보유 관리",
    desc: "보유 배출권 활용 방법 안내",
    keywords: ["보유", "활용", "가지고"],
  },
  {
    icon: "💰",
    text: "배출권 구매 상담",
    desc: "구매 절차 및 가격 정보",
    keywords: ["구매", "사고", "매수"],
  },
  {
    icon: "📊",
    text: "배출권 판매 상담",
    desc: "판매 절차 및 시장 분석",
    keywords: ["판매", "팔고", "매도"],
  },
  {
    icon: "📚",
    text: "배출권 기본 정보",
    desc: "배출권 개념 및 유형 안내",
    keywords: ["기본", "개념", "유형"],
  },
  {
    icon: "🔍",
    text: "NET-Z 플랫폼 안내",
    desc: "플랫폼 사용법 및 기능 소개",
    keywords: ["플랫폼", "NET-Z", "사용법"],
  },
];

// 옵션과 텍스트 매칭 함수
function matchOpenerToOption(opener: string) {
  const openerLower = opener.toLowerCase();
  for (const option of WELCOME_OPTIONS) {
    if (option.keywords.some((kw) => openerLower.includes(kw.toLowerCase()))) {
      return option;
    }
  }
  // 매칭되지 않으면 첫 번째 옵션 반환
  return null;
}

export function ChatOpeners({ chatOpeners, onSelectOpener, disabled }: ChatOpenersProps) {
  const [currentPage, setCurrentPage] = useState(0);
  const itemsPerPage = 4;
  const totalPages = Math.ceil(chatOpeners.length / itemsPerPage);
  const shouldShowCarousel = chatOpeners.length > itemsPerPage;

  const currentItems = useMemo(() => {
    const startIndex = currentPage * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return chatOpeners.slice(startIndex, endIndex);
  }, [currentPage, chatOpeners, itemsPerPage]);

  const goToNextPage = () => {
    setCurrentPage((prev) => (prev + 1) % totalPages);
  };

  const goToPrevPage = () => {
    setCurrentPage((prev) => (prev - 1 + totalPages) % totalPages);
  };

  const openerButtonHandler = (opener: string) => () => {
    if (disabled) {
      return;
    }
    onSelectOpener(opener);
  };

  return (
    <div className="flex flex-col gap-4 w-full max-w-4xl mx-auto">
      {/* 웰컴 헤더 */}
      <div className="text-center mb-2">
        <div className="text-4xl mb-2">🌍</div>
        <h2 className="text-2xl font-bold bg-gradient-to-r from-teal-600 to-emerald-600 bg-clip-text text-transparent mb-2">
          안녕하세요! CarbonAI입니다
        </h2>
        <p className="text-sm text-muted-foreground">
          탄소배출 관리부터 배출권 거래까지<br />
          전문적으로 안내해드립니다
        </p>
      </div>

      <div className="relative">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentPage}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="grid grid-cols-1 sm:grid-cols-2 gap-3"
          >
            {currentItems.map((opener, index) => {
              const option = matchOpenerToOption(opener);
              const displayIcon = option?.icon || "💬";
              const displayText = option?.text || opener.split(" - ")[0] || opener;
              const displayDesc = option?.desc || opener.split(" - ")[1] || "";

              return (
                <button
                  key={`${currentPage}-${index}`}
                  onClick={openerButtonHandler(opener)}
                  disabled={disabled}
                  className={cn(
                    "group relative overflow-hidden rounded-2xl border-2 border-teal-100 dark:border-teal-900",
                    "bg-gradient-to-br from-white to-teal-50/50 dark:from-gray-900 dark:to-teal-950/30",
                    "hover:border-teal-400 dark:hover:border-teal-600",
                    "hover:shadow-lg hover:shadow-teal-200/50 dark:hover:shadow-teal-900/20",
                    "transition-all duration-300 p-5 text-left",
                    "min-h-[6rem] flex items-start gap-4 cursor-pointer",
                    "hover:scale-[1.02] active:scale-[0.98]",
                    disabled && "opacity-50 cursor-not-allowed hover:scale-100"
                  )}
                >
                  {/* 아이콘 */}
                  <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-gradient-to-br from-teal-100 to-emerald-100 dark:from-teal-900 dark:to-emerald-900 flex items-center justify-center text-2xl shadow-sm">
                    {displayIcon}
                  </div>

                  {/* 텍스트 영역 */}
                  <div className="flex-1 min-w-0">
                    <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-1 group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                      {displayText}
                    </h3>
                    {displayDesc && (
                      <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">
                        {displayDesc}
                      </p>
                    )}
                  </div>

                  {/* 호버 효과 배경 */}
                  <div className="absolute inset-0 bg-gradient-to-br from-teal-500/5 to-emerald-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
                </button>
              );
            })}
          </motion.div>
        </AnimatePresence>
      </div>

      {shouldShowCarousel && (
        <div className="flex items-center justify-center gap-2 mt-2">
          <button
            onClick={goToPrevPage}
            className="flex h-8 w-8 items-center justify-center rounded-full border border-teal-200 dark:border-teal-800 bg-white dark:bg-gray-900 hover:bg-teal-50 dark:hover:bg-teal-950 transition-colors"
            aria-label="Previous page"
          >
            <ChevronLeft className="h-4 w-4 text-teal-600 dark:text-teal-400" />
          </button>

          <div className="flex items-center gap-1.5">
            {Array.from({ length: totalPages }).map((_, index) => (
              <button
                key={index}
                onClick={() => setCurrentPage(index)}
                className={cn(
                  "h-2 rounded-full transition-all",
                  index === currentPage
                    ? "w-6 bg-teal-500 dark:bg-teal-400"
                    : "w-2 bg-teal-200/50 dark:bg-teal-800/50 hover:bg-teal-300 dark:hover:bg-teal-700"
                )}
                aria-label={`Go to page ${index + 1}`}
              />
            ))}
          </div>

          <button
            onClick={goToNextPage}
            className="flex h-8 w-8 items-center justify-center rounded-full border border-teal-200 dark:border-teal-800 bg-white dark:bg-gray-900 hover:bg-teal-50 dark:hover:bg-teal-950 transition-colors"
            aria-label="Next page"
          >
            <ChevronRight className="h-4 w-4 text-teal-600 dark:text-teal-400" />
          </button>
        </div>
      )}
    </div>
  );
}
