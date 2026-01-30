/**
 * 스트리밍 중 불완전한 시각화 코드 블록을 처리하는 유틸리티
 */

// 시각화 컴포넌트로 렌더링되는 언어들
const VISUALIZATION_LANGUAGES = ['agchart', 'aggrid', 'mermaid', 'map', 'geomap', 'deckgl'];

interface CodeBlockInfo {
  isComplete: boolean;
  language: string | null;
  startIndex: number;
  endIndex: number;
  content: string;
}

/**
 * 텍스트에서 코드 블록들을 찾아 분석
 */
function findCodeBlocks(text: string): CodeBlockInfo[] {
  const blocks: CodeBlockInfo[] = [];
  const codeBlockRegex = /```(\w*)\n?([\s\S]*?)(?:```|$)/g;
  let match;

  while ((match = codeBlockRegex.exec(text)) !== null) {
    const fullMatch = match[0];
    const language = match[1] || null;
    const content = match[2] || '';
    const isComplete = fullMatch.endsWith('```');

    blocks.push({
      isComplete,
      language,
      startIndex: match.index,
      endIndex: match.index + fullMatch.length,
      content,
    });
  }

  return blocks;
}

/**
 * 불완전한 시각화 코드 블록이 있는지 확인
 */
export function hasIncompleteVisualizationBlock(text: string): boolean {
  const blocks = findCodeBlocks(text);
  return blocks.some(
    block => !block.isComplete &&
    block.language &&
    VISUALIZATION_LANGUAGES.includes(block.language.toLowerCase())
  );
}

/**
 * 현재 진행 중인 시각화 언어 반환 (없으면 null)
 */
export function getIncompleteVisualizationLanguage(text: string): string | null {
  const blocks = findCodeBlocks(text);
  const incompleteBlock = blocks.find(
    block => !block.isComplete &&
    block.language &&
    VISUALIZATION_LANGUAGES.includes(block.language.toLowerCase())
  );
  return incompleteBlock?.language || null;
}

/**
 * 불완전한 시각화 코드 블록을 플레이스홀더로 교체
 * 완전한 코드 블록은 그대로 유지
 */
export function filterIncompleteVisualizationBlocks(text: string): {
  filteredText: string;
  pendingLanguage: string | null;
} {
  if (!text) {
    return { filteredText: '', pendingLanguage: null };
  }

  const blocks = findCodeBlocks(text);
  let pendingLanguage: string | null = null;
  let result = text;

  // 뒤에서부터 처리해야 인덱스가 밀리지 않음
  for (let i = blocks.length - 1; i >= 0; i--) {
    const block = blocks[i];

    if (!block.isComplete && block.language &&
        VISUALIZATION_LANGUAGES.includes(block.language.toLowerCase())) {
      // 불완전한 시각화 블록 제거
      pendingLanguage = block.language;
      result = result.substring(0, block.startIndex) + result.substring(block.endIndex);
    }
  }

  return { filteredText: result.trim(), pendingLanguage };
}

/**
 * 시각화 언어별 로딩 메시지
 */
export function getVisualizationLoadingMessage(language: string): string {
  const messages: Record<string, string> = {
    agchart: '차트 생성 중...',
    aggrid: '테이블 생성 중...',
    mermaid: '다이어그램 생성 중...',
    map: '지도 생성 중...',
    geomap: '지도 생성 중...',
    deckgl: '지도 생성 중...',
  };
  return messages[language.toLowerCase()] || '시각화 생성 중...';
}
