"""Weekly pipeline module for policy/news analysis."""

from .analyzer import ANALYSIS_PROMPT, AnalysisResult, ExpertAnalyzer
from .classifier import ClassificationResult, RuleBasedClassifier
from .crawler import BaseCrawler, CrawledContent, CrawlerRegistry, RSSCrawler
from .expert_generator import (
    DynamicExpertRole,
    ExpertGenerator,
    clear_dynamic_experts,
    get_dynamic_expert,
    get_dynamic_experts,
    register_dynamic_expert,
)
from .expert_meeting import ExpertMeeting, MeetingResult, NewExpertProposal
from .preprocessor import PreprocessedContent, Preprocessor
from .report_generator import ExpertSection, ReportGenerator, WeeklyReport
from .sources import (
    DOMESTIC_SOURCES,
    INTERNATIONAL_SOURCES,
    MEDIA_SOURCES,
    SourceConfig,
    get_default_registry,
)

__all__ = [
    "ANALYSIS_PROMPT",
    "AnalysisResult",
    "BaseCrawler",
    "ClassificationResult",
    "CrawledContent",
    "CrawlerRegistry",
    "DOMESTIC_SOURCES",
    "DynamicExpertRole",
    "ExpertAnalyzer",
    "ExpertGenerator",
    "ExpertMeeting",
    "ExpertSection",
    "INTERNATIONAL_SOURCES",
    "MEDIA_SOURCES",
    "MeetingResult",
    "NewExpertProposal",
    "PreprocessedContent",
    "Preprocessor",
    "ReportGenerator",
    "RSSCrawler",
    "RuleBasedClassifier",
    "SourceConfig",
    "WeeklyReport",
    "clear_dynamic_experts",
    "get_default_registry",
    "get_dynamic_expert",
    "get_dynamic_experts",
    "register_dynamic_expert",
]
