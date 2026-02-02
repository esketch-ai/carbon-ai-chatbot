import { useState, useEffect, useRef, useMemo } from "react";

interface UseTypingEffectOptions {
  /** 타이핑 속도 (ms per character) */
  speed?: number;
  /** 타이핑 효과 활성화 여부 */
  enabled?: boolean;
  /** 완료 콜백 */
  onComplete?: () => void;
}

/**
 * 코드 블록과 이미지를 제외한 안전한 표시 위치를 찾습니다.
 * 미완성 코드 블록이나 이미지는 표시하지 않습니다.
 */
function getSafeDisplayIndex(text: string, currentIndex: number): number {
  const displayText = text.slice(0, currentIndex);

  // 코드 블록 체크: ```로 시작하는 블록
  const codeBlockPattern = /```/g;
  const matches = [...displayText.matchAll(codeBlockPattern)];

  // 코드 블록이 홀수개면 아직 닫히지 않은 블록이 있음
  if (matches.length % 2 === 1) {
    // 마지막 열린 코드 블록 시작 위치 찾기
    const lastOpenIndex = matches[matches.length - 1].index!;
    return lastOpenIndex;
  }

  // 이미지 패턴 체크: ![...](...) 형태
  // 미완성 이미지 링크 확인
  const lastExclamation = displayText.lastIndexOf('![');
  if (lastExclamation !== -1) {
    const afterExclamation = displayText.slice(lastExclamation);
    // ![...] 패턴이 시작됐지만 완성되지 않은 경우
    const hasClosingBracket = afterExclamation.includes(']');
    const hasClosingParen = afterExclamation.includes(')');

    if (!hasClosingBracket || !hasClosingParen) {
      // 이미지 문법이 완성되지 않았으면 그 전까지만 표시
      return lastExclamation;
    }

    // ]( 패턴 확인 - 링크 부분이 시작됐는지
    if (hasClosingBracket && !hasClosingParen) {
      return lastExclamation;
    }
  }

  // 인라인 코드 체크: ` 로 감싸진 부분
  const backtickCount = (displayText.match(/(?<!`)`(?!`)/g) || []).length;
  if (backtickCount % 2 === 1) {
    // 마지막 열린 백틱 위치
    const lastBacktick = displayText.lastIndexOf('`');
    // 코드 블록(```)이 아닌 단일 백틱인 경우만
    if (lastBacktick > 0 && displayText[lastBacktick - 1] !== '`') {
      return lastBacktick;
    }
  }

  return currentIndex;
}

/**
 * ChatGPT 스타일의 타이핑 효과를 제공하는 훅
 * 일반 텍스트만 점진적으로 표시하고, 코드 블록/이미지는 완성 후 한 번에 표시합니다.
 */
export function useTypingEffect(
  text: string,
  options: UseTypingEffectOptions = {}
) {
  const { speed = 15, enabled = true, onComplete } = options;

  const [rawIndex, setRawIndex] = useState(0);
  const [isTyping, setIsTyping] = useState(false);
  const previousTextRef = useRef("");
  const animationRef = useRef<number | null>(null);

  // 안전한 표시 텍스트 계산
  const displayedText = useMemo(() => {
    if (!enabled) return text;
    if (!text) return "";

    const safeIndex = getSafeDisplayIndex(text, rawIndex);
    return text.slice(0, safeIndex);
  }, [text, rawIndex, enabled]);

  useEffect(() => {
    // 타이핑 효과가 비활성화되면 전체 텍스트를 바로 표시
    if (!enabled) {
      setRawIndex(text.length);
      setIsTyping(false);
      return;
    }

    // 텍스트가 비어있으면 초기화
    if (!text) {
      setRawIndex(0);
      setIsTyping(false);
      previousTextRef.current = "";
      return;
    }

    // 텍스트가 이전과 같으면 아무것도 하지 않음
    if (text === previousTextRef.current) {
      return;
    }

    // 시작 인덱스 결정
    let startIndex = 0;
    if (text.startsWith(previousTextRef.current) && previousTextRef.current.length > 0) {
      // 이전 텍스트에서 이어서 타이핑
      startIndex = previousTextRef.current.length;
    } else {
      // 완전히 새로운 텍스트 - 처음부터 시작
      setRawIndex(0);
    }

    previousTextRef.current = text;
    setIsTyping(true);

    // 이전 애니메이션 취소
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }

    let currentIdx = startIndex;
    let lastTime = performance.now();

    const animate = (currentTime: number) => {
      const elapsed = currentTime - lastTime;

      if (elapsed >= speed) {
        const charsToAdd = Math.floor(elapsed / speed);
        const newIndex = Math.min(currentIdx + charsToAdd, text.length);

        if (newIndex > currentIdx) {
          currentIdx = newIndex;
          setRawIndex(newIndex);
          lastTime = currentTime;
        }

        if (currentIdx >= text.length) {
          setIsTyping(false);
          onComplete?.();
          return;
        }
      }

      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [text, speed, enabled, onComplete]);

  return {
    displayedText,
    isTyping,
    isComplete: displayedText === text,
  };
}
