"""ChromaDB 기반 지식베이스 저장소

청크를 저장하고 검색하는 지식베이스 모듈입니다.
"""

import json
from dataclasses import dataclass, fields
from typing import Dict, List, Optional

import chromadb

from .chunking import Chunk, ChunkMetadata, EnhancedChunkMetadata


@dataclass
class KnowledgeBaseConfig:
    """지식베이스 설정

    Attributes:
        persist_directory: 데이터 저장 경로
        collection_name: ChromaDB 컬렉션 이름
        embedding_model: 임베딩 모델 이름
    """

    persist_directory: str = "./data/knowledge_base"
    collection_name: str = "weekly_analysis"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class KnowledgeBase:
    """ChromaDB 기반 지식베이스

    청크를 저장하고 벡터 검색을 수행합니다.

    Attributes:
        config: 지식베이스 설정
    """

    def __init__(self, config: Optional[KnowledgeBaseConfig] = None):
        """KnowledgeBase 초기화

        Args:
            config: 지식베이스 설정. None이면 기본값 사용.
        """
        self.config = config or KnowledgeBaseConfig()

        # ChromaDB 클라이언트 초기화 (새 API 사용)
        # PersistentClient를 사용하여 데이터를 디스크에 저장
        self._client = chromadb.PersistentClient(
            path=self.config.persist_directory,
        )

        # 컬렉션 생성 또는 가져오기
        self._collection = self._client.get_or_create_collection(
            name=self.config.collection_name,
        )

    def add_chunk(self, chunk: Chunk) -> None:
        """청크 추가

        Args:
            chunk: 추가할 청크
        """
        metadata = self._prepare_metadata(chunk.metadata)

        self._collection.add(
            ids=[chunk.metadata.chunk_id],
            documents=[chunk.content],
            metadatas=[metadata],
        )

    def add_chunks(self, chunks: List[Chunk]) -> int:
        """여러 청크 일괄 추가

        Args:
            chunks: 추가할 청크 목록

        Returns:
            추가된 청크 수
        """
        if not chunks:
            return 0

        ids = [chunk.metadata.chunk_id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [self._prepare_metadata(chunk.metadata) for chunk in chunks]

        self._collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        return len(chunks)

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """청크 조회

        Args:
            chunk_id: 조회할 청크 ID

        Returns:
            청크 객체. 없으면 None.
        """
        result = self._collection.get(
            ids=[chunk_id],
            include=["documents", "metadatas"],
        )

        if not result["ids"]:
            return None

        content = result["documents"][0]
        metadata = result["metadatas"][0]

        return self._reconstruct_chunk(content, metadata)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None,
    ) -> List[Chunk]:
        """검색 수행

        Args:
            query: 검색 쿼리
            top_k: 반환할 최대 결과 수
            filter_metadata: 메타데이터 필터 조건

        Returns:
            검색된 청크 목록
        """
        where_filter = None
        if filter_metadata:
            where_filter = filter_metadata

        results = self._collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas"],
        )

        chunks = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                content = results["documents"][0][i]
                metadata = results["metadatas"][0][i]
                chunk = self._reconstruct_chunk(content, metadata)
                chunks.append(chunk)

        return chunks

    def get_chunks_by_source(self, source: str) -> List[Chunk]:
        """소스별 청크 조회

        Args:
            source: 소스 경로/URL

        Returns:
            해당 소스의 청크 목록
        """
        results = self._collection.get(
            where={"source": source},
            include=["documents", "metadatas"],
        )

        chunks = []
        for i in range(len(results["ids"])):
            content = results["documents"][i]
            metadata = results["metadatas"][i]
            chunk = self._reconstruct_chunk(content, metadata)
            chunks.append(chunk)

        return chunks

    def get_chunks_by_date(self, date: str) -> List[Chunk]:
        """날짜별 청크 조회

        Args:
            date: 날짜 (YYYY-MM-DD 형식)

        Returns:
            해당 날짜의 청크 목록
        """
        results = self._collection.get(
            where={"date_collected": date},
            include=["documents", "metadatas"],
        )

        chunks = []
        for i in range(len(results["ids"])):
            content = results["documents"][i]
            metadata = results["metadatas"][i]
            chunk = self._reconstruct_chunk(content, metadata)
            chunks.append(chunk)

        return chunks

    def get_stats(self) -> Dict:
        """통계 조회

        Returns:
            통계 정보 딕셔너리
        """
        count = self._collection.count()

        return {
            "total_chunks": count,
            "collection_name": self.config.collection_name,
            "persist_directory": self.config.persist_directory,
        }

    def _prepare_metadata(self, metadata: ChunkMetadata) -> Dict:
        """메타데이터 준비 (리스트를 문자열로 변환)

        ChromaDB는 리스트 타입을 지원하지 않으므로 JSON 문자열로 변환합니다.

        Args:
            metadata: 청크 메타데이터

        Returns:
            ChromaDB 저장용 메타데이터 딕셔너리
        """
        result = {}

        # dataclass 필드를 순회하며 변환
        for field in fields(metadata):
            value = getattr(metadata, field.name)

            if isinstance(value, list):
                # 리스트는 JSON 문자열로 변환
                result[field.name] = json.dumps(value, ensure_ascii=False)
            elif value is None:
                result[field.name] = ""
            else:
                result[field.name] = value

        return result

    def _reconstruct_chunk(self, content: str, metadata: Dict) -> Chunk:
        """청크 재구성

        저장된 메타데이터에서 Chunk 객체를 재구성합니다.

        Args:
            content: 청크 내용
            metadata: 메타데이터 딕셔너리

        Returns:
            재구성된 Chunk 객체
        """
        # 리스트 필드 복원
        list_fields = [
            "expert_domain",
            "keywords",
            "analyzed_by",
            "related_chunks",
        ]

        for field in list_fields:
            if field in metadata and isinstance(metadata[field], str):
                try:
                    metadata[field] = json.loads(metadata[field])
                except json.JSONDecodeError:
                    metadata[field] = []

        # EnhancedChunkMetadata 필드가 있는지 확인
        enhanced_fields = {"date_collected", "analyzed_by", "confidence_score", "related_chunks", "analysis_notes"}
        has_enhanced = any(field in metadata for field in enhanced_fields)

        if has_enhanced:
            chunk_metadata = EnhancedChunkMetadata(
                doc_id=metadata.get("doc_id", ""),
                chunk_id=metadata.get("chunk_id", ""),
                source=metadata.get("source", ""),
                document_type=metadata.get("document_type", ""),
                region=metadata.get("region", ""),
                topic=metadata.get("topic", ""),
                language=metadata.get("language", "ko"),
                expert_domain=metadata.get("expert_domain", []),
                keywords=metadata.get("keywords", []),
                date_collected=metadata.get("date_collected", ""),
                analyzed_by=metadata.get("analyzed_by", []),
                confidence_score=float(metadata.get("confidence_score", 0.0)),
                related_chunks=metadata.get("related_chunks", []),
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
                expert_domain=metadata.get("expert_domain", []),
                keywords=metadata.get("keywords", []),
            )

        return Chunk(content=content, metadata=chunk_metadata)
