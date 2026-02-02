/**
 * 스트리밍 중 미완성 코드블록을 감지하여 ReactMarkdown에 전달하기 전에 전처리하는 유틸리티.
 *
 * - 백틱 펜스(```)를 순회하며 열림/닫힘 추적
 * - 미완성 코드블록 발견 시 해당 부분을 잘라냄
 * - 줄 끝의 부분 펜스(` 또는 ``)도 처리
 */

// 시각화 컴포넌트로 렌더링되는 언어 목록
const VISUALIZATION_LANGUAGES = [
  "agchart",
  "aggrid",
  "mermaid",
  "map",
  "geomap",
  "deckgl",
];

export interface PreprocessResult {
  /** ReactMarkdown에 전달할 안전한 텍스트 */
  processed: string;
  /** 미완성 코드블록이 존재하는지 여부 */
  hasIncompleteCodeBlock: boolean;
  /** 미완성 코드블록의 언어 (없으면 null) */
  language: string | null;
}

/**
 * 시각화 언어별 로딩 메시지
 */
export function getVisualizationLabel(language: string): string {
  const labels: Record<string, string> = {
    agchart: "차트 시각화",
    aggrid: "테이블",
    mermaid: "다이어그램",
    map: "지도",
    geomap: "지도",
    deckgl: "지도",
  };
  return labels[language.toLowerCase()] || "시각화";
}

/**
 * 스트리밍 텍스트를 ReactMarkdown에 넘기기 전에 전처리.
 *
 * isStreaming === false 이면 전처리 없이 원본 그대로 반환.
 */
export function preprocessStreamingMarkdown(
  text: string,
  isStreaming: boolean,
): PreprocessResult {
  // 스트리밍이 아닌 경우 원본 그대로 반환
  if (!isStreaming) {
    return { processed: text, hasIncompleteCodeBlock: false, language: null };
  }

  if (!text) {
    return { processed: "", hasIncompleteCodeBlock: false, language: null };
  }

  // 불완전한 서로게이트 페어(이모지 등) 처리:
  // UTF-16에서 이모지는 2개의 코드유닛(서로게이트 페어)으로 구성됨.
  // 스트리밍 토큰 경계에서 high surrogate만 도착하고 low가 아직 안 온 경우
  // 깨진 문자가 보이므로, 끝의 불완전한 서로게이트를 잘라냄.
  let safeEnd = text.length;
  if (safeEnd > 0) {
    const lastChar = text.charCodeAt(safeEnd - 1);
    // High surrogate (0xD800-0xDBFF) 이면서 뒤에 low surrogate가 없는 경우
    if (lastChar >= 0xD800 && lastChar <= 0xDBFF) {
      safeEnd -= 1;
    }
  }
  if (safeEnd !== text.length) {
    text = text.slice(0, safeEnd);
  }

  // 줄 끝의 부분 펜스 처리: 줄 끝이 ` 또는 ``로 끝나면서
  // 코드블록 펜스의 시작일 수 있는 경우 잘라냄
  const partialFenceMatch = text.match(/\n(`{1,2})$/);
  if (partialFenceMatch) {
    const trimmed = text.slice(0, -partialFenceMatch[1].length);
    return {
      processed: trimmed,
      hasIncompleteCodeBlock: false,
      language: null,
    };
  }

  // 백틱 펜스를 순회하며 열림/닫힘 추적
  const fenceRegex = /^```(\w*)/gm;
  let openFenceIndex = -1;
  let openLanguage: string | null = null;
  let fenceCount = 0;
  let match: RegExpExecArray | null;

  while ((match = fenceRegex.exec(text)) !== null) {
    fenceCount++;
    if (fenceCount % 2 === 1) {
      // 홀수번째 = 열림 펜스
      openFenceIndex = match.index;
      openLanguage = match[1] || null;
    } else {
      // 짝수번째 = 닫힘 펜스 → 블록 완성
      openFenceIndex = -1;
      openLanguage = null;
    }
  }

  // 열린 펜스가 없으면 그대로 반환
  if (openFenceIndex === -1) {
    return { processed: text, hasIncompleteCodeBlock: false, language: null };
  }

  // 미완성 코드블록이 시각화 언어인지 확인
  const isVisualization =
    openLanguage !== null &&
    VISUALIZATION_LANGUAGES.includes(openLanguage.toLowerCase());

  // 미완성 코드블록 부분을 잘라냄
  const safeText = text.slice(0, openFenceIndex).trimEnd();

  return {
    processed: safeText,
    hasIncompleteCodeBlock: true,
    language: isVisualization ? openLanguage : openLanguage,
  };
}
