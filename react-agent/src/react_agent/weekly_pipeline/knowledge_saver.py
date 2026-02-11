"""Knowledge base saver module.

This module saves crawled and analyzed content to the knowledge base
for vector DB indexing and RAG retrieval.
"""

import os
import logging
import hashlib
import unicodedata
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from .preprocessor import PreprocessedContent
from .classifier import ClassificationResult
from .analyzer import AnalysisResult

logger = logging.getLogger(__name__)


# Category to folder mapping
CATEGORY_FOLDER_MAP = {
    "POLICY_EXPERT": "정책법규",
    "CARBON_CREDIT_EXPERT": "탄소배출권",
    "MARKET_EXPERT": "시장거래",
    "TECHNOLOGY_EXPERT": "감축기술",
    "MRV_EXPERT": "MRV검증",
}


def get_knowledge_base_path() -> Path:
    """Get the knowledge base directory path."""
    kb_path = os.getenv("KNOWLEDGE_BASE_PATH")
    if kb_path:
        return Path(kb_path)

    # Default to the knowledge_base folder relative to the project
    return Path(__file__).parent.parent / "knowledge_base"


def sanitize_filename(title: str, max_length: int = 100) -> str:
    """Sanitize a title to be used as a filename.

    Args:
        title: Original title string
        max_length: Maximum length of the filename

    Returns:
        Sanitized filename string
    """
    # Normalize unicode characters
    normalized = unicodedata.normalize('NFC', title)

    # Remove or replace invalid characters
    # Keep Korean characters, alphanumeric, spaces, hyphens, underscores
    cleaned = re.sub(r'[^\w\s가-힣\-]', '', normalized)

    # Replace multiple spaces with single space
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # Replace spaces with underscores
    cleaned = cleaned.replace(' ', '_')

    # Truncate to max length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    # Remove trailing underscores
    cleaned = cleaned.rstrip('_')

    return cleaned or "untitled"


def get_content_hash(content: str) -> str:
    """Generate a short hash for content deduplication.

    Args:
        content: Content string to hash

    Returns:
        8-character hash string
    """
    return hashlib.md5(content.encode()).hexdigest()[:8]


class KnowledgeSaver:
    """Saves processed content to the knowledge base.

    Saves crawled content as structured documents organized by category,
    ready for vector DB indexing.
    """

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize the knowledge saver.

        Args:
            base_path: Base path for the knowledge base. If None, uses default.
        """
        self.base_path = base_path or get_knowledge_base_path()
        logger.info(f"[KnowledgeSaver] Initialized with base_path: {self.base_path}")
        logger.info(f"[KnowledgeSaver] Base path exists: {self.base_path.exists()}")
        self._ensure_directories()
        logger.info(f"[KnowledgeSaver] After _ensure_directories, base path exists: {self.base_path.exists()}")
        self._saved_hashes: set = set()

    def _ensure_directories(self):
        """Ensure all category directories exist."""
        self.base_path.mkdir(parents=True, exist_ok=True)

        for folder in CATEGORY_FOLDER_MAP.values():
            folder_path = self.base_path / folder
            folder_path.mkdir(exist_ok=True)

            # Create .gitkeep if empty
            gitkeep = folder_path / ".gitkeep"
            if not gitkeep.exists() and not list(folder_path.glob("*.md")):
                gitkeep.touch()

    def get_category_folder(self, expert_role: str) -> str:
        """Get the folder name for an expert role.

        Args:
            expert_role: Expert role string (e.g., "POLICY_EXPERT")

        Returns:
            Folder name for the category
        """
        role_upper = expert_role.upper()
        return CATEGORY_FOLDER_MAP.get(role_upper, "기타")

    def save_content(
        self,
        content: PreprocessedContent,
        classification: ClassificationResult,
        analysis: Optional[AnalysisResult] = None,
    ) -> Optional[str]:
        """Save a single content item to the knowledge base.

        Args:
            content: Preprocessed content to save
            classification: Classification result with expert assignment
            analysis: Optional analysis result to include

        Returns:
            Path to the saved file, or None if skipped/failed
        """
        try:
            # Check for duplicates
            content_hash = content.content_hash
            if content_hash in self._saved_hashes:
                logger.debug(f"Skipping duplicate content: {content.clean_title}")
                return None

            # Determine category folder
            expert_role = classification.primary_expert.value.upper()
            folder = self.get_category_folder(expert_role)
            folder_path = self.base_path / folder

            # Generate filename
            date_str = content.original.published_date.strftime("%Y%m%d")
            title_slug = sanitize_filename(content.clean_title)
            hash_suffix = get_content_hash(content.clean_content)
            filename = f"{date_str}_{title_slug}_{hash_suffix}.md"
            filepath = folder_path / filename

            # Skip if file already exists
            if filepath.exists():
                logger.debug(f"File already exists: {filepath}")
                self._saved_hashes.add(content_hash)
                return str(filepath)

            # Build document content
            document = self._build_document(content, classification, analysis)

            # Write to file
            logger.info(f"[KnowledgeSaver] Writing to: {filepath}")
            filepath.write_text(document, encoding="utf-8")
            self._saved_hashes.add(content_hash)

            logger.info(f"Saved to knowledge base: {filepath.name}")
            return str(filepath)

        except Exception as e:
            import traceback
            logger.error(f"Failed to save content '{content.clean_title}': {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def _build_document(
        self,
        content: PreprocessedContent,
        classification: ClassificationResult,
        analysis: Optional[AnalysisResult] = None,
    ) -> str:
        """Build a markdown document from content and analysis.

        Args:
            content: Preprocessed content
            classification: Classification result
            analysis: Optional analysis result

        Returns:
            Markdown formatted document string
        """
        lines = []

        # YAML frontmatter
        lines.append("---")
        lines.append(f"title: \"{content.clean_title}\"")
        lines.append(f"source: \"{content.original.source}\"")
        lines.append(f"url: \"{content.original.url}\"")
        lines.append(f"published_date: \"{content.original.published_date.strftime('%Y-%m-%d')}\"")
        lines.append(f"crawled_date: \"{datetime.now().strftime('%Y-%m-%d')}\"")
        lines.append(f"category: \"{classification.primary_expert.value}\"")
        lines.append(f"language: \"{content.original.language}\"")
        lines.append(f"word_count: {content.word_count}")
        if classification.secondary_expert:
            lines.append(f"related_categories: \"{classification.secondary_expert.value}\"")
        lines.append("---")
        lines.append("")

        # Title
        lines.append(f"# {content.clean_title}")
        lines.append("")

        # Metadata summary
        lines.append("## 메타데이터")
        lines.append("")
        lines.append(f"- **출처**: {content.original.source}")
        lines.append(f"- **원문 URL**: {content.original.url}")
        lines.append(f"- **발행일**: {content.original.published_date.strftime('%Y-%m-%d')}")
        lines.append(f"- **분류**: {classification.primary_expert.value}")
        lines.append("")

        # Analysis section (if available)
        if analysis and not analysis.error:
            lines.append("## 전문가 분석")
            lines.append("")

            if analysis.summary:
                lines.append("### 요약")
                lines.append(analysis.summary)
                lines.append("")

            if analysis.key_findings:
                lines.append("### 주요 발견")
                for finding in analysis.key_findings:
                    lines.append(f"- {finding}")
                lines.append("")

            if analysis.implications:
                lines.append("### 시사점")
                for implication in analysis.implications:
                    lines.append(f"- {implication}")
                lines.append("")

        # Original content
        lines.append("## 원문 내용")
        lines.append("")
        lines.append(content.clean_content)
        lines.append("")

        return "\n".join(lines)

    def save_batch(
        self,
        contents: List[PreprocessedContent],
        classifications: List[ClassificationResult],
        analyses: Optional[List[AnalysisResult]] = None,
    ) -> int:
        """Save multiple contents to the knowledge base.

        Args:
            contents: List of preprocessed contents
            classifications: List of classification results
            analyses: Optional list of analysis results

        Returns:
            Number of successfully saved documents
        """
        logger.info(f"[save_batch] Starting batch save: {len(contents)} contents, {len(classifications)} classifications, {len(analyses) if analyses else 0} analyses")

        saved_count = 0
        failed_count = 0

        for i, (content, classification) in enumerate(zip(contents, classifications)):
            analysis = analyses[i] if analyses and i < len(analyses) else None

            try:
                result = self.save_content(content, classification, analysis)
                if result:
                    saved_count += 1
                else:
                    failed_count += 1
                    if i < 3:  # Log first few failures
                        logger.warning(f"[save_batch] Item {i} returned None: {content.clean_title[:50]}")
            except Exception as e:
                failed_count += 1
                logger.error(f"[save_batch] Exception for item {i}: {e}")

        logger.info(f"Saved {saved_count}/{len(contents)} documents to knowledge base (failed: {failed_count})")
        return saved_count

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base.

        Returns:
            Dictionary with statistics
        """
        stats = {
            "total_documents": 0,
            "by_category": {},
            "last_updated": None,
        }

        if not self.base_path.exists():
            return stats

        latest_mtime = 0.0

        for folder in CATEGORY_FOLDER_MAP.values():
            folder_path = self.base_path / folder
            if folder_path.exists():
                docs = list(folder_path.glob("*.md"))
                stats["by_category"][folder] = len(docs)
                stats["total_documents"] += len(docs)

                for doc in docs:
                    mtime = doc.stat().st_mtime
                    if mtime > latest_mtime:
                        latest_mtime = mtime

        if latest_mtime > 0:
            stats["last_updated"] = datetime.fromtimestamp(latest_mtime).isoformat()

        return stats
