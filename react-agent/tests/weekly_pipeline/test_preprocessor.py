"""Tests for preprocessor module."""

from datetime import datetime

import pytest

from react_agent.weekly_pipeline import CrawledContent
from react_agent.weekly_pipeline.preprocessor import Preprocessor, PreprocessedContent


class TestPreprocessor:
    """Test Preprocessor class."""

    @pytest.fixture
    def preprocessor(self):
        """Create a Preprocessor instance."""
        return Preprocessor()

    def test_clean_html_removes_script_tags(self, preprocessor):
        """Test that clean_html removes script tags."""
        html = """
        <html>
            <head>
                <script>alert('test');</script>
            </head>
            <body>
                <p>Hello World</p>
                <script type="text/javascript">
                    console.log('test');
                </script>
            </body>
        </html>
        """
        result = preprocessor.clean_html(html)

        assert "alert" not in result
        assert "console.log" not in result
        assert "Hello World" in result

    def test_clean_html_removes_style_tags(self, preprocessor):
        """Test that clean_html removes style tags."""
        html = """
        <html>
            <head>
                <style>.test { color: red; }</style>
            </head>
            <body>
                <p>Content here</p>
            </body>
        </html>
        """
        result = preprocessor.clean_html(html)

        assert "color: red" not in result
        assert "Content here" in result

    def test_clean_html_removes_nav_footer_header(self, preprocessor):
        """Test that clean_html removes nav, footer, and header tags."""
        html = """
        <html>
            <body>
                <header>Site Header</header>
                <nav>Navigation Menu</nav>
                <main>
                    <article>Main Content</article>
                </main>
                <footer>Site Footer</footer>
            </body>
        </html>
        """
        result = preprocessor.clean_html(html)

        assert "Site Header" not in result
        assert "Navigation Menu" not in result
        assert "Site Footer" not in result
        assert "Main Content" in result

    def test_clean_html_extracts_text(self, preprocessor):
        """Test that clean_html extracts text from HTML."""
        html = "<div><p>Paragraph 1</p><p>Paragraph 2</p></div>"
        result = preprocessor.clean_html(html)

        assert "Paragraph 1" in result
        assert "Paragraph 2" in result

    def test_normalize_text_removes_consecutive_spaces(self, preprocessor):
        """Test that normalize_text removes consecutive spaces."""
        text = "Hello    World    Test"
        result = preprocessor.normalize_text(text)

        assert result == "Hello World Test"

    def test_normalize_text_removes_consecutive_newlines(self, preprocessor):
        """Test that normalize_text removes consecutive newlines."""
        text = "Line 1\n\n\n\nLine 2\n\n\nLine 3"
        result = preprocessor.normalize_text(text)

        # Should have single newlines or spaces
        assert "\n\n\n" not in result
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_normalize_text_strips_leading_trailing_whitespace(self, preprocessor):
        """Test that normalize_text strips leading and trailing whitespace."""
        text = "   Hello World   "
        result = preprocessor.normalize_text(text)

        assert result == "Hello World"

    def test_detect_language_korean(self, preprocessor):
        """Test that detect_language returns 'ko' for Korean text."""
        korean_text = "안녕하세요. 오늘 날씨가 좋습니다. 탄소중립 정책에 대해 알아봅시다."
        result = preprocessor.detect_language(korean_text)

        assert result == "ko"

    def test_detect_language_english(self, preprocessor):
        """Test that detect_language returns 'en' for English text."""
        english_text = "Hello World. This is a test. Carbon neutrality is important."
        result = preprocessor.detect_language(english_text)

        assert result == "en"

    def test_detect_language_mixed_mostly_korean(self, preprocessor):
        """Test that detect_language returns 'ko' for mostly Korean text."""
        mixed_text = "오늘의 뉴스입니다. Carbon credit 시장이 활성화되고 있습니다."
        result = preprocessor.detect_language(mixed_text)

        assert result == "ko"

    def test_compute_hash(self, preprocessor):
        """Test that compute_hash generates consistent MD5 hash."""
        text = "Test content for hashing"
        hash1 = preprocessor.compute_hash(text)
        hash2 = preprocessor.compute_hash(text)

        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hex digest length

    def test_compute_hash_different_content(self, preprocessor):
        """Test that compute_hash generates different hashes for different content."""
        hash1 = preprocessor.compute_hash("Content A")
        hash2 = preprocessor.compute_hash("Content B")

        assert hash1 != hash2

    def test_count_words(self, preprocessor):
        """Test that count_words counts words correctly."""
        text = "This is a test sentence with seven words"
        result = preprocessor.count_words(text)

        assert result == 8  # Actually 8 words

    def test_count_words_korean(self, preprocessor):
        """Test that count_words counts Korean words by spaces."""
        text = "안녕하세요 오늘 날씨가 좋습니다"
        result = preprocessor.count_words(text)

        assert result == 4

    def test_count_words_empty_string(self, preprocessor):
        """Test that count_words returns 0 for empty string."""
        result = preprocessor.count_words("")

        assert result == 0

    def test_preprocess_content(self, preprocessor):
        """Test that preprocess creates PreprocessedContent correctly."""
        now = datetime.now()
        crawled = CrawledContent(
            title="<b>Test Title</b>",
            content="<p>Test content body</p><script>alert('x');</script>",
            url="https://example.com/article",
            source="test_source",
            published_date=now,
            language="ko",
            raw_html="<html><body><p>Test content body</p><script>alert('x');</script></body></html>",
        )

        result = preprocessor.preprocess(crawled)

        assert isinstance(result, PreprocessedContent)
        assert result.original is crawled
        assert "alert" not in result.clean_content
        assert "Test content body" in result.clean_content
        assert result.clean_title == "Test Title"
        assert result.language in ["ko", "en"]
        assert result.word_count > 0
        assert len(result.content_hash) == 32

    def test_preprocess_content_with_html_title(self, preprocessor):
        """Test that preprocess cleans HTML from title."""
        now = datetime.now()
        crawled = CrawledContent(
            title="<span style='color:red'>Important</span> <b>News</b>",
            content="Article content here",
            url="https://example.com/article",
            source="test_source",
            published_date=now,
        )

        result = preprocessor.preprocess(crawled)

        assert "<span" not in result.clean_title
        assert "<b>" not in result.clean_title
        assert "Important" in result.clean_title
        assert "News" in result.clean_title

    def test_deduplicate_removes_duplicates(self, preprocessor):
        """Test that deduplicate removes content with same title and content."""
        now = datetime.now()
        content1 = CrawledContent(
            title="Same Title",
            content="Same Content",
            url="https://example.com/1",
            source="source1",
            published_date=now,
        )
        content2 = CrawledContent(
            title="Same Title",
            content="Same Content",
            url="https://example.com/2",
            source="source2",
            published_date=now,
        )
        content3 = CrawledContent(
            title="Different Title",
            content="Different Content",
            url="https://example.com/3",
            source="source3",
            published_date=now,
        )

        result = preprocessor.deduplicate([content1, content2, content3])

        assert len(result) == 2
        # First occurrence should be kept
        assert content1 in result
        assert content3 in result

    def test_deduplicate_empty_list(self, preprocessor):
        """Test that deduplicate handles empty list."""
        result = preprocessor.deduplicate([])

        assert result == []

    def test_deduplicate_no_duplicates(self, preprocessor):
        """Test that deduplicate preserves all unique content."""
        now = datetime.now()
        contents = [
            CrawledContent(
                title=f"Title {i}",
                content=f"Content {i}",
                url=f"https://example.com/{i}",
                source="source",
                published_date=now,
            )
            for i in range(5)
        ]

        result = preprocessor.deduplicate(contents)

        assert len(result) == 5

    def test_preprocess_batch(self, preprocessor):
        """Test that preprocess_batch processes multiple contents."""
        now = datetime.now()
        contents = [
            CrawledContent(
                title=f"Title {i}",
                content=f"<p>Content {i}</p>",
                url=f"https://example.com/{i}",
                source="source",
                published_date=now,
            )
            for i in range(3)
        ]

        result = preprocessor.preprocess_batch(contents)

        assert len(result) == 3
        for i, preprocessed in enumerate(result):
            assert isinstance(preprocessed, PreprocessedContent)
            assert f"Content {i}" in preprocessed.clean_content


class TestPreprocessedContent:
    """Test PreprocessedContent dataclass."""

    def test_create_preprocessed_content(self):
        """Test creating PreprocessedContent."""
        now = datetime.now()
        crawled = CrawledContent(
            title="Test",
            content="Content",
            url="https://example.com",
            source="source",
            published_date=now,
        )

        preprocessed = PreprocessedContent(
            original=crawled,
            clean_content="Clean content",
            clean_title="Clean title",
            language="ko",
            word_count=2,
            content_hash="abc123def456abc123def456abc12345",
        )

        assert preprocessed.original is crawled
        assert preprocessed.clean_content == "Clean content"
        assert preprocessed.clean_title == "Clean title"
        assert preprocessed.language == "ko"
        assert preprocessed.word_count == 2
        assert preprocessed.content_hash == "abc123def456abc123def456abc12345"
        assert preprocessed.extracted_keywords == []

    def test_preprocessed_content_with_keywords(self):
        """Test creating PreprocessedContent with keywords."""
        now = datetime.now()
        crawled = CrawledContent(
            title="Test",
            content="Content",
            url="https://example.com",
            source="source",
            published_date=now,
        )

        keywords = ["climate", "carbon", "policy"]
        preprocessed = PreprocessedContent(
            original=crawled,
            clean_content="Clean content",
            clean_title="Clean title",
            language="en",
            word_count=2,
            content_hash="abc123def456abc123def456abc12345",
            extracted_keywords=keywords,
        )

        assert preprocessed.extracted_keywords == keywords
