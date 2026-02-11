"""Weekly pipeline module for policy/news analysis."""

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
from .sources import (
    DOMESTIC_SOURCES,
    INTERNATIONAL_SOURCES,
    MEDIA_SOURCES,
    SourceConfig,
    get_default_registry,
)

__all__ = [
    "BaseCrawler",
    "ClassificationResult",
    "CrawledContent",
    "CrawlerRegistry",
    "DOMESTIC_SOURCES",
    "DynamicExpertRole",
    "ExpertGenerator",
    "ExpertMeeting",
    "INTERNATIONAL_SOURCES",
    "MEDIA_SOURCES",
    "MeetingResult",
    "NewExpertProposal",
    "PreprocessedContent",
    "Preprocessor",
    "RSSCrawler",
    "RuleBasedClassifier",
    "SourceConfig",
    "clear_dynamic_experts",
    "get_default_registry",
    "get_dynamic_expert",
    "get_dynamic_experts",
    "register_dynamic_expert",
]
