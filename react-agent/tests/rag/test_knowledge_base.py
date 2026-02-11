"""KnowledgeBase 테스트

ChromaDB 기반 지식베이스 저장소 테스트입니다.
"""

import tempfile
import pytest

from react_agent.rag.chunking import Chunk, ChunkMetadata, EnhancedChunkMetadata
from react_agent.rag.knowledge_base import KnowledgeBase, KnowledgeBaseConfig


@pytest.fixture
def temp_persist_dir():
    """임시 디렉토리 fixture"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def knowledge_base(temp_persist_dir):
    """KnowledgeBase fixture"""
    config = KnowledgeBaseConfig(
        persist_directory=temp_persist_dir,
        collection_name="test_collection",
    )
    return KnowledgeBase(config)


@pytest.fixture
def sample_chunk():
    """샘플 청크 fixture"""
    metadata = ChunkMetadata(
        doc_id="doc-001",
        chunk_id="chunk-001",
        source="https://example.com/policy.pdf",
        document_type="정책",
        region="한국",
        topic="배출권거래",
        language="ko",
        expert_domain=["정책법규", "탄소배출권"],
        keywords=["배출권", "거래", "탄소"],
    )
    return Chunk(
        content="대한민국의 배출권거래제는 2015년부터 시행되었습니다. "
                "이 제도는 온실가스 감축을 위한 핵심 정책 수단입니다.",
        metadata=metadata,
    )


@pytest.fixture
def sample_enhanced_chunk():
    """확장된 메타데이터 청크 fixture"""
    metadata = EnhancedChunkMetadata(
        doc_id="doc-002",
        chunk_id="chunk-002",
        source="https://example.com/report.pdf",
        document_type="보고서",
        region="EU",
        topic="탄소세",
        language="ko",
        expert_domain=["시장거래"],
        keywords=["탄소세", "EU", "정책"],
        date_collected="2024-01-15",
        analyzed_by=["정책법규전문가"],
        confidence_score=0.85,
        related_chunks=["chunk-001"],
        analysis_notes="주간 분석 노트",
    )
    return Chunk(
        content="EU의 탄소국경조정메커니즘(CBAM)은 수입품에 대한 탄소세입니다. "
                "이는 탄소 누출을 방지하기 위한 조치입니다.",
        metadata=metadata,
    )


class TestKnowledgeBaseConfig:
    """KnowledgeBaseConfig 테스트"""

    def test_default_config(self):
        """기본 설정값 테스트"""
        config = KnowledgeBaseConfig()
        assert config.persist_directory == "./data/knowledge_base"
        assert config.collection_name == "weekly_analysis"
        assert config.embedding_model == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    def test_custom_config(self, temp_persist_dir):
        """커스텀 설정값 테스트"""
        config = KnowledgeBaseConfig(
            persist_directory=temp_persist_dir,
            collection_name="custom_collection",
            embedding_model="custom-model",
        )
        assert config.persist_directory == temp_persist_dir
        assert config.collection_name == "custom_collection"
        assert config.embedding_model == "custom-model"


class TestKnowledgeBaseInitialization:
    """KnowledgeBase 초기화 테스트"""

    def test_init_with_default_config(self, temp_persist_dir):
        """기본 설정으로 초기화"""
        config = KnowledgeBaseConfig(persist_directory=temp_persist_dir)
        kb = KnowledgeBase(config)
        assert kb is not None
        assert kb.config.persist_directory == temp_persist_dir

    def test_init_without_config(self):
        """설정 없이 초기화"""
        kb = KnowledgeBase()
        assert kb is not None
        assert kb.config.persist_directory == "./data/knowledge_base"


class TestAddAndGetChunk:
    """청크 추가 및 조회 테스트"""

    def test_add_and_get_chunk(self, knowledge_base, sample_chunk):
        """청크 추가 후 조회"""
        # 청크 추가
        knowledge_base.add_chunk(sample_chunk)

        # 청크 조회
        retrieved = knowledge_base.get_chunk(sample_chunk.metadata.chunk_id)

        assert retrieved is not None
        assert retrieved.content == sample_chunk.content
        assert retrieved.metadata.doc_id == sample_chunk.metadata.doc_id
        assert retrieved.metadata.chunk_id == sample_chunk.metadata.chunk_id
        assert retrieved.metadata.source == sample_chunk.metadata.source
        assert retrieved.metadata.document_type == sample_chunk.metadata.document_type
        assert retrieved.metadata.region == sample_chunk.metadata.region

    def test_add_chunks_batch(self, knowledge_base, sample_chunk, sample_enhanced_chunk):
        """여러 청크 일괄 추가"""
        chunks = [sample_chunk, sample_enhanced_chunk]
        count = knowledge_base.add_chunks(chunks)

        assert count == 2

        # 각 청크 조회 확인
        chunk1 = knowledge_base.get_chunk(sample_chunk.metadata.chunk_id)
        chunk2 = knowledge_base.get_chunk(sample_enhanced_chunk.metadata.chunk_id)

        assert chunk1 is not None
        assert chunk2 is not None

    def test_get_nonexistent_chunk(self, knowledge_base):
        """존재하지 않는 청크 조회"""
        result = knowledge_base.get_chunk("nonexistent-id")
        assert result is None

    def test_add_enhanced_chunk(self, knowledge_base, sample_enhanced_chunk):
        """확장된 메타데이터 청크 추가 및 조회"""
        knowledge_base.add_chunk(sample_enhanced_chunk)

        retrieved = knowledge_base.get_chunk(sample_enhanced_chunk.metadata.chunk_id)

        assert retrieved is not None
        assert retrieved.content == sample_enhanced_chunk.content
        # EnhancedChunkMetadata 필드 확인
        assert retrieved.metadata.date_collected == "2024-01-15"
        assert retrieved.metadata.confidence_score == 0.85


class TestSearchChunks:
    """검색 기능 테스트"""

    def test_search_chunks(self, knowledge_base, sample_chunk, sample_enhanced_chunk):
        """검색 기능 테스트"""
        # 청크 추가
        knowledge_base.add_chunks([sample_chunk, sample_enhanced_chunk])

        # 검색 수행
        results = knowledge_base.search("배출권거래제 정책", top_k=5)

        assert len(results) > 0
        # 검색 결과가 Chunk 객체인지 확인
        assert isinstance(results[0], Chunk)

    def test_search_with_top_k(self, knowledge_base, sample_chunk, sample_enhanced_chunk):
        """top_k 파라미터 테스트"""
        knowledge_base.add_chunks([sample_chunk, sample_enhanced_chunk])

        results = knowledge_base.search("탄소", top_k=1)

        assert len(results) == 1

    def test_search_with_filter(self, knowledge_base, sample_chunk, sample_enhanced_chunk):
        """메타데이터 필터 검색 테스트"""
        knowledge_base.add_chunks([sample_chunk, sample_enhanced_chunk])

        # region 필터로 검색
        results = knowledge_base.search(
            "정책",
            filter_metadata={"region": "한국"}
        )

        assert len(results) > 0
        for result in results:
            assert result.metadata.region == "한국"


class TestGetChunksBySource:
    """소스별 청크 조회 테스트"""

    def test_get_chunks_by_source(self, knowledge_base, sample_chunk, sample_enhanced_chunk):
        """소스별 필터 테스트"""
        knowledge_base.add_chunks([sample_chunk, sample_enhanced_chunk])

        # 소스로 필터링
        results = knowledge_base.get_chunks_by_source("https://example.com/policy.pdf")

        assert len(results) == 1
        assert results[0].metadata.source == "https://example.com/policy.pdf"

    def test_get_chunks_by_nonexistent_source(self, knowledge_base, sample_chunk):
        """존재하지 않는 소스로 조회"""
        knowledge_base.add_chunk(sample_chunk)

        results = knowledge_base.get_chunks_by_source("nonexistent-source.pdf")

        assert len(results) == 0


class TestGetChunksByDate:
    """날짜별 청크 조회 테스트"""

    def test_get_chunks_by_date(self, knowledge_base, sample_enhanced_chunk):
        """날짜별 필터 테스트"""
        knowledge_base.add_chunk(sample_enhanced_chunk)

        results = knowledge_base.get_chunks_by_date("2024-01-15")

        assert len(results) == 1
        assert results[0].metadata.date_collected == "2024-01-15"


class TestGetStats:
    """통계 조회 테스트"""

    def test_get_stats(self, knowledge_base, sample_chunk, sample_enhanced_chunk):
        """통계 조회 테스트"""
        knowledge_base.add_chunks([sample_chunk, sample_enhanced_chunk])

        stats = knowledge_base.get_stats()

        assert "total_chunks" in stats
        assert stats["total_chunks"] == 2
        assert "collection_name" in stats


class TestMetadataHandling:
    """메타데이터 처리 테스트"""

    def test_prepare_metadata_converts_lists(self, knowledge_base, sample_chunk):
        """리스트 필드가 문자열로 변환되는지 테스트"""
        # _prepare_metadata는 내부 메서드이지만 동작 검증을 위해 테스트
        metadata_dict = knowledge_base._prepare_metadata(sample_chunk.metadata)

        # 리스트 필드가 문자열로 변환되었는지 확인
        assert isinstance(metadata_dict.get("expert_domain"), str)
        assert isinstance(metadata_dict.get("keywords"), str)
        # JSON 형태로 저장되었는지 확인
        assert "정책법규" in metadata_dict["expert_domain"]

    def test_reconstruct_chunk(self, knowledge_base, sample_chunk):
        """청크 재구성 테스트"""
        # 메타데이터 준비 및 재구성 테스트
        metadata_dict = knowledge_base._prepare_metadata(sample_chunk.metadata)

        reconstructed = knowledge_base._reconstruct_chunk(
            sample_chunk.content,
            metadata_dict
        )

        assert reconstructed.content == sample_chunk.content
        assert reconstructed.metadata.doc_id == sample_chunk.metadata.doc_id
        assert "정책법규" in reconstructed.metadata.expert_domain
