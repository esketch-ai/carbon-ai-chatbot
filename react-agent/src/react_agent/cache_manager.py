# 캐시 매니저 - RAG 및 LLM 응답 캐싱
# 메모리 기반 캐싱 지원

import os
import json
import hashlib
import logging
import re
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


# ==================== FAQ 데이터베이스 임포트 ====================

try:
    from react_agent.faq_rules import FAQ_DATABASE, get_all_faq_keys
    logger.info(f"[FAQ] {len(FAQ_DATABASE)}개 FAQ 규칙 로드 완료")
except ImportError:
    logger.warning("[FAQ] faq_rules.py를 찾을 수 없습니다. 기본 FAQ 사용")
    FAQ_DATABASE = {}


def normalize_question(question: str) -> str:
    """질문을 정규화하여 FAQ 매칭에 사용

    Args:
        question: 사용자 질문

    Returns:
        정규화된 질문 (소문자, 공백 제거, 특수문자 제거)
    """
    # 소문자 변환
    normalized = question.lower()

    # 특수문자 제거 (한글, 영문, 숫자만 남김)
    normalized = re.sub(r'[^\w\s가-힣]', '', normalized)

    # 연속된 공백을 하나로
    normalized = re.sub(r'\s+', ' ', normalized)

    # 앞뒤 공백 제거
    normalized = normalized.strip()

    return normalized


class CacheManager:
    # 메모리 기반 캐시

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = 86400,  # 24시간 (초 단위)
        use_redis: bool = True
    ):
        """
        캐시 매니저 초기화

        Args:
            redis_url: Redis 연결 URL (예: redis://localhost:6379/0)
            default_ttl: 기본 TTL (초 단위, 기본값: 24시간)
            use_redis: Redis 사용 여부
        """
        self.default_ttl = default_ttl
        self.use_redis = use_redis
        self._redis_client = None
        self._memory_cache: Dict[str, tuple[Any, datetime]] = {}

        # Redis 초기화 시도
        if use_redis and redis_url:
            try:
                import redis
                self._redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5
                )
                # 연결 테스트
                self._redis_client.ping()
                logger.info(f"✓ Redis 캐시 연결 성공: {redis_url}")
            except ImportError:
                logger.warning("redis 패키지가 설치되지 않았습니다. 메모리 캐시를 사용합니다.")
                self._redis_client = None
            except Exception as e:
                logger.warning(f"Redis 연결 실패 ({redis_url}): {e}. 메모리 캐시를 사용합니다.")
                self._redis_client = None
        else:
            logger.info("메모리 캐시를 사용합니다.")

    def _generate_cache_key(self, prefix: str, content: str) -> str:
        """
        캐시 키 생성 (해시 기반)

        Args:
            prefix: 키 접두사 (예: "rag", "llm")
            content: 해시할 콘텐츠

        Returns:
            캐시 키
        """
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
        return f"{prefix}:{content_hash}"

    def get(self, prefix: str, content: str) -> Optional[Any]:
        """
        캐시에서 값 가져오기

        Args:
            prefix: 키 접두사
            content: 해시할 콘텐츠

        Returns:
            캐시된 값 또는 None
        """
        cache_key = self._generate_cache_key(prefix, content)

        # Redis 캐시 확인
        if self._redis_client:
            try:
                cached_data = self._redis_client.get(cache_key)
                if cached_data:
                    logger.info(f"[캐시 HIT] Redis: {prefix} - {content[:50]}...")
                    return json.loads(cached_data)
            except Exception as e:
                logger.error(f"Redis 캐시 읽기 실패: {e}")

        # 메모리 캐시 확인
        if cache_key in self._memory_cache:
            cached_value, expiry_time = self._memory_cache[cache_key]
            if datetime.now() < expiry_time:
                logger.info(f"[캐시 HIT] 메모리: {prefix} - {content[:50]}...")
                return cached_value
            else:
                # 만료된 캐시 제거
                del self._memory_cache[cache_key]
                logger.debug(f"[캐시 만료] {prefix} - {content[:50]}...")

        logger.debug(f"[캐시 MISS] {prefix} - {content[:50]}...")
        return None

    def set(
        self,
        prefix: str,
        content: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        캐시에 값 저장

        Args:
            prefix: 키 접두사
            content: 해시할 콘텐츠
            value: 저장할 값
            ttl: TTL (초 단위, None이면 default_ttl 사용)

        Returns:
            성공 여부
        """
        cache_key = self._generate_cache_key(prefix, content)
        ttl = ttl or self.default_ttl

        # Redis 캐시 저장
        if self._redis_client:
            try:
                serialized = json.dumps(value, ensure_ascii=False)
                self._redis_client.setex(cache_key, ttl, serialized)
                logger.info(f"[캐시 저장] Redis: {prefix} - {content[:50]}... (TTL: {ttl}초)")
                return True
            except Exception as e:
                logger.error(f"Redis 캐시 저장 실패: {e}")

        # 메모리 캐시 저장
        expiry_time = datetime.now() + timedelta(seconds=ttl)
        self._memory_cache[cache_key] = (value, expiry_time)
        logger.info(f"[캐시 저장] 메모리: {prefix} - {content[:50]}... (TTL: {ttl}초)")

        # 메모리 캐시 크기 제한 (1000개)
        if len(self._memory_cache) > 1000:
            self._cleanup_expired_memory_cache()

        return True

    def _cleanup_expired_memory_cache(self):
        """만료된 메모리 캐시 정리"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, expiry) in self._memory_cache.items()
            if now >= expiry
        ]
        for key in expired_keys:
            del self._memory_cache[key]
        logger.info(f"메모리 캐시 정리: {len(expired_keys)}개 만료된 항목 제거")

    def clear(self, prefix: Optional[str] = None) -> int:
        """
        캐시 클리어

        Args:
            prefix: 특정 접두사만 클리어 (None이면 전체)

        Returns:
            클리어된 항목 수
        """
        count = 0

        # Redis 캐시 클리어
        if self._redis_client:
            try:
                if prefix:
                    # 특정 접두사 패턴 삭제
                    pattern = f"{prefix}:*"
                    keys = self._redis_client.keys(pattern)
                    if keys:
                        count += self._redis_client.delete(*keys)
                    logger.info(f"Redis 캐시 클리어: {prefix} 패턴 - {count}개")
                else:
                    # 전체 삭제
                    self._redis_client.flushdb()
                    logger.info("Redis 캐시 전체 클리어")
                    count += 1
            except Exception as e:
                logger.error(f"Redis 캐시 클리어 실패: {e}")

        # 메모리 캐시 클리어
        if prefix:
            mem_keys = [k for k in self._memory_cache.keys() if k.startswith(f"{prefix}:")]
            for key in mem_keys:
                del self._memory_cache[key]
            count += len(mem_keys)
            logger.info(f"메모리 캐시 클리어: {prefix} 패턴 - {len(mem_keys)}개")
        else:
            count += len(self._memory_cache)
            self._memory_cache.clear()
            logger.info("메모리 캐시 전체 클리어")

        return count

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 정보 반환"""
        stats = {
            "backend": "redis" if self._redis_client else "memory",
            "memory_cache_size": len(self._memory_cache),
            "default_ttl_seconds": self.default_ttl
        }

        if self._redis_client:
            try:
                info = self._redis_client.info("stats")
                stats["redis_keys"] = self._redis_client.dbsize()
                stats["redis_hits"] = info.get("keyspace_hits", 0)
                stats["redis_misses"] = info.get("keyspace_misses", 0)
            except Exception as e:
                logger.error(f"Redis 통계 조회 실패: {e}")

        return stats

    def get_faq(self, question: str, similarity_threshold: float = 0.7) -> Optional[str]:
        """FAQ 데이터베이스에서 답변 검색

        질문을 정규화하고 FAQ 데이터베이스에서 유사한 질문을 찾습니다.

        Args:
            question: 사용자 질문
            similarity_threshold: 유사도 임계값 (0~1, 기본값: 0.7)

        Returns:
            FAQ 답변 또는 None
        """
        normalized_q = normalize_question(question)

        # 정확히 일치하는 키워드 찾기
        for faq_key, faq_answer in FAQ_DATABASE.items():
            # FAQ 키도 정규화
            normalized_key = normalize_question(faq_key)

            # 부분 문자열 매칭
            if normalized_key in normalized_q or normalized_q in normalized_key:
                logger.info(f"[FAQ HIT] '{question}' → '{faq_key}'")
                return faq_answer

            # 단어 기반 매칭 (유사도 계산)
            key_words = set(normalized_key.split())
            question_words = set(normalized_q.split())

            if key_words and question_words:
                # Jaccard 유사도
                intersection = key_words & question_words
                union = key_words | question_words
                similarity = len(intersection) / len(union) if union else 0

                if similarity >= similarity_threshold:
                    logger.info(f"[FAQ HIT] '{question}' → '{faq_key}' (유사도: {similarity:.2f})")
                    return faq_answer

        logger.debug(f"[FAQ MISS] '{question}'")
        return None


# 전역 캐시 매니저 인스턴스
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """캐시 매니저 싱글톤 인스턴스 반환"""
    global _cache_manager
    if _cache_manager is None:
        redis_url = os.getenv("REDIS_URL")
        cache_ttl = int(os.getenv("CACHE_TTL", "86400"))  # 기본 24시간
        use_redis = os.getenv("USE_REDIS_CACHE", "true").lower() == "true"

        _cache_manager = CacheManager(
            redis_url=redis_url,
            default_ttl=cache_ttl,
            use_redis=use_redis
        )
    return _cache_manager
