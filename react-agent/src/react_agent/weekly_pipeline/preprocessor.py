"""Preprocessor module for cleaning and normalizing crawled content.

This module provides functionality to clean HTML content, normalize text,
detect language, and deduplicate crawled content.
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import List

from bs4 import BeautifulSoup

from .crawler import CrawledContent


@dataclass
class PreprocessedContent:
    """Data class representing preprocessed content.

    Attributes:
        original: The original CrawledContent object.
        clean_content: Cleaned and normalized content text.
        clean_title: Cleaned title without HTML tags.
        language: Detected language code ('ko' or 'en').
        word_count: Number of words in the content.
        content_hash: MD5 hash of the cleaned content.
        extracted_keywords: List of extracted keywords.
    """

    original: CrawledContent
    clean_content: str
    clean_title: str
    language: str
    word_count: int
    content_hash: str
    extracted_keywords: List[str] = field(default_factory=list)


class Preprocessor:
    """Preprocessor class for cleaning and normalizing crawled content.

    Provides methods for HTML cleaning, text normalization, language detection,
    hashing, and deduplication of crawled content.
    """

    # Tags to remove completely (including their content)
    REMOVE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "iframe"]

    def clean_html(self, html: str) -> str:
        """Clean HTML content by removing unwanted tags and extracting text.

        Removes script, style, navigation, and other non-content tags,
        then extracts the remaining text.

        Args:
            html: Raw HTML string to clean.

        Returns:
            Cleaned text content without HTML tags.
        """
        if not html:
            return ""

        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted tags completely
        for tag in self.REMOVE_TAGS:
            for element in soup.find_all(tag):
                element.decompose()

        # Extract text from remaining content
        text = soup.get_text(separator=" ", strip=True)

        return text

    def normalize_text(self, text: str) -> str:
        """Normalize text by removing consecutive whitespace and newlines.

        Replaces multiple consecutive spaces with a single space,
        multiple consecutive newlines with a single newline,
        and strips leading/trailing whitespace.

        Args:
            text: Text to normalize.

        Returns:
            Normalized text.
        """
        if not text:
            return ""

        # Replace consecutive whitespace (spaces, tabs) with single space
        text = re.sub(r"[ \t]+", " ", text)

        # Replace consecutive newlines with single newline
        text = re.sub(r"\n+", "\n", text)

        # Strip leading and trailing whitespace
        text = text.strip()

        return text

    def detect_language(self, text: str) -> str:
        """Detect language based on Korean character ratio.

        Uses the ratio of Korean characters (Hangul) to determine
        if the text is primarily Korean or English.

        Args:
            text: Text to analyze.

        Returns:
            Language code: 'ko' for Korean, 'en' for English.
        """
        if not text:
            return "en"

        # Count Korean characters (Hangul)
        korean_pattern = re.compile(r"[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]")
        korean_chars = len(korean_pattern.findall(text))

        # Count total alphabetic characters (excluding spaces, punctuation)
        alpha_pattern = re.compile(r"[a-zA-Z\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]")
        total_alpha = len(alpha_pattern.findall(text))

        if total_alpha == 0:
            return "en"

        korean_ratio = korean_chars / total_alpha

        # If more than 30% Korean characters, consider it Korean
        return "ko" if korean_ratio > 0.3 else "en"

    def compute_hash(self, text: str) -> str:
        """Compute MD5 hash of the given text.

        Args:
            text: Text to hash.

        Returns:
            MD5 hex digest of the text.
        """
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def count_words(self, text: str) -> int:
        """Count the number of words in the text.

        Words are counted by splitting on whitespace.

        Args:
            text: Text to count words in.

        Returns:
            Number of words.
        """
        if not text or not text.strip():
            return 0

        words = text.split()
        return len(words)

    def preprocess(self, content: CrawledContent) -> PreprocessedContent:
        """Preprocess a single CrawledContent object.

        Cleans HTML, normalizes text, detects language, computes hash,
        and counts words.

        Args:
            content: CrawledContent object to preprocess.

        Returns:
            PreprocessedContent object with cleaned and processed data.
        """
        # Clean content - use raw_html if available, otherwise clean the content field
        if content.raw_html:
            clean_content = self.clean_html(content.raw_html)
        else:
            clean_content = self.clean_html(content.content)

        # Normalize the cleaned content
        clean_content = self.normalize_text(clean_content)

        # Clean the title
        clean_title = self.clean_html(content.title)
        clean_title = self.normalize_text(clean_title)

        # Detect language from clean content
        language = self.detect_language(clean_content)

        # Compute hash for deduplication
        content_hash = self.compute_hash(clean_title + clean_content)

        # Count words
        word_count = self.count_words(clean_content)

        return PreprocessedContent(
            original=content,
            clean_content=clean_content,
            clean_title=clean_title,
            language=language,
            word_count=word_count,
            content_hash=content_hash,
        )

    def deduplicate(self, contents: List[CrawledContent]) -> List[CrawledContent]:
        """Remove duplicate content based on title and content hash.

        Keeps the first occurrence of content with the same title and content.

        Args:
            contents: List of CrawledContent objects to deduplicate.

        Returns:
            List of unique CrawledContent objects.
        """
        if not contents:
            return []

        seen_hashes = set()
        unique_contents = []

        for content in contents:
            # Compute hash from title and content
            hash_input = content.title + content.content
            content_hash = self.compute_hash(hash_input)

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_contents.append(content)

        return unique_contents

    def preprocess_batch(
        self, contents: List[CrawledContent]
    ) -> List[PreprocessedContent]:
        """Preprocess multiple CrawledContent objects.

        Args:
            contents: List of CrawledContent objects to preprocess.

        Returns:
            List of PreprocessedContent objects.
        """
        return [self.preprocess(content) for content in contents]
