"""통합 테스트"""

import pytest

from react_agent.weekly_pipeline import (
    WeeklyPipeline,
    PipelineScheduler,
    SchedulerConfig,
    get_default_registry,
    BaseCrawler,
    CrawlerRegistry,
    Preprocessor,
    RuleBasedClassifier,
    ExpertMeeting,
    ExpertAnalyzer,
    ReportGenerator,
)


class TestIntegration:
    """통합 테스트"""

    def test_all_components_importable(self):
        """모든 컴포넌트 임포트 가능"""
        assert BaseCrawler is not None
        assert CrawlerRegistry is not None
        assert Preprocessor is not None
        assert RuleBasedClassifier is not None
        assert ExpertMeeting is not None
        assert ExpertAnalyzer is not None
        assert ReportGenerator is not None
        assert WeeklyPipeline is not None
        assert PipelineScheduler is not None

    def test_default_registry_has_crawlers(self):
        """기본 레지스트리에 크롤러 존재"""
        registry = get_default_registry()
        crawlers = registry.get_all()
        assert len(crawlers) > 0

    def test_pipeline_can_be_created(self):
        """파이프라인 생성 가능"""
        pipeline = WeeklyPipeline(days_back=1, enable_llm_meeting=False)
        assert pipeline is not None

    def test_scheduler_can_be_configured(self):
        """스케줄러 설정 가능"""
        config = SchedulerConfig(
            day_of_week="mon",
            hour=0,
            minute=0,
        )
        scheduler = PipelineScheduler(config=config)
        assert scheduler is not None

    def test_all_exports_in_init(self):
        """__init__.py에서 모든 주요 클래스 export"""
        from react_agent.weekly_pipeline import (
            # Crawler
            BaseCrawler,
            CrawlerRegistry,
            CrawledContent,
            RSSCrawler,
            # Sources
            SourceConfig,
            DOMESTIC_SOURCES,
            INTERNATIONAL_SOURCES,
            MEDIA_SOURCES,
            get_default_registry,
            # Preprocessor
            Preprocessor,
            PreprocessedContent,
            # Classifier
            RuleBasedClassifier,
            ClassificationResult,
            # Expert Meeting
            ExpertMeeting,
            MeetingResult,
            NewExpertProposal,
            # Expert Generator
            ExpertGenerator,
            register_dynamic_expert,
            get_dynamic_experts,
            # Analyzer
            ExpertAnalyzer,
            AnalysisResult,
            # Report
            ReportGenerator,
            WeeklyReport,
            # Pipeline
            WeeklyPipeline,
            PipelineResult,
            # Scheduler
            PipelineScheduler,
            SchedulerConfig,
        )
        assert True  # 임포트 성공하면 통과
