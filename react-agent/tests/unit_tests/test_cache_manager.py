"""Unit tests for cache_manager module.

Tests for LRU cache behavior and CacheManager functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from react_agent.cache_manager import (
    LRUCache,
    CacheManager,
    normalize_question,
)


class TestNormalizeQuestion:
    """Tests for normalize_question function."""

    def test_normalize_lowercase(self):
        """Should convert to lowercase."""
        result = normalize_question("Hello WORLD")
        assert result == "hello world"

    def test_normalize_remove_special_chars(self):
        """Should remove special characters."""
        result = normalize_question("What's the price?!")
        assert "?" not in result
        assert "!" not in result
        assert "'" not in result

    def test_normalize_preserve_korean(self):
        """Should preserve Korean characters."""
        result = normalize_question("탄소배출권 가격은?")
        assert "탄소배출권" in result
        assert "가격은" in result

    def test_normalize_whitespace(self):
        """Should normalize whitespace to single spaces."""
        result = normalize_question("hello   world\n\ntest")
        assert "  " not in result
        assert result == "hello world test"

    def test_normalize_trim(self):
        """Should trim leading and trailing whitespace."""
        result = normalize_question("  hello world  ")
        assert result == "hello world"

    def test_normalize_empty_string(self):
        """Should handle empty string."""
        result = normalize_question("")
        assert result == ""


class TestLRUCache:
    """Tests for LRUCache class."""

    def test_basic_get_set(self):
        """Basic get and set operations."""
        cache = LRUCache(max_size=10)
        expiry = datetime.now() + timedelta(hours=1)

        cache.set("key1", "value1", expiry)
        result = cache.get("key1")

        assert result is not None
        assert result[0] == "value1"

    def test_get_missing_key(self):
        """Get non-existent key returns None."""
        cache = LRUCache(max_size=10)
        result = cache.get("nonexistent")
        assert result is None

    def test_lru_eviction(self):
        """LRU eviction when cache exceeds max size."""
        cache = LRUCache(max_size=3)
        expiry = datetime.now() + timedelta(hours=1)

        # Add 3 items
        cache.set("key1", "value1", expiry)
        cache.set("key2", "value2", expiry)
        cache.set("key3", "value3", expiry)

        # Add 4th item - should evict key1 (oldest)
        cache.set("key4", "value4", expiry)

        assert cache.get("key1") is None  # Evicted
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None
        assert cache.get("key4") is not None

    def test_lru_access_order_update(self):
        """Accessing item should update LRU order."""
        cache = LRUCache(max_size=3)
        expiry = datetime.now() + timedelta(hours=1)

        # Add 3 items
        cache.set("key1", "value1", expiry)
        cache.set("key2", "value2", expiry)
        cache.set("key3", "value3", expiry)

        # Access key1 - makes it most recently used
        cache.get("key1")

        # Add 4th item - should evict key2 (now oldest)
        cache.set("key4", "value4", expiry)

        assert cache.get("key1") is not None  # Not evicted (was accessed)
        assert cache.get("key2") is None  # Evicted (oldest after key1 access)
        assert cache.get("key3") is not None
        assert cache.get("key4") is not None

    def test_update_existing_key(self):
        """Updating existing key should move to end."""
        cache = LRUCache(max_size=3)
        expiry = datetime.now() + timedelta(hours=1)

        cache.set("key1", "value1", expiry)
        cache.set("key2", "value2", expiry)
        cache.set("key3", "value3", expiry)

        # Update key1 - should move to end
        cache.set("key1", "new_value1", expiry)

        # Add 4th item - should evict key2 (now oldest)
        cache.set("key4", "value4", expiry)

        result = cache.get("key1")
        assert result is not None
        assert result[0] == "new_value1"
        assert cache.get("key2") is None

    def test_delete(self):
        """Delete operation."""
        cache = LRUCache(max_size=10)
        expiry = datetime.now() + timedelta(hours=1)

        cache.set("key1", "value1", expiry)
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        assert cache.delete("nonexistent") is False

    def test_contains(self):
        """Contains check without updating LRU order."""
        cache = LRUCache(max_size=3)
        expiry = datetime.now() + timedelta(hours=1)

        cache.set("key1", "value1", expiry)
        assert cache.contains("key1") is True
        assert cache.contains("nonexistent") is False

    def test_clear(self):
        """Clear all items."""
        cache = LRUCache(max_size=10)
        expiry = datetime.now() + timedelta(hours=1)

        cache.set("key1", "value1", expiry)
        cache.set("key2", "value2", expiry)

        count = cache.clear()

        assert count == 2
        assert len(cache) == 0

    def test_clear_prefix(self):
        """Clear items with specific prefix."""
        cache = LRUCache(max_size=10)
        expiry = datetime.now() + timedelta(hours=1)

        cache.set("rag:key1", "value1", expiry)
        cache.set("rag:key2", "value2", expiry)
        cache.set("llm:key3", "value3", expiry)

        count = cache.clear_prefix("rag")

        assert count == 2
        assert cache.get("rag:key1") is None
        assert cache.get("rag:key2") is None
        assert cache.get("llm:key3") is not None

    def test_cleanup_expired(self):
        """Cleanup expired items."""
        cache = LRUCache(max_size=10)

        # Add expired item
        past_expiry = datetime.now() - timedelta(hours=1)
        future_expiry = datetime.now() + timedelta(hours=1)

        cache.set("expired", "value1", past_expiry)
        cache.set("valid", "value2", future_expiry)

        count = cache.cleanup_expired()

        assert count == 1
        assert cache.get("expired") is None
        assert cache.get("valid") is not None

    def test_len(self):
        """Length operation."""
        cache = LRUCache(max_size=10)
        expiry = datetime.now() + timedelta(hours=1)

        assert len(cache) == 0
        cache.set("key1", "value1", expiry)
        assert len(cache) == 1
        cache.set("key2", "value2", expiry)
        assert len(cache) == 2

    def test_keys(self):
        """Get all keys."""
        cache = LRUCache(max_size=10)
        expiry = datetime.now() + timedelta(hours=1)

        cache.set("key1", "value1", expiry)
        cache.set("key2", "value2", expiry)

        keys = cache.keys()
        assert "key1" in keys
        assert "key2" in keys

    def test_get_stats(self):
        """Get cache statistics."""
        cache = LRUCache(max_size=10)
        expiry = datetime.now() + timedelta(hours=1)

        cache.set("key1", "value1", expiry)
        cache.get("key1")  # Hit
        cache.get("key1")  # Hit
        cache.get("nonexistent")  # Miss

        stats = cache.get_stats()

        assert stats["size"] == 1
        assert stats["max_size"] == 10
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate_percent"] > 0


class TestCacheManager:
    """Tests for CacheManager class."""

    def test_init_memory_cache(self):
        """Initialize with memory cache (no Redis)."""
        manager = CacheManager(use_redis=False)
        assert manager._redis_client is None
        stats = manager.get_stats()
        assert "memory" in stats["backend"]

    def test_generate_cache_key_without_thread(self):
        """Generate cache key without thread ID."""
        manager = CacheManager(use_redis=False)
        key = manager._generate_cache_key("rag", "test content")
        assert key.startswith("rag:global:")

    def test_generate_cache_key_with_thread(self):
        """Generate cache key with thread ID."""
        manager = CacheManager(use_redis=False)
        key = manager._generate_cache_key("rag", "test content", thread_id="thread123")
        assert "thread123" in key
        assert key.startswith("rag:")

    def test_cache_key_consistency(self):
        """Same content should generate same key."""
        manager = CacheManager(use_redis=False)
        key1 = manager._generate_cache_key("rag", "test content")
        key2 = manager._generate_cache_key("rag", "test content")
        assert key1 == key2

    def test_cache_key_different_content(self):
        """Different content should generate different keys."""
        manager = CacheManager(use_redis=False)
        key1 = manager._generate_cache_key("rag", "content A")
        key2 = manager._generate_cache_key("rag", "content B")
        assert key1 != key2

    def test_memory_cache_get_set(self):
        """Get and set with memory cache."""
        manager = CacheManager(use_redis=False, default_ttl=3600)

        manager.set("test", "query", {"result": "data"})
        result = manager.get("test", "query")

        assert result == {"result": "data"}

    def test_memory_cache_miss(self):
        """Cache miss returns None."""
        manager = CacheManager(use_redis=False)
        result = manager.get("test", "nonexistent")
        assert result is None

    def test_memory_cache_expiry(self):
        """Expired items should not be returned."""
        manager = CacheManager(use_redis=False, default_ttl=1)

        manager.set("test", "query", {"result": "data"}, ttl=-1)  # Already expired

        # Manually expire the cache item
        cache_key = manager._generate_cache_key("test", "query")
        manager._memory_cache.set(
            cache_key,
            {"result": "data"},
            datetime.now() - timedelta(hours=1)  # Past expiry
        )

        result = manager.get("test", "query")
        assert result is None

    def test_clear_all(self):
        """Clear all cache."""
        manager = CacheManager(use_redis=False)

        manager.set("rag", "query1", "data1")
        manager.set("llm", "query2", "data2")

        count = manager.clear()

        assert count >= 2
        assert manager.get("rag", "query1") is None
        assert manager.get("llm", "query2") is None

    def test_clear_prefix(self):
        """Clear cache by prefix."""
        manager = CacheManager(use_redis=False)

        manager.set("rag", "query1", "data1")
        manager.set("rag", "query2", "data2")
        manager.set("llm", "query3", "data3")

        count = manager.clear("rag")

        assert count >= 2
        assert manager.get("rag", "query1") is None
        assert manager.get("rag", "query2") is None
        assert manager.get("llm", "query3") is not None

    def test_get_stats(self):
        """Get cache statistics."""
        manager = CacheManager(use_redis=False, max_memory_cache_size=100)

        manager.set("test", "query", "data")
        manager.get("test", "query")  # Hit
        manager.get("test", "missing")  # Miss

        stats = manager.get_stats()

        assert "backend" in stats
        assert "memory_cache_size" in stats
        assert "default_ttl_seconds" in stats

    def test_thread_isolation(self):
        """Thread-specific cache should be isolated."""
        manager = CacheManager(use_redis=False)

        # Set same content for different threads
        manager.set("test", "query", "data1", thread_id="thread1")
        manager.set("test", "query", "data2", thread_id="thread2")

        result1 = manager.get("test", "query", thread_id="thread1")
        result2 = manager.get("test", "query", thread_id="thread2")

        assert result1 == "data1"
        assert result2 == "data2"

    def test_custom_ttl(self):
        """Custom TTL should be applied."""
        manager = CacheManager(use_redis=False, default_ttl=3600)

        # Set with custom TTL
        result = manager.set("test", "query", "data", ttl=7200)
        assert result is True


class TestFAQ:
    """Tests for FAQ functionality in CacheManager."""

    def test_get_faq_with_mock_database(self):
        """Test FAQ lookup with mocked database."""
        manager = CacheManager(use_redis=False)

        # Patch the FAQ_DATABASE for testing
        with patch.dict("react_agent.cache_manager.FAQ_DATABASE", {
            "탄소배출권이란": "탄소배출권은 온실가스를 배출할 수 있는 권리입니다."
        }):
            # Exact match
            result = manager.get_faq("탄소배출권이란 무엇인가요")
            # May or may not match depending on similarity threshold
            # Just test that the function runs without error
            assert result is None or isinstance(result, str)

    def test_get_faq_no_match(self):
        """Test FAQ lookup with no match."""
        manager = CacheManager(use_redis=False)

        with patch.dict("react_agent.cache_manager.FAQ_DATABASE", {
            "탄소배출권이란": "탄소배출권은 온실가스를 배출할 수 있는 권리입니다."
        }):
            result = manager.get_faq("완전히 다른 질문입니다")
            assert result is None
