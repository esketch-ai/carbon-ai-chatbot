"""시맨틱 청킹 파이프라인

문서를 의미 단위로 분할하고 메타데이터를 추출하는 파이프라인입니다.
"""

import re
import uuid
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ChunkMetadata:
    """청크 메타데이터

    Attributes:
        doc_id: 문서 고유 식별자
        chunk_id: 청크 고유 식별자
        source: 문서 출처 (파일 경로, URL 등)
        document_type: 문서 유형 (정책, 법규, 보고서 등)
        region: 지역/국가 (한국, EU, 미국 등)
        topic: 주제 (배출권거래, 탄소세, MRV 등)
        language: 언어 코드 (ko, en 등)
        expert_domain: 관련 전문가 도메인 목록
        keywords: 핵심 키워드 목록
    """
    doc_id: str
    chunk_id: str
    source: str
    document_type: str = ""
    region: str = ""
    topic: str = ""
    language: str = "ko"
    expert_domain: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)


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


@dataclass
class Chunk:
    """텍스트 청크

    Attributes:
        content: 청크 텍스트 내용
        metadata: 청크 메타데이터
    """
    content: str
    metadata: ChunkMetadata


class SemanticChunker:
    """시맨틱 청킹 클래스

    문서를 의미 단위로 분할하고 메타데이터를 자동 추출합니다.

    Attributes:
        chunk_size: 청크 최대 크기 (문자 수)
        chunk_overlap: 청크 간 중복 크기 (문자 수)
        min_chunk_size: 청크 최소 크기 (문자 수)
    """

    # 전문가 도메인 키워드 매핑
    DOMAIN_KEYWORDS = {
        "정책법규": [
            "법", "규정", "조례", "지침", "고시", "법률", "법령", "규제", "정책",
            "제도", "기본계획", "국가계획", "NDC", "2050", "탄소중립", "넷제로",
            "파리협정", "기후변화협약", "UNFCCC", "COP", "교토의정서"
        ],
        "탄소배출권": [
            "배출권", "할당", "크레딧", "상쇄", "offset", "ETS", "cap-and-trade",
            "배출량", "허용량", "거래량", "인증", "감축량", "잉여", "이월", "차입",
            "KAU", "KCU", "KOC", "EU-ETS", "K-ETS"
        ],
        "시장거래": [
            "시장", "거래", "가격", "선물", "옵션", "헤지", "투자", "수익률",
            "변동성", "리스크", "포트폴리오", "시세", "매수", "매도", "호가",
            "경매", "중개", "브로커", "청산", "결제"
        ],
        "감축기술": [
            "기술", "혁신", "CCS", "CCUS", "수소", "재생에너지", "태양광", "풍력",
            "전기차", "EV", "배터리", "에너지효율", "스마트그리드", "히트펌프",
            "바이오연료", "그린암모니아", "DAC", "탄소포집"
        ],
        "MRV검증": [
            "MRV", "모니터링", "보고", "검증", "측정", "인벤토리", "배출계수",
            "활동자료", "불확도", "검증기관", "제3자검증", "IPCC", "가이드라인",
            "Tier", "방법론", "Scope", "배출원", "흡수원"
        ]
    }

    # 키워드 추출용 불용어
    STOPWORDS = {
        "것", "수", "등", "및", "또는", "그", "이", "저", "위", "의", "를", "을",
        "에", "에서", "로", "으로", "와", "과", "는", "은", "가", "이다", "있다",
        "하다", "되다", "한다", "한", "할", "함", "하는", "있는", "없는", "때문",
        "경우", "대해", "대한", "통해", "통한", "따라", "따른", "위한", "위해",
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "of", "to", "in", "for", "on", "with",
        "at", "by", "from", "or", "and", "as", "that", "this", "it", "its"
    }

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        min_chunk_size: int = 100
    ):
        """SemanticChunker 초기화

        Args:
            chunk_size: 청크 최대 크기 (문자 수). 기본값 800.
            chunk_overlap: 청크 간 중복 크기 (문자 수). 기본값 150.
            min_chunk_size: 청크 최소 크기 (문자 수). 기본값 100.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_document(
        self,
        text: str,
        doc_id: str,
        source: str,
        document_type: str = "",
        region: str = "",
        topic: str = ""
    ) -> List[Chunk]:
        """문서를 청크로 분할

        Args:
            text: 분할할 문서 텍스트
            doc_id: 문서 고유 식별자
            source: 문서 출처
            document_type: 문서 유형
            region: 지역/국가
            topic: 주제

        Returns:
            분할된 청크 목록
        """
        if not text or not text.strip():
            return []

        # 텍스트 정규화
        text = self._normalize_text(text)

        # 문단 단위로 분할
        paragraphs = self._split_paragraphs(text)

        # 청크 생성
        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            # 현재 청크에 문단 추가 시 크기 확인
            if len(current_chunk) + len(paragraph) + 1 <= self.chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                # 현재 청크 저장
                if len(current_chunk) >= self.min_chunk_size:
                    chunk = self._create_chunk(
                        current_chunk, doc_id, source, document_type, region, topic
                    )
                    chunks.append(chunk)

                    # 중복 처리
                    overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else ""
                    current_chunk = overlap_text + ("\n\n" if overlap_text else "") + paragraph
                else:
                    # 최소 크기 미달 시 다음 문단과 합치기
                    current_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph

                # 문단이 너무 긴 경우 강제 분할
                while len(current_chunk) > self.chunk_size:
                    split_point = self._find_split_point(current_chunk, self.chunk_size)
                    chunk = self._create_chunk(
                        current_chunk[:split_point].strip(),
                        doc_id, source, document_type, region, topic
                    )
                    chunks.append(chunk)
                    current_chunk = current_chunk[split_point - self.chunk_overlap:].strip()

        # 마지막 청크 저장
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunk = self._create_chunk(
                current_chunk, doc_id, source, document_type, region, topic
            )
            chunks.append(chunk)
        elif current_chunk and chunks:
            # 마지막 청크가 너무 작으면 이전 청크에 병합
            prev_content = chunks[-1].content
            merged_content = prev_content + "\n\n" + current_chunk
            chunks[-1] = self._create_chunk(
                merged_content, doc_id, source, document_type, region, topic
            )

        return chunks

    def _normalize_text(self, text: str) -> str:
        """텍스트 정규화

        Args:
            text: 정규화할 텍스트

        Returns:
            정규화된 텍스트
        """
        # 연속 공백 제거
        text = re.sub(r'[ \t]+', ' ', text)
        # 연속 개행 정리 (3개 이상 -> 2개)
        text = re.sub(r'\n{3,}', '\n\n', text)
        # 앞뒤 공백 제거
        return text.strip()

    def _split_paragraphs(self, text: str) -> List[str]:
        """텍스트를 문단으로 분할

        Args:
            text: 분할할 텍스트

        Returns:
            문단 목록
        """
        # 빈 줄 기준으로 분할
        paragraphs = re.split(r'\n\s*\n', text)

        # 빈 문단 제거 및 정리
        result = []
        for p in paragraphs:
            p = p.strip()
            if p:
                result.append(p)

        return result

    def _find_split_point(self, text: str, max_length: int) -> int:
        """적절한 분할 지점 찾기

        Args:
            text: 분할할 텍스트
            max_length: 최대 길이

        Returns:
            분할 지점 인덱스
        """
        if len(text) <= max_length:
            return len(text)

        # 문장 끝에서 분할 시도 (. ! ? 뒤의 공백)
        sentence_end = max(
            text.rfind('. ', 0, max_length),
            text.rfind('! ', 0, max_length),
            text.rfind('? ', 0, max_length),
            text.rfind('。', 0, max_length),
        )
        if sentence_end > max_length // 2:
            return sentence_end + 1

        # 쉼표에서 분할 시도
        comma_pos = max(
            text.rfind(', ', 0, max_length),
            text.rfind('， ', 0, max_length),
        )
        if comma_pos > max_length // 2:
            return comma_pos + 1

        # 공백에서 분할
        space_pos = text.rfind(' ', 0, max_length)
        if space_pos > max_length // 2:
            return space_pos + 1

        # 강제 분할
        return max_length

    def _create_chunk(
        self,
        content: str,
        doc_id: str,
        source: str,
        document_type: str,
        region: str,
        topic: str
    ) -> Chunk:
        """청크 객체 생성

        Args:
            content: 청크 내용
            doc_id: 문서 ID
            source: 문서 출처
            document_type: 문서 유형
            region: 지역
            topic: 주제

        Returns:
            생성된 Chunk 객체
        """
        chunk_id = str(uuid.uuid4())
        expert_domain = self._detect_expert_domain(content)
        keywords = self._extract_keywords(content)

        # 언어 감지 (간단한 휴리스틱)
        language = self._detect_language(content)

        metadata = ChunkMetadata(
            doc_id=doc_id,
            chunk_id=chunk_id,
            source=source,
            document_type=document_type,
            region=region,
            topic=topic,
            language=language,
            expert_domain=expert_domain,
            keywords=keywords
        )

        return Chunk(content=content, metadata=metadata)

    def _detect_expert_domain(self, text: str) -> List[str]:
        """텍스트에서 전문가 도메인 감지

        Args:
            text: 분석할 텍스트

        Returns:
            감지된 전문가 도메인 목록
        """
        text_lower = text.lower()
        domains = []
        domain_scores = {}

        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > 0:
                domain_scores[domain] = score

        # 점수 기준 정렬하여 상위 도메인 반환
        sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
        domains = [d[0] for d in sorted_domains if d[1] >= 2]  # 최소 2개 키워드 매칭

        # 최소 1개는 반환
        if not domains and sorted_domains:
            domains = [sorted_domains[0][0]]

        return domains[:3]  # 최대 3개 도메인

    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """텍스트에서 키워드 추출

        Args:
            text: 분석할 텍스트
            max_keywords: 최대 키워드 수. 기본값 10.

        Returns:
            추출된 키워드 목록
        """
        # 단어 추출 (한글, 영문, 숫자 포함 단어)
        words = re.findall(r'[가-힣a-zA-Z0-9]+(?:-[가-힣a-zA-Z0-9]+)*', text)

        # 빈도수 계산
        word_freq = {}
        for word in words:
            # 불용어 및 짧은 단어 제외
            if word.lower() in self.STOPWORDS:
                continue
            if len(word) < 2:
                continue
            # 숫자만 있는 경우 제외
            if word.isdigit():
                continue

            word_freq[word] = word_freq.get(word, 0) + 1

        # 빈도수 기준 정렬
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

        # 상위 키워드 반환
        keywords = [word for word, _ in sorted_words[:max_keywords]]

        return keywords

    def _detect_language(self, text: str) -> str:
        """텍스트 언어 감지

        Args:
            text: 분석할 텍스트

        Returns:
            언어 코드 (ko, en)
        """
        # 한글 비율 계산
        korean_chars = len(re.findall(r'[가-힣]', text))
        total_chars = len(re.findall(r'[가-힣a-zA-Z]', text))

        if total_chars == 0:
            return "ko"

        korean_ratio = korean_chars / total_chars
        return "ko" if korean_ratio > 0.3 else "en"


# 싱글톤 인스턴스
_chunker_instance: Optional[SemanticChunker] = None


def get_chunker(
    chunk_size: int = 800,
    chunk_overlap: int = 150,
    min_chunk_size: int = 100
) -> SemanticChunker:
    """SemanticChunker 싱글톤 인스턴스 반환

    처음 호출 시 인스턴스를 생성하고, 이후 호출에서는 동일한 인스턴스를 반환합니다.

    Args:
        chunk_size: 청크 최대 크기 (문자 수). 기본값 800.
        chunk_overlap: 청크 간 중복 크기 (문자 수). 기본값 150.
        min_chunk_size: 청크 최소 크기 (문자 수). 기본값 100.

    Returns:
        SemanticChunker 싱글톤 인스턴스
    """
    global _chunker_instance

    if _chunker_instance is None:
        _chunker_instance = SemanticChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_size=min_chunk_size
        )

    return _chunker_instance
