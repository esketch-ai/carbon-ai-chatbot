"""Tests for expert analyzer module.

Tests run without LLM calls - focuses on structure and parsing logic.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from react_agent.agents.expert_panel.config import ExpertRole
from react_agent.weekly_pipeline.analyzer import (
    ANALYSIS_PROMPT,
    AnalysisResult,
    ExpertAnalyzer,
)
from react_agent.weekly_pipeline.classifier import ClassificationResult
from react_agent.weekly_pipeline.crawler import CrawledContent
from react_agent.weekly_pipeline.preprocessor import PreprocessedContent


class TestAnalysisResult:
    """Test AnalysisResult dataclass."""

    def test_analysis_result_structure(self):
        """Test creating AnalysisResult with required fields."""
        result = AnalysisResult(
            expert_role=ExpertRole.POLICY_EXPERT,
            content_id="test-content-123",
            summary="파리협정에 따른 NDC 목표 상향 조정 발표",
            key_findings=["NDC 목표 40% 상향", "2030년까지 달성 예정"],
            implications=["기업 배출권 비용 증가 예상", "신재생에너지 투자 확대 필요"],
            confidence=0.85,
        )

        assert result.expert_role == ExpertRole.POLICY_EXPERT
        assert result.content_id == "test-content-123"
        assert result.summary == "파리협정에 따른 NDC 목표 상향 조정 발표"
        assert len(result.key_findings) == 2
        assert len(result.implications) == 2
        assert result.confidence == 0.85
        assert result.raw_response == ""
        assert result.error is None

    def test_analysis_result_with_error(self):
        """Test creating AnalysisResult with error."""
        result = AnalysisResult(
            expert_role=ExpertRole.MARKET_EXPERT,
            content_id="test-content-456",
            summary="",
            key_findings=[],
            implications=[],
            confidence=0.0,
            error="LLM 호출 실패: API 오류",
        )

        assert result.expert_role == ExpertRole.MARKET_EXPERT
        assert result.content_id == "test-content-456"
        assert result.summary == ""
        assert result.key_findings == []
        assert result.implications == []
        assert result.confidence == 0.0
        assert result.error == "LLM 호출 실패: API 오류"

    def test_analysis_result_with_raw_response(self):
        """Test creating AnalysisResult with raw_response."""
        raw_response = """## 요약
파리협정 NDC 목표 상향

## 주요 발견
- NDC 40% 상향
- 2030년까지 달성

## 시사점
- 기업 비용 증가
"""
        result = AnalysisResult(
            expert_role=ExpertRole.POLICY_EXPERT,
            content_id="test-123",
            summary="파리협정 NDC 목표 상향",
            key_findings=["NDC 40% 상향", "2030년까지 달성"],
            implications=["기업 비용 증가"],
            confidence=0.9,
            raw_response=raw_response,
        )

        assert result.raw_response == raw_response
        assert result.error is None


class TestExpertAnalyzer:
    """Test ExpertAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create an ExpertAnalyzer instance."""
        return ExpertAnalyzer()

    @pytest.fixture
    def sample_crawled_content(self):
        """Create a sample CrawledContent for testing."""
        return CrawledContent(
            title="2024년 NDC 목표 상향 조정 발표",
            url="https://example.com/ndc-2024",
            content="정부가 파리협정에 따른 NDC 목표를 40% 상향 조정한다고 발표했습니다.",
            source="환경부",
            published_date=datetime.now(),
        )

    @pytest.fixture
    def sample_preprocessed_content(self, sample_crawled_content):
        """Create a sample PreprocessedContent for testing."""
        return PreprocessedContent(
            original=sample_crawled_content,
            clean_content="정부가 파리협정에 따른 NDC 목표를 40% 상향 조정한다고 발표했습니다.",
            clean_title="2024년 NDC 목표 상향 조정 발표",
            language="ko",
            word_count=15,
            content_hash="abc123def456",
            extracted_keywords=["NDC", "파리협정", "탄소중립"],
        )

    @pytest.fixture
    def sample_classification_result(self):
        """Create a sample ClassificationResult for testing."""
        return ClassificationResult(
            primary_expert=ExpertRole.POLICY_EXPERT,
            primary_score=0.8,
            confidence=0.85,
            reason="키워드 'NDC', '파리협정' 매칭으로 정책 전문가 선정",
        )

    def test_analyzer_init(self, analyzer):
        """Test ExpertAnalyzer initialization."""
        assert analyzer is not None
        assert analyzer.model_name == "claude-sonnet-4-20250514"
        assert analyzer.llm is not None

    def test_analyzer_init_custom_model(self):
        """Test ExpertAnalyzer initialization with custom model."""
        analyzer = ExpertAnalyzer(model="claude-3-opus-20240229")
        assert analyzer.model_name == "claude-3-opus-20240229"

    def test_analysis_prompt_exists(self):
        """Test that ANALYSIS_PROMPT is defined and has required placeholders."""
        assert ANALYSIS_PROMPT is not None
        assert isinstance(ANALYSIS_PROMPT, str)
        assert "{title}" in ANALYSIS_PROMPT
        assert "{source}" in ANALYSIS_PROMPT
        assert "{content}" in ANALYSIS_PROMPT

    def test_parse_analysis_valid_response(
        self, analyzer, sample_preprocessed_content
    ):
        """Test _parse_analysis with valid response format."""
        response = """## 요약
정부가 파리협정 NDC 목표를 40% 상향 조정하는 계획을 발표했습니다.

## 주요 발견
- NDC 목표 40% 상향 조정
- 2030년까지 달성 목표
- 신재생에너지 비중 확대

## 시사점
- 기업의 탄소배출권 비용 증가 예상
- 에너지 전환 투자 필요성 증대
"""
        result = analyzer._parse_analysis(
            response=response,
            expert_role=ExpertRole.POLICY_EXPERT,
            content=sample_preprocessed_content,
        )

        assert isinstance(result, AnalysisResult)
        assert result.expert_role == ExpertRole.POLICY_EXPERT
        assert result.content_id == sample_preprocessed_content.content_hash
        assert "NDC" in result.summary or "파리협정" in result.summary
        assert len(result.key_findings) == 3
        assert len(result.implications) == 2
        assert result.confidence > 0
        assert result.raw_response == response
        assert result.error is None

    def test_parse_analysis_minimal_response(
        self, analyzer, sample_preprocessed_content
    ):
        """Test _parse_analysis with minimal valid response."""
        response = """## 요약
NDC 목표 상향

## 주요 발견
- 목표 상향

## 시사점
- 비용 증가
"""
        result = analyzer._parse_analysis(
            response=response,
            expert_role=ExpertRole.MARKET_EXPERT,
            content=sample_preprocessed_content,
        )

        assert isinstance(result, AnalysisResult)
        assert result.expert_role == ExpertRole.MARKET_EXPERT
        assert len(result.key_findings) >= 1
        assert len(result.implications) >= 1

    def test_parse_analysis_empty_response(
        self, analyzer, sample_preprocessed_content
    ):
        """Test _parse_analysis with empty response."""
        response = ""
        result = analyzer._parse_analysis(
            response=response,
            expert_role=ExpertRole.POLICY_EXPERT,
            content=sample_preprocessed_content,
        )

        assert isinstance(result, AnalysisResult)
        assert result.summary == ""
        assert result.key_findings == []
        assert result.implications == []
        assert result.confidence == 0.0

    def test_parse_analysis_malformed_response(
        self, analyzer, sample_preprocessed_content
    ):
        """Test _parse_analysis with malformed response."""
        response = "이것은 포맷에 맞지 않는 응답입니다."
        result = analyzer._parse_analysis(
            response=response,
            expert_role=ExpertRole.TECHNOLOGY_EXPERT,
            content=sample_preprocessed_content,
        )

        assert isinstance(result, AnalysisResult)
        # Should handle gracefully - possibly using full response as summary
        assert result.error is None or result.summary != ""

    @pytest.mark.asyncio
    async def test_analyze_mocked(
        self, analyzer, sample_preprocessed_content
    ):
        """Test analyze method with mocked LLM."""
        mock_response = MagicMock()
        mock_response.content = """## 요약
정책 분석 결과입니다.

## 주요 발견
- 발견 1
- 발견 2

## 시사점
- 시사점 1
"""
        with patch(
            "react_agent.weekly_pipeline.analyzer.ChatAnthropic"
        ) as mock_chat:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(return_value=mock_response)
            mock_chat.return_value = mock_instance

            # Create a new analyzer with the mocked LLM
            test_analyzer = ExpertAnalyzer()
            result = await test_analyzer.analyze(
                content=sample_preprocessed_content,
                expert_role=ExpertRole.POLICY_EXPERT,
            )

            assert isinstance(result, AnalysisResult)
            assert result.expert_role == ExpertRole.POLICY_EXPERT
            mock_instance.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_handles_llm_error(
        self, analyzer, sample_preprocessed_content
    ):
        """Test analyze method handles LLM errors gracefully."""
        with patch(
            "react_agent.weekly_pipeline.analyzer.ChatAnthropic"
        ) as mock_chat:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(side_effect=Exception("API 오류"))
            mock_chat.return_value = mock_instance

            # Create a new analyzer with the mocked LLM
            test_analyzer = ExpertAnalyzer()
            result = await test_analyzer.analyze(
                content=sample_preprocessed_content,
                expert_role=ExpertRole.POLICY_EXPERT,
            )

            assert isinstance(result, AnalysisResult)
            assert result.error is not None
            assert "API 오류" in result.error or "오류" in result.error

    @pytest.mark.asyncio
    async def test_analyze_batch_mocked(
        self,
        analyzer,
        sample_preprocessed_content,
        sample_classification_result,
    ):
        """Test analyze_batch method with mocked LLM."""
        mock_response = MagicMock()
        mock_response.content = """## 요약
배치 분석 결과입니다.

## 주요 발견
- 배치 발견 1

## 시사점
- 배치 시사점 1
"""
        with patch(
            "react_agent.weekly_pipeline.analyzer.ChatAnthropic"
        ) as mock_chat:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(return_value=mock_response)
            mock_chat.return_value = mock_instance

            # Create a new analyzer with the mocked LLM
            test_analyzer = ExpertAnalyzer()
            contents = [sample_preprocessed_content]
            classifications = [sample_classification_result]

            results = await test_analyzer.analyze_batch(
                contents=contents,
                classifications=classifications,
            )

            assert len(results) == 1
            assert all(isinstance(r, AnalysisResult) for r in results)
            assert results[0].expert_role == ExpertRole.POLICY_EXPERT

    @pytest.mark.asyncio
    async def test_analyze_batch_empty_lists(self, analyzer):
        """Test analyze_batch with empty lists."""
        results = await analyzer.analyze_batch(
            contents=[],
            classifications=[],
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_analyze_batch_parallel_execution(
        self,
        analyzer,
        sample_preprocessed_content,
    ):
        """Test that analyze_batch executes analyses in parallel."""
        mock_response = MagicMock()
        mock_response.content = """## 요약
분석 결과

## 주요 발견
- 발견

## 시사점
- 시사점
"""
        # Create multiple contents and classifications
        contents = [sample_preprocessed_content] * 3
        classifications = [
            ClassificationResult(
                primary_expert=ExpertRole.POLICY_EXPERT,
                primary_score=0.8,
            ),
            ClassificationResult(
                primary_expert=ExpertRole.MARKET_EXPERT,
                primary_score=0.7,
            ),
            ClassificationResult(
                primary_expert=ExpertRole.TECHNOLOGY_EXPERT,
                primary_score=0.9,
            ),
        ]

        with patch(
            "react_agent.weekly_pipeline.analyzer.ChatAnthropic"
        ) as mock_chat:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(return_value=mock_response)
            mock_chat.return_value = mock_instance

            # Create a new analyzer with the mocked LLM
            test_analyzer = ExpertAnalyzer()
            results = await test_analyzer.analyze_batch(
                contents=contents,
                classifications=classifications,
            )

            assert len(results) == 3
            # Check each result matches its classification
            assert results[0].expert_role == ExpertRole.POLICY_EXPERT
            assert results[1].expert_role == ExpertRole.MARKET_EXPERT
            assert results[2].expert_role == ExpertRole.TECHNOLOGY_EXPERT


class TestAnalysisPrompt:
    """Test ANALYSIS_PROMPT template."""

    def test_prompt_has_required_sections(self):
        """Test that prompt template has required instruction sections."""
        assert "요약" in ANALYSIS_PROMPT or "summary" in ANALYSIS_PROMPT.lower()
        assert "발견" in ANALYSIS_PROMPT or "finding" in ANALYSIS_PROMPT.lower()
        assert "시사점" in ANALYSIS_PROMPT or "implication" in ANALYSIS_PROMPT.lower()

    def test_prompt_can_be_formatted(self):
        """Test that prompt can be formatted with required fields."""
        formatted = ANALYSIS_PROMPT.format(
            title="테스트 제목",
            source="테스트 출처",
            content="테스트 내용",
            expert_name="테스트 전문가",
            expert_persona="전문가 페르소나",
            expertise_areas="전문 분야",
        )

        assert "테스트 제목" in formatted
        assert "테스트 출처" in formatted
        assert "테스트 내용" in formatted
