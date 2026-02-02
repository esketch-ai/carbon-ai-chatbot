/**
 * 스트리밍 중 미완성 마크다운 요소를 감지하여 ReactMarkdown에 전달하기 전에 전처리하는 유틸리티.
 *
 * 처리 대상:
 * - 미완성 코드블록 (```)
 * - 미완성 마크다운 테이블 (| ... |)
 * - 줄 끝의 부분 펜스 (` 또는 ``)
 * - 불완전한 서로게이트 페어 (이모지)
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
  /** 미완성 테이블이 존재하는지 여부 */
  hasIncompleteTable: boolean;
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
 * 텍스트 끝부분에 미완성 마크다운 테이블이 있는지 감지하고,
 * 있다면 테이블 시작 지점과 완성 여부를 반환.
 *
 * 완성된 테이블 조건:
 * - 헤더 행 (| ... |)
 * - 구분자 행 (|---|---|)
 * - 최소 1개의 데이터 행
 * - 테이블 뒤에 빈 줄이 있거나 테이블이 아닌 텍스트가 이어짐
 *
 * 미완성 판정:
 * - 텍스트가 테이블 행으로 끝남 (마지막 줄이 | 로 시작)
 * - 구분자 행이 아직 안 왔거나, 테이블이 아직 작성 중
 */
function detectIncompleteTable(text: string): {
  isIncomplete: boolean;
  tableStartIndex: number;
} {
  const lines = text.split("\n");

  // 뒤에서부터 테이블 행이 이어지는 구간을 찾음
  let tableEndLine = -1;
  for (let i = lines.length - 1; i >= 0; i--) {
    const trimmed = lines[i].trim();
    if (trimmed.startsWith("|")) {
      if (tableEndLine === -1) tableEndLine = i;
    } else {
      break;
    }
  }

  // 테이블 행이 없으면 미완성 아님
  if (tableEndLine === -1) {
    return { isIncomplete: false, tableStartIndex: -1 };
  }

  // 테이블의 시작 줄 찾기 (연속된 | 줄의 첫번째)
  let tableStartLine = tableEndLine;
  for (let i = tableEndLine; i >= 0; i--) {
    const trimmed = lines[i].trim();
    if (trimmed.startsWith("|")) {
      tableStartLine = i;
    } else {
      break;
    }
  }

  // 테이블 줄들 추출
  const tableLines = lines.slice(tableStartLine, tableEndLine + 1);

  // 구분자 행이 있는지 확인 (|---|---|  또는  | --- | --- |)
  const hasSeparator = tableLines.some((line) =>
    /^\|[\s\-:|]+\|$/.test(line.trim()),
  );

  // 텍스트의 마지막이 테이블 행으로 끝나면 → 아직 작성 중
  const lastLine = lines[lines.length - 1].trim();
  const endsWithTableRow = lastLine.startsWith("|");

  // 미완성 판정: 마지막 줄이 테이블이고, (구분자가 없거나 테이블이 끝나지 않은 경우)
  // 구분자가 있어도 텍스트가 테이블 행으로 끝나면 아직 행이 추가될 수 있음
  if (endsWithTableRow) {
    // 구분자가 없으면 확실히 미완성 (헤더만 있거나 구분자 작성 중)
    if (!hasSeparator) {
      const charOffset = lines.slice(0, tableStartLine).join("\n").length;
      const startIndex = tableStartLine === 0 ? 0 : charOffset + 1;
      return { isIncomplete: true, tableStartIndex: startIndex };
    }

    // 구분자가 있고, 마지막 줄이 불완전한 행인지 확인
    // (닫는 | 가 없는 경우)
    if (!lastLine.endsWith("|")) {
      const charOffset = lines.slice(0, tableStartLine).join("\n").length;
      const startIndex = tableStartLine === 0 ? 0 : charOffset + 1;
      return { isIncomplete: true, tableStartIndex: startIndex };
    }
  }

  return { isIncomplete: false, tableStartIndex: -1 };
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
  const defaultResult: PreprocessResult = {
    processed: text,
    hasIncompleteCodeBlock: false,
    language: null,
    hasIncompleteTable: false,
  };

  // 스트리밍이 아닌 경우 원본 그대로 반환
  if (!isStreaming) {
    return defaultResult;
  }

  if (!text) {
    return { ...defaultResult, processed: "" };
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
      hasIncompleteTable: false,
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

  // 미완성 코드블록이 있으면 잘라냄
  if (openFenceIndex !== -1) {
    const safeText = text.slice(0, openFenceIndex).trimEnd();

    return {
      processed: safeText,
      hasIncompleteCodeBlock: true,
      language: openLanguage,
      hasIncompleteTable: false,
    };
  }

  // 미완성 테이블 감지
  const tableResult = detectIncompleteTable(text);
  if (tableResult.isIncomplete) {
    const safeText = text.slice(0, tableResult.tableStartIndex).trimEnd();

    return {
      processed: safeText,
      hasIncompleteCodeBlock: false,
      language: null,
      hasIncompleteTable: true,
    };
  }

  return defaultResult;
}
