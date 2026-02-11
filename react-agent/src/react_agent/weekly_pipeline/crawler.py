"""Crawler module for collecting content from policy and news sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional
from xml.etree import ElementTree

import httpx


@dataclass
class CrawledContent:
    """Data class representing crawled content from a source.

    Attributes:
        title: Article or content title.
        content: Main text content.
        url: Source URL of the content.
        source: Name of the source (e.g., 'moef_rss').
        published_date: Publication date of the content.
        language: Language code (default: 'ko' for Korean).
        category: Category or classification of the content.
        raw_html: Original HTML content if available.
        metadata: Additional metadata as key-value pairs.
    """

    title: str
    content: str
    url: str
    source: str
    published_date: datetime
    language: str = "ko"
    category: str = ""
    raw_html: str = ""
    metadata: Dict = field(default_factory=dict)


class BaseCrawler(ABC):
    """Abstract base class for all crawlers.

    Provides common functionality for HTTP requests and defines
    the interface that all crawlers must implement.

    Attributes:
        name: Unique identifier for the crawler.
        base_url: Base URL of the source website.
        source_type: Type of source (e.g., 'rss', 'html').
        language: Language code for the content.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        source_type: str,
        language: str = "ko",
        timeout: float = 30.0,
    ) -> None:
        """Initialize the base crawler.

        Args:
            name: Unique identifier for the crawler.
            base_url: Base URL of the source website.
            source_type: Type of source (e.g., 'rss', 'html').
            language: Language code for the content (default: 'ko').
            timeout: HTTP request timeout in seconds (default: 30.0).
        """
        self.name = name
        self.base_url = base_url
        self.source_type = source_type
        self.language = language
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create an async HTTP client.

        Returns:
            An httpx.AsyncClient instance.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; PolicyCrawler/1.0)"
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @abstractmethod
    async def crawl(self, days_back: int = 7) -> List[CrawledContent]:
        """Crawl the source and return collected content.

        Args:
            days_back: Number of days to look back for content.

        Returns:
            List of CrawledContent objects.
        """
        pass

    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page and return its content.

        Args:
            url: URL to fetch.

        Returns:
            Page content as string, or None if fetch failed.
        """
        try:
            client = await self._get_client()
            response = await client.get(url)
            response.raise_for_status()
            return response.text
        except Exception:
            return None


class RSSCrawler(BaseCrawler):
    """Crawler for RSS feed sources.

    Extends BaseCrawler with RSS-specific functionality including
    feed parsing and date handling.

    Attributes:
        rss_url: URL of the RSS feed.
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        rss_url: str,
        source_type: str,
        language: str = "ko",
        timeout: float = 30.0,
    ) -> None:
        """Initialize the RSS crawler.

        Args:
            name: Unique identifier for the crawler.
            base_url: Base URL of the source website.
            rss_url: URL of the RSS feed.
            source_type: Type of source (should be 'rss').
            language: Language code for the content (default: 'ko').
            timeout: HTTP request timeout in seconds (default: 30.0).
        """
        super().__init__(name, base_url, source_type, language, timeout)
        self.rss_url = rss_url

    async def crawl(self, days_back: int = 7) -> List[CrawledContent]:
        """Crawl the RSS feed and return collected content.

        Args:
            days_back: Number of days to look back for content.

        Returns:
            List of CrawledContent objects from the feed.
        """
        contents: List[CrawledContent] = []
        cutoff_date = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        cutoff_date = cutoff_date.replace(
            day=cutoff_date.day - days_back if cutoff_date.day > days_back else 1
        )

        feed_content = await self.fetch_page(self.rss_url)
        if not feed_content:
            return contents

        try:
            root = ElementTree.fromstring(feed_content)

            # Handle both RSS 2.0 and Atom feeds
            items = root.findall(".//item")
            if not items:
                items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

            for item in items:
                try:
                    # Extract title
                    title_elem = item.find("title")
                    if title_elem is None:
                        title_elem = item.find(
                            "{http://www.w3.org/2005/Atom}title"
                        )
                    title = (
                        title_elem.text if title_elem is not None else "Untitled"
                    )

                    # Extract link
                    link_elem = item.find("link")
                    if link_elem is None:
                        link_elem = item.find(
                            "{http://www.w3.org/2005/Atom}link"
                        )
                        url = (
                            link_elem.get("href", "")
                            if link_elem is not None
                            else ""
                        )
                    else:
                        url = link_elem.text or ""

                    # Extract description/content
                    desc_elem = item.find("description")
                    if desc_elem is None:
                        desc_elem = item.find(
                            "{http://www.w3.org/2005/Atom}content"
                        )
                    if desc_elem is None:
                        desc_elem = item.find(
                            "{http://www.w3.org/2005/Atom}summary"
                        )
                    content = desc_elem.text if desc_elem is not None else ""

                    # Extract publication date
                    pub_date_elem = item.find("pubDate")
                    if pub_date_elem is None:
                        pub_date_elem = item.find(
                            "{http://www.w3.org/2005/Atom}published"
                        )
                    if pub_date_elem is None:
                        pub_date_elem = item.find(
                            "{http://www.w3.org/2005/Atom}updated"
                        )

                    if pub_date_elem is not None and pub_date_elem.text:
                        pub_date = self._parse_rss_date(pub_date_elem.text)
                    else:
                        pub_date = datetime.now()

                    # Filter by date
                    if pub_date.replace(tzinfo=None) < cutoff_date:
                        continue

                    # Extract category
                    category_elem = item.find("category")
                    if category_elem is None:
                        category_elem = item.find(
                            "{http://www.w3.org/2005/Atom}category"
                        )
                    category = ""
                    if category_elem is not None:
                        category = (
                            category_elem.text
                            or category_elem.get("term", "")
                            or ""
                        )

                    contents.append(
                        CrawledContent(
                            title=title or "",
                            content=content or "",
                            url=url,
                            source=self.name,
                            published_date=pub_date,
                            language=self.language,
                            category=category,
                        )
                    )
                except Exception:
                    # Skip malformed items
                    continue

        except ElementTree.ParseError:
            pass

        return contents

    def _parse_rss_date(self, date_str: str) -> datetime:
        """Parse various RSS date formats.

        Supports RFC 822 (RSS 2.0) and ISO 8601 (Atom) formats.

        Args:
            date_str: Date string to parse.

        Returns:
            Parsed datetime object.
        """
        # Try RFC 822 format (RSS 2.0)
        try:
            return parsedate_to_datetime(date_str)
        except (ValueError, TypeError):
            pass

        # Try ISO 8601 format (Atom)
        try:
            # Handle various ISO formats
            if date_str.endswith("Z"):
                date_str = date_str[:-1] + "+00:00"
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            pass

        # Fallback to current time
        return datetime.now()


class CrawlerRegistry:
    """Registry for managing multiple crawlers.

    Provides methods to register, retrieve, and operate on
    multiple crawler instances.
    """

    def __init__(self) -> None:
        """Initialize the crawler registry."""
        self._crawlers: Dict[str, BaseCrawler] = {}

    def register(self, crawler: BaseCrawler) -> None:
        """Register a crawler.

        Args:
            crawler: Crawler instance to register.
        """
        self._crawlers[crawler.name] = crawler

    def get(self, name: str) -> Optional[BaseCrawler]:
        """Get a crawler by name.

        Args:
            name: Name of the crawler.

        Returns:
            Crawler instance if found, None otherwise.
        """
        return self._crawlers.get(name)

    def get_all(self) -> List[BaseCrawler]:
        """Get all registered crawlers.

        Returns:
            List of all registered crawler instances.
        """
        return list(self._crawlers.values())

    def get_by_type(self, source_type: str) -> List[BaseCrawler]:
        """Get crawlers by source type.

        Args:
            source_type: Type of source (e.g., 'rss', 'html').

        Returns:
            List of crawlers matching the specified type.
        """
        return [
            crawler
            for crawler in self._crawlers.values()
            if crawler.source_type == source_type
        ]

    async def crawl_all(self, days_back: int = 7) -> List[CrawledContent]:
        """Crawl from all registered crawlers.

        Args:
            days_back: Number of days to look back for content.

        Returns:
            Combined list of CrawledContent from all crawlers.
        """
        all_content: List[CrawledContent] = []

        for crawler in self._crawlers.values():
            try:
                content = await crawler.crawl(days_back=days_back)
                all_content.extend(content)
            except Exception:
                # Continue with other crawlers if one fails
                continue

        return all_content

    async def close_all(self) -> None:
        """Close all registered crawlers and release resources."""
        for crawler in self._crawlers.values():
            try:
                await crawler.close()
            except Exception:
                # Continue closing other crawlers if one fails
                continue
