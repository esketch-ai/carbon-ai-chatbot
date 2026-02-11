"""Expert analyzer module for content analysis.

This module provides functionality for expert-based content analysis,
extracting summaries, key findings, and implications from preprocessed content.
"""

import asyncio
import re
from dataclasses import dataclass, field
from typing import List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from react_agent.agents.expert_panel.config import EXPERT_REGISTRY, ExpertRole

from .classifier import ClassificationResult
from .preprocessor import PreprocessedContent


@dataclass
class AnalysisResult:
    """Data class representing analysis result from an expert.

    Attributes:
        expert_role: The expert role that performed the analysis.
        content_id: Unique identifier (hash) of the analyzed content.
        summary: Brief summary of the content.
        key_findings: List of key findings extracted from the content.
        implications: List of implications derived from the analysis.
        confidence: Confidence score for the analysis (0.0-1.0).
        raw_response: Raw LLM response text.
        error: Error message if analysis failed.
    """

    expert_role: ExpertRole
    content_id: str
    summary: str
    key_findings: List[str]
    implications: List[str]
    confidence: float
    raw_response: str = ""
    error: Optional[str] = None


ANALYSIS_PROMPT = """당신은 {expert_name}입니다.

{expert_persona}

다음 콘텐츠를 분석하여 요약, 주요 발견, 시사점을 추출해주세요.

## 분석 대상 콘텐츠

제목: {title}
출처: {source}
내용:
{content}

## 응답 형식

반드시 다음 형식으로 응답해주세요:

## 요약
(2-3문장으로 핵심 내용 요약)

## 주요 발견
- (첫 번째 주요 발견)
- (두 번째 주요 발견)
- (세 번째 주요 발견)

## 시사점
- (첫 번째 시사점)
- (두 번째 시사점)

분석 시 당신의 전문 분야({expertise_areas})에 초점을 맞추어 분석해주세요.
"""


class ExpertAnalyzer:
    """Expert analyzer for parallel content analysis.

    Uses LLM to analyze content from the perspective of domain experts,
    extracting summaries, key findings, and implications.

    Attributes:
        model_name: Name of the LLM model to use.
        llm: LangChain ChatAnthropic instance.
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514") -> None:
        """Initialize the ExpertAnalyzer.

        Args:
            model: Name of the Anthropic model to use for analysis.
        """
        self.model_name = model
        self.llm = ChatAnthropic(model=model, temperature=0.3)

    async def analyze(
        self,
        content: PreprocessedContent,
        expert_role: ExpertRole,
    ) -> AnalysisResult:
        """Analyze content from the perspective of a specific expert.

        Args:
            content: Preprocessed content to analyze.
            expert_role: The expert role to use for analysis.

        Returns:
            AnalysisResult containing the analysis output.
        """
        try:
            # Get expert configuration
            expert_config = EXPERT_REGISTRY[expert_role]

            # Build the prompt
            prompt = ANALYSIS_PROMPT.format(
                expert_name=expert_config.name,
                expert_persona=expert_config.persona,
                title=content.clean_title,
                source=content.original.source,
                content=content.clean_content,
                expertise_areas=", ".join(expert_config.expertise),
            )

            # Create messages
            messages = [
                SystemMessage(
                    content="당신은 탄소시장 및 기후변화 분야의 전문가입니다. 주어진 콘텐츠를 분석하여 요약, 주요 발견, 시사점을 추출합니다."
                ),
                HumanMessage(content=prompt),
            ]

            # Call LLM
            response = await self.llm.ainvoke(messages)
            response_text = response.content

            # Parse the response
            return self._parse_analysis(
                response=response_text,
                expert_role=expert_role,
                content=content,
            )

        except Exception as e:
            # Return error result
            return AnalysisResult(
                expert_role=expert_role,
                content_id=content.content_hash,
                summary="",
                key_findings=[],
                implications=[],
                confidence=0.0,
                raw_response="",
                error=f"분석 오류: {str(e)}",
            )

    async def analyze_batch(
        self,
        contents: List[PreprocessedContent],
        classifications: List[ClassificationResult],
    ) -> List[AnalysisResult]:
        """Analyze multiple contents in parallel.

        Each content is analyzed by the expert assigned in its classification.

        Args:
            contents: List of preprocessed contents to analyze.
            classifications: List of classification results with expert assignments.

        Returns:
            List of AnalysisResult for each content.
        """
        if not contents or not classifications:
            return []

        # Create analysis tasks
        tasks = []
        for content, classification in zip(contents, classifications):
            task = self.analyze(
                content=content,
                expert_role=classification.primary_expert,
            )
            tasks.append(task)

        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(
                    AnalysisResult(
                        expert_role=classifications[i].primary_expert,
                        content_id=contents[i].content_hash,
                        summary="",
                        key_findings=[],
                        implications=[],
                        confidence=0.0,
                        error=f"분석 오류: {str(result)}",
                    )
                )
            else:
                final_results.append(result)

        return final_results

    def _parse_analysis(
        self,
        response: str,
        expert_role: ExpertRole,
        content: PreprocessedContent,
    ) -> AnalysisResult:
        """Parse LLM response into AnalysisResult.

        Args:
            response: Raw LLM response text.
            expert_role: The expert role that performed the analysis.
            content: The original preprocessed content.

        Returns:
            Parsed AnalysisResult.
        """
        if not response or not response.strip():
            return AnalysisResult(
                expert_role=expert_role,
                content_id=content.content_hash,
                summary="",
                key_findings=[],
                implications=[],
                confidence=0.0,
                raw_response=response,
            )

        # Extract summary
        summary = self._extract_section(response, "요약")

        # Extract key findings
        key_findings = self._extract_list_section(response, "주요 발견")

        # Extract implications
        implications = self._extract_list_section(response, "시사점")

        # Calculate confidence based on completeness
        confidence = self._calculate_confidence(summary, key_findings, implications)

        return AnalysisResult(
            expert_role=expert_role,
            content_id=content.content_hash,
            summary=summary,
            key_findings=key_findings,
            implications=implications,
            confidence=confidence,
            raw_response=response,
        )

    def _extract_section(self, text: str, section_name: str) -> str:
        """Extract a text section from the response.

        Args:
            text: Full response text.
            section_name: Name of the section to extract.

        Returns:
            Extracted section text or empty string.
        """
        # Pattern to match section header and content until next section or end
        pattern = rf"##\s*{section_name}\s*\n(.*?)(?=\n##|$)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

        if match:
            return match.group(1).strip()

        return ""

    def _extract_list_section(self, text: str, section_name: str) -> List[str]:
        """Extract a list section from the response.

        Args:
            text: Full response text.
            section_name: Name of the section to extract.

        Returns:
            List of items from the section.
        """
        section_text = self._extract_section(text, section_name)

        if not section_text:
            return []

        # Extract list items (lines starting with - or *)
        items = []
        for line in section_text.split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("*"):
                item = line.lstrip("-*").strip()
                if item:
                    items.append(item)

        return items

    def _calculate_confidence(
        self,
        summary: str,
        key_findings: List[str],
        implications: List[str],
    ) -> float:
        """Calculate confidence score based on analysis completeness.

        Args:
            summary: Extracted summary text.
            key_findings: List of key findings.
            implications: List of implications.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        score = 0.0

        # Summary contributes 40%
        if summary:
            score += 0.4
            # Bonus for longer summaries
            if len(summary) > 50:
                score += 0.1

        # Key findings contribute 30%
        if key_findings:
            # Base score for having findings
            score += 0.15
            # Bonus for multiple findings (up to 0.15)
            findings_bonus = min(len(key_findings) / 3, 1.0) * 0.15
            score += findings_bonus

        # Implications contribute 20%
        if implications:
            # Base score for having implications
            score += 0.1
            # Bonus for multiple implications (up to 0.1)
            implications_bonus = min(len(implications) / 2, 1.0) * 0.1
            score += implications_bonus

        return min(score, 1.0)
