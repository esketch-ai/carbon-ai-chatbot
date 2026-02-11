"""Tests for source registry configuration."""

import pytest

from react_agent.weekly_pipeline.sources import (
    DOMESTIC_SOURCES,
    INTERNATIONAL_SOURCES,
    MEDIA_SOURCES,
    SourceConfig,
    create_crawler_from_config,
    get_all_sources,
    get_default_registry,
)


class TestSourceConfig:
    """Tests for SourceConfig dataclass."""

    def test_source_config_required_fields(self) -> None:
        """Test that SourceConfig can be created with required fields."""
        config = SourceConfig(
            name="Test Source",
            base_url="https://example.com",
        )
        assert config.name == "Test Source"
        assert config.base_url == "https://example.com"

    def test_source_config_default_values(self) -> None:
        """Test that SourceConfig has correct default values."""
        config = SourceConfig(
            name="Test Source",
            base_url="https://example.com",
        )
        assert config.rss_url is None
        assert config.list_url is None
        assert config.source_type == "official"
        assert config.language == "ko"
        assert config.category == ""
        assert config.description == ""

    def test_source_config_all_fields(self) -> None:
        """Test that SourceConfig can be created with all fields."""
        config = SourceConfig(
            name="Test Source",
            base_url="https://example.com",
            rss_url="https://example.com/rss",
            list_url="https://example.com/list",
            source_type="media",
            language="en",
            category="climate",
            description="Test description",
        )
        assert config.name == "Test Source"
        assert config.base_url == "https://example.com"
        assert config.rss_url == "https://example.com/rss"
        assert config.list_url == "https://example.com/list"
        assert config.source_type == "media"
        assert config.language == "en"
        assert config.category == "climate"
        assert config.description == "Test description"


class TestDomesticSources:
    """Tests for domestic (Korean) source configurations."""

    def test_domestic_sources_exist(self) -> None:
        """Test that at least 4 domestic sources exist."""
        assert len(DOMESTIC_SOURCES) >= 4

    def test_domestic_sources_include_ministry_of_environment(self) -> None:
        """Test that domestic sources include Ministry of Environment (환경부)."""
        source_names = [source.name for source in DOMESTIC_SOURCES]
        assert "환경부" in source_names

    def test_domestic_sources_are_source_configs(self) -> None:
        """Test that all domestic sources are SourceConfig instances."""
        for source in DOMESTIC_SOURCES:
            assert isinstance(source, SourceConfig)

    def test_domestic_sources_have_valid_urls(self) -> None:
        """Test that all domestic sources have valid base URLs."""
        for source in DOMESTIC_SOURCES:
            assert source.base_url.startswith("https://")

    def test_domestic_sources_are_korean(self) -> None:
        """Test that all domestic sources have Korean language setting."""
        for source in DOMESTIC_SOURCES:
            assert source.language == "ko"


class TestInternationalSources:
    """Tests for international source configurations."""

    def test_international_sources_exist(self) -> None:
        """Test that at least 4 international sources exist."""
        assert len(INTERNATIONAL_SOURCES) >= 4

    def test_international_sources_include_unfccc(self) -> None:
        """Test that international sources include UNFCCC."""
        source_names = [source.name for source in INTERNATIONAL_SOURCES]
        assert "UNFCCC" in source_names

    def test_international_sources_are_source_configs(self) -> None:
        """Test that all international sources are SourceConfig instances."""
        for source in INTERNATIONAL_SOURCES:
            assert isinstance(source, SourceConfig)

    def test_international_sources_have_valid_urls(self) -> None:
        """Test that all international sources have valid base URLs."""
        for source in INTERNATIONAL_SOURCES:
            assert source.base_url.startswith("https://")

    def test_international_sources_are_english(self) -> None:
        """Test that all international sources have English language setting."""
        for source in INTERNATIONAL_SOURCES:
            assert source.language == "en"


class TestMediaSources:
    """Tests for media source configurations."""

    def test_media_sources_exist(self) -> None:
        """Test that at least 2 media sources exist."""
        assert len(MEDIA_SOURCES) >= 2

    def test_media_sources_are_source_configs(self) -> None:
        """Test that all media sources are SourceConfig instances."""
        for source in MEDIA_SOURCES:
            assert isinstance(source, SourceConfig)

    def test_media_sources_have_valid_urls(self) -> None:
        """Test that all media sources have valid base URLs."""
        for source in MEDIA_SOURCES:
            assert source.base_url.startswith("https://")

    def test_media_sources_have_media_type(self) -> None:
        """Test that all media sources have 'media' source type."""
        for source in MEDIA_SOURCES:
            assert source.source_type == "media"


class TestGetDefaultRegistry:
    """Tests for get_default_registry function."""

    def test_get_default_registry_returns_registry(self) -> None:
        """Test that get_default_registry returns a CrawlerRegistry."""
        from react_agent.weekly_pipeline.crawler import CrawlerRegistry

        registry = get_default_registry()
        assert isinstance(registry, CrawlerRegistry)

    def test_get_default_registry_has_crawlers(self) -> None:
        """Test that the default registry has at least 1 crawler registered."""
        registry = get_default_registry()
        crawlers = registry.get_all()
        assert len(crawlers) >= 1


class TestCreateCrawlerFromConfig:
    """Tests for create_crawler_from_config function."""

    def test_create_crawler_from_rss_config(self) -> None:
        """Test creating a crawler from RSS config."""
        from react_agent.weekly_pipeline.crawler import RSSCrawler

        config = SourceConfig(
            name="Test RSS Source",
            base_url="https://example.com",
            rss_url="https://example.com/rss.xml",
            source_type="official",
        )
        crawler = create_crawler_from_config(config)
        assert crawler is not None
        assert isinstance(crawler, RSSCrawler)
        assert crawler.name == "Test RSS Source"
        assert crawler.rss_url == "https://example.com/rss.xml"

    def test_create_crawler_from_config_without_rss(self) -> None:
        """Test that config without RSS URL returns None."""
        config = SourceConfig(
            name="Test Source",
            base_url="https://example.com",
        )
        crawler = create_crawler_from_config(config)
        assert crawler is None


class TestGetAllSources:
    """Tests for get_all_sources function."""

    def test_get_all_sources_returns_list(self) -> None:
        """Test that get_all_sources returns a list."""
        sources = get_all_sources()
        assert isinstance(sources, list)

    def test_get_all_sources_contains_all_source_types(self) -> None:
        """Test that get_all_sources contains sources from all categories."""
        sources = get_all_sources()
        total_expected = (
            len(DOMESTIC_SOURCES)
            + len(INTERNATIONAL_SOURCES)
            + len(MEDIA_SOURCES)
        )
        assert len(sources) == total_expected

    def test_get_all_sources_all_are_configs(self) -> None:
        """Test that all items from get_all_sources are SourceConfig instances."""
        sources = get_all_sources()
        for source in sources:
            assert isinstance(source, SourceConfig)
