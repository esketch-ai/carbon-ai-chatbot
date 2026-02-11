"""Tests for scheduler and pipeline modules."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from react_agent.weekly_pipeline.scheduler import SchedulerConfig, PipelineScheduler
from react_agent.weekly_pipeline.pipeline import PipelineResult, WeeklyPipeline


class TestSchedulerConfig:
    """Test SchedulerConfig dataclass."""

    def test_default_config(self):
        """Test default SchedulerConfig values."""
        config = SchedulerConfig()

        assert config.day_of_week == "mon"
        assert config.hour == 0
        assert config.minute == 0
        assert config.timezone == "Asia/Seoul"

    def test_custom_config(self):
        """Test SchedulerConfig with custom values."""
        config = SchedulerConfig(
            day_of_week="fri",
            hour=9,
            minute=30,
            timezone="UTC",
        )

        assert config.day_of_week == "fri"
        assert config.hour == 9
        assert config.minute == 30
        assert config.timezone == "UTC"


class TestPipelineResult:
    """Test PipelineResult dataclass."""

    def test_pipeline_result_creation(self):
        """Test creating PipelineResult with all fields."""
        start = datetime.now()
        end = datetime.now()

        result = PipelineResult(
            start_time=start,
            end_time=end,
            crawled_count=10,
            preprocessed_count=8,
            analyzed_count=8,
            chunks_created=15,
            new_experts=["hydrogen_expert"],
            report_path="/path/to/report.md",
            errors=[],
        )

        assert result.start_time == start
        assert result.end_time == end
        assert result.crawled_count == 10
        assert result.preprocessed_count == 8
        assert result.analyzed_count == 8
        assert result.chunks_created == 15
        assert result.new_experts == ["hydrogen_expert"]
        assert result.report_path == "/path/to/report.md"
        assert result.errors == []

    def test_pipeline_result_with_errors(self):
        """Test creating PipelineResult with errors."""
        start = datetime.now()
        end = datetime.now()

        result = PipelineResult(
            start_time=start,
            end_time=end,
            crawled_count=5,
            preprocessed_count=3,
            analyzed_count=2,
            chunks_created=4,
            new_experts=[],
            report_path="",
            errors=["Crawl error", "Analysis error"],
        )

        assert len(result.errors) == 2
        assert "Crawl error" in result.errors


class TestWeeklyPipeline:
    """Test WeeklyPipeline class."""

    def test_pipeline_init(self):
        """Test WeeklyPipeline initialization."""
        pipeline = WeeklyPipeline()

        assert pipeline.days_back == 7
        assert pipeline.enable_llm_meeting is True

    def test_pipeline_init_custom(self):
        """Test WeeklyPipeline initialization with custom values."""
        pipeline = WeeklyPipeline(days_back=14, enable_llm_meeting=False)

        assert pipeline.days_back == 14
        assert pipeline.enable_llm_meeting is False

    def test_pipeline_stages(self):
        """Test that run method exists."""
        pipeline = WeeklyPipeline()

        # Verify run method exists
        assert hasattr(pipeline, "run")
        assert callable(getattr(pipeline, "run"))

    def test_pipeline_has_stage_methods(self):
        """Test that all stage methods exist."""
        pipeline = WeeklyPipeline()

        # Verify all stage methods exist
        assert hasattr(pipeline, "_stage_crawl")
        assert hasattr(pipeline, "_stage_preprocess")
        assert hasattr(pipeline, "_stage_classify")
        assert hasattr(pipeline, "_stage_meeting")
        assert hasattr(pipeline, "_stage_analyze")
        assert hasattr(pipeline, "_stage_report")


class TestPipelineScheduler:
    """Test PipelineScheduler class."""

    def test_scheduler_init_default(self):
        """Test PipelineScheduler initialization with defaults."""
        scheduler = PipelineScheduler()

        assert scheduler.config.day_of_week == "mon"
        assert scheduler.config.hour == 0
        assert scheduler.config.minute == 0
        assert scheduler._on_complete is None

    def test_scheduler_init_custom(self):
        """Test PipelineScheduler initialization with custom config."""
        config = SchedulerConfig(
            day_of_week="wed",
            hour=14,
            minute=0,
            timezone="Asia/Seoul",
        )
        callback = MagicMock()

        scheduler = PipelineScheduler(config=config, on_complete=callback)

        assert scheduler.config.day_of_week == "wed"
        assert scheduler.config.hour == 14
        assert scheduler._on_complete is callback

    def test_scheduler_is_running_property(self):
        """Test is_running property."""
        scheduler = PipelineScheduler()

        # Initially not running
        assert scheduler.is_running is False

    def test_scheduler_has_start_stop_methods(self):
        """Test that start and stop methods exist."""
        scheduler = PipelineScheduler()

        assert hasattr(scheduler, "start")
        assert hasattr(scheduler, "stop")
        assert hasattr(scheduler, "run_now")

    def test_scheduler_next_run_time_property(self):
        """Test next_run_time property when not running."""
        scheduler = PipelineScheduler()

        # When not running, next_run_time should be None
        assert scheduler.next_run_time is None


class TestPipelineIntegration:
    """Integration tests for pipeline and scheduler."""

    @pytest.mark.asyncio
    async def test_run_now(self):
        """Test running pipeline immediately via scheduler."""
        scheduler = PipelineScheduler()

        # Mock the internal pipeline
        with patch.object(scheduler, "_run_pipeline") as mock_run:
            mock_result = PipelineResult(
                start_time=datetime.now(),
                end_time=datetime.now(),
                crawled_count=5,
                preprocessed_count=5,
                analyzed_count=5,
                chunks_created=10,
                new_experts=[],
                report_path="/test/report.md",
                errors=[],
            )
            mock_run.return_value = mock_result

            result = await scheduler.run_now()

            assert result is mock_result
            mock_run.assert_called_once()
