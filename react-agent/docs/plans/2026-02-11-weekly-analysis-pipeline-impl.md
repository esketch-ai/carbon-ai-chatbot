# Weekly Analysis Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 매주 국내외 정책/뉴스를 자동 크롤링하여 PhD 전문가가 분석하고 지식베이스를 발전시키는 파이프라인 구축

**Architecture:** 크롤러 → 전처리 → 규칙분류(+LLM회의) → 전문가분석 → 청킹저장 → 리포트생성 순차 파이프라인. APScheduler로 주간 자동 실행.

**Tech Stack:** Python 3.11+, httpx, BeautifulSoup4, APScheduler, ChromaDB, LangChain/LangGraph

---

## Task 1: 크롤러 기본 구조

**Files:**
- Create: `src/react_agent/weekly_pipeline/__init__.py`
- Create: `src/react_agent/weekly_pipeline/crawler.py`
- Test: `tests/weekly_pipeline/test_crawler.py`

**Step 1: Create weekly_pipeline package**

```python
# src/react_agent/weekly_pipeline/__init__.py
"""Weekly Analysis Pipeline - 주간 정책/뉴스 분석 파이프라인"""

from .crawler import BaseCrawler, CrawlerRegistry, CrawledContent

__all__ = ["BaseCrawler", "CrawlerRegistry", "CrawledContent"]
```

**Step 2: Write the failing test**

```python
# tests/weekly_pipeline/test_crawler.py
"""크롤러 테스트"""

import pytest
from datetime import datetime, timedelta

from react_agent.weekly_pipeline.crawler import (
    BaseCrawler,
    CrawledContent,
    CrawlerRegistry,
    RSSCrawler,
)


class TestCrawledContent:
    """CrawledContent 데이터 클래스 테스트"""

    def test_create_content(self):
        content = CrawledContent(
            title="테스트 제목",
            content="테스트 내용",
            url="https://example.com/test",
            source="test_source",
            published_date=datetime.now(),
            language="ko",
        )
        assert content.title == "테스트 제목"
        assert content.source == "test_source"
        assert content.language == "ko"


class TestCrawlerRegistry:
    """CrawlerRegistry 테스트"""

    def test_register_and_get_crawler(self):
        registry = CrawlerRegistry()

        class MockCrawler(BaseCrawler):
            async def crawl(self, days_back=7):
                return []

        crawler = MockCrawler(
            name="mock",
            base_url="https://example.com",
            source_type="test"
        )
        registry.register(crawler)

        assert registry.get("mock") == crawler
        assert len(registry.get_all()) == 1


class TestRSSCrawler:
    """RSS 크롤러 테스트"""

    @pytest.mark.asyncio
    async def test_rss_crawler_init(self):
        crawler = RSSCrawler(
            name="test_rss",
            base_url="https://example.com",
            rss_url="https://example.com/rss.xml",
            source_type="news"
        )
        assert crawler.name == "test_rss"
        assert crawler.rss_url == "https://example.com/rss.xml"
```

**Step 3: Run test to verify it fails**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/weekly_pipeline/test_crawler.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 4: Write minimal implementation**

```python
# src/react_agent/weekly_pipeline/crawler.py
"""크롤러 모듈 - 정책/뉴스 소스별 크롤러 구현"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class CrawledContent:
    """크롤링된 콘텐츠 데이터 클래스"""

    title: str
    content: str
    url: str
    source: str
    published_date: datetime
    language: str = "ko"
    category: str = ""
    raw_html: str = ""
    metadata: Dict = field(default_factory=dict)


class BaseCrawler(ABC):
    """크롤러 기본 추상 클래스"""

    def __init__(
        self,
        name: str,
        base_url: str,
        source_type: str,
        language: str = "ko",
        timeout: float = 30.0,
    ):
        self.name = name
        self.base_url = base_url
        self.source_type = source_type
        self.language = language
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """HTTP 클라이언트 반환 (lazy init)"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; WeeklyAnalysisBot/1.0)"
                }
            )
        return self._client

    async def close(self):
        """클라이언트 종료"""
        if self._client:
            await self._client.aclose()
            self._client = None

    @abstractmethod
    async def crawl(self, days_back: int = 7) -> List[CrawledContent]:
        """크롤링 실행 - 서브클래스에서 구현"""
        pass

    async def fetch_page(self, url: str) -> Optional[str]:
        """페이지 HTML 가져오기"""
        try:
            client = await self._get_client()
            response = await client.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"[{self.name}] 페이지 fetch 실패: {url} - {e}")
            return None


class RSSCrawler(BaseCrawler):
    """RSS 피드 기반 크롤러"""

    def __init__(
        self,
        name: str,
        base_url: str,
        rss_url: str,
        source_type: str,
        language: str = "ko",
        timeout: float = 30.0,
    ):
        super().__init__(name, base_url, source_type, language, timeout)
        self.rss_url = rss_url

    async def crawl(self, days_back: int = 7) -> List[CrawledContent]:
        """RSS 피드 크롤링"""
        results = []
        cutoff_date = datetime.now() - timedelta(days=days_back)

        try:
            xml_content = await self.fetch_page(self.rss_url)
            if not xml_content:
                return results

            soup = BeautifulSoup(xml_content, "xml")
            items = soup.find_all("item")

            for item in items:
                try:
                    # 날짜 파싱
                    pub_date_str = item.find("pubDate")
                    if pub_date_str:
                        pub_date = self._parse_rss_date(pub_date_str.text)
                        if pub_date < cutoff_date:
                            continue
                    else:
                        pub_date = datetime.now()

                    # 콘텐츠 추출
                    title = item.find("title")
                    link = item.find("link")
                    description = item.find("description")

                    content = CrawledContent(
                        title=title.text.strip() if title else "",
                        content=description.text.strip() if description else "",
                        url=link.text.strip() if link else "",
                        source=self.name,
                        published_date=pub_date,
                        language=self.language,
                    )
                    results.append(content)

                except Exception as e:
                    logger.warning(f"[{self.name}] 아이템 파싱 오류: {e}")
                    continue

            logger.info(f"[{self.name}] {len(results)}개 콘텐츠 크롤링 완료")

        except Exception as e:
            logger.error(f"[{self.name}] RSS 크롤링 실패: {e}")

        return results

    def _parse_rss_date(self, date_str: str) -> datetime:
        """RSS 날짜 문자열 파싱"""
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return datetime.now()


class WebPageCrawler(BaseCrawler):
    """웹페이지 직접 크롤링"""

    def __init__(
        self,
        name: str,
        base_url: str,
        list_url: str,
        source_type: str,
        language: str = "ko",
        timeout: float = 30.0,
    ):
        super().__init__(name, base_url, source_type, language, timeout)
        self.list_url = list_url

    async def crawl(self, days_back: int = 7) -> List[CrawledContent]:
        """웹페이지 크롤링 - 서브클래스에서 파싱 로직 구현 필요"""
        # 기본 구현: 빈 리스트 반환
        logger.warning(f"[{self.name}] WebPageCrawler는 서브클래스에서 구현 필요")
        return []


class CrawlerRegistry:
    """크롤러 레지스트리 - 등록된 크롤러 관리"""

    def __init__(self):
        self._crawlers: Dict[str, BaseCrawler] = {}

    def register(self, crawler: BaseCrawler) -> None:
        """크롤러 등록"""
        self._crawlers[crawler.name] = crawler
        logger.info(f"크롤러 등록: {crawler.name} ({crawler.source_type})")

    def get(self, name: str) -> Optional[BaseCrawler]:
        """이름으로 크롤러 조회"""
        return self._crawlers.get(name)

    def get_all(self) -> List[BaseCrawler]:
        """모든 크롤러 반환"""
        return list(self._crawlers.values())

    def get_by_type(self, source_type: str) -> List[BaseCrawler]:
        """타입으로 크롤러 필터"""
        return [c for c in self._crawlers.values() if c.source_type == source_type]

    async def crawl_all(self, days_back: int = 7) -> List[CrawledContent]:
        """모든 크롤러 병렬 실행"""
        tasks = [crawler.crawl(days_back) for crawler in self._crawlers.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_content = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"크롤링 오류: {result}")
            else:
                all_content.extend(result)

        return all_content

    async def close_all(self):
        """모든 크롤러 클라이언트 종료"""
        for crawler in self._crawlers.values():
            await crawler.close()
```

**Step 5: Run test to verify it passes**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/weekly_pipeline/test_crawler.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/react_agent/weekly_pipeline/ tests/weekly_pipeline/
git commit -m "feat: add crawler base classes and registry"
```

---

## Task 2: 소스 레지스트리 설정

**Files:**
- Create: `src/react_agent/weekly_pipeline/sources.py`
- Test: `tests/weekly_pipeline/test_sources.py`

**Step 1: Write the failing test**

```python
# tests/weekly_pipeline/test_sources.py
"""소스 레지스트리 테스트"""

import pytest

from react_agent.weekly_pipeline.sources import (
    SourceConfig,
    DOMESTIC_SOURCES,
    INTERNATIONAL_SOURCES,
    MEDIA_SOURCES,
    get_default_registry,
)


class TestSourceConfig:
    """SourceConfig 테스트"""

    def test_domestic_sources_exist(self):
        assert len(DOMESTIC_SOURCES) >= 4
        assert any(s.name == "환경부" for s in DOMESTIC_SOURCES)

    def test_international_sources_exist(self):
        assert len(INTERNATIONAL_SOURCES) >= 4
        assert any(s.name == "UNFCCC" for s in INTERNATIONAL_SOURCES)

    def test_media_sources_exist(self):
        assert len(MEDIA_SOURCES) >= 2


class TestDefaultRegistry:
    """기본 레지스트리 테스트"""

    def test_get_default_registry(self):
        registry = get_default_registry()
        assert len(registry.get_all()) > 0
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/weekly_pipeline/test_sources.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/react_agent/weekly_pipeline/sources.py
"""크롤링 소스 설정 - 국내/국제/언론 소스 정의"""

from dataclasses import dataclass
from typing import List, Optional

from .crawler import CrawlerRegistry, RSSCrawler, BaseCrawler


@dataclass
class SourceConfig:
    """소스 설정"""
    name: str
    base_url: str
    rss_url: Optional[str] = None
    list_url: Optional[str] = None
    source_type: str = "official"  # official, media, research
    language: str = "ko"
    category: str = ""  # policy, market, technology, etc.
    description: str = ""


# 국내 공식 소스
DOMESTIC_SOURCES: List[SourceConfig] = [
    SourceConfig(
        name="환경부",
        base_url="https://www.me.go.kr",
        rss_url="https://www.me.go.kr/home/web/rss.do",
        source_type="official",
        language="ko",
        category="policy",
        description="환경부 보도자료 및 정책공고",
    ),
    SourceConfig(
        name="산업통상자원부",
        base_url="https://www.motie.go.kr",
        rss_url="https://www.motie.go.kr/motie/py/brf/motiebriefing/rss.do",
        source_type="official",
        language="ko",
        category="policy",
        description="에너지정책 및 산업정책",
    ),
    SourceConfig(
        name="한국환경공단",
        base_url="https://www.keco.or.kr",
        list_url="https://www.keco.or.kr/kr/board/notice/list.do",
        source_type="official",
        language="ko",
        category="carbon_credit",
        description="배출권 공고 및 검증 안내",
    ),
    SourceConfig(
        name="온실가스종합정보센터",
        base_url="https://www.gir.go.kr",
        list_url="https://www.gir.go.kr/home/board/list.do",
        source_type="official",
        language="ko",
        category="mrv",
        description="통계 및 인벤토리",
    ),
]

# 국제 공식 소스
INTERNATIONAL_SOURCES: List[SourceConfig] = [
    SourceConfig(
        name="UNFCCC",
        base_url="https://unfccc.int",
        rss_url="https://unfccc.int/news/feed",
        source_type="official",
        language="en",
        category="policy",
        description="협상 결과 및 NDC 갱신",
    ),
    SourceConfig(
        name="EU_Commission",
        base_url="https://ec.europa.eu",
        rss_url="https://ec.europa.eu/commission/presscorner/api/rss?topic=CLIMA",
        source_type="official",
        language="en",
        category="policy",
        description="ETS 정책 및 CBAM 업데이트",
    ),
    SourceConfig(
        name="IPCC",
        base_url="https://www.ipcc.ch",
        rss_url="https://www.ipcc.ch/feed/",
        source_type="official",
        language="en",
        category="technology",
        description="보고서 및 가이드라인",
    ),
    SourceConfig(
        name="IEA",
        base_url="https://www.iea.org",
        rss_url="https://www.iea.org/rss/news.xml",
        source_type="official",
        language="en",
        category="technology",
        description="에너지 전망 및 기술 리포트",
    ),
]

# 주요 언론
MEDIA_SOURCES: List[SourceConfig] = [
    SourceConfig(
        name="에너지경제",
        base_url="https://www.ekn.kr",
        rss_url="https://www.ekn.kr/rss/allArticle.xml",
        source_type="media",
        language="ko",
        category="market",
        description="에너지/환경 전문 언론",
    ),
    SourceConfig(
        name="전기신문",
        base_url="https://www.electimes.com",
        rss_url="https://www.electimes.com/rss/allArticle.xml",
        source_type="media",
        language="ko",
        category="technology",
        description="전력/에너지 전문 언론",
    ),
]


def create_crawler_from_config(config: SourceConfig) -> Optional[BaseCrawler]:
    """SourceConfig에서 크롤러 생성"""
    if config.rss_url:
        return RSSCrawler(
            name=config.name,
            base_url=config.base_url,
            rss_url=config.rss_url,
            source_type=config.source_type,
            language=config.language,
        )
    # list_url만 있는 경우는 WebPageCrawler 서브클래스 필요
    return None


def get_default_registry() -> CrawlerRegistry:
    """기본 크롤러 레지스트리 생성"""
    registry = CrawlerRegistry()

    all_sources = DOMESTIC_SOURCES + INTERNATIONAL_SOURCES + MEDIA_SOURCES

    for config in all_sources:
        crawler = create_crawler_from_config(config)
        if crawler:
            registry.register(crawler)

    return registry


def get_all_sources() -> List[SourceConfig]:
    """모든 소스 설정 반환"""
    return DOMESTIC_SOURCES + INTERNATIONAL_SOURCES + MEDIA_SOURCES
```

**Step 4: Update __init__.py**

```python
# src/react_agent/weekly_pipeline/__init__.py
"""Weekly Analysis Pipeline - 주간 정책/뉴스 분석 파이프라인"""

from .crawler import BaseCrawler, CrawlerRegistry, CrawledContent, RSSCrawler
from .sources import (
    SourceConfig,
    DOMESTIC_SOURCES,
    INTERNATIONAL_SOURCES,
    MEDIA_SOURCES,
    get_default_registry,
)

__all__ = [
    "BaseCrawler",
    "CrawlerRegistry",
    "CrawledContent",
    "RSSCrawler",
    "SourceConfig",
    "DOMESTIC_SOURCES",
    "INTERNATIONAL_SOURCES",
    "MEDIA_SOURCES",
    "get_default_registry",
]
```

**Step 5: Run test to verify it passes**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/weekly_pipeline/test_sources.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/react_agent/weekly_pipeline/
git commit -m "feat: add source configurations for crawling"
```

---

## Task 3: 전처리 파이프라인

**Files:**
- Create: `src/react_agent/weekly_pipeline/preprocessor.py`
- Test: `tests/weekly_pipeline/test_preprocessor.py`

**Step 1: Write the failing test**

```python
# tests/weekly_pipeline/test_preprocessor.py
"""전처리 파이프라인 테스트"""

import pytest
from datetime import datetime

from react_agent.weekly_pipeline.crawler import CrawledContent
from react_agent.weekly_pipeline.preprocessor import (
    Preprocessor,
    PreprocessedContent,
)


class TestPreprocessor:
    """Preprocessor 테스트"""

    def test_clean_html(self):
        preprocessor = Preprocessor()
        html = "<p>테스트 <b>내용</b></p><script>alert('x')</script>"
        result = preprocessor.clean_html(html)
        assert "테스트" in result
        assert "<script>" not in result
        assert "<p>" not in result

    def test_normalize_text(self):
        preprocessor = Preprocessor()
        text = "공백이   많은    텍스트\n\n\n\n여러줄"
        result = preprocessor.normalize_text(text)
        assert "  " not in result
        assert "\n\n\n" not in result

    def test_detect_language(self):
        preprocessor = Preprocessor()
        assert preprocessor.detect_language("한글 텍스트입니다") == "ko"
        assert preprocessor.detect_language("This is English text") == "en"

    def test_preprocess_content(self):
        preprocessor = Preprocessor()
        content = CrawledContent(
            title="테스트 제목",
            content="<p>테스트 내용</p>",
            url="https://example.com",
            source="test",
            published_date=datetime.now(),
        )
        result = preprocessor.preprocess(content)
        assert isinstance(result, PreprocessedContent)
        assert result.clean_content == "테스트 내용"

    def test_deduplicate(self):
        preprocessor = Preprocessor()
        contents = [
            CrawledContent(
                title="제목1",
                content="내용1",
                url="https://example.com/1",
                source="test",
                published_date=datetime.now(),
            ),
            CrawledContent(
                title="제목1",  # 중복
                content="내용1",
                url="https://example.com/2",
                source="test",
                published_date=datetime.now(),
            ),
            CrawledContent(
                title="제목2",
                content="내용2",
                url="https://example.com/3",
                source="test",
                published_date=datetime.now(),
            ),
        ]
        result = preprocessor.deduplicate(contents)
        assert len(result) == 2
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/weekly_pipeline/test_preprocessor.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/react_agent/weekly_pipeline/preprocessor.py
"""전처리 파이프라인 - HTML 정제, 정규화, 중복 제거"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Set

from bs4 import BeautifulSoup

from .crawler import CrawledContent

logger = logging.getLogger(__name__)


@dataclass
class PreprocessedContent:
    """전처리된 콘텐츠"""

    original: CrawledContent
    clean_content: str
    clean_title: str
    language: str
    word_count: int
    content_hash: str
    extracted_keywords: List[str] = field(default_factory=list)


class Preprocessor:
    """전처리기 - HTML 정제, 정규화, 중복 제거"""

    # 제거할 HTML 태그
    REMOVE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "iframe"]

    def __init__(self):
        self._seen_hashes: Set[str] = set()

    def clean_html(self, html: str) -> str:
        """HTML에서 텍스트 추출 및 정제"""
        if not html:
            return ""

        soup = BeautifulSoup(html, "html.parser")

        # 불필요한 태그 제거
        for tag in self.REMOVE_TAGS:
            for element in soup.find_all(tag):
                element.decompose()

        # 텍스트 추출
        text = soup.get_text(separator=" ", strip=True)

        return text

    def normalize_text(self, text: str) -> str:
        """텍스트 정규화"""
        if not text:
            return ""

        # 연속 공백 제거
        text = re.sub(r"[ \t]+", " ", text)

        # 연속 개행 정리 (3개 이상 -> 2개)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # 앞뒤 공백 제거
        text = text.strip()

        return text

    def detect_language(self, text: str) -> str:
        """간단한 언어 감지"""
        if not text:
            return "ko"

        # 한글 비율 계산
        korean_chars = len(re.findall(r"[가-힣]", text))
        total_chars = len(re.findall(r"[가-힣a-zA-Z]", text))

        if total_chars == 0:
            return "ko"

        korean_ratio = korean_chars / total_chars
        return "ko" if korean_ratio > 0.3 else "en"

    def compute_hash(self, text: str) -> str:
        """콘텐츠 해시 계산"""
        return hashlib.md5(text.encode()).hexdigest()

    def count_words(self, text: str) -> int:
        """단어 수 계산"""
        # 한글: 공백 기준, 영어: 공백 기준
        words = text.split()
        return len(words)

    def preprocess(self, content: CrawledContent) -> PreprocessedContent:
        """단일 콘텐츠 전처리"""
        # HTML 정제
        clean_content = self.clean_html(content.content)
        clean_content = self.normalize_text(clean_content)

        clean_title = self.normalize_text(content.title)

        # 언어 감지
        language = self.detect_language(clean_content)

        # 해시 계산
        content_hash = self.compute_hash(clean_title + clean_content)

        # 단어 수
        word_count = self.count_words(clean_content)

        return PreprocessedContent(
            original=content,
            clean_content=clean_content,
            clean_title=clean_title,
            language=language,
            word_count=word_count,
            content_hash=content_hash,
        )

    def deduplicate(
        self, contents: List[CrawledContent]
    ) -> List[CrawledContent]:
        """중복 콘텐츠 제거 (제목 + 내용 기준)"""
        seen_hashes: Set[str] = set()
        unique_contents: List[CrawledContent] = []

        for content in contents:
            content_hash = self.compute_hash(content.title + content.content)

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_contents.append(content)

        removed_count = len(contents) - len(unique_contents)
        if removed_count > 0:
            logger.info(f"중복 제거: {removed_count}개 콘텐츠 제거됨")

        return unique_contents

    def preprocess_batch(
        self, contents: List[CrawledContent]
    ) -> List[PreprocessedContent]:
        """배치 전처리 (중복 제거 포함)"""
        # 중복 제거
        unique_contents = self.deduplicate(contents)

        # 전처리
        results = []
        for content in unique_contents:
            try:
                preprocessed = self.preprocess(content)
                # 내용이 너무 짧으면 제외
                if preprocessed.word_count >= 10:
                    results.append(preprocessed)
            except Exception as e:
                logger.warning(f"전처리 오류: {e}")
                continue

        logger.info(f"전처리 완료: {len(results)}개 콘텐츠")
        return results
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/weekly_pipeline/test_preprocessor.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/react_agent/weekly_pipeline/preprocessor.py tests/weekly_pipeline/
git commit -m "feat: add preprocessor for content cleaning"
```

---

## Task 4: 규칙 기반 분류기

**Files:**
- Create: `src/react_agent/weekly_pipeline/classifier.py`
- Test: `tests/weekly_pipeline/test_classifier.py`

**Step 1: Write the failing test**

```python
# tests/weekly_pipeline/test_classifier.py
"""규칙 기반 분류기 테스트"""

import pytest

from react_agent.agents.expert_panel.config import ExpertRole
from react_agent.weekly_pipeline.classifier import (
    RuleBasedClassifier,
    ClassificationResult,
)


class TestRuleBasedClassifier:
    """RuleBasedClassifier 테스트"""

    def test_classify_policy_content(self):
        classifier = RuleBasedClassifier()
        result = classifier.classify(
            "파리협정 NDC 상향안 발표, 2050 탄소중립 목표 강화"
        )
        assert result.primary_expert == ExpertRole.POLICY_EXPERT
        assert result.confidence >= 0.5

    def test_classify_market_content(self):
        classifier = RuleBasedClassifier()
        result = classifier.classify(
            "EU ETS 가격 80유로 돌파, 거래량 증가세"
        )
        assert result.primary_expert == ExpertRole.MARKET_EXPERT

    def test_classify_technology_content(self):
        classifier = RuleBasedClassifier()
        result = classifier.classify(
            "CCUS 탄소포집 기술 상용화, 그린수소 생산 확대"
        )
        assert result.primary_expert == ExpertRole.TECHNOLOGY_EXPERT

    def test_classify_with_secondary(self):
        classifier = RuleBasedClassifier()
        result = classifier.classify(
            "EU CBAM 발효로 철강업계 배출권 수요 급증 전망"
        )
        assert result.primary_expert is not None
        # CBAM은 정책+시장 연관

    def test_needs_llm_meeting(self):
        classifier = RuleBasedClassifier()
        # 매칭률 낮은 새로운 주제
        result = classifier.classify(
            "블록체인 기반 탄소 토큰화 플랫폼 등장"
        )
        # 새로운 개념이 많으면 LLM 회의 필요
        assert isinstance(result.needs_llm_meeting, bool)
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/weekly_pipeline/test_classifier.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/react_agent/weekly_pipeline/classifier.py
"""규칙 기반 분류기 - 키워드 매칭으로 전문가 배정"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from react_agent.agents.expert_panel.config import (
    ExpertRole,
    EXPERT_REGISTRY,
    get_expert_keywords,
)

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """분류 결과"""

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
    """규칙 기반 분류기"""

    # LLM 회의 트리거 조건
    LOW_CONFIDENCE_THRESHOLD = 0.3
    MULTI_EXPERT_THRESHOLD = 3  # 3개 이상 전문가 관련 시

    def __init__(self):
        self.expert_keywords = get_expert_keywords()

    def classify(self, text: str) -> ClassificationResult:
        """텍스트 분류하여 담당 전문가 결정"""
        text_lower = text.lower()

        # 각 전문가별 점수 계산
        scores: Dict[ExpertRole, float] = {}
        matched: Dict[ExpertRole, List[str]] = {}

        for role, keywords in self.expert_keywords.items():
            score, matches = self._calculate_score(text_lower, keywords)
            scores[role] = score
            matched[role] = matches

        # 점수순 정렬
        sorted_experts = sorted(
            scores.items(), key=lambda x: x[1], reverse=True
        )

        # 1순위, 2순위 추출
        primary_expert, primary_score = sorted_experts[0]
        secondary_expert, secondary_score = (
            sorted_experts[1] if len(sorted_experts) > 1 else (None, 0.0)
        )

        # 신뢰도 계산 (1순위와 2순위 점수 차이 기반)
        if primary_score > 0:
            confidence = min(1.0, primary_score / 10)  # 정규화
            if secondary_score > 0:
                gap = (primary_score - secondary_score) / primary_score
                confidence = confidence * (0.5 + gap * 0.5)
        else:
            confidence = 0.0

        # LLM 회의 필요 여부 판단
        needs_llm = self._needs_llm_meeting(
            scores, confidence, matched
        )

        # 이유 생성
        reason = self._generate_reason(
            primary_expert, matched.get(primary_expert, [])
        )

        return ClassificationResult(
            primary_expert=primary_expert,
            primary_score=primary_score,
            secondary_expert=secondary_expert,
            secondary_score=secondary_score,
            all_scores=scores,
            matched_keywords=matched,
            confidence=confidence,
            needs_llm_meeting=needs_llm,
            reason=reason,
        )

    def _calculate_score(
        self, text: str, keywords: List[str]
    ) -> Tuple[float, List[str]]:
        """키워드 매칭 점수 계산"""
        matches = []
        score = 0.0

        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in text:
                matches.append(keyword)
                # 키워드 길이에 따른 가중치
                weight = 1.0 + (len(keyword) - 2) * 0.1
                score += weight

        return score, matches

    def _needs_llm_meeting(
        self,
        scores: Dict[ExpertRole, float],
        confidence: float,
        matched: Dict[ExpertRole, List[str]],
    ) -> bool:
        """LLM 회의 필요 여부 판단"""
        # 조건 1: 낮은 신뢰도
        if confidence < self.LOW_CONFIDENCE_THRESHOLD:
            logger.info("LLM 회의 필요: 낮은 신뢰도")
            return True

        # 조건 2: 다중 전문가 관련 (3개 이상)
        experts_with_matches = sum(
            1 for role, matches in matched.items() if len(matches) >= 2
        )
        if experts_with_matches >= self.MULTI_EXPERT_THRESHOLD:
            logger.info("LLM 회의 필요: 다중 전문가 관련")
            return True

        # 조건 3: 전체 매칭 키워드가 너무 적음
        total_matches = sum(len(m) for m in matched.values())
        if total_matches < 2:
            logger.info("LLM 회의 필요: 키워드 매칭 부족")
            return True

        return False

    def _generate_reason(
        self, expert: ExpertRole, keywords: List[str]
    ) -> str:
        """분류 이유 생성"""
        if not keywords:
            return f"{expert.value} 전문가에게 기본 배정"

        keyword_str = ", ".join(keywords[:5])
        return f"키워드 [{keyword_str}] 기반 {expert.value} 배정"

    def classify_batch(
        self, texts: List[str]
    ) -> List[ClassificationResult]:
        """배치 분류"""
        return [self.classify(text) for text in texts]
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/weekly_pipeline/test_classifier.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/react_agent/weekly_pipeline/classifier.py tests/weekly_pipeline/
git commit -m "feat: add rule-based classifier for expert assignment"
```

---

## Task 5: LLM 회의 엔진

**Files:**
- Create: `src/react_agent/weekly_pipeline/expert_meeting.py`
- Test: `tests/weekly_pipeline/test_expert_meeting.py`

**Step 1: Write the failing test**

```python
# tests/weekly_pipeline/test_expert_meeting.py
"""LLM 회의 엔진 테스트"""

import pytest

from react_agent.agents.expert_panel.config import ExpertRole
from react_agent.weekly_pipeline.expert_meeting import (
    ExpertMeeting,
    MeetingResult,
    NewExpertProposal,
)


class TestExpertMeeting:
    """ExpertMeeting 테스트"""

    def test_meeting_result_structure(self):
        result = MeetingResult(
            assigned_experts=[ExpertRole.POLICY_EXPERT],
            new_expert_proposals=[],
            reasoning="정책 관련 콘텐츠",
            consensus_score=0.9,
        )
        assert len(result.assigned_experts) == 1
        assert result.consensus_score == 0.9

    def test_new_expert_proposal_structure(self):
        proposal = NewExpertProposal(
            suggested_role="trade_expert",
            suggested_name="Dr. 정통상",
            expertise=["WTO", "CBAM", "통상분쟁"],
            keywords=["무역", "통상", "관세"],
            reason="CBAM 무역 분쟁 관련 전문성 필요",
        )
        assert proposal.suggested_role == "trade_expert"
        assert "WTO" in proposal.expertise

    @pytest.mark.asyncio
    async def test_expert_meeting_init(self):
        meeting = ExpertMeeting()
        assert meeting is not None
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/weekly_pipeline/test_expert_meeting.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/react_agent/weekly_pipeline/expert_meeting.py
"""LLM 회의 엔진 - 전문가 협의 및 신규 전문가 제안"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from react_agent.agents.expert_panel.config import (
    ExpertRole,
    EXPERT_REGISTRY,
    ExpertConfig,
)

logger = logging.getLogger(__name__)


@dataclass
class NewExpertProposal:
    """신규 전문가 제안"""

    suggested_role: str
    suggested_name: str
    expertise: List[str]
    keywords: List[str]
    reason: str


@dataclass
class MeetingResult:
    """회의 결과"""

    assigned_experts: List[ExpertRole]
    new_expert_proposals: List[NewExpertProposal]
    reasoning: str
    consensus_score: float
    raw_response: str = ""


MEETING_SYSTEM_PROMPT = """당신은 온실가스 감축 정책 분석 전문가 패널의 회의 진행자입니다.

현재 패널 구성:
{expert_list}

## 역할
주어진 콘텐츠를 분석하여:
1. 가장 적합한 담당 전문가 선정 (1-2명)
2. 기존 전문가로 다룰 수 없는 분야가 있다면 신규 전문가 제안

## 응답 형식 (JSON)
```json
{{
    "assigned_experts": ["policy_expert", "market_expert"],
    "new_expert_proposals": [
        {{
            "suggested_role": "trade_expert",
            "suggested_name": "Dr. 정통상",
            "expertise": ["WTO", "CBAM", "통상분쟁", "관세"],
            "keywords": ["무역", "통상", "관세", "WTO", "분쟁", "보호무역"],
            "reason": "CBAM 등 탄소국경조정 관련 무역/통상 전문성 필요"
        }}
    ],
    "reasoning": "이 콘텐츠는 ... 관련이므로 ...",
    "consensus_score": 0.85
}}
```

consensus_score는 0.0-1.0 사이 값으로, 전문가 배정에 대한 확신도를 나타냅니다.
신규 전문가가 필요 없으면 new_expert_proposals는 빈 배열로 두세요.
"""


class ExpertMeeting:
    """LLM 기반 전문가 회의 엔진"""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.llm = ChatAnthropic(
            model=model,
            temperature=0.3,
        )

    def _get_expert_list(self) -> str:
        """현재 전문가 목록 문자열 생성"""
        lines = []
        for role, config in EXPERT_REGISTRY.items():
            expertise_str = ", ".join(config.expertise[:5])
            lines.append(
                f"- {role.value} ({config.name}): {expertise_str}"
            )
        return "\n".join(lines)

    async def conduct_meeting(
        self,
        content: str,
        title: str = "",
        source: str = "",
    ) -> MeetingResult:
        """전문가 회의 진행"""

        expert_list = self._get_expert_list()
        system_prompt = MEETING_SYSTEM_PROMPT.format(expert_list=expert_list)

        user_message = f"""다음 콘텐츠에 대해 전문가 배정을 결정해주세요.

**제목**: {title}
**출처**: {source}
**내용**:
{content[:2000]}
"""

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message),
            ])

            raw_response = response.content
            result = self._parse_response(raw_response)
            result.raw_response = raw_response

            logger.info(
                f"[Expert Meeting] 완료: {result.assigned_experts}, "
                f"신규 제안: {len(result.new_expert_proposals)}개"
            )

            return result

        except Exception as e:
            logger.error(f"[Expert Meeting] 오류: {e}")
            # 기본 결과 반환
            return MeetingResult(
                assigned_experts=[ExpertRole.POLICY_EXPERT],
                new_expert_proposals=[],
                reasoning=f"회의 오류로 기본 전문가 배정: {e}",
                consensus_score=0.0,
            )

    def _parse_response(self, response: str) -> MeetingResult:
        """LLM 응답 파싱"""
        try:
            # JSON 추출
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
            else:
                raise ValueError("JSON not found in response")

            # assigned_experts 파싱
            assigned_experts = []
            for expert_str in data.get("assigned_experts", []):
                try:
                    role = ExpertRole(expert_str)
                    assigned_experts.append(role)
                except ValueError:
                    logger.warning(f"알 수 없는 전문가 역할: {expert_str}")

            # 기본값 설정
            if not assigned_experts:
                assigned_experts = [ExpertRole.POLICY_EXPERT]

            # new_expert_proposals 파싱
            new_proposals = []
            for proposal_data in data.get("new_expert_proposals", []):
                proposal = NewExpertProposal(
                    suggested_role=proposal_data.get("suggested_role", ""),
                    suggested_name=proposal_data.get("suggested_name", ""),
                    expertise=proposal_data.get("expertise", []),
                    keywords=proposal_data.get("keywords", []),
                    reason=proposal_data.get("reason", ""),
                )
                new_proposals.append(proposal)

            return MeetingResult(
                assigned_experts=assigned_experts,
                new_expert_proposals=new_proposals,
                reasoning=data.get("reasoning", ""),
                consensus_score=float(data.get("consensus_score", 0.5)),
            )

        except Exception as e:
            logger.error(f"응답 파싱 오류: {e}")
            return MeetingResult(
                assigned_experts=[ExpertRole.POLICY_EXPERT],
                new_expert_proposals=[],
                reasoning=f"파싱 오류: {e}",
                consensus_score=0.0,
            )
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/weekly_pipeline/test_expert_meeting.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/react_agent/weekly_pipeline/expert_meeting.py tests/weekly_pipeline/
git commit -m "feat: add LLM expert meeting engine"
```

---

## Task 6: 동적 전문가 생성

**Files:**
- Modify: `src/react_agent/agents/expert_panel/config.py`
- Create: `src/react_agent/weekly_pipeline/expert_generator.py`
- Test: `tests/weekly_pipeline/test_expert_generator.py`

**Step 1: Write the failing test**

```python
# tests/weekly_pipeline/test_expert_generator.py
"""동적 전문가 생성 테스트"""

import pytest

from react_agent.agents.expert_panel.config import ExpertRole, EXPERT_REGISTRY
from react_agent.weekly_pipeline.expert_meeting import NewExpertProposal
from react_agent.weekly_pipeline.expert_generator import (
    ExpertGenerator,
    register_dynamic_expert,
    get_dynamic_experts,
)


class TestExpertGenerator:
    """ExpertGenerator 테스트"""

    def test_generate_expert_from_proposal(self):
        generator = ExpertGenerator()
        proposal = NewExpertProposal(
            suggested_role="trade_expert",
            suggested_name="Dr. 정통상",
            expertise=["WTO", "CBAM", "통상분쟁"],
            keywords=["무역", "통상", "관세"],
            reason="통상 전문성 필요",
        )
        expert_config = generator.generate_from_proposal(proposal)

        assert expert_config is not None
        assert expert_config.name == "Dr. 정통상"
        assert "WTO" in expert_config.expertise

    def test_register_dynamic_expert(self):
        proposal = NewExpertProposal(
            suggested_role="finance_expert",
            suggested_name="Dr. 박금융",
            expertise=["탄소금융", "녹색채권"],
            keywords=["금융", "채권", "투자"],
            reason="탄소금융 전문성 필요",
        )

        result = register_dynamic_expert(proposal)
        assert result is True

        # 등록 확인
        dynamic = get_dynamic_experts()
        assert any(e.name == "Dr. 박금융" for e in dynamic)
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/weekly_pipeline/test_expert_generator.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/react_agent/weekly_pipeline/expert_generator.py
"""동적 전문가 생성기 - 신규 전문가 프로필 생성 및 등록"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from react_agent.agents.expert_panel.config import ExpertConfig, ExpertRole
from .expert_meeting import NewExpertProposal

logger = logging.getLogger(__name__)

# 동적으로 생성된 전문가 저장소
_DYNAMIC_EXPERTS: Dict[str, ExpertConfig] = {}


@dataclass
class DynamicExpertRole:
    """동적 전문가 역할 (Enum 대신 사용)"""
    value: str

    def __str__(self):
        return self.value

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        if isinstance(other, DynamicExpertRole):
            return self.value == other.value
        if isinstance(other, ExpertRole):
            return self.value == other.value
        return False


class ExpertGenerator:
    """동적 전문가 생성기"""

    # 기본 페르소나 템플릿
    PERSONA_TEMPLATE = """당신은 {domain} 분야의 박사급 전문가입니다.
{expertise_summary}에 대한 깊은 이해를 보유하고 있습니다.
해당 분야의 최신 동향과 실무 경험을 바탕으로 전문적인 분석을 제공합니다."""

    # 기본 도구
    DEFAULT_TOOLS = ["tavily_search", "web_browser"]

    def generate_from_proposal(
        self, proposal: NewExpertProposal
    ) -> Optional[ExpertConfig]:
        """제안서에서 전문가 설정 생성"""

        if not proposal.suggested_role or not proposal.suggested_name:
            logger.warning("제안서에 필수 정보 누락")
            return None

        # 도메인 추론
        domain = self._infer_domain(proposal.expertise)

        # 전문분야 요약
        expertise_summary = ", ".join(proposal.expertise[:5])

        # 페르소나 생성
        persona = self.PERSONA_TEMPLATE.format(
            domain=domain,
            expertise_summary=expertise_summary,
        )

        # 설명 생성
        description = f"{domain} 분야 전문가 ({proposal.reason})"

        # DynamicExpertRole 생성
        role = DynamicExpertRole(value=proposal.suggested_role)

        config = ExpertConfig(
            role=role,  # type: ignore
            name=proposal.suggested_name,
            persona=persona,
            description=description,
            expertise=proposal.expertise,
            tools=self.DEFAULT_TOOLS.copy(),
            keywords=proposal.keywords,
        )

        logger.info(f"새 전문가 생성: {config.name} ({proposal.suggested_role})")

        return config

    def _infer_domain(self, expertise: List[str]) -> str:
        """전문분야에서 도메인 추론"""
        if not expertise:
            return "탄소정책"

        # 키워드 기반 도메인 매핑
        domain_keywords = {
            "통상": ["WTO", "CBAM", "무역", "관세", "통상"],
            "금융": ["금융", "채권", "투자", "펀드", "ESG"],
            "에너지": ["에너지", "전력", "발전", "원자력"],
            "산업": ["철강", "시멘트", "석유화학", "제조"],
            "농업": ["농업", "산림", "토지이용", "LULUCF"],
            "해운": ["해운", "항공", "운송", "물류"],
        }

        for domain, keywords in domain_keywords.items():
            for exp in expertise:
                if any(kw in exp for kw in keywords):
                    return domain

        return expertise[0] if expertise else "탄소정책"


def register_dynamic_expert(proposal: NewExpertProposal) -> bool:
    """동적 전문가 등록"""
    generator = ExpertGenerator()
    config = generator.generate_from_proposal(proposal)

    if config is None:
        return False

    role_key = proposal.suggested_role
    _DYNAMIC_EXPERTS[role_key] = config

    logger.info(f"동적 전문가 등록 완료: {role_key}")
    return True


def get_dynamic_experts() -> List[ExpertConfig]:
    """등록된 동적 전문가 목록 반환"""
    return list(_DYNAMIC_EXPERTS.values())


def get_dynamic_expert(role: str) -> Optional[ExpertConfig]:
    """역할로 동적 전문가 조회"""
    return _DYNAMIC_EXPERTS.get(role)


def clear_dynamic_experts() -> None:
    """동적 전문가 초기화 (테스트용)"""
    _DYNAMIC_EXPERTS.clear()
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/weekly_pipeline/test_expert_generator.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/react_agent/weekly_pipeline/expert_generator.py tests/weekly_pipeline/
git commit -m "feat: add dynamic expert generator"
```

---

## Task 7: 청크 메타데이터 강화

**Files:**
- Modify: `src/react_agent/rag/chunking.py`
- Test: `tests/rag/test_chunking_enhanced.py`

**Step 1: Write the failing test**

```python
# tests/rag/test_chunking_enhanced.py
"""청크 메타데이터 강화 테스트"""

import pytest
from datetime import datetime

from react_agent.rag.chunking import (
    ChunkMetadata,
    EnhancedChunkMetadata,
    Chunk,
    SemanticChunker,
)


class TestEnhancedChunkMetadata:
    """EnhancedChunkMetadata 테스트"""

    def test_enhanced_metadata_fields(self):
        metadata = EnhancedChunkMetadata(
            doc_id="doc-001",
            chunk_id="chunk-001",
            source="환경부",
            date_collected="2026-02-11",
            analyzed_by=["policy_expert"],
            confidence_score=0.92,
            related_chunks=["chunk-002"],
        )
        assert metadata.date_collected == "2026-02-11"
        assert "policy_expert" in metadata.analyzed_by
        assert metadata.confidence_score == 0.92

    def test_metadata_to_dict(self):
        metadata = EnhancedChunkMetadata(
            doc_id="doc-001",
            chunk_id="chunk-001",
            source="UNFCCC",
            date_collected="2026-02-11",
            analyzed_by=["policy_expert", "market_expert"],
            confidence_score=0.85,
        )
        d = metadata.to_dict()
        assert d["date_collected"] == "2026-02-11"
        assert d["analyzed_by"] == ["policy_expert", "market_expert"]
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/rag/test_chunking_enhanced.py -v`
Expected: FAIL

**Step 3: Modify chunking.py to add EnhancedChunkMetadata**

Add to `src/react_agent/rag/chunking.py`:

```python
# 기존 ChunkMetadata 아래에 추가

@dataclass
class EnhancedChunkMetadata(ChunkMetadata):
    """확장된 청크 메타데이터 (주간 분석용)

    Attributes:
        date_collected: 수집 일자 (YYYY-MM-DD)
        analyzed_by: 분석한 전문가 역할 목록
        confidence_score: 분석 신뢰도 (0.0-1.0)
        related_chunks: 연관 청크 ID 목록
        analysis_notes: 분석 노트
    """
    date_collected: str = ""
    analyzed_by: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    related_chunks: List[str] = field(default_factory=list)
    analysis_notes: str = ""

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "doc_id": self.doc_id,
            "chunk_id": self.chunk_id,
            "source": self.source,
            "document_type": self.document_type,
            "region": self.region,
            "topic": self.topic,
            "language": self.language,
            "expert_domain": self.expert_domain,
            "keywords": self.keywords,
            "date_collected": self.date_collected,
            "analyzed_by": self.analyzed_by,
            "confidence_score": self.confidence_score,
            "related_chunks": self.related_chunks,
            "analysis_notes": self.analysis_notes,
        }
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/rag/test_chunking_enhanced.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/react_agent/rag/chunking.py tests/rag/
git commit -m "feat: add enhanced chunk metadata for weekly analysis"
```

---

## Task 8: 지식베이스 저장소

**Files:**
- Create: `src/react_agent/rag/knowledge_base.py`
- Test: `tests/rag/test_knowledge_base.py`

**Step 1: Write the failing test**

```python
# tests/rag/test_knowledge_base.py
"""지식베이스 저장소 테스트"""

import pytest
import tempfile
import shutil
from pathlib import Path

from react_agent.rag.chunking import Chunk, EnhancedChunkMetadata
from react_agent.rag.knowledge_base import (
    KnowledgeBase,
    KnowledgeBaseConfig,
)


class TestKnowledgeBase:
    """KnowledgeBase 테스트"""

    @pytest.fixture
    def temp_dir(self):
        """임시 디렉토리"""
        path = tempfile.mkdtemp()
        yield path
        shutil.rmtree(path)

    def test_add_and_get_chunk(self, temp_dir):
        config = KnowledgeBaseConfig(persist_directory=temp_dir)
        kb = KnowledgeBase(config)

        metadata = EnhancedChunkMetadata(
            doc_id="doc-001",
            chunk_id="chunk-001",
            source="test",
            date_collected="2026-02-11",
        )
        chunk = Chunk(content="테스트 청크 내용입니다.", metadata=metadata)

        kb.add_chunk(chunk)

        result = kb.get_chunk("chunk-001")
        assert result is not None
        assert result.content == "테스트 청크 내용입니다."

    def test_search_chunks(self, temp_dir):
        config = KnowledgeBaseConfig(persist_directory=temp_dir)
        kb = KnowledgeBase(config)

        # 여러 청크 추가
        for i in range(3):
            metadata = EnhancedChunkMetadata(
                doc_id=f"doc-{i}",
                chunk_id=f"chunk-{i}",
                source="test",
            )
            chunk = Chunk(
                content=f"탄소배출권 거래에 관한 내용 {i}",
                metadata=metadata,
            )
            kb.add_chunk(chunk)

        results = kb.search("탄소배출권", top_k=2)
        assert len(results) <= 2

    def test_get_chunks_by_source(self, temp_dir):
        config = KnowledgeBaseConfig(persist_directory=temp_dir)
        kb = KnowledgeBase(config)

        # 소스별 청크 추가
        for source in ["환경부", "환경부", "UNFCCC"]:
            metadata = EnhancedChunkMetadata(
                doc_id=f"doc-{source}",
                chunk_id=f"chunk-{source}-{id(source)}",
                source=source,
            )
            chunk = Chunk(content=f"{source} 발표 내용", metadata=metadata)
            kb.add_chunk(chunk)

        results = kb.get_chunks_by_source("환경부")
        assert len(results) == 2
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/rag/test_knowledge_base.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/react_agent/rag/knowledge_base.py
"""지식베이스 저장소 - ChromaDB 기반 청크 저장/검색"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import chromadb
from chromadb.config import Settings

from .chunking import Chunk, ChunkMetadata, EnhancedChunkMetadata

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeBaseConfig:
    """지식베이스 설정"""

    persist_directory: str = "./data/knowledge_base"
    collection_name: str = "weekly_analysis"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class KnowledgeBase:
    """ChromaDB 기반 지식베이스"""

    def __init__(self, config: Optional[KnowledgeBaseConfig] = None):
        self.config = config or KnowledgeBaseConfig()

        # 디렉토리 생성
        Path(self.config.persist_directory).mkdir(parents=True, exist_ok=True)

        # ChromaDB 클라이언트 초기화
        self._client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=self.config.persist_directory,
            anonymized_telemetry=False,
        ))

        # 컬렉션 가져오기 또는 생성
        self._collection = self._client.get_or_create_collection(
            name=self.config.collection_name,
            metadata={"description": "Weekly analysis chunks"},
        )

        # 메모리 캐시 (빠른 조회용)
        self._cache: Dict[str, Chunk] = {}

        logger.info(
            f"KnowledgeBase 초기화: {self.config.persist_directory}, "
            f"컬렉션: {self.config.collection_name}"
        )

    def add_chunk(self, chunk: Chunk) -> None:
        """청크 추가"""
        chunk_id = chunk.metadata.chunk_id

        # 메타데이터 준비
        metadata_dict = self._prepare_metadata(chunk.metadata)

        # ChromaDB에 추가
        self._collection.add(
            ids=[chunk_id],
            documents=[chunk.content],
            metadatas=[metadata_dict],
        )

        # 캐시에 추가
        self._cache[chunk_id] = chunk

        logger.debug(f"청크 추가: {chunk_id}")

    def add_chunks(self, chunks: List[Chunk]) -> int:
        """청크 배치 추가"""
        if not chunks:
            return 0

        ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            ids.append(chunk.metadata.chunk_id)
            documents.append(chunk.content)
            metadatas.append(self._prepare_metadata(chunk.metadata))
            self._cache[chunk.metadata.chunk_id] = chunk

        self._collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        logger.info(f"{len(chunks)}개 청크 추가 완료")
        return len(chunks)

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """청크 조회"""
        # 캐시 확인
        if chunk_id in self._cache:
            return self._cache[chunk_id]

        # ChromaDB에서 조회
        result = self._collection.get(ids=[chunk_id])

        if not result["ids"]:
            return None

        # Chunk 재구성
        chunk = self._reconstruct_chunk(
            result["documents"][0],
            result["metadatas"][0],
        )

        # 캐시에 저장
        self._cache[chunk_id] = chunk

        return chunk

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None,
    ) -> List[Chunk]:
        """쿼리로 청크 검색"""
        where = filter_metadata if filter_metadata else None

        results = self._collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where,
        )

        chunks = []
        for doc, meta in zip(
            results["documents"][0],
            results["metadatas"][0],
        ):
            chunk = self._reconstruct_chunk(doc, meta)
            chunks.append(chunk)

        return chunks

    def get_chunks_by_source(self, source: str) -> List[Chunk]:
        """소스별 청크 조회"""
        results = self._collection.get(
            where={"source": source},
        )

        chunks = []
        for doc, meta in zip(results["documents"], results["metadatas"]):
            chunk = self._reconstruct_chunk(doc, meta)
            chunks.append(chunk)

        return chunks

    def get_chunks_by_date(self, date: str) -> List[Chunk]:
        """날짜별 청크 조회"""
        results = self._collection.get(
            where={"date_collected": date},
        )

        chunks = []
        for doc, meta in zip(results["documents"], results["metadatas"]):
            chunk = self._reconstruct_chunk(doc, meta)
            chunks.append(chunk)

        return chunks

    def get_stats(self) -> Dict:
        """통계 정보 반환"""
        count = self._collection.count()
        return {
            "total_chunks": count,
            "collection_name": self.config.collection_name,
            "persist_directory": self.config.persist_directory,
        }

    def _prepare_metadata(self, metadata: ChunkMetadata) -> Dict:
        """메타데이터를 ChromaDB용으로 변환"""
        base = {
            "doc_id": metadata.doc_id,
            "chunk_id": metadata.chunk_id,
            "source": metadata.source,
            "document_type": metadata.document_type,
            "region": metadata.region,
            "topic": metadata.topic,
            "language": metadata.language,
        }

        # EnhancedChunkMetadata인 경우 추가 필드
        if isinstance(metadata, EnhancedChunkMetadata):
            base["date_collected"] = metadata.date_collected
            base["confidence_score"] = metadata.confidence_score
            base["analysis_notes"] = metadata.analysis_notes
            # 리스트는 문자열로 변환
            base["analyzed_by"] = ",".join(metadata.analyzed_by)
            base["expert_domain"] = ",".join(metadata.expert_domain)
            base["keywords"] = ",".join(metadata.keywords)
            base["related_chunks"] = ",".join(metadata.related_chunks)
        else:
            base["expert_domain"] = ",".join(metadata.expert_domain)
            base["keywords"] = ",".join(metadata.keywords)

        return base

    def _reconstruct_chunk(self, content: str, metadata: Dict) -> Chunk:
        """저장된 데이터에서 Chunk 재구성"""
        # 리스트 필드 복원
        expert_domain = metadata.get("expert_domain", "").split(",")
        keywords = metadata.get("keywords", "").split(",")
        analyzed_by = metadata.get("analyzed_by", "").split(",")
        related_chunks = metadata.get("related_chunks", "").split(",")

        # 빈 문자열 필터
        expert_domain = [e for e in expert_domain if e]
        keywords = [k for k in keywords if k]
        analyzed_by = [a for a in analyzed_by if a]
        related_chunks = [r for r in related_chunks if r]

        if "date_collected" in metadata:
            chunk_metadata = EnhancedChunkMetadata(
                doc_id=metadata.get("doc_id", ""),
                chunk_id=metadata.get("chunk_id", ""),
                source=metadata.get("source", ""),
                document_type=metadata.get("document_type", ""),
                region=metadata.get("region", ""),
                topic=metadata.get("topic", ""),
                language=metadata.get("language", "ko"),
                expert_domain=expert_domain,
                keywords=keywords,
                date_collected=metadata.get("date_collected", ""),
                analyzed_by=analyzed_by,
                confidence_score=float(metadata.get("confidence_score", 0.0)),
                related_chunks=related_chunks,
                analysis_notes=metadata.get("analysis_notes", ""),
            )
        else:
            chunk_metadata = ChunkMetadata(
                doc_id=metadata.get("doc_id", ""),
                chunk_id=metadata.get("chunk_id", ""),
                source=metadata.get("source", ""),
                document_type=metadata.get("document_type", ""),
                region=metadata.get("region", ""),
                topic=metadata.get("topic", ""),
                language=metadata.get("language", "ko"),
                expert_domain=expert_domain,
                keywords=keywords,
            )

        return Chunk(content=content, metadata=chunk_metadata)
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/rag/test_knowledge_base.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/react_agent/rag/knowledge_base.py tests/rag/
git commit -m "feat: add ChromaDB-based knowledge base"
```

---

## Task 9: 전문가 분석 러너

**Files:**
- Create: `src/react_agent/weekly_pipeline/analyzer.py`
- Test: `tests/weekly_pipeline/test_analyzer.py`

**Step 1: Write the failing test**

```python
# tests/weekly_pipeline/test_analyzer.py
"""전문가 분석 러너 테스트"""

import pytest
from datetime import datetime

from react_agent.agents.expert_panel.config import ExpertRole
from react_agent.weekly_pipeline.preprocessor import PreprocessedContent
from react_agent.weekly_pipeline.crawler import CrawledContent
from react_agent.weekly_pipeline.analyzer import (
    ExpertAnalyzer,
    AnalysisResult,
)


class TestExpertAnalyzer:
    """ExpertAnalyzer 테스트"""

    def test_analysis_result_structure(self):
        result = AnalysisResult(
            expert_role=ExpertRole.POLICY_EXPERT,
            content_id="doc-001",
            summary="정책 분석 요약",
            key_findings=["발견1", "발견2"],
            implications=["시사점1"],
            confidence=0.85,
        )
        assert result.expert_role == ExpertRole.POLICY_EXPERT
        assert len(result.key_findings) == 2

    @pytest.mark.asyncio
    async def test_analyzer_init(self):
        analyzer = ExpertAnalyzer()
        assert analyzer is not None
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/weekly_pipeline/test_analyzer.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/react_agent/weekly_pipeline/analyzer.py
"""전문가 분석 러너 - 병렬 분석 실행"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from react_agent.agents.expert_panel.config import (
    ExpertRole,
    EXPERT_REGISTRY,
    ExpertConfig,
)
from react_agent.agents.expert_panel.prompts import get_expert_prompt
from .preprocessor import PreprocessedContent
from .classifier import ClassificationResult

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """분석 결과"""

    expert_role: ExpertRole
    content_id: str
    summary: str
    key_findings: List[str]
    implications: List[str]
    confidence: float
    raw_response: str = ""
    error: Optional[str] = None


ANALYSIS_PROMPT = """다음 콘텐츠를 분석하고 주요 내용을 정리해주세요.

**제목**: {title}
**출처**: {source}
**내용**:
{content}

## 분석 요청
1. 핵심 내용 요약 (2-3문장)
2. 주요 발견 사항 (3-5개 bullet points)
3. 시사점 및 영향 (2-3개 bullet points)

## 응답 형식
### 요약
[요약 내용]

### 주요 발견
- 발견1
- 발견2
- ...

### 시사점
- 시사점1
- 시사점2
- ...
"""


class ExpertAnalyzer:
    """전문가 분석 러너"""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.llm = ChatAnthropic(
            model=model,
            temperature=0.3,
        )

    async def analyze(
        self,
        content: PreprocessedContent,
        expert_role: ExpertRole,
    ) -> AnalysisResult:
        """단일 콘텐츠 분석"""
        expert_config = EXPERT_REGISTRY.get(expert_role)

        if not expert_config:
            return AnalysisResult(
                expert_role=expert_role,
                content_id=content.original.url,
                summary="",
                key_findings=[],
                implications=[],
                confidence=0.0,
                error="전문가 설정을 찾을 수 없음",
            )

        # 시스템 프롬프트 (전문가 페르소나)
        system_prompt = expert_config.persona

        # 분석 프롬프트
        user_prompt = ANALYSIS_PROMPT.format(
            title=content.clean_title,
            source=content.original.source,
            content=content.clean_content[:3000],  # 토큰 제한
        )

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ])

            raw_response = response.content
            result = self._parse_analysis(raw_response, expert_role, content)
            result.raw_response = raw_response

            logger.info(
                f"[{expert_config.name}] 분석 완료: {content.clean_title[:30]}..."
            )

            return result

        except Exception as e:
            logger.error(f"분석 오류: {e}")
            return AnalysisResult(
                expert_role=expert_role,
                content_id=content.original.url,
                summary="",
                key_findings=[],
                implications=[],
                confidence=0.0,
                error=str(e),
            )

    async def analyze_batch(
        self,
        contents: List[PreprocessedContent],
        classifications: List[ClassificationResult],
    ) -> List[AnalysisResult]:
        """배치 분석 (병렬 실행)"""
        tasks = []

        for content, classification in zip(contents, classifications):
            task = self.analyze(content, classification.primary_expert)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 예외 처리
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"분석 실패: {result}")
                processed_results.append(AnalysisResult(
                    expert_role=classifications[i].primary_expert,
                    content_id=contents[i].original.url,
                    summary="",
                    key_findings=[],
                    implications=[],
                    confidence=0.0,
                    error=str(result),
                ))
            else:
                processed_results.append(result)

        logger.info(f"배치 분석 완료: {len(processed_results)}개")
        return processed_results

    def _parse_analysis(
        self,
        response: str,
        expert_role: ExpertRole,
        content: PreprocessedContent,
    ) -> AnalysisResult:
        """분석 응답 파싱"""
        summary = ""
        key_findings = []
        implications = []

        lines = response.split("\n")
        current_section = None

        for line in lines:
            line = line.strip()

            if "### 요약" in line or "## 요약" in line:
                current_section = "summary"
            elif "### 주요 발견" in line or "## 주요 발견" in line:
                current_section = "findings"
            elif "### 시사점" in line or "## 시사점" in line:
                current_section = "implications"
            elif line.startswith("- ") or line.startswith("* "):
                bullet = line[2:].strip()
                if current_section == "findings":
                    key_findings.append(bullet)
                elif current_section == "implications":
                    implications.append(bullet)
            elif current_section == "summary" and line:
                summary += line + " "

        return AnalysisResult(
            expert_role=expert_role,
            content_id=content.original.url,
            summary=summary.strip(),
            key_findings=key_findings,
            implications=implications,
            confidence=0.8 if key_findings else 0.5,
        )
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/weekly_pipeline/test_analyzer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/react_agent/weekly_pipeline/analyzer.py tests/weekly_pipeline/
git commit -m "feat: add expert analyzer for parallel analysis"
```

---

## Task 10: 주간 브리핑 생성기

**Files:**
- Create: `src/react_agent/weekly_pipeline/report_generator.py`
- Test: `tests/weekly_pipeline/test_report_generator.py`

**Step 1: Write the failing test**

```python
# tests/weekly_pipeline/test_report_generator.py
"""주간 브리핑 생성기 테스트"""

import pytest
from datetime import datetime, timedelta

from react_agent.agents.expert_panel.config import ExpertRole
from react_agent.weekly_pipeline.analyzer import AnalysisResult
from react_agent.weekly_pipeline.report_generator import (
    ReportGenerator,
    WeeklyReport,
)


class TestReportGenerator:
    """ReportGenerator 테스트"""

    def test_weekly_report_structure(self):
        report = WeeklyReport(
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            total_crawled=50,
            total_analyzed=48,
            new_chunks=120,
            new_experts=[],
            expert_sections={},
        )
        assert report.total_crawled == 50
        assert report.total_analyzed == 48

    def test_generate_markdown(self):
        generator = ReportGenerator()

        results = [
            AnalysisResult(
                expert_role=ExpertRole.POLICY_EXPERT,
                content_id="test-001",
                summary="정책 요약",
                key_findings=["발견1", "발견2"],
                implications=["시사점1"],
                confidence=0.85,
            ),
        ]

        report = generator.generate_report(
            analysis_results=results,
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
        )

        markdown = generator.to_markdown(report)
        assert "주간 탄소정책 브리핑" in markdown
        assert "정책 요약" in markdown
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/weekly_pipeline/test_report_generator.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/react_agent/weekly_pipeline/report_generator.py
"""주간 브리핑 생성기 - 마크다운 리포트 생성"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from react_agent.agents.expert_panel.config import ExpertRole, EXPERT_REGISTRY
from .analyzer import AnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class ExpertSection:
    """전문가별 섹션"""

    expert_role: ExpertRole
    expert_name: str
    summaries: List[str]
    key_findings: List[str]
    implications: List[str]
    content_count: int


@dataclass
class WeeklyReport:
    """주간 리포트"""

    start_date: datetime
    end_date: datetime
    total_crawled: int
    total_analyzed: int
    new_chunks: int
    new_experts: List[str]
    expert_sections: Dict[ExpertRole, ExpertSection]
    cross_analysis: str = ""
    generated_at: datetime = field(default_factory=datetime.now)


class ReportGenerator:
    """주간 브리핑 생성기"""

    REPORT_TEMPLATE = """# 주간 탄소정책 브리핑 ({start_date} ~ {end_date})

## 📊 요약 대시보드

| 항목 | 수치 |
|------|------|
| 수집 콘텐츠 | {total_crawled}건 |
| 분석 완료 | {total_analyzed}건 ({analysis_rate}%) |
| 신규 청크 | {new_chunks}개 |
| 신규 전문가 | {new_expert_count}명 |

---

{expert_sections}

---

## 🔗 상호 연관 분석

{cross_analysis}

---

## 📁 지식베이스 업데이트 요약

{chunk_summary}

---

*생성일시: {generated_at}*
"""

    EXPERT_SECTION_TEMPLATE = """## {icon} {expert_name} 분석

### 주요 발견
{findings}

### 시사점
{implications}

"""

    EXPERT_ICONS = {
        ExpertRole.POLICY_EXPERT: "🏛️",
        ExpertRole.CARBON_CREDIT_EXPERT: "📜",
        ExpertRole.MARKET_EXPERT: "💹",
        ExpertRole.TECHNOLOGY_EXPERT: "⚡",
        ExpertRole.MRV_EXPERT: "📋",
    }

    def __init__(self, output_dir: str = "./data/weekly_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        analysis_results: List[AnalysisResult],
        start_date: datetime,
        end_date: datetime,
        total_crawled: int = 0,
        new_chunks: int = 0,
        new_experts: Optional[List[str]] = None,
    ) -> WeeklyReport:
        """분석 결과에서 리포트 생성"""

        # 전문가별 섹션 생성
        expert_sections: Dict[ExpertRole, ExpertSection] = {}

        for result in analysis_results:
            role = result.expert_role

            if role not in expert_sections:
                expert_config = EXPERT_REGISTRY.get(role)
                expert_sections[role] = ExpertSection(
                    expert_role=role,
                    expert_name=expert_config.name if expert_config else str(role),
                    summaries=[],
                    key_findings=[],
                    implications=[],
                    content_count=0,
                )

            section = expert_sections[role]
            section.content_count += 1

            if result.summary:
                section.summaries.append(result.summary)
            section.key_findings.extend(result.key_findings)
            section.implications.extend(result.implications)

        # 상호 연관 분석 생성
        cross_analysis = self._generate_cross_analysis(expert_sections)

        return WeeklyReport(
            start_date=start_date,
            end_date=end_date,
            total_crawled=total_crawled or len(analysis_results),
            total_analyzed=len([r for r in analysis_results if not r.error]),
            new_chunks=new_chunks,
            new_experts=new_experts or [],
            expert_sections=expert_sections,
            cross_analysis=cross_analysis,
        )

    def to_markdown(self, report: WeeklyReport) -> str:
        """리포트를 마크다운으로 변환"""

        # 전문가 섹션 생성
        expert_sections_md = ""
        for role, section in report.expert_sections.items():
            icon = self.EXPERT_ICONS.get(role, "📌")

            findings = "\n".join(f"- {f}" for f in section.key_findings[:10])
            implications = "\n".join(f"- {i}" for i in section.implications[:5])

            expert_sections_md += self.EXPERT_SECTION_TEMPLATE.format(
                icon=icon,
                expert_name=section.expert_name,
                findings=findings or "- 분석된 발견 사항 없음",
                implications=implications or "- 도출된 시사점 없음",
            )

        # 청크 요약
        chunk_summary = self._generate_chunk_summary(report.expert_sections)

        # 분석률 계산
        analysis_rate = (
            round(report.total_analyzed / report.total_crawled * 100)
            if report.total_crawled > 0 else 0
        )

        return self.REPORT_TEMPLATE.format(
            start_date=report.start_date.strftime("%Y-%m-%d"),
            end_date=report.end_date.strftime("%Y-%m-%d"),
            total_crawled=report.total_crawled,
            total_analyzed=report.total_analyzed,
            analysis_rate=analysis_rate,
            new_chunks=report.new_chunks,
            new_expert_count=len(report.new_experts),
            expert_sections=expert_sections_md,
            cross_analysis=report.cross_analysis or "상호 연관 분석 없음",
            chunk_summary=chunk_summary,
            generated_at=report.generated_at.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def save_report(self, report: WeeklyReport) -> str:
        """리포트를 파일로 저장"""
        markdown = self.to_markdown(report)

        filename = f"weekly-briefing-{report.end_date.strftime('%Y-%m-%d')}.md"
        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown)

        logger.info(f"리포트 저장: {filepath}")
        return str(filepath)

    def _generate_cross_analysis(
        self, expert_sections: Dict[ExpertRole, ExpertSection]
    ) -> str:
        """상호 연관 분석 생성"""
        if len(expert_sections) < 2:
            return "단일 분야 분석으로 상호 연관 분석 생략"

        roles = list(expert_sections.keys())
        role_names = {
            ExpertRole.POLICY_EXPERT: "정책/법규",
            ExpertRole.CARBON_CREDIT_EXPERT: "탄소배출권",
            ExpertRole.MARKET_EXPERT: "시장/거래",
            ExpertRole.TECHNOLOGY_EXPERT: "감축기술",
            ExpertRole.MRV_EXPERT: "MRV/검증",
        }

        fields = [role_names.get(r, str(r)) for r in roles]

        return f"""이번 주 분석에서 **{', '.join(fields)}** 분야의 동향이 확인되었습니다.

각 분야의 발견 사항을 종합하여 검토하시기 바랍니다.
특정 분야에 대한 심층 분석이 필요하시면 해당 전문가에게 추가 질문을 해주세요."""

    def _generate_chunk_summary(
        self, expert_sections: Dict[ExpertRole, ExpertSection]
    ) -> str:
        """청크 저장 요약 생성"""
        lines = []
        for role, section in expert_sections.items():
            role_name = {
                ExpertRole.POLICY_EXPERT: "정책법규",
                ExpertRole.CARBON_CREDIT_EXPERT: "탄소배출권",
                ExpertRole.MARKET_EXPERT: "시장거래",
                ExpertRole.TECHNOLOGY_EXPERT: "감축기술",
                ExpertRole.MRV_EXPERT: "MRV검증",
            }.get(role, str(role))

            lines.append(f"- {role_name}: +{section.content_count * 3} 청크 (예상)")

        return "\n".join(lines) if lines else "저장된 청크 없음"
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/weekly_pipeline/test_report_generator.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/react_agent/weekly_pipeline/report_generator.py tests/weekly_pipeline/
git commit -m "feat: add weekly report generator"
```

---

## Task 11: 스케줄러 설정

**Files:**
- Create: `src/react_agent/weekly_pipeline/scheduler.py`
- Create: `src/react_agent/weekly_pipeline/pipeline.py`
- Test: `tests/weekly_pipeline/test_scheduler.py`

**Step 1: Write the failing test**

```python
# tests/weekly_pipeline/test_scheduler.py
"""스케줄러 테스트"""

import pytest

from react_agent.weekly_pipeline.scheduler import (
    PipelineScheduler,
    SchedulerConfig,
)
from react_agent.weekly_pipeline.pipeline import WeeklyPipeline


class TestSchedulerConfig:
    """SchedulerConfig 테스트"""

    def test_default_config(self):
        config = SchedulerConfig()
        assert config.day_of_week == "mon"
        assert config.hour == 0
        assert config.minute == 0

    def test_custom_config(self):
        config = SchedulerConfig(
            day_of_week="sun",
            hour=6,
            minute=30,
        )
        assert config.day_of_week == "sun"
        assert config.hour == 6


class TestWeeklyPipeline:
    """WeeklyPipeline 테스트"""

    def test_pipeline_init(self):
        pipeline = WeeklyPipeline()
        assert pipeline is not None

    @pytest.mark.asyncio
    async def test_pipeline_stages(self):
        pipeline = WeeklyPipeline()
        # stages 속성 확인
        assert hasattr(pipeline, 'run')
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/weekly_pipeline/test_scheduler.py -v`
Expected: FAIL

**Step 3: Write pipeline implementation**

```python
# src/react_agent/weekly_pipeline/pipeline.py
"""주간 분석 파이프라인 - 전체 워크플로우 오케스트레이션"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from .crawler import CrawlerRegistry, CrawledContent
from .sources import get_default_registry
from .preprocessor import Preprocessor, PreprocessedContent
from .classifier import RuleBasedClassifier, ClassificationResult
from .expert_meeting import ExpertMeeting, MeetingResult
from .expert_generator import register_dynamic_expert
from .analyzer import ExpertAnalyzer, AnalysisResult
from .report_generator import ReportGenerator, WeeklyReport
from react_agent.rag.chunking import SemanticChunker, Chunk, EnhancedChunkMetadata

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """파이프라인 실행 결과"""

    start_time: datetime
    end_time: datetime
    crawled_count: int
    preprocessed_count: int
    analyzed_count: int
    chunks_created: int
    new_experts: List[str]
    report_path: str
    errors: List[str]


class WeeklyPipeline:
    """주간 분석 파이프라인"""

    def __init__(
        self,
        days_back: int = 7,
        enable_llm_meeting: bool = True,
    ):
        self.days_back = days_back
        self.enable_llm_meeting = enable_llm_meeting

        # 컴포넌트 초기화
        self.registry = get_default_registry()
        self.preprocessor = Preprocessor()
        self.classifier = RuleBasedClassifier()
        self.meeting = ExpertMeeting() if enable_llm_meeting else None
        self.analyzer = ExpertAnalyzer()
        self.chunker = SemanticChunker()
        self.report_generator = ReportGenerator()

        self.errors: List[str] = []

    async def run(self) -> PipelineResult:
        """파이프라인 실행"""
        start_time = datetime.now()
        logger.info(f"=== 주간 분석 파이프라인 시작 ===")

        new_experts: List[str] = []
        chunks_created = 0

        try:
            # Stage 1: 크롤링
            logger.info("[Stage 1/6] 크롤링 시작...")
            crawled = await self._stage_crawl()
            logger.info(f"[Stage 1/6] 크롤링 완료: {len(crawled)}건")

            # Stage 2: 전처리
            logger.info("[Stage 2/6] 전처리 시작...")
            preprocessed = self._stage_preprocess(crawled)
            logger.info(f"[Stage 2/6] 전처리 완료: {len(preprocessed)}건")

            # Stage 3: 분류
            logger.info("[Stage 3/6] 분류 시작...")
            classified = self._stage_classify(preprocessed)
            logger.info(f"[Stage 3/6] 분류 완료: {len(classified)}건")

            # Stage 4: LLM 회의 (필요시)
            if self.enable_llm_meeting:
                logger.info("[Stage 4/6] LLM 회의 시작...")
                new_experts = await self._stage_meeting(preprocessed, classified)
                logger.info(f"[Stage 4/6] LLM 회의 완료: 신규 전문가 {len(new_experts)}명")

            # Stage 5: 전문가 분석
            logger.info("[Stage 5/6] 전문가 분석 시작...")
            analyzed = await self._stage_analyze(preprocessed, classified)
            logger.info(f"[Stage 5/6] 분석 완료: {len(analyzed)}건")

            # Stage 6: 리포트 생성
            logger.info("[Stage 6/6] 리포트 생성...")
            report_path = self._stage_report(analyzed, new_experts)
            logger.info(f"[Stage 6/6] 리포트 저장: {report_path}")

        except Exception as e:
            logger.error(f"파이프라인 오류: {e}")
            self.errors.append(str(e))
            report_path = ""
            crawled = []
            preprocessed = []
            analyzed = []

        finally:
            # 크롤러 정리
            await self.registry.close_all()

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        logger.info(f"=== 파이프라인 완료: {elapsed:.1f}초 ===")

        return PipelineResult(
            start_time=start_time,
            end_time=end_time,
            crawled_count=len(crawled),
            preprocessed_count=len(preprocessed),
            analyzed_count=len(analyzed),
            chunks_created=chunks_created,
            new_experts=new_experts,
            report_path=report_path,
            errors=self.errors,
        )

    async def _stage_crawl(self) -> List[CrawledContent]:
        """크롤링 단계"""
        return await self.registry.crawl_all(days_back=self.days_back)

    def _stage_preprocess(
        self, crawled: List[CrawledContent]
    ) -> List[PreprocessedContent]:
        """전처리 단계"""
        return self.preprocessor.preprocess_batch(crawled)

    def _stage_classify(
        self, preprocessed: List[PreprocessedContent]
    ) -> List[ClassificationResult]:
        """분류 단계"""
        texts = [p.clean_title + " " + p.clean_content for p in preprocessed]
        return self.classifier.classify_batch(texts)

    async def _stage_meeting(
        self,
        preprocessed: List[PreprocessedContent],
        classified: List[ClassificationResult],
    ) -> List[str]:
        """LLM 회의 단계 (필요한 콘텐츠만)"""
        new_experts = []

        for content, classification in zip(preprocessed, classified):
            if not classification.needs_llm_meeting:
                continue

            if not self.meeting:
                continue

            try:
                result = await self.meeting.conduct_meeting(
                    content=content.clean_content,
                    title=content.clean_title,
                    source=content.original.source,
                )

                # 신규 전문가 등록
                for proposal in result.new_expert_proposals:
                    if register_dynamic_expert(proposal):
                        new_experts.append(proposal.suggested_name)

            except Exception as e:
                logger.warning(f"LLM 회의 오류: {e}")
                self.errors.append(f"LLM meeting: {e}")

        return new_experts

    async def _stage_analyze(
        self,
        preprocessed: List[PreprocessedContent],
        classified: List[ClassificationResult],
    ) -> List[AnalysisResult]:
        """전문가 분석 단계"""
        return await self.analyzer.analyze_batch(preprocessed, classified)

    def _stage_report(
        self,
        analyzed: List[AnalysisResult],
        new_experts: List[str],
    ) -> str:
        """리포트 생성 단계"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.days_back)

        report = self.report_generator.generate_report(
            analysis_results=analyzed,
            start_date=start_date,
            end_date=end_date,
            new_experts=new_experts,
        )

        return self.report_generator.save_report(report)
```

**Step 4: Write scheduler implementation**

```python
# src/react_agent/weekly_pipeline/scheduler.py
"""스케줄러 설정 - APScheduler 기반 주간 실행"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .pipeline import WeeklyPipeline, PipelineResult

logger = logging.getLogger(__name__)


@dataclass
class SchedulerConfig:
    """스케줄러 설정"""

    day_of_week: str = "mon"  # mon, tue, wed, thu, fri, sat, sun
    hour: int = 0
    minute: int = 0
    timezone: str = "Asia/Seoul"


class PipelineScheduler:
    """파이프라인 스케줄러"""

    def __init__(
        self,
        config: Optional[SchedulerConfig] = None,
        on_complete: Optional[Callable[[PipelineResult], None]] = None,
    ):
        self.config = config or SchedulerConfig()
        self.on_complete = on_complete
        self.scheduler = AsyncIOScheduler(timezone=self.config.timezone)
        self.pipeline = WeeklyPipeline()
        self._is_running = False

    def start(self) -> None:
        """스케줄러 시작"""
        trigger = CronTrigger(
            day_of_week=self.config.day_of_week,
            hour=self.config.hour,
            minute=self.config.minute,
            timezone=self.config.timezone,
        )

        self.scheduler.add_job(
            self._run_pipeline,
            trigger=trigger,
            id="weekly_analysis_pipeline",
            name="Weekly Analysis Pipeline",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info(
            f"스케줄러 시작: 매주 {self.config.day_of_week} "
            f"{self.config.hour:02d}:{self.config.minute:02d}"
        )

    def stop(self) -> None:
        """스케줄러 중지"""
        self.scheduler.shutdown()
        logger.info("스케줄러 중지")

    async def run_now(self) -> PipelineResult:
        """즉시 실행"""
        return await self._run_pipeline()

    async def _run_pipeline(self) -> PipelineResult:
        """파이프라인 실행"""
        if self._is_running:
            logger.warning("파이프라인이 이미 실행 중입니다")
            return PipelineResult(
                start_time=None,
                end_time=None,
                crawled_count=0,
                preprocessed_count=0,
                analyzed_count=0,
                chunks_created=0,
                new_experts=[],
                report_path="",
                errors=["Pipeline already running"],
            )

        self._is_running = True

        try:
            result = await self.pipeline.run()

            if self.on_complete:
                self.on_complete(result)

            return result

        finally:
            self._is_running = False

    @property
    def is_running(self) -> bool:
        """실행 중 여부"""
        return self._is_running

    @property
    def next_run_time(self) -> Optional[str]:
        """다음 실행 시간"""
        job = self.scheduler.get_job("weekly_analysis_pipeline")
        if job and job.next_run_time:
            return job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
        return None
```

**Step 5: Update __init__.py**

```python
# src/react_agent/weekly_pipeline/__init__.py
"""Weekly Analysis Pipeline - 주간 정책/뉴스 분석 파이프라인"""

from .crawler import BaseCrawler, CrawlerRegistry, CrawledContent, RSSCrawler
from .sources import (
    SourceConfig,
    DOMESTIC_SOURCES,
    INTERNATIONAL_SOURCES,
    MEDIA_SOURCES,
    get_default_registry,
)
from .preprocessor import Preprocessor, PreprocessedContent
from .classifier import RuleBasedClassifier, ClassificationResult
from .expert_meeting import ExpertMeeting, MeetingResult, NewExpertProposal
from .expert_generator import (
    ExpertGenerator,
    register_dynamic_expert,
    get_dynamic_experts,
)
from .analyzer import ExpertAnalyzer, AnalysisResult
from .report_generator import ReportGenerator, WeeklyReport
from .pipeline import WeeklyPipeline, PipelineResult
from .scheduler import PipelineScheduler, SchedulerConfig

__all__ = [
    # Crawler
    "BaseCrawler",
    "CrawlerRegistry",
    "CrawledContent",
    "RSSCrawler",
    # Sources
    "SourceConfig",
    "DOMESTIC_SOURCES",
    "INTERNATIONAL_SOURCES",
    "MEDIA_SOURCES",
    "get_default_registry",
    # Preprocessor
    "Preprocessor",
    "PreprocessedContent",
    # Classifier
    "RuleBasedClassifier",
    "ClassificationResult",
    # Expert Meeting
    "ExpertMeeting",
    "MeetingResult",
    "NewExpertProposal",
    # Expert Generator
    "ExpertGenerator",
    "register_dynamic_expert",
    "get_dynamic_experts",
    # Analyzer
    "ExpertAnalyzer",
    "AnalysisResult",
    # Report
    "ReportGenerator",
    "WeeklyReport",
    # Pipeline
    "WeeklyPipeline",
    "PipelineResult",
    # Scheduler
    "PipelineScheduler",
    "SchedulerConfig",
]
```

**Step 6: Run test to verify it passes**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/weekly_pipeline/test_scheduler.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add src/react_agent/weekly_pipeline/
git commit -m "feat: add pipeline orchestration and scheduler"
```

---

## Task 12: 의존성 추가 및 최종 테스트

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/weekly_pipeline/test_integration.py`

**Step 1: Update pyproject.toml**

Add to dependencies:

```toml
"apscheduler>=3.10.0",
"beautifulsoup4>=4.12.0",
"lxml>=5.0.0",
```

**Step 2: Write integration test**

```python
# tests/weekly_pipeline/test_integration.py
"""통합 테스트"""

import pytest

from react_agent.weekly_pipeline import (
    WeeklyPipeline,
    PipelineScheduler,
    SchedulerConfig,
    get_default_registry,
)


class TestIntegration:
    """통합 테스트"""

    def test_all_components_importable(self):
        """모든 컴포넌트 임포트 가능"""
        from react_agent.weekly_pipeline import (
            BaseCrawler,
            CrawlerRegistry,
            Preprocessor,
            RuleBasedClassifier,
            ExpertMeeting,
            ExpertAnalyzer,
            ReportGenerator,
            WeeklyPipeline,
            PipelineScheduler,
        )
        assert True

    def test_default_registry_has_crawlers(self):
        """기본 레지스트리에 크롤러 존재"""
        registry = get_default_registry()
        crawlers = registry.get_all()
        assert len(crawlers) > 0

    def test_pipeline_can_be_created(self):
        """파이프라인 생성 가능"""
        pipeline = WeeklyPipeline(days_back=1, enable_llm_meeting=False)
        assert pipeline is not None

    def test_scheduler_can_be_configured(self):
        """스케줄러 설정 가능"""
        config = SchedulerConfig(
            day_of_week="mon",
            hour=0,
            minute=0,
        )
        scheduler = PipelineScheduler(config=config)
        assert scheduler is not None
```

**Step 3: Run all tests**

Run: `cd /Users/ssh/Documents/Develope/carbon-ai-chatbot/react-agent && python -m pytest tests/weekly_pipeline/ -v`
Expected: All PASS

**Step 4: Final commit**

```bash
git add pyproject.toml tests/weekly_pipeline/
git commit -m "feat: complete weekly analysis pipeline with all components"
```

---

## Summary

12개 태스크 완료 시 생성되는 파일:

**신규 파일 (10개):**
1. `src/react_agent/weekly_pipeline/__init__.py`
2. `src/react_agent/weekly_pipeline/crawler.py`
3. `src/react_agent/weekly_pipeline/sources.py`
4. `src/react_agent/weekly_pipeline/preprocessor.py`
5. `src/react_agent/weekly_pipeline/classifier.py`
6. `src/react_agent/weekly_pipeline/expert_meeting.py`
7. `src/react_agent/weekly_pipeline/expert_generator.py`
8. `src/react_agent/weekly_pipeline/analyzer.py`
9. `src/react_agent/weekly_pipeline/report_generator.py`
10. `src/react_agent/weekly_pipeline/pipeline.py`
11. `src/react_agent/weekly_pipeline/scheduler.py`
12. `src/react_agent/rag/knowledge_base.py`

**수정 파일 (2개):**
1. `src/react_agent/rag/chunking.py` - EnhancedChunkMetadata 추가
2. `pyproject.toml` - 의존성 추가

**테스트 파일 (9개):**
1. `tests/weekly_pipeline/test_crawler.py`
2. `tests/weekly_pipeline/test_sources.py`
3. `tests/weekly_pipeline/test_preprocessor.py`
4. `tests/weekly_pipeline/test_classifier.py`
5. `tests/weekly_pipeline/test_expert_meeting.py`
6. `tests/weekly_pipeline/test_expert_generator.py`
7. `tests/weekly_pipeline/test_analyzer.py`
8. `tests/weekly_pipeline/test_report_generator.py`
9. `tests/weekly_pipeline/test_scheduler.py`
10. `tests/weekly_pipeline/test_integration.py`
11. `tests/rag/test_chunking_enhanced.py`
12. `tests/rag/test_knowledge_base.py`
