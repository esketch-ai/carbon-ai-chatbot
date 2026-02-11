"""Tests for crawler module."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from react_agent.weekly_pipeline import (
    BaseCrawler,
    CrawledContent,
    CrawlerRegistry,
    RSSCrawler,
)


class TestCrawledContent:
    """Test CrawledContent dataclass."""

    def test_create_with_required_fields(self):
        """Test creating CrawledContent with required fields."""
        now = datetime.now()
        content = CrawledContent(
            title="Test Title",
            content="Test content body",
            url="https://example.com/article",
            source="test_source",
            published_date=now,
        )

        assert content.title == "Test Title"
        assert content.content == "Test content body"
        assert content.url == "https://example.com/article"
        assert content.source == "test_source"
        assert content.published_date == now
        assert content.language == "ko"  # default
        assert content.category == ""  # default
        assert content.raw_html == ""  # default
        assert content.metadata == {}  # default

    def test_create_with_all_fields(self):
        """Test creating CrawledContent with all fields."""
        now = datetime.now()
        metadata = {"author": "John Doe", "tags": ["policy", "news"]}

        content = CrawledContent(
            title="Full Article",
            content="Full content body",
            url="https://example.com/full",
            source="full_source",
            published_date=now,
            language="en",
            category="policy",
            raw_html="<html>...</html>",
            metadata=metadata,
        )

        assert content.language == "en"
        assert content.category == "policy"
        assert content.raw_html == "<html>...</html>"
        assert content.metadata == metadata


class TestCrawlerRegistry:
    """Test CrawlerRegistry class."""

    def test_register_and_get_crawler(self):
        """Test registering and retrieving a crawler."""
        registry = CrawlerRegistry()

        # Create a mock crawler
        mock_crawler = MagicMock(spec=BaseCrawler)
        mock_crawler.name = "test_crawler"
        mock_crawler.source_type = "rss"

        registry.register(mock_crawler)

        retrieved = registry.get("test_crawler")
        assert retrieved is mock_crawler

    def test_get_nonexistent_crawler(self):
        """Test getting a crawler that doesn't exist."""
        registry = CrawlerRegistry()

        result = registry.get("nonexistent")
        assert result is None

    def test_get_all_crawlers(self):
        """Test getting all registered crawlers."""
        registry = CrawlerRegistry()

        mock_crawler1 = MagicMock(spec=BaseCrawler)
        mock_crawler1.name = "crawler1"
        mock_crawler1.source_type = "rss"

        mock_crawler2 = MagicMock(spec=BaseCrawler)
        mock_crawler2.name = "crawler2"
        mock_crawler2.source_type = "html"

        registry.register(mock_crawler1)
        registry.register(mock_crawler2)

        all_crawlers = registry.get_all()
        assert len(all_crawlers) == 2
        assert mock_crawler1 in all_crawlers
        assert mock_crawler2 in all_crawlers

    def test_get_by_type(self):
        """Test getting crawlers by source type."""
        registry = CrawlerRegistry()

        mock_rss1 = MagicMock(spec=BaseCrawler)
        mock_rss1.name = "rss1"
        mock_rss1.source_type = "rss"

        mock_rss2 = MagicMock(spec=BaseCrawler)
        mock_rss2.name = "rss2"
        mock_rss2.source_type = "rss"

        mock_html = MagicMock(spec=BaseCrawler)
        mock_html.name = "html1"
        mock_html.source_type = "html"

        registry.register(mock_rss1)
        registry.register(mock_rss2)
        registry.register(mock_html)

        rss_crawlers = registry.get_by_type("rss")
        assert len(rss_crawlers) == 2

        html_crawlers = registry.get_by_type("html")
        assert len(html_crawlers) == 1

    @pytest.mark.asyncio
    async def test_crawl_all(self):
        """Test crawling from all registered crawlers."""
        registry = CrawlerRegistry()

        now = datetime.now()
        content1 = CrawledContent(
            title="Article 1",
            content="Content 1",
            url="https://example.com/1",
            source="source1",
            published_date=now,
        )
        content2 = CrawledContent(
            title="Article 2",
            content="Content 2",
            url="https://example.com/2",
            source="source2",
            published_date=now,
        )

        mock_crawler1 = MagicMock(spec=BaseCrawler)
        mock_crawler1.name = "crawler1"
        mock_crawler1.source_type = "rss"
        mock_crawler1.crawl = AsyncMock(return_value=[content1])

        mock_crawler2 = MagicMock(spec=BaseCrawler)
        mock_crawler2.name = "crawler2"
        mock_crawler2.source_type = "rss"
        mock_crawler2.crawl = AsyncMock(return_value=[content2])

        registry.register(mock_crawler1)
        registry.register(mock_crawler2)

        all_content = await registry.crawl_all(days_back=7)

        assert len(all_content) == 2
        assert content1 in all_content
        assert content2 in all_content

    @pytest.mark.asyncio
    async def test_close_all(self):
        """Test closing all crawlers."""
        registry = CrawlerRegistry()

        mock_crawler1 = MagicMock(spec=BaseCrawler)
        mock_crawler1.name = "crawler1"
        mock_crawler1.source_type = "rss"
        mock_crawler1.close = AsyncMock()

        mock_crawler2 = MagicMock(spec=BaseCrawler)
        mock_crawler2.name = "crawler2"
        mock_crawler2.source_type = "rss"
        mock_crawler2.close = AsyncMock()

        registry.register(mock_crawler1)
        registry.register(mock_crawler2)

        await registry.close_all()

        mock_crawler1.close.assert_called_once()
        mock_crawler2.close.assert_called_once()


class TestRSSCrawler:
    """Test RSSCrawler class."""

    def test_initialization(self):
        """Test RSSCrawler initialization."""
        crawler = RSSCrawler(
            name="test_rss",
            base_url="https://example.com",
            rss_url="https://example.com/feed.xml",
            source_type="rss",
            language="ko",
        )

        assert crawler.name == "test_rss"
        assert crawler.base_url == "https://example.com"
        assert crawler.rss_url == "https://example.com/feed.xml"
        assert crawler.source_type == "rss"
        assert crawler.language == "ko"
        assert crawler.timeout == 30.0  # default

    def test_initialization_with_custom_timeout(self):
        """Test RSSCrawler initialization with custom timeout."""
        crawler = RSSCrawler(
            name="test_rss",
            base_url="https://example.com",
            rss_url="https://example.com/feed.xml",
            source_type="rss",
            timeout=60.0,
        )

        assert crawler.timeout == 60.0

    def test_parse_rss_date_rfc822(self):
        """Test parsing RFC 822 date format."""
        crawler = RSSCrawler(
            name="test_rss",
            base_url="https://example.com",
            rss_url="https://example.com/feed.xml",
            source_type="rss",
        )

        # RFC 822 format
        date_str = "Mon, 10 Feb 2025 12:00:00 +0900"
        result = crawler._parse_rss_date(date_str)

        assert result.year == 2025
        assert result.month == 2
        assert result.day == 10

    def test_parse_rss_date_iso(self):
        """Test parsing ISO date format."""
        crawler = RSSCrawler(
            name="test_rss",
            base_url="https://example.com",
            rss_url="https://example.com/feed.xml",
            source_type="rss",
        )

        # ISO format
        date_str = "2025-02-10T12:00:00Z"
        result = crawler._parse_rss_date(date_str)

        assert result.year == 2025
        assert result.month == 2
        assert result.day == 10


class TestBaseCrawler:
    """Test BaseCrawler abstract class."""

    def test_cannot_instantiate_directly(self):
        """Test that BaseCrawler cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseCrawler(
                name="test",
                base_url="https://example.com",
                source_type="test",
            )

    @pytest.mark.asyncio
    async def test_fetch_page(self):
        """Test fetch_page method."""
        crawler = RSSCrawler(
            name="test_rss",
            base_url="https://example.com",
            rss_url="https://example.com/feed.xml",
            source_type="rss",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>Test</html>"
        mock_response.raise_for_status = MagicMock()

        with patch.object(crawler, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await crawler.fetch_page("https://example.com/page")

            assert result == "<html>Test</html>"
            mock_client.get.assert_called_once_with("https://example.com/page")

    @pytest.mark.asyncio
    async def test_fetch_page_error(self):
        """Test fetch_page method with error."""
        crawler = RSSCrawler(
            name="test_rss",
            base_url="https://example.com",
            rss_url="https://example.com/feed.xml",
            source_type="rss",
        )

        with patch.object(crawler, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Network error"))
            mock_get_client.return_value = mock_client

            result = await crawler.fetch_page("https://example.com/page")

            assert result is None

    @pytest.mark.asyncio
    async def test_close(self):
        """Test close method."""
        crawler = RSSCrawler(
            name="test_rss",
            base_url="https://example.com",
            rss_url="https://example.com/feed.xml",
            source_type="rss",
        )

        # Simulate client being created
        mock_client = AsyncMock()
        crawler._client = mock_client

        await crawler.close()

        mock_client.aclose.assert_called_once()
        assert crawler._client is None
