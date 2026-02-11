"""Expert Panel Topics - 신규 토픽 수집 및 관리

매주 수집되는 정보에서 신규 토픽을 추출하고 관리하는 모듈
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


# 토픽 분류 키워드 매핑
TOPIC_CATEGORIES = {
    "정책/법규": [
        "법률", "법", "규제", "정책", "기본계획", "시행령", "지침",
        "NDC", "탄소중립", "넷제로", "CBAM", "COP", "협약"
    ],
    "탄소배출권": [
        "KAU", "KCU", "KOC", "배출권", "할당", "상쇄", "외부사업",
        "크레딧", "거래제", "VCS", "CDM", "ITMO"
    ],
    "시장/거래": [
        "가격", "시세", "거래", "시장", "ETS", "경매", "유동성",
        "선물", "투자", "전망", "예측"
    ],
    "감축기술": [
        "CCUS", "CCS", "수소", "재생에너지", "태양광", "풍력",
        "ESS", "DAC", "기술", "효율", "전기화", "SMR"
    ],
    "MRV/검증": [
        "Scope", "배출량", "산정", "검증", "모니터링", "보고",
        "GHG Protocol", "ISO 14064", "인벤토리", "탄소발자국"
    ]
}


def get_knowledge_base_path() -> Path:
    """지식베이스 경로 반환"""
    # 환경변수에서 경로 가져오기 또는 기본 경로 사용
    kb_path = os.getenv("KNOWLEDGE_BASE_PATH", "knowledge_base")
    return Path(kb_path)


def get_recent_documents(days: int = 7) -> List[Dict[str, Any]]:
    """최근 N일 내 추가된 문서 목록 반환

    Args:
        days: 조회 기간 (일)

    Returns:
        최근 추가된 문서 목록
    """
    kb_path = get_knowledge_base_path()

    if not kb_path.exists():
        logger.warning(f"지식베이스 경로가 존재하지 않습니다: {kb_path}")
        return []

    recent_docs = []
    cutoff_date = datetime.now() - timedelta(days=days)

    try:
        for file_path in kb_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in [".pdf", ".txt", ".md", ".json"]:
                # 파일 수정 시간 확인
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                if mtime >= cutoff_date:
                    # 파일명에서 제목 추출
                    title = file_path.stem.replace("_", " ").replace("-", " ")

                    # 카테고리 분류
                    category = _classify_topic(title + " " + str(file_path))

                    recent_docs.append({
                        "title": title,
                        "path": str(file_path),
                        "date_added": mtime.strftime("%Y-%m-%d"),
                        "category": category,
                        "file_type": file_path.suffix.lower()
                    })

        # 날짜순 정렬 (최신순)
        recent_docs.sort(key=lambda x: x["date_added"], reverse=True)

    except Exception as e:
        logger.error(f"최근 문서 조회 중 오류: {e}")

    return recent_docs


def _classify_topic(text: str) -> str:
    """텍스트를 토픽 카테고리로 분류"""
    text_lower = text.lower()

    # 각 카테고리별 매칭 점수 계산
    scores = {}
    for category, keywords in TOPIC_CATEGORIES.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score > 0:
            scores[category] = score

    # 가장 높은 점수의 카테고리 반환
    if scores:
        best_category = max(scores.keys(), key=lambda k: scores.get(k, 0))
        return best_category

    return "일반"


def extract_weekly_updates() -> List[Dict[str, Any]]:
    """이번 주 주요 업데이트 추출

    Returns:
        주간 업데이트 목록
    """
    # 최근 7일 문서 가져오기
    recent_docs = get_recent_documents(days=7)

    updates = []
    for doc in recent_docs[:10]:  # 최대 10개
        updates.append({
            "title": doc["title"],
            "date": doc["date_added"],
            "category": doc["category"],
            "summary": f"{doc['category']} 분야 신규 자료",
            "source": doc.get("path", "")
        })

    return updates


def get_topics_by_category(category: str, days: int = 30) -> List[Dict[str, Any]]:
    """특정 카테고리의 최근 토픽 반환

    Args:
        category: 토픽 카테고리
        days: 조회 기간 (일)

    Returns:
        해당 카테고리의 토픽 목록
    """
    recent_docs = get_recent_documents(days=days)

    return [doc for doc in recent_docs if doc.get("category") == category]


def get_trending_topics(days: int = 30) -> Dict[str, int]:
    """트렌딩 토픽 분석 (카테고리별 문서 수)

    Args:
        days: 분석 기간 (일)

    Returns:
        카테고리별 문서 수
    """
    recent_docs = get_recent_documents(days=days)

    # 카테고리별 카운트
    category_counts = {}
    for doc in recent_docs:
        category = doc.get("category", "일반")
        category_counts[category] = category_counts.get(category, 0) + 1

    # 정렬하여 반환
    return dict(sorted(category_counts.items(), key=lambda x: x[1], reverse=True))


def format_weekly_summary() -> str:
    """주간 요약 텍스트 생성"""
    updates = extract_weekly_updates()
    trending = get_trending_topics(days=7)

    if not updates and not trending:
        return "이번 주 수집된 새로운 자료가 없습니다."

    summary_parts = []

    # 트렌딩 토픽
    if trending:
        summary_parts.append("📊 **이번 주 주요 분야**")
        for category, count in list(trending.items())[:5]:
            summary_parts.append(f"  - {category}: {count}건")

    # 신규 문서
    if updates:
        summary_parts.append("\n📄 **신규 자료**")
        for update in updates[:5]:
            summary_parts.append(f"  - [{update['category']}] {update['title']} ({update['date']})")

    return "\n".join(summary_parts)


# ============ 전문가별 토픽 매핑 ============

EXPERT_TOPIC_MAPPING = {
    "policy_expert": "정책/법규",
    "carbon_credit_expert": "탄소배출권",
    "market_expert": "시장/거래",
    "technology_expert": "감축기술",
    "mrv_expert": "MRV/검증"
}


def get_expert_recent_topics(expert_role: str, days: int = 14) -> List[Dict[str, Any]]:
    """특정 전문가 영역의 최근 토픽 반환

    Args:
        expert_role: 전문가 역할 (예: "policy_expert")
        days: 조회 기간 (일)

    Returns:
        해당 전문가 영역의 최근 토픽 목록
    """
    category = EXPERT_TOPIC_MAPPING.get(expert_role)
    if not category:
        return []

    return get_topics_by_category(category, days=days)


def get_expert_topic_summary(expert_role: str) -> str:
    """전문가별 토픽 요약 생성

    Args:
        expert_role: 전문가 역할

    Returns:
        해당 전문가 영역의 토픽 요약 텍스트
    """
    topics = get_expert_recent_topics(expert_role, days=14)

    if not topics:
        category = EXPERT_TOPIC_MAPPING.get(expert_role, expert_role)
        return f"최근 2주간 {category} 분야의 신규 자료가 없습니다."

    summary_parts = [f"📚 **최근 2주간 신규 자료** (총 {len(topics)}건)"]

    for topic in topics[:5]:
        summary_parts.append(f"  📄 {topic['title']} ({topic['date_added']})")

    if len(topics) > 5:
        summary_parts.append(f"  ... 외 {len(topics) - 5}건")

    return "\n".join(summary_parts)


# ============ 캐시 관리 (선택적) ============

_topic_cache: Dict[str, Any] = {}
_cache_time: Optional[datetime] = None
CACHE_DURATION = timedelta(hours=1)  # 1시간 캐시


def get_cached_topics() -> Optional[Dict[str, Any]]:
    """캐시된 토픽 정보 반환"""
    global _topic_cache, _cache_time

    if _cache_time and datetime.now() - _cache_time < CACHE_DURATION:
        return _topic_cache

    return None


def update_topic_cache():
    """토픽 캐시 업데이트"""
    global _topic_cache, _cache_time

    _topic_cache = {
        "weekly_updates": extract_weekly_updates(),
        "trending": get_trending_topics(days=7),
        "recent_docs": get_recent_documents(days=7)
    }
    _cache_time = datetime.now()

    logger.info(f"토픽 캐시 업데이트 완료: {len(_topic_cache.get('recent_docs', []))}개 문서")

    return _topic_cache


def get_all_topics_info() -> Dict[str, Any]:
    """전체 토픽 정보 반환 (캐시 활용)"""
    cached = get_cached_topics()
    if cached:
        return cached

    return update_topic_cache()
