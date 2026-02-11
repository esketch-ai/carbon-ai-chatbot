"""Tests for weekly report generator module.

Tests focus on report structure, markdown generation, and file operations.
"""

import os
import tempfile
from datetime import datetime

import pytest

from react_agent.agents.expert_panel.config import ExpertRole
from react_agent.weekly_pipeline.report_generator import (
    ExpertSection,
    ReportGenerator,
    WeeklyReport,
)


class TestExpertSection:
    """Test ExpertSection dataclass."""

    def test_expert_section_creation(self):
        """Test creating ExpertSection with required fields."""
        section = ExpertSection(
            expert_role=ExpertRole.POLICY_EXPERT,
            expert_name="Dr. 김정책",
            summaries=["NDC 목표 상향 조정 발표", "탄소중립 정책 강화"],
            key_findings=["2030년까지 40% 감축 목표", "배출권거래제 확대"],
            implications=["기업 규제 강화 예상", "신규 투자 필요"],
            content_count=5,
        )

        assert section.expert_role == ExpertRole.POLICY_EXPERT
        assert section.expert_name == "Dr. 김정책"
        assert len(section.summaries) == 2
        assert len(section.key_findings) == 2
        assert len(section.implications) == 2
        assert section.content_count == 5

    def test_expert_section_empty_lists(self):
        """Test creating ExpertSection with empty lists."""
        section = ExpertSection(
            expert_role=ExpertRole.MARKET_EXPERT,
            expert_name="Dr. 이시장",
            summaries=[],
            key_findings=[],
            implications=[],
            content_count=0,
        )

        assert section.expert_role == ExpertRole.MARKET_EXPERT
        assert section.summaries == []
        assert section.key_findings == []
        assert section.implications == []
        assert section.content_count == 0


class TestWeeklyReport:
    """Test WeeklyReport dataclass."""

    def test_weekly_report_structure(self):
        """Test creating WeeklyReport with required fields."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 7)

        section = ExpertSection(
            expert_role=ExpertRole.POLICY_EXPERT,
            expert_name="Dr. 김정책",
            summaries=["정책 요약"],
            key_findings=["발견 1"],
            implications=["시사점 1"],
            content_count=3,
        )

        report = WeeklyReport(
            start_date=start_date,
            end_date=end_date,
            total_crawled=100,
            total_analyzed=50,
            new_chunks=25,
            new_experts=["신규전문가"],
            expert_sections={ExpertRole.POLICY_EXPERT: section},
        )

        assert report.start_date == start_date
        assert report.end_date == end_date
        assert report.total_crawled == 100
        assert report.total_analyzed == 50
        assert report.new_chunks == 25
        assert report.new_experts == ["신규전문가"]
        assert ExpertRole.POLICY_EXPERT in report.expert_sections
        assert report.cross_analysis == ""
        assert report.generated_at is not None

    def test_weekly_report_with_cross_analysis(self):
        """Test creating WeeklyReport with cross_analysis."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 7)

        report = WeeklyReport(
            start_date=start_date,
            end_date=end_date,
            total_crawled=100,
            total_analyzed=50,
            new_chunks=25,
            new_experts=[],
            expert_sections={},
            cross_analysis="정책과 시장 간 상호작용 분석 결과",
        )

        assert report.cross_analysis == "정책과 시장 간 상호작용 분석 결과"

    def test_weekly_report_generated_at_default(self):
        """Test that generated_at has a default value."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 7)

        before = datetime.now()
        report = WeeklyReport(
            start_date=start_date,
            end_date=end_date,
            total_crawled=100,
            total_analyzed=50,
            new_chunks=25,
            new_experts=[],
            expert_sections={},
        )
        after = datetime.now()

        assert before <= report.generated_at <= after


class TestReportGenerator:
    """Test ReportGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create a ReportGenerator instance with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield ReportGenerator(output_dir=tmpdir)

    @pytest.fixture
    def sample_expert_section(self):
        """Create a sample ExpertSection for testing."""
        return ExpertSection(
            expert_role=ExpertRole.POLICY_EXPERT,
            expert_name="Dr. 김정책",
            summaries=["NDC 목표 상향 조정 발표", "탄소중립 기본계획 발표"],
            key_findings=[
                "2030년까지 40% 감축 목표",
                "배출권거래제 3기 계획 확정",
                "RE100 참여 기업 확대",
            ],
            implications=[
                "기업 탄소비용 증가 예상",
                "재생에너지 투자 확대 필요",
            ],
            content_count=5,
        )

    @pytest.fixture
    def sample_weekly_report(self, sample_expert_section):
        """Create a sample WeeklyReport for testing."""
        return WeeklyReport(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            total_crawled=100,
            total_analyzed=50,
            new_chunks=25,
            new_experts=["신재생에너지 전문가"],
            expert_sections={ExpertRole.POLICY_EXPERT: sample_expert_section},
            cross_analysis="정책 변화가 시장에 미치는 영향 분석",
        )

    def test_generator_init_default_output_dir(self):
        """Test ReportGenerator initialization with default output directory."""
        generator = ReportGenerator()
        assert generator.output_dir == "./data/weekly_reports"

    def test_generator_init_custom_output_dir(self, generator):
        """Test ReportGenerator initialization with custom output directory."""
        assert generator.output_dir is not None
        assert generator.output_dir != "./data/weekly_reports"

    def test_expert_icons_defined(self):
        """Test that EXPERT_ICONS dictionary is properly defined."""
        assert hasattr(ReportGenerator, "EXPERT_ICONS")
        assert ExpertRole.POLICY_EXPERT in ReportGenerator.EXPERT_ICONS
        assert ExpertRole.CARBON_CREDIT_EXPERT in ReportGenerator.EXPERT_ICONS
        assert ExpertRole.MARKET_EXPERT in ReportGenerator.EXPERT_ICONS
        assert ExpertRole.TECHNOLOGY_EXPERT in ReportGenerator.EXPERT_ICONS
        assert ExpertRole.MRV_EXPERT in ReportGenerator.EXPERT_ICONS

    def test_expert_icons_emoji_values(self):
        """Test that EXPERT_ICONS contain the correct emojis."""
        icons = ReportGenerator.EXPERT_ICONS
        assert icons[ExpertRole.POLICY_EXPERT] == "🏛️"
        assert icons[ExpertRole.CARBON_CREDIT_EXPERT] == "📜"
        assert icons[ExpertRole.MARKET_EXPERT] == "💹"
        assert icons[ExpertRole.TECHNOLOGY_EXPERT] == "⚡"
        assert icons[ExpertRole.MRV_EXPERT] == "📋"

    def test_report_template_exists(self):
        """Test that REPORT_TEMPLATE is defined."""
        assert hasattr(ReportGenerator, "REPORT_TEMPLATE")
        assert isinstance(ReportGenerator.REPORT_TEMPLATE, str)
        assert len(ReportGenerator.REPORT_TEMPLATE) > 0

    def test_expert_section_template_exists(self):
        """Test that EXPERT_SECTION_TEMPLATE is defined."""
        assert hasattr(ReportGenerator, "EXPERT_SECTION_TEMPLATE")
        assert isinstance(ReportGenerator.EXPERT_SECTION_TEMPLATE, str)
        assert len(ReportGenerator.EXPERT_SECTION_TEMPLATE) > 0

    def test_generate_markdown(self, generator, sample_weekly_report):
        """Test markdown generation from WeeklyReport."""
        markdown = generator.to_markdown(sample_weekly_report)

        # Check basic structure
        assert "주간 탄소정책 브리핑" in markdown
        assert "2024" in markdown

        # Check statistics section
        assert "100" in markdown  # total_crawled
        assert "50" in markdown  # total_analyzed
        assert "25" in markdown  # new_chunks

        # Check expert section
        assert "Dr. 김정책" in markdown or "정책" in markdown

        # Check cross-analysis
        assert "정책 변화가 시장에 미치는 영향 분석" in markdown

    def test_generate_markdown_with_multiple_experts(self, generator):
        """Test markdown generation with multiple expert sections."""
        sections = {
            ExpertRole.POLICY_EXPERT: ExpertSection(
                expert_role=ExpertRole.POLICY_EXPERT,
                expert_name="Dr. 김정책",
                summaries=["정책 요약"],
                key_findings=["정책 발견"],
                implications=["정책 시사점"],
                content_count=3,
            ),
            ExpertRole.MARKET_EXPERT: ExpertSection(
                expert_role=ExpertRole.MARKET_EXPERT,
                expert_name="Dr. 이시장",
                summaries=["시장 요약"],
                key_findings=["시장 발견"],
                implications=["시장 시사점"],
                content_count=4,
            ),
        }

        report = WeeklyReport(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            total_crawled=100,
            total_analyzed=50,
            new_chunks=25,
            new_experts=[],
            expert_sections=sections,
        )

        markdown = generator.to_markdown(report)

        # Check both expert sections are included
        assert "정책" in markdown
        assert "시장" in markdown

    def test_generate_markdown_empty_report(self, generator):
        """Test markdown generation with minimal/empty report."""
        report = WeeklyReport(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            total_crawled=0,
            total_analyzed=0,
            new_chunks=0,
            new_experts=[],
            expert_sections={},
        )

        markdown = generator.to_markdown(report)

        # Should still generate valid markdown
        assert "주간 탄소정책 브리핑" in markdown
        assert "2024" in markdown

    def test_save_report(self, generator, sample_weekly_report):
        """Test saving report to file."""
        filepath = generator.save_report(sample_weekly_report)

        # Check file was created
        assert os.path.exists(filepath)
        assert filepath.endswith(".md")

        # Check file content
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        assert "주간 탄소정책 브리핑" in content

    def test_save_report_creates_directory(self):
        """Test that save_report creates output directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "new_subdir", "reports")
            generator = ReportGenerator(output_dir=output_dir)

            report = WeeklyReport(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 7),
                total_crawled=10,
                total_analyzed=5,
                new_chunks=3,
                new_experts=[],
                expert_sections={},
            )

            filepath = generator.save_report(report)

            assert os.path.exists(output_dir)
            assert os.path.exists(filepath)

    def test_save_report_filename_format(self, generator, sample_weekly_report):
        """Test that saved report has correct filename format."""
        filepath = generator.save_report(sample_weekly_report)

        filename = os.path.basename(filepath)
        # Filename should contain date information
        assert "2024" in filename
        assert "01" in filename
        assert filename.endswith(".md")

    def test_generate_cross_analysis(self, generator, sample_expert_section):
        """Test _generate_cross_analysis method."""
        sections = {ExpertRole.POLICY_EXPERT: sample_expert_section}
        cross_analysis = generator._generate_cross_analysis(sections)

        # Should return a string (may be empty if only one expert)
        assert isinstance(cross_analysis, str)

    def test_generate_cross_analysis_multiple_experts(self, generator):
        """Test _generate_cross_analysis with multiple experts."""
        sections = {
            ExpertRole.POLICY_EXPERT: ExpertSection(
                expert_role=ExpertRole.POLICY_EXPERT,
                expert_name="Dr. 김정책",
                summaries=["정책 요약"],
                key_findings=["정책 발견"],
                implications=["정책 시사점"],
                content_count=3,
            ),
            ExpertRole.MARKET_EXPERT: ExpertSection(
                expert_role=ExpertRole.MARKET_EXPERT,
                expert_name="Dr. 이시장",
                summaries=["시장 요약"],
                key_findings=["시장 발견"],
                implications=["시장 시사점"],
                content_count=4,
            ),
        }

        cross_analysis = generator._generate_cross_analysis(sections)

        assert isinstance(cross_analysis, str)

    def test_generate_chunk_summary(self, generator, sample_expert_section):
        """Test _generate_chunk_summary method."""
        sections = {ExpertRole.POLICY_EXPERT: sample_expert_section}
        summary = generator._generate_chunk_summary(sections)

        assert isinstance(summary, str)


class TestGenerateReport:
    """Test generate_report method with AnalysisResult integration."""

    @pytest.fixture
    def generator(self):
        """Create a ReportGenerator instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield ReportGenerator(output_dir=tmpdir)

    def test_generate_report_basic(self, generator):
        """Test generate_report with minimal inputs."""
        from react_agent.weekly_pipeline.analyzer import AnalysisResult

        analysis_results = [
            AnalysisResult(
                expert_role=ExpertRole.POLICY_EXPERT,
                content_id="content-1",
                summary="NDC 목표 상향 발표",
                key_findings=["40% 감축 목표"],
                implications=["기업 비용 증가"],
                confidence=0.9,
            ),
        ]

        report = generator.generate_report(
            analysis_results=analysis_results,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
        )

        assert isinstance(report, WeeklyReport)
        assert report.start_date == datetime(2024, 1, 1)
        assert report.end_date == datetime(2024, 1, 7)
        assert ExpertRole.POLICY_EXPERT in report.expert_sections

    def test_generate_report_with_stats(self, generator):
        """Test generate_report with crawling statistics."""
        from react_agent.weekly_pipeline.analyzer import AnalysisResult

        analysis_results = [
            AnalysisResult(
                expert_role=ExpertRole.POLICY_EXPERT,
                content_id="content-1",
                summary="정책 요약",
                key_findings=["발견 1"],
                implications=["시사점 1"],
                confidence=0.9,
            ),
        ]

        report = generator.generate_report(
            analysis_results=analysis_results,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            total_crawled=100,
            total_analyzed=50,
            new_chunks=25,
            new_experts=["신규전문가"],
        )

        assert report.total_crawled == 100
        assert report.total_analyzed == 50
        assert report.new_chunks == 25
        assert report.new_experts == ["신규전문가"]

    def test_generate_report_groups_by_expert(self, generator):
        """Test that generate_report groups analysis results by expert."""
        from react_agent.weekly_pipeline.analyzer import AnalysisResult

        analysis_results = [
            AnalysisResult(
                expert_role=ExpertRole.POLICY_EXPERT,
                content_id="content-1",
                summary="정책 요약 1",
                key_findings=["정책 발견 1"],
                implications=["정책 시사점 1"],
                confidence=0.9,
            ),
            AnalysisResult(
                expert_role=ExpertRole.POLICY_EXPERT,
                content_id="content-2",
                summary="정책 요약 2",
                key_findings=["정책 발견 2"],
                implications=["정책 시사점 2"],
                confidence=0.85,
            ),
            AnalysisResult(
                expert_role=ExpertRole.MARKET_EXPERT,
                content_id="content-3",
                summary="시장 요약",
                key_findings=["시장 발견"],
                implications=["시장 시사점"],
                confidence=0.8,
            ),
        ]

        report = generator.generate_report(
            analysis_results=analysis_results,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
        )

        # Check proper grouping
        assert len(report.expert_sections) == 2
        assert ExpertRole.POLICY_EXPERT in report.expert_sections
        assert ExpertRole.MARKET_EXPERT in report.expert_sections

        # Check policy expert section has both summaries
        policy_section = report.expert_sections[ExpertRole.POLICY_EXPERT]
        assert policy_section.content_count == 2
        assert len(policy_section.summaries) == 2

    def test_generate_report_empty_results(self, generator):
        """Test generate_report with empty analysis results."""
        report = generator.generate_report(
            analysis_results=[],
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
        )

        assert isinstance(report, WeeklyReport)
        assert len(report.expert_sections) == 0
