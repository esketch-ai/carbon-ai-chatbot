"""Weekly pipeline orchestration module.

This module provides the main pipeline that orchestrates the entire
weekly analysis workflow, including crawling, preprocessing, classification,
expert meeting, analysis, and report generation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from .analyzer import AnalysisResult, ExpertAnalyzer
from .classifier import ClassificationResult, RuleBasedClassifier
from .crawler import CrawledContent
from .expert_generator import register_dynamic_expert
from .expert_meeting import ExpertMeeting, MeetingResult
from .preprocessor import PreprocessedContent, Preprocessor
from .report_generator import ReportGenerator
from .sources import get_default_registry
from .knowledge_saver import KnowledgeSaver


@dataclass
class PipelineResult:
    """Result from a complete pipeline run.

    Attributes:
        start_time: When the pipeline started.
        end_time: When the pipeline finished.
        crawled_count: Number of contents crawled.
        preprocessed_count: Number of contents preprocessed.
        analyzed_count: Number of contents analyzed.
        chunks_created: Number of knowledge base chunks created.
        new_experts: List of newly registered dynamic expert names.
        report_path: Path to the generated report file.
        errors: List of error messages encountered during the run.
    """

    start_time: datetime
    end_time: datetime
    crawled_count: int
    preprocessed_count: int
    analyzed_count: int
    chunks_created: int
    new_experts: List[str]
    report_path: str
    errors: List[str] = field(default_factory=list)


class WeeklyPipeline:
    """Orchestrator for the weekly analysis pipeline.

    Coordinates all stages of the weekly analysis workflow:
    1. Crawl - Collect content from configured sources
    2. Preprocess - Clean and normalize content
    3. Classify - Assign content to experts using rules
    4. Meeting - Run LLM meeting for complex assignments
    5. Analyze - Have experts analyze assigned content
    6. Report - Generate weekly briefing report

    Attributes:
        days_back: Number of days to look back when crawling.
        enable_llm_meeting: Whether to enable LLM-based expert meetings.
    """

    def __init__(
        self,
        days_back: int = 7,
        enable_llm_meeting: bool = True,
    ) -> None:
        """Initialize the WeeklyPipeline.

        Args:
            days_back: Number of days to look back when crawling (default: 7).
            enable_llm_meeting: Whether to enable LLM-based expert meetings
                               for complex content routing (default: True).
        """
        self.days_back = days_back
        self.enable_llm_meeting = enable_llm_meeting

        # Initialize components
        self._registry = get_default_registry()
        self._preprocessor = Preprocessor()
        self._classifier = RuleBasedClassifier()
        self._expert_meeting: Optional[ExpertMeeting] = None
        self._analyzer: Optional[ExpertAnalyzer] = None
        self._report_generator = ReportGenerator()
        self._knowledge_saver = KnowledgeSaver()

        # Pipeline state
        self._errors: List[str] = []
        self._new_experts: List[str] = []
        self._chunks_created: int = 0

    async def run(self) -> PipelineResult:
        """Execute the complete weekly pipeline.

        Runs all stages in sequence: crawl, preprocess, classify,
        meeting (optional), analyze, and report.

        Returns:
            PipelineResult containing statistics and results from the run.
        """
        start_time = datetime.now()
        self._errors = []
        self._new_experts = []
        self._chunks_created = 0

        # Stage 1: Crawl
        crawled = await self._stage_crawl()

        # Stage 2: Preprocess
        preprocessed = self._stage_preprocess(crawled)

        # Stage 3: Classify
        classified = self._stage_classify(preprocessed)

        # Stage 4: LLM Meeting (optional)
        if self.enable_llm_meeting:
            new_experts = await self._stage_meeting(preprocessed, classified)
            self._new_experts.extend(new_experts)

        # Stage 5: Analyze
        analyzed = await self._stage_analyze(preprocessed, classified)

        # Stage 6: Save to Knowledge Base
        self._chunks_created = self._stage_save(preprocessed, classified, analyzed)

        # Stage 7: Report
        report_path = self._stage_report(analyzed, self._new_experts)

        end_time = datetime.now()

        return PipelineResult(
            start_time=start_time,
            end_time=end_time,
            crawled_count=len(crawled),
            preprocessed_count=len(preprocessed),
            analyzed_count=len(analyzed),
            chunks_created=self._chunks_created,
            new_experts=self._new_experts,
            report_path=report_path,
            errors=self._errors,
        )

    async def _stage_crawl(self) -> List[CrawledContent]:
        """Stage 1: Crawl content from all registered sources.

        Returns:
            List of crawled content items.
        """
        try:
            crawled = await self._registry.crawl_all(days_back=self.days_back)
            return crawled
        except Exception as e:
            self._errors.append(f"Crawl stage error: {str(e)}")
            return []
        finally:
            # Close all crawler connections
            try:
                await self._registry.close_all()
            except Exception:
                pass

    def _stage_preprocess(
        self, crawled: List[CrawledContent]
    ) -> List[PreprocessedContent]:
        """Stage 2: Preprocess and deduplicate crawled content.

        Args:
            crawled: List of crawled content to preprocess.

        Returns:
            List of preprocessed content items.
        """
        try:
            # Deduplicate first
            unique = self._preprocessor.deduplicate(crawled)

            # Then preprocess
            preprocessed = self._preprocessor.preprocess_batch(unique)

            # Filter out empty content
            return [p for p in preprocessed if p.word_count > 0]
        except Exception as e:
            self._errors.append(f"Preprocess stage error: {str(e)}")
            return []

    def _stage_classify(
        self, preprocessed: List[PreprocessedContent]
    ) -> List[ClassificationResult]:
        """Stage 3: Classify content using rule-based classifier.

        Args:
            preprocessed: List of preprocessed content to classify.

        Returns:
            List of classification results.
        """
        try:
            results = []
            for content in preprocessed:
                # Use both title and content for classification
                text = f"{content.clean_title} {content.clean_content}"
                result = self._classifier.classify(text)
                results.append(result)
            return results
        except Exception as e:
            self._errors.append(f"Classify stage error: {str(e)}")
            return []

    async def _stage_meeting(
        self,
        preprocessed: List[PreprocessedContent],
        classified: List[ClassificationResult],
    ) -> List[str]:
        """Stage 4: Run LLM meeting for complex content routing.

        Only processes content that was flagged as needing LLM meeting
        during classification.

        Args:
            preprocessed: List of preprocessed content.
            classified: List of classification results.

        Returns:
            List of newly registered dynamic expert names.
        """
        new_experts: List[str] = []

        if not self.enable_llm_meeting:
            return new_experts

        try:
            # Initialize expert meeting on demand
            if self._expert_meeting is None:
                self._expert_meeting = ExpertMeeting()

            # Find content that needs LLM meeting
            for content, classification in zip(preprocessed, classified):
                if classification.needs_llm_meeting:
                    try:
                        meeting_result = await self._expert_meeting.conduct_meeting(
                            content=content.clean_content[:3000],
                            title=content.clean_title,
                            source=content.original.source,
                        )

                        # Register any new experts proposed
                        for proposal in meeting_result.new_expert_proposals:
                            if register_dynamic_expert(proposal):
                                new_experts.append(proposal.suggested_name)

                    except Exception as e:
                        self._errors.append(
                            f"Meeting error for '{content.clean_title}': {str(e)}"
                        )

            return new_experts

        except Exception as e:
            self._errors.append(f"Meeting stage error: {str(e)}")
            return new_experts

    async def _stage_analyze(
        self,
        preprocessed: List[PreprocessedContent],
        classified: List[ClassificationResult],
    ) -> List[AnalysisResult]:
        """Stage 5: Run expert analysis on content.

        Args:
            preprocessed: List of preprocessed content.
            classified: List of classification results.

        Returns:
            List of analysis results.
        """
        try:
            # Initialize analyzer on demand
            if self._analyzer is None:
                self._analyzer = ExpertAnalyzer()

            # Run batch analysis
            results = await self._analyzer.analyze_batch(preprocessed, classified)
            return results

        except Exception as e:
            self._errors.append(f"Analyze stage error: {str(e)}")
            return []

    def _stage_save(
        self,
        preprocessed: List[PreprocessedContent],
        classified: List[ClassificationResult],
        analyzed: List[AnalysisResult],
    ) -> int:
        """Stage 6: Save content to knowledge base.

        Saves all crawled and analyzed content to the knowledge base
        for vector DB indexing and RAG retrieval.

        Args:
            preprocessed: List of preprocessed content.
            classified: List of classification results.
            analyzed: List of analysis results.

        Returns:
            Number of documents saved.
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"[Save] Starting save stage: {len(preprocessed)} preprocessed, {len(classified)} classified, {len(analyzed)} analyzed")
        logger.info(f"[Save] Knowledge base path: {self._knowledge_saver.base_path}")

        try:
            saved_count = self._knowledge_saver.save_batch(
                contents=preprocessed,
                classifications=classified,
                analyses=analyzed,
            )
            logger.info(f"[Save] Saved {saved_count} documents to knowledge base")
            return saved_count

        except Exception as e:
            import traceback
            logger.error(f"[Save] Exception: {str(e)}")
            logger.error(f"[Save] Traceback: {traceback.format_exc()}")
            self._errors.append(f"Save stage error: {str(e)}")
            return 0

    def _stage_report(
        self,
        analyzed: List[AnalysisResult],
        new_experts: List[str],
    ) -> str:
        """Stage 7: Generate weekly briefing report.

        Args:
            analyzed: List of analysis results.
            new_experts: List of newly registered expert names.

        Returns:
            Path to the generated report file.
        """
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.days_back)

            # Count content
            total_analyzed = len([r for r in analyzed if not r.error])

            # Generate report
            report = self._report_generator.generate_report(
                analysis_results=analyzed,
                start_date=start_date,
                end_date=end_date,
                total_crawled=len(analyzed),
                total_analyzed=total_analyzed,
                new_chunks=self._chunks_created,
                new_experts=new_experts,
            )

            # Save report
            report_path = self._report_generator.save_report(report)
            return report_path

        except Exception as e:
            self._errors.append(f"Report stage error: {str(e)}")
            return ""
