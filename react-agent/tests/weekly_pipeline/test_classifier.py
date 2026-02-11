"""Tests for rule-based classifier module."""

import pytest

from react_agent.agents.expert_panel.config import ExpertRole
from react_agent.weekly_pipeline.classifier import (
    ClassificationResult,
    RuleBasedClassifier,
)


class TestClassificationResult:
    """Test ClassificationResult dataclass."""

    def test_create_classification_result(self):
        """Test creating ClassificationResult with required fields."""
        result = ClassificationResult(
            primary_expert=ExpertRole.POLICY_EXPERT,
            primary_score=0.8,
        )

        assert result.primary_expert == ExpertRole.POLICY_EXPERT
        assert result.primary_score == 0.8
        assert result.secondary_expert is None
        assert result.secondary_score == 0.0
        assert result.all_scores == {}
        assert result.matched_keywords == {}
        assert result.confidence == 0.0
        assert result.needs_llm_meeting is False
        assert result.reason == ""

    def test_create_classification_result_with_all_fields(self):
        """Test creating ClassificationResult with all fields."""
        all_scores = {
            ExpertRole.POLICY_EXPERT: 0.8,
            ExpertRole.MARKET_EXPERT: 0.5,
        }
        matched_keywords = {
            ExpertRole.POLICY_EXPERT: ["NDC", "파리협정"],
            ExpertRole.MARKET_EXPERT: ["가격"],
        }

        result = ClassificationResult(
            primary_expert=ExpertRole.POLICY_EXPERT,
            primary_score=0.8,
            secondary_expert=ExpertRole.MARKET_EXPERT,
            secondary_score=0.5,
            all_scores=all_scores,
            matched_keywords=matched_keywords,
            confidence=0.75,
            needs_llm_meeting=False,
            reason="키워드 'NDC', '파리협정' 매칭으로 정책 전문가 선정",
        )

        assert result.primary_expert == ExpertRole.POLICY_EXPERT
        assert result.primary_score == 0.8
        assert result.secondary_expert == ExpertRole.MARKET_EXPERT
        assert result.secondary_score == 0.5
        assert result.all_scores == all_scores
        assert result.matched_keywords == matched_keywords
        assert result.confidence == 0.75
        assert result.needs_llm_meeting is False
        assert "NDC" in result.reason


class TestRuleBasedClassifier:
    """Test RuleBasedClassifier class."""

    @pytest.fixture
    def classifier(self):
        """Create a RuleBasedClassifier instance."""
        return RuleBasedClassifier()

    def test_init_loads_expert_keywords(self, classifier):
        """Test that __init__ loads expert keywords."""
        assert classifier.expert_keywords is not None
        assert len(classifier.expert_keywords) == 5
        assert ExpertRole.POLICY_EXPERT in classifier.expert_keywords
        assert ExpertRole.MARKET_EXPERT in classifier.expert_keywords
        assert ExpertRole.TECHNOLOGY_EXPERT in classifier.expert_keywords
        assert ExpertRole.CARBON_CREDIT_EXPERT in classifier.expert_keywords
        assert ExpertRole.MRV_EXPERT in classifier.expert_keywords

    def test_classify_policy_content(self, classifier):
        """Test classification of policy-related content."""
        text = "파리협정 NDC 목표에 따른 탄소중립 정책 이행 현황"
        result = classifier.classify(text)

        assert isinstance(result, ClassificationResult)
        assert result.primary_expert == ExpertRole.POLICY_EXPERT
        assert result.primary_score > 0
        assert ExpertRole.POLICY_EXPERT in result.matched_keywords
        assert any(kw in ["파리협정", "NDC"] for kw in result.matched_keywords[ExpertRole.POLICY_EXPERT])

    def test_classify_market_content(self, classifier):
        """Test classification of market-related content."""
        text = "EU ETS 가격 동향 분석 및 거래량 전망"
        result = classifier.classify(text)

        assert isinstance(result, ClassificationResult)
        assert result.primary_expert == ExpertRole.MARKET_EXPERT
        assert result.primary_score > 0
        assert ExpertRole.MARKET_EXPERT in result.matched_keywords
        assert any(kw in ["EU ETS", "가격", "거래"] for kw in result.matched_keywords[ExpertRole.MARKET_EXPERT])

    def test_classify_technology_content(self, classifier):
        """Test classification of technology-related content."""
        text = "CCUS 탄소포집 기술 개발 현황 및 상용화 전망"
        result = classifier.classify(text)

        assert isinstance(result, ClassificationResult)
        assert result.primary_expert == ExpertRole.TECHNOLOGY_EXPERT
        assert result.primary_score > 0
        assert ExpertRole.TECHNOLOGY_EXPERT in result.matched_keywords
        assert any(kw in ["CCUS", "탄소포집", "기술"] for kw in result.matched_keywords[ExpertRole.TECHNOLOGY_EXPERT])

    def test_classify_carbon_credit_content(self, classifier):
        """Test classification of carbon credit-related content."""
        text = "KAU 배출권 할당량 조정 및 KCU 상쇄 크레딧 활용"
        result = classifier.classify(text)

        assert isinstance(result, ClassificationResult)
        assert result.primary_expert == ExpertRole.CARBON_CREDIT_EXPERT
        assert result.primary_score > 0
        assert ExpertRole.CARBON_CREDIT_EXPERT in result.matched_keywords

    def test_classify_mrv_content(self, classifier):
        """Test classification of MRV-related content."""
        text = "Scope 1, 2, 3 배출량 산정 및 GHG Protocol 기반 검증"
        result = classifier.classify(text)

        assert isinstance(result, ClassificationResult)
        assert result.primary_expert == ExpertRole.MRV_EXPERT
        assert result.primary_score > 0
        assert ExpertRole.MRV_EXPERT in result.matched_keywords

    def test_classify_with_secondary(self, classifier):
        """Test classification of complex content with multiple expert relevance."""
        # Content that relates to both policy and market
        text = "파리협정 NDC 목표와 EU ETS 가격 연계 분석"
        result = classifier.classify(text)

        assert isinstance(result, ClassificationResult)
        assert result.primary_expert is not None
        assert result.primary_score > 0
        # Should have secondary expert due to multiple domain relevance
        assert result.secondary_expert is not None
        assert result.secondary_score > 0
        assert result.primary_expert != result.secondary_expert

    def test_classify_generates_reason(self, classifier):
        """Test that classification generates a reason."""
        text = "파리협정 NDC 정책 분석"
        result = classifier.classify(text)

        assert result.reason != ""
        assert len(result.reason) > 0

    def test_classify_sets_confidence(self, classifier):
        """Test that classification sets confidence score."""
        text = "파리협정 NDC 탄소중립 정책 이행 UNFCCC COP 협약"
        result = classifier.classify(text)

        assert result.confidence > 0
        assert result.confidence <= 1.0

    def test_needs_llm_meeting_low_confidence(self, classifier):
        """Test needs_llm_meeting is True when confidence is low."""
        # Ambiguous or irrelevant content
        text = "오늘 날씨가 좋습니다"
        result = classifier.classify(text)

        # Low confidence should trigger LLM meeting
        if result.confidence < classifier.LOW_CONFIDENCE_THRESHOLD:
            assert result.needs_llm_meeting is True

    def test_needs_llm_meeting_multi_expert(self, classifier):
        """Test needs_llm_meeting is True when multiple experts are relevant."""
        # Content relevant to multiple experts
        text = """
        파리협정 NDC 정책에 따라 EU ETS 가격이 상승하고 있습니다.
        CCUS 탄소포집 기술 투자가 증가하며, Scope 1,2,3 배출량 산정이 중요해졌습니다.
        """
        result = classifier.classify(text)

        # Count how many experts have significant scores
        relevant_experts = sum(1 for score in result.all_scores.values() if score > 0)

        if relevant_experts >= classifier.MULTI_EXPERT_THRESHOLD:
            assert result.needs_llm_meeting is True

    def test_calculate_score(self, classifier):
        """Test _calculate_score method."""
        text = "파리협정 NDC 탄소중립"
        keywords = ["파리협정", "NDC", "탄소중립", "정책"]

        score, matched = classifier._calculate_score(text, keywords)

        assert score > 0
        assert isinstance(matched, list)
        assert "파리협정" in matched
        assert "NDC" in matched
        assert "탄소중립" in matched

    def test_calculate_score_no_match(self, classifier):
        """Test _calculate_score with no matching keywords."""
        text = "오늘 날씨가 좋습니다"
        keywords = ["파리협정", "NDC", "탄소중립"]

        score, matched = classifier._calculate_score(text, keywords)

        assert score == 0.0
        assert matched == []

    def test_classify_batch(self, classifier):
        """Test batch classification of multiple texts."""
        texts = [
            "파리협정 NDC 정책 분석",
            "EU ETS 가격 동향",
            "CCUS 탄소포집 기술",
        ]

        results = classifier.classify_batch(texts)

        assert len(results) == 3
        assert all(isinstance(r, ClassificationResult) for r in results)
        assert results[0].primary_expert == ExpertRole.POLICY_EXPERT
        assert results[1].primary_expert == ExpertRole.MARKET_EXPERT
        assert results[2].primary_expert == ExpertRole.TECHNOLOGY_EXPERT

    def test_classify_batch_empty_list(self, classifier):
        """Test batch classification with empty list."""
        results = classifier.classify_batch([])

        assert results == []

    def test_thresholds(self, classifier):
        """Test that thresholds are set correctly."""
        assert classifier.LOW_CONFIDENCE_THRESHOLD == 0.3
        assert classifier.MULTI_EXPERT_THRESHOLD == 3
