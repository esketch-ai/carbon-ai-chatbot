"""Weekly pipeline module for policy/news analysis."""

from .classifier import ClassificationResult, RuleBasedClassifier
from .crawler import BaseCrawler, CrawledContent, CrawlerRegistry, RSSCrawler
from .preprocessor import PreprocessedContent, Preprocessor
from .sources import (
    DOMESTIC_SOURCES,
    INTERNATIONAL_SOURCES,
    MEDIA_SOURCES,
    SourceConfig,
    get_default_registry,
)

__all__ = [
    "BaseCrawler",
    "ClassificationResult",
    "CrawledContent",
    "CrawlerRegistry",
    "DOMESTIC_SOURCES",
    "INTERNATIONAL_SOURCES",
    "MEDIA_SOURCES",
    "PreprocessedContent",
    "Preprocessor",
    "RSSCrawler",
    "RuleBasedClassifier",
    "SourceConfig",
    "get_default_registry",
]
