import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

interface Category {
  icon: string;
  description: string;
  openers: string[];
}

interface CategorySelectorsProps {
  categories: {
    [key: string]: Category;
  };
  onSelectCategory: (categoryName: string, opener: string) => void;
  disabled: boolean;
}

export function CategorySelectors({
  categories,
  onSelectCategory,
  disabled,
}: CategorySelectorsProps) {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(0);
  const itemsPerPage = 4;

  const categoryNames = Object.keys(categories);
  const selectedCategoryData = selectedCategory
    ? categories[selectedCategory]
    : null;

  const currentOpeners = selectedCategoryData
    ? selectedCategoryData.openers.slice(
        currentPage * itemsPerPage,
        (currentPage + 1) * itemsPerPage
      )
    : [];
  const totalPages = selectedCategoryData
    ? Math.ceil(selectedCategoryData.openers.length / itemsPerPage)
    : 0;
  const shouldShowCarousel = totalPages > 1;

  const goToNextPage = () => {
    setCurrentPage((prev) => (prev + 1) % totalPages);
  };

  const goToPrevPage = () => {
    setCurrentPage((prev) => (prev - 1 + totalPages) % totalPages);
  };

  const handleCategoryClick = (categoryName: string) => {
    if (disabled) return;
    setSelectedCategory(categoryName);
    setCurrentPage(0);
  };

  const handleOpenerClick = (opener: string) => {
    if (disabled || !selectedCategory) return;
    onSelectCategory(selectedCategory, opener);
  };

  const handleBack = () => {
    setSelectedCategory(null);
    setCurrentPage(0);
  };

  return (
    <div className="flex flex-col gap-6 w-full max-w-5xl mx-auto px-4">
      {/* 웰컴 헤더 */}
      <div className="text-center mb-4">
        <div className="text-5xl mb-3">🌍</div>
        <h2 className="text-3xl font-bold bg-gradient-to-r from-teal-600 to-emerald-600 bg-clip-text text-transparent mb-2">
          안녕하세요! CarbonAI입니다
        </h2>
        <p className="text-sm text-muted-foreground">
          탄소배출 관리부터 배출권 거래까지<br />
          전문적으로 안내해드립니다
        </p>
      </div>

      {!selectedCategory ? (
        /* 카테고리 선택 화면 */
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {categoryNames.map((categoryName) => {
            const category = categories[categoryName];
            return (
              <motion.button
                key={categoryName}
                onClick={() => handleCategoryClick(categoryName)}
                disabled={disabled}
                className={cn(
                  "group relative overflow-hidden rounded-2xl border-2",
                  "bg-gradient-to-br from-white to-teal-50/50 dark:from-gray-900 dark:to-teal-950/30",
                  "border-teal-200 dark:border-teal-800",
                  "hover:border-teal-400 dark:hover:border-teal-600",
                  "hover:shadow-xl hover:shadow-teal-200/50 dark:hover:shadow-teal-900/20",
                  "transition-all duration-300 p-6 text-center",
                  "min-h-[10rem] flex flex-col items-center justify-center gap-3 cursor-pointer",
                  "hover:scale-[1.02] active:scale-[0.98]",
                  disabled && "opacity-50 cursor-not-allowed hover:scale-100"
                )}
                whileHover={{ y: -4 }}
                whileTap={{ scale: 0.98 }}
              >
                {/* 아이콘 */}
                <div className="text-5xl mb-2">{category.icon}</div>

                {/* 제목 */}
                <h3 className="text-xl font-bold text-gray-900 dark:text-gray-100 group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                  {categoryName}
                </h3>

                {/* 설명 */}
                <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                  {category.description}
                </p>

                {/* 호버 효과 배경 */}
                <div className="absolute inset-0 bg-gradient-to-br from-teal-500/5 to-emerald-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
              </motion.button>
            );
          })}
        </div>
      ) : (
        /* 선택된 카테고리의 질문 오프너 화면 */
        <div className="flex flex-col gap-4">
          {/* 뒤로가기 버튼 */}
          <button
            onClick={handleBack}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors self-start"
          >
            <ChevronLeft className="h-4 w-4" />
            카테고리 선택으로 돌아가기
          </button>

          {/* 카테고리 헤더 */}
          <div className="text-center mb-4">
            <div className="text-4xl mb-2">
              {selectedCategoryData?.icon}
            </div>
            <h3 className="text-2xl font-bold text-foreground mb-1">
              {selectedCategory}
            </h3>
            <p className="text-sm text-muted-foreground">
              {selectedCategoryData?.description}
            </p>
          </div>

          {/* 질문 오프너 그리드 */}
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
                {currentOpeners.map((opener, index) => (
                  <button
                    key={`${currentPage}-${index}`}
                    onClick={() => handleOpenerClick(opener)}
                    disabled={disabled}
                    className={cn(
                      "group relative overflow-hidden rounded-xl border-2",
                      "bg-gradient-to-br from-white to-teal-50/50 dark:from-gray-900 dark:to-teal-950/30",
                      "border-teal-100 dark:border-teal-900",
                      "hover:border-teal-400 dark:hover:border-teal-600",
                      "hover:shadow-lg hover:shadow-teal-200/50 dark:hover:shadow-teal-900/20",
                      "transition-all duration-300 p-4 text-left",
                      "min-h-[5rem] flex items-center cursor-pointer",
                      "hover:scale-[1.02] active:scale-[0.98]",
                      disabled && "opacity-50 cursor-not-allowed hover:scale-100"
                    )}
                  >
                    <p className="text-sm text-foreground group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                      {opener}
                    </p>
                    <div className="absolute inset-0 bg-gradient-to-br from-teal-500/5 to-emerald-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
                  </button>
                ))}
              </motion.div>
            </AnimatePresence>
          </div>

          {/* 페이지네이션 */}
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
      )}
    </div>
  );
}

