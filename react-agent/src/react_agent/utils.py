"""Utility & helper functions."""

import re
import zlib
import base64
import logging
from typing import Tuple, Optional, List, Dict, Any
from collections import Counter

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

logger = logging.getLogger(__name__)


def get_message_text(msg: BaseMessage) -> str:
    """Get the text content of a message."""
    content = msg.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    else:
        txts = [c if isinstance(c, str) else (c.get("text") or "") for c in content]
        return "".join(txts).strip()


def load_chat_model(fully_specified_name: str) -> BaseChatModel:
    """Load a chat model from a fully specified name.

    Args:
        fully_specified_name (str): String in the format 'provider/model'.
    """
    provider, model = fully_specified_name.split("/", maxsplit=1)
    return init_chat_model(model, model_provider=provider)


def mermaid_to_image_url(mermaid_code: str, output_format: str = "svg") -> str:
    """Mermaid 코드를 kroki.io API를 사용하여 이미지 URL로 변환합니다.

    kroki.io는 무료 다이어그램 렌더링 서비스로, 서버 설치 없이 사용 가능합니다.

    Args:
        mermaid_code: Mermaid 다이어그램 코드
        output_format: 출력 형식 ("svg", "png", "pdf")

    Returns:
        이미지 URL (kroki.io 형식)
    """
    # mermaid 코드 정리 (앞뒤 공백 제거)
    mermaid_code = mermaid_code.strip()

    # zlib으로 압축 후 base64 인코딩 (URL-safe)
    compressed = zlib.compress(mermaid_code.encode('utf-8'), level=9)
    encoded = base64.urlsafe_b64encode(compressed).decode('ascii')

    # kroki.io URL 생성
    url = f"https://kroki.io/mermaid/{output_format}/{encoded}"

    logger.debug(f"[Mermaid] Generated kroki.io URL: {url[:100]}...")
    return url


def extract_mermaid_blocks(content: str) -> list[Tuple[str, str, int, int]]:
    """텍스트에서 mermaid 코드 블록을 추출합니다.

    Args:
        content: 검색할 텍스트

    Returns:
        [(full_match, mermaid_code, start_pos, end_pos), ...] 형식의 리스트
    """
    # ```mermaid ... ``` 패턴 매칭
    pattern = r'```mermaid\s*\n(.*?)```'
    matches = []

    for match in re.finditer(pattern, content, re.DOTALL | re.IGNORECASE):
        full_match = match.group(0)
        mermaid_code = match.group(1).strip()
        start_pos = match.start()
        end_pos = match.end()
        matches.append((full_match, mermaid_code, start_pos, end_pos))

    return matches


def process_mermaid_in_content(content: str, output_format: str = "svg") -> Tuple[str, bool]:
    """텍스트 내의 모든 mermaid 코드 블록을 이미지로 변환합니다.

    ```mermaid ... ``` 형식의 코드 블록을 찾아서
    ![Mermaid Diagram](kroki_url) 형식의 마크다운 이미지로 변환합니다.

    Args:
        content: 처리할 텍스트
        output_format: 이미지 출력 형식 ("svg", "png")

    Returns:
        (변환된 텍스트, 변환 여부)
    """
    if not content or not isinstance(content, str):
        return content, False

    mermaid_blocks = extract_mermaid_blocks(content)

    if not mermaid_blocks:
        return content, False

    logger.info(f"[Mermaid] Found {len(mermaid_blocks)} mermaid block(s) to convert")

    # 역순으로 처리하여 위치가 변경되지 않도록 함
    result = content
    for full_match, mermaid_code, start_pos, end_pos in reversed(mermaid_blocks):
        try:
            # mermaid 코드를 이미지 URL로 변환
            image_url = mermaid_to_image_url(mermaid_code, output_format)

            # 다이어그램 타입 추출 (flowchart, sequenceDiagram, etc.)
            diagram_type = "Diagram"
            first_line = mermaid_code.split('\n')[0].strip().lower()
            if 'flowchart' in first_line or 'graph' in first_line:
                diagram_type = "플로우차트"
            elif 'sequencediagram' in first_line or 'sequence' in first_line:
                diagram_type = "시퀀스 다이어그램"
            elif 'classDiagram' in first_line or 'class' in first_line:
                diagram_type = "클래스 다이어그램"
            elif 'gantt' in first_line:
                diagram_type = "간트 차트"
            elif 'pie' in first_line:
                diagram_type = "파이 차트"
            elif 'erdiagram' in first_line or 'er' in first_line:
                diagram_type = "ER 다이어그램"
            elif 'statediagram' in first_line or 'state' in first_line:
                diagram_type = "상태 다이어그램"
            elif 'journey' in first_line:
                diagram_type = "사용자 여정"
            elif 'timeline' in first_line:
                diagram_type = "타임라인"

            # 마크다운 이미지로 변환
            markdown_image = f"![{diagram_type}]({image_url})"

            # 원본 mermaid 블록을 이미지로 교체
            result = result[:start_pos] + markdown_image + result[end_pos:]

            logger.info(f"[Mermaid] Successfully converted {diagram_type}")

        except Exception as e:
            logger.error(f"[Mermaid] Failed to convert mermaid block: {e}")
            # 실패 시 원본 유지
            continue

    return result, True


def detect_and_convert_mermaid(content: str) -> str:
    """메시지 내용에서 mermaid를 감지하고 이미지로 변환하는 편의 함수.

    Args:
        content: 처리할 메시지 내용

    Returns:
        변환된 메시지 내용 (mermaid가 없으면 원본 반환)
    """
    processed_content, was_converted = process_mermaid_in_content(content)

    if was_converted:
        logger.info("[Mermaid] Content was processed and mermaid blocks were converted to images")

    return processed_content


# =============================================================================
# 🔥 대화 맥락 분석 (Conversation Context Analysis)
# =============================================================================

def extract_keywords_simple(text: str, top_n: int = 5) -> List[str]:
    """텍스트에서 간단한 키워드 추출 (명사 위주)

    Args:
        text: 분석할 텍스트
        top_n: 추출할 키워드 수

    Returns:
        상위 N개 키워드 리스트
    """
    # 불용어 (조사, 접속사 등)
    stopwords = {
        '은', '는', '이', '가', '을', '를', '의', '에', '로', '와', '과',
        '도', '만', '하다', '있다', '되다', '않다', '같다', '위해', '대한',
        '통해', '따라', '어떤', '어떻게', '무엇', '왜', '언제', '어디',
        '그', '저', '이런', '저런', '것', '거', '등', '및'
    }

    # 한글 단어만 추출 (2글자 이상)
    words = re.findall(r'[가-힣]{2,}', text.lower())

    # 불용어 제거 및 빈도 계산
    filtered_words = [w for w in words if w not in stopwords]
    word_counts = Counter(filtered_words)

    # 상위 N개 반환
    return [word for word, _ in word_counts.most_common(top_n)]


def detect_user_emotion(text: str) -> str:
    """사용자 메시지에서 감정 감지

    Args:
        text: 사용자 메시지

    Returns:
        감지된 감정 ("neutral", "urgent", "curious", "frustrated")
    """
    text_lower = text.lower()

    # 긴급/불안
    if any(kw in text_lower for kw in ['빨리', '급해', '문제', '안돼', '오류', '에러']):
        return "urgent"

    # 불만/좌절
    if any(kw in text_lower for kw in ['이해 안', '모르겠', '어려워', '실패', '안되는']):
        return "frustrated"

    # 호기심/학습
    if any(kw in text_lower for kw in ['궁금', '알고 싶', '배우', '어떻게', '왜']):
        return "curious"

    return "neutral"


def detect_response_style(text: str) -> str:
    """사용자가 선호하는 응답 스타일 감지

    Args:
        text: 사용자 메시지

    Returns:
        응답 스타일 ("brief", "detailed", "practical")
    """
    text_lower = text.lower()

    # 간단한 답변 선호
    if any(kw in text_lower for kw in ['간단히', '요약', '핵심만', '짧게']):
        return "brief"

    # 실무 중심
    if any(kw in text_lower for kw in ['실제로', '적용', '업무', '실무', '어떻게 하']):
        return "practical"

    # 상세 설명 선호
    if any(kw in text_lower for kw in ['자세히', '상세히', '구체적', '왜', '이유']):
        return "detailed"

    return "detailed"  # 기본값


def extract_entities(text: str) -> List[str]:
    """텍스트에서 주요 엔티티 추출 (회사명, 제품명, 숫자 등)

    Args:
        text: 분석할 텍스트

    Returns:
        추출된 엔티티 리스트
    """
    entities = []

    # 회사명 패턴 (예: "○○주식회사", "○○(주)")
    company_pattern = r'[가-힣]{2,}(?:주식회사|\(주\)|기업|회사)'
    entities.extend(re.findall(company_pattern, text))

    # 배출권 관련 코드 (예: "KOC", "KCU", "KAU")
    emission_codes = re.findall(r'\b[A-Z]{3}\b', text)
    entities.extend(emission_codes)

    # 숫자 + 단위 (예: "1000톤", "500만원")
    number_patterns = re.findall(r'\d+(?:,\d{3})*(?:톤|원|개|건|년|월|일)', text)
    entities.extend(number_patterns)

    return list(set(entities))  # 중복 제거


def determine_conversation_stage(messages: List[BaseMessage]) -> str:
    """대화 단계 판단

    Args:
        messages: 대화 메시지 리스트

    Returns:
        대화 단계 ("initial", "progressing", "advanced")
    """
    # 사용자 메시지만 카운트 (HumanMessage)
    user_message_count = sum(1 for m in messages if isinstance(m, HumanMessage))

    if user_message_count <= 2:
        return "initial"
    elif user_message_count <= 5:
        return "progressing"
    else:
        return "advanced"


def analyze_conversation_context(messages: List[BaseMessage]) -> Dict[str, Any]:
    """대화 이력을 분석하여 맥락 정보 추출

    Args:
        messages: 전체 대화 메시지 리스트

    Returns:
        대화 맥락 정보 딕셔너리
        {
            "recent_topics": List[str],  # 최근 3개 주제(키워드)
            "user_emotion": str,  # 사용자 감정
            "response_style": str,  # 선호 응답 스타일
            "mentioned_entities": List[str],  # 언급된 엔티티
            "conversation_stage": str,  # 대화 단계
            "question_count": int,  # 총 질문 수
        }
    """
    context = {
        "recent_topics": [],
        "user_emotion": "neutral",
        "response_style": "detailed",
        "mentioned_entities": [],
        "conversation_stage": "initial",
        "question_count": 0,
    }

    # 메시지가 비어있거나 너무 적으면 기본값 반환
    if not messages or len(messages) < 2:
        return context

    # 사용자 메시지만 추출
    user_messages = [
        get_message_text(m)
        for m in messages
        if isinstance(m, HumanMessage)
    ]

    if not user_messages:
        return context

    context["question_count"] = len(user_messages)

    # 최근 3개 메시지 분석
    recent_messages = user_messages[-3:]

    # 1. 최근 주제(키워드) 추출
    all_recent_text = " ".join(recent_messages)
    context["recent_topics"] = extract_keywords_simple(all_recent_text, top_n=5)

    # 2. 최근 메시지에서 감정 감지
    if recent_messages:
        context["user_emotion"] = detect_user_emotion(recent_messages[-1])

    # 3. 응답 스타일 감지
    if recent_messages:
        context["response_style"] = detect_response_style(recent_messages[-1])

    # 4. 전체 대화에서 엔티티 추출
    all_text = " ".join(user_messages)
    context["mentioned_entities"] = extract_entities(all_text)

    # 5. 대화 단계 판단
    context["conversation_stage"] = determine_conversation_stage(messages)

    logger.info(f"[Context] 분석 완료: topics={context['recent_topics']}, "
                f"emotion={context['user_emotion']}, stage={context['conversation_stage']}")

    return context


def build_context_aware_prompt_addition(context: Dict[str, Any]) -> str:
    """대화 맥락을 기반으로 프롬프트 추가 섹션 생성

    Args:
        context: analyze_conversation_context()의 반환값

    Returns:
        프롬프트에 추가할 맥락 정보 문자열
    """
    if not context or context.get("question_count", 0) <= 1:
        return ""  # 첫 대화는 맥락 없음

    sections = []

    # 대화 단계
    stage_map = {
        "initial": "초기 대화 단계 - 기본 개념 위주로 설명하세요",
        "progressing": "대화 진행 중 - 사용자가 이미 기본을 이해했다고 가정하세요",
        "advanced": "심화 대화 단계 - 전문적이고 구체적인 내용을 제공하세요"
    }
    stage = context.get("conversation_stage", "initial")
    sections.append(f"**대화 단계**: {stage_map.get(stage, '')}")

    # 최근 주제
    topics = context.get("recent_topics", [])
    if topics:
        topics_str = ", ".join(topics[:3])
        sections.append(f"**최근 논의된 주제**: {topics_str}")
        sections.append(f"→ 이 주제들을 참고하여 연속성 있는 답변을 제공하세요")

    # 사용자 감정
    emotion = context.get("user_emotion", "neutral")
    emotion_guide = {
        "urgent": "⚡ 사용자가 급한 상황입니다. 핵심 답변을 먼저 제공하고, 단계별 액션을 명확히 하세요.",
        "frustrated": "😓 사용자가 어려움을 겪고 있습니다. 더 쉽게 풀어서 설명하고, 단계를 세분화하세요.",
        "curious": "🤔 사용자가 학습 의욕이 높습니다. 상세하고 교육적인 답변을 제공하세요.",
        "neutral": ""
    }
    if emotion != "neutral":
        sections.append(f"**사용자 상태**: {emotion_guide.get(emotion, '')}")

    # 응답 스타일
    style = context.get("response_style", "detailed")
    style_guide = {
        "brief": "📝 간결한 답변을 원합니다. 핵심만 2-3문장으로 제공하고, 추가 설명은 선택적으로 제안하세요.",
        "practical": "💼 실무 적용을 원합니다. 즉시 실행 가능한 체크리스트와 예시를 중심으로 답변하세요.",
        "detailed": "📚 상세한 설명을 원합니다. 배경, 이유, 예시를 포함하여 충분히 설명하세요."
    }
    sections.append(f"**답변 스타일**: {style_guide.get(style, '')}")

    # 언급된 엔티티
    entities = context.get("mentioned_entities", [])
    if entities:
        entities_str = ", ".join(entities[:5])
        sections.append(f"**대화 중 언급된 내용**: {entities_str}")
        sections.append(f"→ 이전에 언급된 내용은 다시 설명하지 말고 참조만 하세요")

    # 최종 조합
    prompt_addition = "\n\n" + "=" * 60 + "\n"
    prompt_addition += "📝 **대화 맥락 정보 (이전 대화 기반)**\n"
    prompt_addition += "=" * 60 + "\n"
    prompt_addition += "\n".join(sections)
    prompt_addition += "\n" + "=" * 60 + "\n"

    return prompt_addition
