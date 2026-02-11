"""EnhancedChunkMetadata 테스트

확장된 청크 메타데이터의 새 필드 및 메서드를 테스트합니다.
"""

import pytest

from react_agent.rag.chunking import ChunkMetadata, EnhancedChunkMetadata


class TestEnhancedChunkMetadata:
    """EnhancedChunkMetadata 클래스 테스트"""

    def test_enhanced_metadata_fields(self):
        """새 필드들 (date_collected, analyzed_by, confidence_score, related_chunks) 테스트"""
        metadata = EnhancedChunkMetadata(
            doc_id="doc-001",
            chunk_id="chunk-001",
            source="https://example.com/report.pdf",
            date_collected="2024-01-15",
            analyzed_by=["정책법규전문가", "탄소시장전문가"],
            confidence_score=0.85,
            related_chunks=["chunk-002", "chunk-003"],
            analysis_notes="주간 분석 노트 내용",
        )

        assert metadata.date_collected == "2024-01-15"
        assert metadata.analyzed_by == ["정책법규전문가", "탄소시장전문가"]
        assert metadata.confidence_score == 0.85
        assert metadata.related_chunks == ["chunk-002", "chunk-003"]
        assert metadata.analysis_notes == "주간 분석 노트 내용"

    def test_enhanced_metadata_default_values(self):
        """새 필드들의 기본값 테스트"""
        metadata = EnhancedChunkMetadata(
            doc_id="doc-002",
            chunk_id="chunk-002",
            source="test.pdf",
        )

        assert metadata.date_collected == ""
        assert metadata.analyzed_by == []
        assert metadata.confidence_score == 0.0
        assert metadata.related_chunks == []
        assert metadata.analysis_notes == ""

    def test_metadata_to_dict(self):
        """to_dict() 메서드 테스트"""
        metadata = EnhancedChunkMetadata(
            doc_id="doc-003",
            chunk_id="chunk-003",
            source="https://example.com/policy.pdf",
            document_type="정책",
            region="한국",
            topic="배출권거래",
            language="ko",
            expert_domain=["정책법규", "탄소배출권"],
            keywords=["배출권", "거래", "탄소"],
            date_collected="2024-02-01",
            analyzed_by=["MRV검증전문가"],
            confidence_score=0.92,
            related_chunks=["chunk-004"],
            analysis_notes="검증 완료",
        )

        result = metadata.to_dict()

        assert isinstance(result, dict)
        # 기존 필드 확인
        assert result["doc_id"] == "doc-003"
        assert result["chunk_id"] == "chunk-003"
        assert result["source"] == "https://example.com/policy.pdf"
        assert result["document_type"] == "정책"
        assert result["region"] == "한국"
        assert result["topic"] == "배출권거래"
        assert result["language"] == "ko"
        assert result["expert_domain"] == ["정책법규", "탄소배출권"]
        assert result["keywords"] == ["배출권", "거래", "탄소"]
        # 새 필드 확인
        assert result["date_collected"] == "2024-02-01"
        assert result["analyzed_by"] == ["MRV검증전문가"]
        assert result["confidence_score"] == 0.92
        assert result["related_chunks"] == ["chunk-004"]
        assert result["analysis_notes"] == "검증 완료"

    def test_inherits_from_chunk_metadata(self):
        """기존 필드 상속 확인"""
        metadata = EnhancedChunkMetadata(
            doc_id="doc-004",
            chunk_id="chunk-004",
            source="report.pdf",
            document_type="보고서",
            region="EU",
            topic="탄소세",
            language="en",
            expert_domain=["시장거래"],
            keywords=["carbon", "tax"],
        )

        # EnhancedChunkMetadata가 ChunkMetadata를 상속하는지 확인
        assert isinstance(metadata, ChunkMetadata)

        # 기존 필드들이 올바르게 상속되었는지 확인
        assert metadata.doc_id == "doc-004"
        assert metadata.chunk_id == "chunk-004"
        assert metadata.source == "report.pdf"
        assert metadata.document_type == "보고서"
        assert metadata.region == "EU"
        assert metadata.topic == "탄소세"
        assert metadata.language == "en"
        assert metadata.expert_domain == ["시장거래"]
        assert metadata.keywords == ["carbon", "tax"]

    def test_confidence_score_range(self):
        """confidence_score 범위 테스트 (0.0-1.0)"""
        # 유효한 값
        metadata = EnhancedChunkMetadata(
            doc_id="doc-005",
            chunk_id="chunk-005",
            source="test.pdf",
            confidence_score=0.5,
        )
        assert 0.0 <= metadata.confidence_score <= 1.0

        # 경계값 테스트
        metadata_low = EnhancedChunkMetadata(
            doc_id="doc-006",
            chunk_id="chunk-006",
            source="test.pdf",
            confidence_score=0.0,
        )
        assert metadata_low.confidence_score == 0.0

        metadata_high = EnhancedChunkMetadata(
            doc_id="doc-007",
            chunk_id="chunk-007",
            source="test.pdf",
            confidence_score=1.0,
        )
        assert metadata_high.confidence_score == 1.0
