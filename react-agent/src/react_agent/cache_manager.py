# 캐시 매니저 - RAG 및 LLM 응답 캐싱
# 메모리 기반 캐싱 지원 (LRU 정책 적용)

import os
import json
import hashlib
import logging
import re
import threading
from collections import OrderedDict
from typing import Optional, Any, Dict, Tuple
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


class LRUCache:
    """Thread-safe LRU 캐시 구현

    OrderedDict를 사용하여 LRU (Least Recently Used) 정책을 구현합니다.
    최대 크기 초과 시 가장 오래 사용되지 않은 항목부터 제거합니다.
    """

    def __init__(self, max_size: int = 1000):
        """
        LRU 캐시 초기화

        Args:
            max_size: 최대 캐시 항목 수 (기본값: 1000)
        """
        self._cache: OrderedDict[str, Tuple[Any, datetime]] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Tuple[Any, datetime]]:
        """캐시에서 값 조회 (LRU 순서 업데이트)

        Args:
            key: 캐시 키

        Returns:
            (값, 만료시간) 튜플 또는 None
        """
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None

    def set(self, key: str, value: Any, expiry_time: datetime) -> None:
        """캐시에 값 저장 (LRU 정책 적용)

        Args:
            key: 캐시 키
            value: 저장할 값
            expiry_time: 만료 시간
        """
        with self._lock:
            if key in self._cache:
                # 기존 키 업데이트 - LRU 순서도 업데이트
                self._cache.move_to_end(key)
            self._cache[key] = (value, expiry_time)

            # 최대 크기 초과 시 가장 오래된 항목 제거 (LRU eviction)
            while len(self._cache) > self._max_size:
                evicted_key, _ = self._cache.popitem(last=False)
                logger.debug(f"[LRU 캐시] 항목 제거: {evicted_key[:50]}...")

    def delete(self, key: str) -> bool:
        """캐시에서 항목 삭제

        Args:
            key: 삭제할 캐시 키

        Returns:
            삭제 성공 여부
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def contains(self, key: str) -> bool:
        """키 존재 여부 확인 (LRU 순서 변경 없음)

        Args:
            key: 확인할 캐시 키

        Returns:
            존재 여부
        """
        with self._lock:
            return key in self._cache

    def clear(self) -> int:
        """전체 캐시 클리어

        Returns:
            클리어된 항목 수
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def clear_prefix(self, prefix: str) -> int:
        """특정 접두사를 가진 항목들 클리어

        Args:
            prefix: 삭제할 키의 접두사

        Returns:
            클리어된 항목 수
        """
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(f"{prefix}:")]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)

    def cleanup_expired(self) -> int:
        """만료된 항목 정리

        Returns:
            정리된 항목 수
        """
        now = datetime.now()
        with self._lock:
            expired_keys = [
                key for key, (_, expiry) in self._cache.items()
                if now >= expiry
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    def keys(self) -> list:
        """모든 키 목록 반환"""
        with self._lock:
            return list(self._cache.keys())

    def __len__(self) -> int:
        """캐시 크기 반환"""
        with self._lock:
            return len(self._cache)

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_percent": round(hit_rate, 2)
            }


class CacheManager:
    # 메모리 기반 캐시 (LRU 정책 적용)

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = 86400,  # 24시간 (초 단위)
        use_redis: bool = True,
        max_memory_cache_size: int = 1000
    ):
        """
        캐시 매니저 초기화

        Args:
            redis_url: Redis 연결 URL (예: redis://localhost:6379/0)
            default_ttl: 기본 TTL (초 단위, 기본값: 24시간)
            use_redis: Redis 사용 여부
            max_memory_cache_size: 최대 메모리 캐시 항목 수 (기본값: 1000)
        """
        self.default_ttl = default_ttl
        self.use_redis = use_redis
        self._redis_client = None
        self._memory_cache = LRUCache(max_size=max_memory_cache_size)

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

    def _generate_cache_key(
        self,
        prefix: str,
        content: str,
        thread_id: Optional[str] = None
    ) -> str:
        """
        캐시 키 생성 (해시 기반, 선택적 스레드 격리)

        Args:
            prefix: 키 접두사 (예: "rag", "llm")
            content: 해시할 콘텐츠
            thread_id: 스레드 ID (제공 시 스레드별 격리된 캐시 키 생성)

        Returns:
            캐시 키 (thread_id 있으면 "prefix:thread_id:hash", 없으면 "prefix:global:hash")

        Note:
            thread_id를 포함하면 사용자/대화 간 캐시 충돌을 방지하여
            다른 사용자의 응답이 섞이는 것을 방지합니다.
        """
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
        if thread_id:
            # 스레드별 격리된 캐시 키
            return f"{prefix}:{thread_id}:{content_hash}"
        else:
            # 전역 캐시 키 (FAQ 등 공유 가능한 데이터)
            return f"{prefix}:global:{content_hash}"

    def get(
        self,
        prefix: str,
        content: str,
        thread_id: Optional[str] = None
    ) -> Optional[Any]:
        """
        캐시에서 값 가져오기

        Args:
            prefix: 키 접두사
            content: 해시할 콘텐츠
            thread_id: 스레드 ID (제공 시 스레드별 격리된 캐시 조회)

        Returns:
            캐시된 값 또는 None
        """
        cache_key = self._generate_cache_key(prefix, content, thread_id)

        # Redis 캐시 확인
        if self._redis_client:
            try:
                cached_data = self._redis_client.get(cache_key)
                if cached_data:
                    logger.info(f"[캐시 HIT] Redis: {prefix} - {content[:50]}...")
                    return json.loads(cached_data)
            except Exception as e:
                logger.error(f"Redis 캐시 읽기 실패: {e}")

        # 메모리 캐시 확인 (LRU 캐시 사용)
        cached_result = self._memory_cache.get(cache_key)
        if cached_result is not None:
            cached_value, expiry_time = cached_result
            if datetime.now() < expiry_time:
                logger.info(f"[캐시 HIT] 메모리 (LRU): {prefix} - {content[:50]}...")
                return cached_value
            else:
                # 만료된 캐시 제거
                self._memory_cache.delete(cache_key)
                logger.debug(f"[캐시 만료] {prefix} - {content[:50]}...")

        logger.debug(f"[캐시 MISS] {prefix} - {content[:50]}...")
        return None

    def set(
        self,
        prefix: str,
        content: str,
        value: Any,
        ttl: Optional[int] = None,
        thread_id: Optional[str] = None
    ) -> bool:
        """
        캐시에 값 저장

        Args:
            prefix: 키 접두사
            content: 해시할 콘텐츠
            value: 저장할 값
            ttl: TTL (초 단위, None이면 default_ttl 사용)
            thread_id: 스레드 ID (제공 시 스레드별 격리된 캐시 저장)

        Returns:
            성공 여부
        """
        cache_key = self._generate_cache_key(prefix, content, thread_id)
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

        # 메모리 캐시 저장 (LRU 캐시 사용 - 자동 eviction 적용)
        expiry_time = datetime.now() + timedelta(seconds=ttl)
        self._memory_cache.set(cache_key, value, expiry_time)
        logger.info(f"[캐시 저장] 메모리 (LRU): {prefix} - {content[:50]}... (TTL: {ttl}초)")

        return True

    def _cleanup_expired_memory_cache(self) -> int:
        """만료된 메모리 캐시 정리

        Returns:
            정리된 항목 수
        """
        expired_count = self._memory_cache.cleanup_expired()
        if expired_count > 0:
            logger.info(f"메모리 캐시 정리: {expired_count}개 만료된 항목 제거")
        return expired_count

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

        # 메모리 캐시 클리어 (LRU 캐시 사용)
        if prefix:
            mem_count = self._memory_cache.clear_prefix(prefix)
            count += mem_count
            logger.info(f"메모리 캐시 클리어: {prefix} 패턴 - {mem_count}개")
        else:
            mem_count = self._memory_cache.clear()
            count += mem_count
            logger.info("메모리 캐시 전체 클리어")

        return count

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 정보 반환"""
        lru_stats = self._memory_cache.get_stats()
        stats = {
            "backend": "redis" if self._redis_client else "memory (LRU)",
            "memory_cache_size": lru_stats["size"],
            "memory_cache_max_size": lru_stats["max_size"],
            "memory_cache_hits": lru_stats["hits"],
            "memory_cache_misses": lru_stats["misses"],
            "memory_cache_hit_rate_percent": lru_stats["hit_rate_percent"],
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
        max_cache_size = int(os.getenv("MAX_MEMORY_CACHE_SIZE", "1000"))

        _cache_manager = CacheManager(
            redis_url=redis_url,
            default_ttl=cache_ttl,
            use_redis=use_redis,
            max_memory_cache_size=max_cache_size
        )
    return _cache_manager
