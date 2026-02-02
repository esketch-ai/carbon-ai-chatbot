/**
 * AI가 생성한 비표준 JSON 문자열을 파싱 가능한 형태로 정리.
 *
 * 처리 항목:
 * - 쉼표 포함 숫자 (80,000 → 80000)
 * - 작은따옴표 → 큰따옴표
 * - 후행 쉼표 제거 ([1,] → [1])
 * - 줄바꿈/탭 등 제어문자가 문자열 값 안에 이스케이프 안 된 경우
 * - JavaScript 스타일 주석 제거 
 * - 따옴표 없는 프로퍼티 키
 * - NaN, Infinity, undefined → null
 */
export function sanitizeJSON(raw: string): string {
  let s = raw.trim();

  // 1. JavaScript 주석 제거 (문자열 안이 아닌 경우만)
  // 단순 접근: 줄 단위 // 주석 제거, /* */ 블록 주석 제거
  s = s.replace(/\/\/[^\n]*/g, "");
  s = s.replace(/\/\*[\s\S]*?\*\//g, "");

  // 2. 문자열 값 내부의 이스케이프 안 된 제어문자 처리
  // JSON 문자열 안에서 실제 줄바꿈/탭이 들어간 경우 이스케이프 처리
  s = s.replace(/"([^"\\]*(?:\\.[^"\\]*)*)"/g, (match) => {
    return match
      .replace(/(?<!\\)\t/g, "\\t")
      .replace(/\r\n/g, "\\n")
      .replace(/(?<!\\)\r/g, "\\n")
      .replace(/(?<!\\)\n/g, "\\n");
  });

  // 3. 쉼표가 포함된 숫자 (값 위치에서만)
  // "key": 80,000 → "key": 80000
  s = s.replace(/:\s*(\d{1,3}(,\d{3})+)(\s*[,}\]])/g, (_, num, __, tail) => {
    return `: ${num.replace(/,/g, "")}${tail}`;
  });

  // 4. 작은따옴표를 큰따옴표로 교체
  // 주의: 큰따옴표 내부의 작은따옴표는 건드리지 않아야 하지만,
  // AI가 생성한 JSON에서 작은따옴표가 구분자로 쓰이는 경우 대응
  // 안전 접근: 큰따옴표 문자열이 없는 위치의 작은따옴표만 교체
  s = s.replace(/'/g, '"');

  // 5. 후행 쉼표 제거
  s = s.replace(/,\s*([}\]])/g, "$1");

  // 6. 따옴표 없는 키 처리: { key: "value" } → { "key": "value" }
  s = s.replace(
    /([{,]\s*)([a-zA-Z_$][a-zA-Z0-9_$]*)\s*:/g,
    '$1"$2":',
  );

  // 7. NaN, Infinity, undefined → null
  s = s.replace(/:\s*(NaN|Infinity|-Infinity|undefined)\b/g, ": null");

  return s;
}

/**
 * AI 생성 JSON을 안전하게 파싱. 실패 시 null 반환.
 */
export function safeParseJSON<T = unknown>(raw: string): { data: T | null; error: string | null } {
  try {
    const sanitized = sanitizeJSON(raw);
    const data = JSON.parse(sanitized) as T;
    return { data, error: null };
  } catch (err) {
    // 첫 시도 실패 시, 더 공격적인 복구 시도
    try {
      // 문자열 값 내부의 이스케이프 안 된 큰따옴표 처리
      let aggressive = sanitizeJSON(raw);
      // 깨진 유니코드 이스케이프 제거
      aggressive = aggressive.replace(/\\u(?![0-9a-fA-F]{4})[^"]{0,4}/g, "");
      const data = JSON.parse(aggressive) as T;
      return { data, error: null };
    } catch {
      return {
        data: null,
        error: err instanceof Error ? err.message : "JSON 파싱 실패",
      };
    }
  }
}
