"""Source registry configuration for crawling policy and news sources.

This module defines the configuration for various sources to be crawled,
including domestic (Korean) official sources, international official sources,
and media sources.
"""

from dataclasses import dataclass
from typing import List, Optional

from .crawler import BaseCrawler, CrawlerRegistry, RSSCrawler


@dataclass
class SourceConfig:
    """Configuration for a crawling source.

    Attributes:
        name: Display name of the source.
        base_url: Base URL of the source website.
        rss_url: URL of the RSS feed if available.
        list_url: URL of the article list page if available.
        source_type: Type of source ('official', 'media', 'research').
        language: Language code ('ko' for Korean, 'en' for English).
        category: Category or classification of the source.
        description: Brief description of the source.
    """

    name: str
    base_url: str
    rss_url: Optional[str] = None
    list_url: Optional[str] = None
    source_type: str = "official"
    language: str = "ko"
    category: str = ""
    description: str = ""


# Domestic (Korean) Official Sources
DOMESTIC_SOURCES: List[SourceConfig] = [
    SourceConfig(
        name="환경부",
        base_url="https://me.go.kr",
        rss_url="https://me.go.kr/rss/news.xml",
        source_type="official",
        language="ko",
        category="환경정책",
        description="대한민국 환경부 - 환경 정책 및 기후변화 대응",
    ),
    SourceConfig(
        name="산업통상자원부",
        base_url="https://motie.go.kr",
        rss_url="https://www.motie.go.kr/rss/news.xml",
        source_type="official",
        language="ko",
        category="산업정책",
        description="산업통상자원부 - 에너지 및 산업 정책",
    ),
    SourceConfig(
        name="한국환경공단",
        base_url="https://keco.or.kr",
        list_url="https://www.keco.or.kr/kr/board/notice/list.do",
        source_type="official",
        language="ko",
        category="환경관리",
        description="한국환경공단 - 환경 관리 및 서비스",
    ),
    SourceConfig(
        name="온실가스종합정보센터",
        base_url="https://gir.go.kr",
        list_url="https://www.gir.go.kr/home/board/read.do",
        source_type="official",
        language="ko",
        category="온실가스",
        description="온실가스종합정보센터 - 온실가스 통계 및 정보",
    ),
    SourceConfig(
        name="탄소중립위원회",
        base_url="https://2050cnc.go.kr",
        list_url="https://www.2050cnc.go.kr/base/board/list",
        source_type="official",
        language="ko",
        category="탄소중립",
        description="2050 탄소중립녹색성장위원회 - 탄소중립 정책 조정",
    ),
]


# International Official Sources
INTERNATIONAL_SOURCES: List[SourceConfig] = [
    SourceConfig(
        name="UNFCCC",
        base_url="https://unfccc.int",
        rss_url="https://unfccc.int/rss.xml",
        source_type="official",
        language="en",
        category="climate",
        description="United Nations Framework Convention on Climate Change",
    ),
    SourceConfig(
        name="EU Commission",
        base_url="https://ec.europa.eu",
        rss_url="https://ec.europa.eu/clima/rss_en",
        source_type="official",
        language="en",
        category="climate",
        description="European Commission - Climate Action",
    ),
    SourceConfig(
        name="IPCC",
        base_url="https://ipcc.ch",
        rss_url="https://www.ipcc.ch/feed/",
        source_type="official",
        language="en",
        category="climate science",
        description="Intergovernmental Panel on Climate Change",
    ),
    SourceConfig(
        name="IEA",
        base_url="https://iea.org",
        rss_url="https://www.iea.org/rss/news.xml",
        source_type="official",
        language="en",
        category="energy",
        description="International Energy Agency",
    ),
    SourceConfig(
        name="UNEP",
        base_url="https://unep.org",
        rss_url="https://www.unep.org/rss.xml",
        source_type="official",
        language="en",
        category="environment",
        description="United Nations Environment Programme",
    ),
]


# Media Sources
MEDIA_SOURCES: List[SourceConfig] = [
    SourceConfig(
        name="에너지경제",
        base_url="https://ekn.kr",
        rss_url="https://www.ekn.kr/rss/allArticle.xml",
        source_type="media",
        language="ko",
        category="에너지",
        description="에너지경제신문 - 에너지 산업 전문 미디어",
    ),
    SourceConfig(
        name="전기신문",
        base_url="https://electimes.com",
        rss_url="https://www.electimes.com/rss/allArticle.xml",
        source_type="media",
        language="ko",
        category="전력",
        description="전기신문 - 전력 산업 전문 미디어",
    ),
    SourceConfig(
        name="이투뉴스",
        base_url="https://e2news.com",
        rss_url="https://www.e2news.com/rss/allArticle.xml",
        source_type="media",
        language="ko",
        category="에너지환경",
        description="이투뉴스 - 에너지환경 전문 미디어",
    ),
]


def create_crawler_from_config(config: SourceConfig) -> Optional[BaseCrawler]:
    """Create a crawler instance from a source configuration.

    Creates an appropriate crawler based on the source configuration.
    Currently supports RSS-based crawlers.

    Args:
        config: Source configuration to create crawler from.

    Returns:
        A BaseCrawler instance if successful, None otherwise.
    """
    if config.rss_url:
        return RSSCrawler(
            name=config.name,
            base_url=config.base_url,
            rss_url=config.rss_url,
            source_type=config.source_type,
            language=config.language,
        )
    # TODO: Add support for HTML list crawlers
    return None


def get_default_registry() -> CrawlerRegistry:
    """Create and return a default crawler registry with all configured sources.

    Creates a CrawlerRegistry and registers crawlers for all sources
    that have RSS feeds configured.

    Returns:
        A CrawlerRegistry with all available crawlers registered.
    """
    registry = CrawlerRegistry()

    # Register all sources that can be crawled
    all_sources = get_all_sources()
    for config in all_sources:
        crawler = create_crawler_from_config(config)
        if crawler is not None:
            registry.register(crawler)

    return registry


def get_all_sources() -> List[SourceConfig]:
    """Get all configured sources across all categories.

    Returns:
        A list of all SourceConfig instances from all categories.
    """
    return DOMESTIC_SOURCES + INTERNATIONAL_SOURCES + MEDIA_SOURCES
