"""Rule-based classifier for expert assignment.

This module provides a keyword-matching based classifier that assigns
content to appropriate domain experts based on keyword relevance.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from react_agent.agents.expert_panel.config import (
    ExpertRole,
    get_expert_keywords,
)


@dataclass
class ClassificationResult:
    """Classification result containing expert assignment and metadata.

    Attributes:
        primary_expert: The primary expert assigned to handle the content.
        primary_score: The relevance score for the primary expert (0.0-1.0).
        secondary_expert: Optional secondary expert for complex content.
        secondary_score: The relevance score for the secondary expert.
        all_scores: Scores for all experts.
        matched_keywords: Keywords matched for each expert.
        confidence: Overall classification confidence (0.0-1.0).
        needs_llm_meeting: Whether LLM meeting is needed for complex routing.
        reason: Human-readable explanation of the classification.
    """

    primary_expert: ExpertRole
    primary_score: float
    secondary_expert: Optional[ExpertRole] = None
    secondary_score: float = 0.0
    all_scores: Dict[ExpertRole, float] = field(default_factory=dict)
    matched_keywords: Dict[ExpertRole, List[str]] = field(default_factory=dict)
    confidence: float = 0.0
    needs_llm_meeting: bool = False
    reason: str = ""


class RuleBasedClassifier:
    """Rule-based classifier using keyword matching for expert assignment.

    This classifier matches content against expert-specific keywords to
    determine the most appropriate expert for handling the content.

    Attributes:
        LOW_CONFIDENCE_THRESHOLD: Minimum confidence to avoid LLM meeting.
        MULTI_EXPERT_THRESHOLD: Number of relevant experts triggering LLM meeting.
        expert_keywords: Mapping of expert roles to their keywords.
    """

    LOW_CONFIDENCE_THRESHOLD = 0.3
    MULTI_EXPERT_THRESHOLD = 3

    def __init__(self) -> None:
        """Initialize the classifier with expert keywords."""
        self.expert_keywords: Dict[ExpertRole, List[str]] = get_expert_keywords()

    def classify(self, text: str) -> ClassificationResult:
        """Classify text and assign to appropriate expert.

        Args:
            text: The content text to classify.

        Returns:
            ClassificationResult containing expert assignment and metadata.
        """
        # Calculate scores for all experts
        all_scores: Dict[ExpertRole, float] = {}
        matched_keywords: Dict[ExpertRole, List[str]] = {}

        for role, keywords in self.expert_keywords.items():
            score, matched = self._calculate_score(text, keywords)
            all_scores[role] = score
            if matched:
                matched_keywords[role] = matched

        # Sort experts by score
        sorted_experts = sorted(
            all_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        # Get primary expert
        primary_expert, primary_score = sorted_experts[0]

        # Get secondary expert if applicable
        secondary_expert: Optional[ExpertRole] = None
        secondary_score = 0.0
        if len(sorted_experts) > 1 and sorted_experts[1][1] > 0:
            secondary_expert, secondary_score = sorted_experts[1]

        # Calculate confidence
        total_keywords = sum(len(kw) for kw in matched_keywords.values())
        max_possible = len(text.split())  # Rough estimate
        if max_possible > 0 and primary_score > 0:
            # Confidence based on primary score relative to others
            confidence = primary_score / max(1.0, sum(all_scores.values()))
            # Boost confidence if many keywords matched
            if total_keywords >= 3:
                confidence = min(1.0, confidence * 1.2)
        else:
            confidence = 0.0

        # Determine if LLM meeting is needed
        needs_llm = self._needs_llm_meeting(all_scores, confidence, matched_keywords)

        # Generate reason
        reason = self._generate_reason(primary_expert, matched_keywords.get(primary_expert, []))

        return ClassificationResult(
            primary_expert=primary_expert,
            primary_score=primary_score,
            secondary_expert=secondary_expert,
            secondary_score=secondary_score,
            all_scores=all_scores,
            matched_keywords=matched_keywords,
            confidence=confidence,
            needs_llm_meeting=needs_llm,
            reason=reason,
        )

    def _calculate_score(
        self,
        text: str,
        keywords: List[str],
    ) -> Tuple[float, List[str]]:
        """Calculate relevance score based on keyword matching.

        Args:
            text: The text to analyze.
            keywords: List of keywords to match against.

        Returns:
            Tuple of (score, list of matched keywords).
        """
        text_lower = text.lower()
        matched: List[str] = []

        for keyword in keywords:
            if keyword.lower() in text_lower:
                matched.append(keyword)

        # Score is the proportion of keywords matched
        if len(keywords) == 0:
            return 0.0, []

        score = len(matched) / len(keywords)
        return score, matched

    def _needs_llm_meeting(
        self,
        scores: Dict[ExpertRole, float],
        confidence: float,
        matched_keywords: Dict[ExpertRole, List[str]],
    ) -> bool:
        """Determine if LLM meeting is needed for complex routing.

        LLM meeting is triggered when:
        - Confidence is below the threshold
        - Multiple experts (>= MULTI_EXPERT_THRESHOLD) have relevant keywords

        Args:
            scores: Scores for all experts.
            confidence: Overall classification confidence.
            matched_keywords: Keywords matched for each expert.

        Returns:
            True if LLM meeting is needed.
        """
        # Low confidence check
        if confidence < self.LOW_CONFIDENCE_THRESHOLD:
            return True

        # Multi-expert relevance check
        relevant_expert_count = sum(
            1 for role, keywords in matched_keywords.items()
            if len(keywords) > 0
        )
        if relevant_expert_count >= self.MULTI_EXPERT_THRESHOLD:
            return True

        return False

    def _generate_reason(
        self,
        expert: ExpertRole,
        keywords: List[str],
    ) -> str:
        """Generate human-readable reason for classification.

        Args:
            expert: The assigned expert role.
            keywords: Keywords that matched for this expert.

        Returns:
            Human-readable explanation string.
        """
        expert_name_map = {
            ExpertRole.POLICY_EXPERT: "정책 전문가",
            ExpertRole.CARBON_CREDIT_EXPERT: "탄소배출권 전문가",
            ExpertRole.MARKET_EXPERT: "시장 전문가",
            ExpertRole.TECHNOLOGY_EXPERT: "기술 전문가",
            ExpertRole.MRV_EXPERT: "MRV 전문가",
        }

        expert_name = expert_name_map.get(expert, str(expert))

        if keywords:
            keyword_str = ", ".join(f"'{kw}'" for kw in keywords[:5])
            if len(keywords) > 5:
                keyword_str += f" 외 {len(keywords) - 5}개"
            return f"키워드 {keyword_str} 매칭으로 {expert_name} 선정"
        else:
            return f"{expert_name}에게 기본 할당"

    def classify_batch(self, texts: List[str]) -> List[ClassificationResult]:
        """Classify multiple texts in batch.

        Args:
            texts: List of content texts to classify.

        Returns:
            List of ClassificationResult for each text.
        """
        return [self.classify(text) for text in texts]
