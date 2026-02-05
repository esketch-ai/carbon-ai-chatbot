"""사용자 입력 검증 및 정제"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# 위험한 패턴 목록
DANGEROUS_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+(instructions?|prompts?)",
    r"disregard\s+(all\s+)?previous",
    r"override\s+(system|instructions?)",
    r"you\s+are\s+now\s+a",
    r"pretend\s+(to\s+be|you\s+are)",
    r"system\s*:\s*",
    r"assistant\s*:\s*",
    r"\[INST\]",
    r"\[/INST\]",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
]

# 컴파일된 패턴
COMPILED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in DANGEROUS_PATTERNS
]


def detect_prompt_injection(message: str) -> Tuple[bool, str]:
    """프롬프트 인젝션 시도 감지"""
    for pattern in COMPILED_PATTERNS:
        match = pattern.search(message)
        if match:
            logger.warning(f"[보안] 프롬프트 인젝션 시도 감지: '{match.group()}'")
            return True, match.group()
    return False, ""


def sanitize_user_input(message: str, strict: bool = False) -> str:
    """사용자 입력 정제"""
    is_dangerous, pattern = detect_prompt_injection(message)

    if is_dangerous:
        if strict:
            raise ValueError(f"잠재적으로 위험한 입력이 감지되었습니다: {pattern}")
        logger.warning(f"[보안] 위험 패턴 감지됨 (비엄격 모드): {pattern}")

    # 기본 정제
    sanitized = re.sub(r'\s+', ' ', message).strip()

    # 최대 길이 제한 (10,000자)
    max_length = 10000
    if len(sanitized) > max_length:
        logger.warning(f"[보안] 입력이 너무 깁니다: {len(sanitized)}자 → {max_length}자로 자름")
        sanitized = sanitized[:max_length]

    return sanitized
