"""Weekly pipeline module for policy/news analysis."""

from .crawler import BaseCrawler, CrawledContent, CrawlerRegistry, RSSCrawler
from .sources import (
    DOMESTIC_SOURCES,
    INTERNATIONAL_SOURCES,
    MEDIA_SOURCES,
    SourceConfig,
    get_default_registry,
)

__all__ = [
    "BaseCrawler",
    "CrawledContent",
    "CrawlerRegistry",
    "DOMESTIC_SOURCES",
    "INTERNATIONAL_SOURCES",
    "MEDIA_SOURCES",
    "RSSCrawler",
    "SourceConfig",
    "get_default_registry",
]
