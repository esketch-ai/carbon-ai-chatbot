# RAG (Retrieval-Augmented Generation) 도구
# Chroma DB를 사용한 벡터 검색 및 문서 검색 기능

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from react_agent.cache_manager import get_cache_manager

try:
    from langchain_chroma import Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_core.documents import Document
    from rank_bm25 import BM25Okapi
    import numpy as np
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

logger = logging.getLogger(__name__)


class RAGTool:
    """RAG 검색 도구 클래스"""

    def __init__(
        self,
        knowledge_base_path: Optional[str] = None,
        chroma_db_path: Optional[str] = None
    ):
        """
        RAG 도구 초기화

        Args:
            knowledge_base_path: 지식베이스 문서 경로
            chroma_db_path: Chroma DB 저장 경로
        """
        if not RAG_AVAILABLE:
            logger.warning("RAG 라이브러리가 설치되지 않았습니다.")
            self.available = False
            return

        self.available = True
        self._kb_last_modified: Optional[float] = None  # 지식베이스 마지막 수정 시간

        # 경로 설정
        if knowledge_base_path is None:
            knowledge_base_path = os.getenv(
                "KNOWLEDGE_BASE_PATH",
                str(Path(__file__).parent.parent.parent / "knowledge_base")
            )
        if chroma_db_path is None:
            chroma_db_path = os.getenv(
                "CHROMA_DB_PATH",
                str(Path(__file__).parent.parent.parent / "chroma_db")
            )

        self.knowledge_base_path = Path(knowledge_base_path)
        self.chroma_db_path = Path(chroma_db_path)

        # 임베딩 모델 초기화
        try:
            # HF_TOKEN 설정 (있으면 사용, 없으면 무시)
            hf_token = os.environ.get("HF_TOKEN")
            if hf_token:
                os.environ["HUGGINGFACE_HUB_TOKEN"] = hf_token

            # Safetensors 자동 변환 비활성화 (타임아웃 방지)
            os.environ["TRANSFORMERS_OFFLINE"] = "0"  # 온라인 유지
            os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"  # 텔레메트리 비활성화

            self.embeddings = HuggingFaceEmbeddings(
                model_name="dragonkue/BGE-m3-ko",
                model_kwargs={
                    'device': 'cpu',
                    'trust_remote_code': False  # 보안 강화
                },
                encode_kwargs={'normalize_embeddings': True}  # 벡터 정규화 활성화
            )
            logger.info("한국어 임베딩 모델 로드 완료: BGE-m3-ko (1024-dim, 정규화 활성화)")
        except Exception as e:
            logger.warning(f"한국어 임베딩 모델 로드 실패, 기본 모델 사용: {e}")
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                encode_kwargs={'normalize_embeddings': True}  # 벡터 정규화 활성화
            )

        # 텍스트 분할기 (의미적 청킹 전략)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150,
            length_function=len,
            separators=[
                "\n\n\n", "\n\n", "\n", ". ", "。", "! ", "? ", ".", ", ", "，", " ", ""
            ],
            keep_separator=True
        )

        # 벡터 스토어 (지연 로딩)
        self._vectorstore: Optional[Chroma] = None

        # BM25 인덱스 (지연 로딩)
        self._bm25_index: Optional['BM25Okapi'] = None
        self._bm25_documents: List[Document] = []

        # 지식베이스 변경 감지 초기화
        self._update_kb_modified_time()

        logger.info(f"RAG 도구 초기화 완료: {knowledge_base_path}")

    def _get_kb_modified_time(self) -> Optional[float]:
        """지식베이스 디렉토리의 최신 수정 시간 반환"""
        if not self.knowledge_base_path.exists():
            return None

        try:
            latest_time = 0.0
            for ext in ['.txt', '.md', '.pdf', '.docx']:
                for file_path in self.knowledge_base_path.rglob(f"*{ext}"):
                    mtime = file_path.stat().st_mtime
                    if mtime > latest_time:
                        latest_time = mtime
            return latest_time if latest_time > 0 else None
        except Exception as e:
            logger.error(f"지식베이스 수정 시간 확인 실패: {e}")
            return None

    def _update_kb_modified_time(self):
        """지식베이스 수정 시간 업데이트"""
        self._kb_last_modified = self._get_kb_modified_time()
        if self._kb_last_modified:
            logger.info(f"지식베이스 마지막 수정 시간: {self._kb_last_modified}")

    def _check_kb_changed(self) -> bool:
        """지식베이스가 변경되었는지 확인"""
        current_time = self._get_kb_modified_time()
        if current_time is None or self._kb_last_modified is None:
            return False

        changed = current_time > self._kb_last_modified
        if changed:
            logger.info("지식베이스 변경 감지! 캐시를 클리어합니다.")
            cache_manager = get_cache_manager()
            cache_manager.clear(prefix="rag")
            cache_manager.clear(prefix="llm")
            self._kb_last_modified = current_time

        return changed

    def _extract_keywords_from_text(self, text: str, max_keywords: int = 5) -> List[str]:
        """텍스트에서 핵심 키워드 추출"""
        stopwords = {'은', '는', '이', '가', '을', '를', '의', '에', '로', '와', '과', '도', '만',
                     '하다', '있다', '되다', '않다', '같다', '위해', '대한', '통해', '따라'}

        words = text.split()
        keywords = []

        for word in words:
            if len(word) >= 2 and word not in stopwords:
                clean_word = ''.join(c for c in word if c.isalnum() or c in ['_', '-'])
                if clean_word and clean_word not in keywords:
                    keywords.append(clean_word)
                    if len(keywords) >= max_keywords:
                        break

        return keywords

    def _load_documents(self) -> List[Document]:
        """지식베이스에서 문서 로드 및 청킹"""
        documents = []

        if not self.knowledge_base_path.exists():
            logger.warning(f"지식베이스 경로가 존재하지 않습니다: {self.knowledge_base_path}")
            return documents

        # 문서 파싱 함수들
        def parse_text_file(file_path: Path) -> str:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"텍스트 파일 읽기 실패 ({file_path}): {e}")
                return ""

        def parse_pdf(file_path: Path) -> str:
            try:
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
            except ImportError:
                logger.warning("pypdf가 설치되지 않았습니다. PDF 파일은 건너뜁니다.")
                return ""
            except Exception as e:
                logger.error(f"PDF 파싱 실패 ({file_path}): {e}")
                return ""

        def parse_docx(file_path: Path) -> str:
            try:
                from docx import Document as DocxDocument
                doc = DocxDocument(file_path)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            except ImportError:
                logger.warning("python-docx가 설치되지 않았습니다. DOCX 파일은 건너뜁니다.")
                return ""
            except Exception as e:
                logger.error(f"DOCX 파싱 실패 ({file_path}): {e}")
                return ""

        # 지원하는 파일 확장자 및 파서 매핑
        parsers = {
            '.txt': parse_text_file,
            '.md': parse_text_file,
            '.pdf': parse_pdf,
            '.docx': parse_docx,
        }

        # 모든 문서 파일 찾기
        for ext, parser_func in parsers.items():
            for file_path in self.knowledge_base_path.rglob(f"*{ext}"):
                try:
                    logger.info(f"문서 로드 중: {file_path.name}")

                    content = parser_func(file_path)
                    if not content.strip():
                        logger.warning(f"빈 문서: {file_path.name}")
                        continue

                    chunks = self.text_splitter.split_text(content)

                    for i, chunk in enumerate(chunks):
                        # 청크 위치 정보
                        if len(chunks) == 1:
                            position = "full"
                        elif i == 0:
                            position = "beginning"
                        elif i == len(chunks) - 1:
                            position = "end"
                        else:
                            position = "middle"

                        # 섹션 제목 추출
                        section_title = ""
                        chunk_lines = chunk.split('\n')
                        for line in chunk_lines[:3]:
                            line = line.strip()
                            if line.startswith('#'):
                                section_title = line.lstrip('#').strip()
                                break

                        # 키워드 추출
                        keywords = self._extract_keywords_from_text(chunk, max_keywords=5)

                        doc = Document(
                            page_content=chunk,
                            metadata={
                                'source': str(file_path),
                                'filename': file_path.name,
                                'extension': ext,
                                'chunk_index': i,
                                'total_chunks': len(chunks),
                                'position': position,
                                'chunk_length': len(chunk),
                                'section_title': section_title,
                                'keywords': ', '.join(keywords),
                            }
                        )
                        documents.append(doc)

                    logger.info(f"✓ 문서 로드 완료: {file_path.name} ({len(chunks)}개 청크)")

                except Exception as e:
                    logger.error(f"문서 로드 실패 ({file_path}): {e}")
                    continue

        logger.info(f"총 {len(documents)}개 문서 청크 로드 완료")
        return documents

    def _build_vectorstore_if_needed(self) -> bool:
        """벡터 DB가 없으면 자동으로 구축"""
        if self._vectorstore is not None:
            return True

        if self.chroma_db_path.exists() and any(self.chroma_db_path.iterdir()):
            return False

        if not self.knowledge_base_path.exists():
            logger.warning(f"지식베이스 경로가 존재하지 않습니다: {self.knowledge_base_path}")
            return False

        # 문서 찾기
        has_documents = False
        for ext in ['.txt', '.md', '.pdf', '.docx']:
            if any(self.knowledge_base_path.rglob(f"*{ext}")):
                has_documents = True
                break

        if not has_documents:
            logger.warning("지식베이스에 문서가 없습니다. 벡터 DB를 구축할 수 없습니다.")
            return False

        # 벡터 DB 자동 구축
        logger.info("벡터 DB가 없습니다. 자동으로 구축을 시작합니다...")
        try:
            documents = self._load_documents()

            if not documents:
                logger.warning("로드할 문서가 없습니다.")
                return False

            # Chroma DB 생성 (cosine distance 사용)
            logger.info(f"벡터 DB 구축 중... ({len(documents)}개 문서 청크)")
            self._vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=str(self.chroma_db_path),
                collection_metadata={"hnsw:space": "cosine"}
            )

            logger.info(f"✓ 벡터 DB 구축 완료: {len(documents)}개 문서 (distance: cosine)")

            return True

        except Exception as e:
            logger.error(f"벡터 DB 구축 실패: {e}")
            return False

    @property
    def vectorstore(self) -> Optional[Chroma]:
        """벡터 스토어 지연 로딩 및 자동 구축"""
        if self._vectorstore is None and self.available:
            try:
                self._build_vectorstore_if_needed()

                if self.chroma_db_path.exists() and any(self.chroma_db_path.iterdir()):
                    if self._vectorstore is None:
                        self._vectorstore = Chroma(
                            persist_directory=str(self.chroma_db_path),
                            embedding_function=self.embeddings
                        )

                    # 진단: ChromaDB distance 함수 확인
                    try:
                        collection = self._vectorstore._collection
                        if collection and hasattr(collection, 'metadata') and collection.metadata:
                            metadata = collection.metadata
                            distance_function = metadata.get('hnsw:space', 'unknown')
                            logger.info(f"ChromaDB distance 함수: {distance_function}")
                        else:
                            logger.info("ChromaDB distance 함수: 확인 불가 (metadata 없음)")
                    except Exception as e:
                        logger.warning(f"Distance 함수 확인 실패: {e}")

                    logger.info("벡터 DB 로드 완료")
                else:
                    logger.warning("벡터 DB가 아직 구축되지 않았습니다.")
            except Exception as e:
                logger.error(f"벡터 스토어 로드 실패: {e}")

        return self._vectorstore

    def _normalize_query(self, query: str) -> str:
        """검색 쿼리 정규화"""
        import re
        normalized = re.sub(r'\s+', ' ', query)
        normalized = normalized.strip()
        return normalized

    def _tokenize(self, text: str) -> List[str]:
        """텍스트를 토큰으로 분할 (한국어/영어 지원)"""
        import re
        text = text.lower()
        tokens = re.findall(r'[가-힣a-z0-9]+', text)
        return tokens

    def _build_bm25_index(self) -> bool:
        """BM25 인덱스 빌드"""
        if not self.available:
            return False

        try:
            if self.vectorstore is not None:
                collection = self.vectorstore._collection
                results = collection.get(include=['documents', 'metadatas'])

                if not results or not results['documents']:
                    logger.warning("BM25 인덱스 구축 실패: 문서가 없습니다.")
                    return False

                self._bm25_documents = []
                for i, (doc_text, metadata) in enumerate(zip(results['documents'], results['metadatas'])):
                    doc = Document(page_content=doc_text, metadata=metadata or {})
                    self._bm25_documents.append(doc)

            else:
                self._bm25_documents = self._load_documents()

            if not self._bm25_documents:
                logger.warning("BM25 인덱스 구축 실패: 문서가 없습니다.")
                return False

            tokenized_corpus = [
                self._tokenize(doc.page_content)
                for doc in self._bm25_documents
            ]

            self._bm25_index = BM25Okapi(tokenized_corpus)
            logger.info(f"✓ BM25 인덱스 구축 완료: {len(self._bm25_documents)}개 문서")
            return True

        except Exception as e:
            logger.error(f"BM25 인덱스 구축 실패: {e}")
            return False

    @property
    def bm25_index(self) -> Optional['BM25Okapi']:
        """BM25 인덱스 지연 로딩"""
        if self._bm25_index is None and self.available:
            self._build_bm25_index()
        return self._bm25_index

    def search_documents(self, query: str, k: int = 3, similarity_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        문서 검색 (코사인 유사도 기반)

        Args:
            query: 검색 쿼리
            k: 반환할 문서 수
            similarity_threshold: 코사인 유사도 임계값

        Returns:
            관련 문서 리스트
        """
        if not self.available or self.vectorstore is None:
            return []

        self._check_kb_changed()

        cache_manager = get_cache_manager()
        cache_content = f"{query}|k={k}|threshold={similarity_threshold}"
        cached_result = cache_manager.get("rag", cache_content)
        if cached_result is not None:
            return cached_result

        try:
            normalized_query = self._normalize_query(query)
            if normalized_query != query:
                logger.info(f"[검색] 쿼리 정규화: '{query}' → '{normalized_query}'")
            else:
                logger.info(f"[검색] 쿼리: '{query}'")

            try:
                total_docs = self.vectorstore._collection.count()
                logger.info(f"지식베이스: 총 {total_docs}개 문서 청크")
            except Exception as e:
                logger.warning(f"지식베이스 문서 수 확인 실패: {e}")

            docs_with_scores = self.vectorstore.similarity_search_with_score(normalized_query, k=k * 3)
            logger.info(f"벡터 검색: {len(docs_with_scores)}개 결과")

            filtered_docs = []
            seen_keys = set()
            rejected_count = 0

            for idx, (doc, distance) in enumerate(docs_with_scores):
                if distance < 0:
                    similarity = 1.0
                elif distance > 2.0:
                    similarity = max(0.0, 1.0 - (distance / 2.0))
                else:
                    similarity = 1.0 - distance

                if similarity < similarity_threshold:
                    rejected_count += 1
                    continue

                source = doc.metadata.get('source', 'unknown')
                chunk_index = doc.metadata.get('chunk_index', 0)
                doc_key = (source, chunk_index)

                if doc_key in seen_keys:
                    continue

                seen_keys.add(doc_key)

                filtered_docs.append({
                    'content': doc.page_content,
                    'source': source,
                    'filename': doc.metadata.get('filename', 'unknown'),
                    'chunk_index': chunk_index,
                    'similarity': float(similarity)
                })

                if len(filtered_docs) >= k:
                    break

            if not filtered_docs:
                logger.warning(
                    f"임계값 {similarity_threshold} 미만: "
                    f"{len(docs_with_scores)}개 결과 모두 제외됨"
                )
                cache_manager.set("rag", cache_content, [], ttl=3600)
                return []

            logger.info(f"필터링 완료: {len(filtered_docs)}개 선택, {rejected_count}개 제외")

            for idx, doc in enumerate(filtered_docs[:5]):
                logger.info(f"  #{idx+1}: {doc['filename']} (유사도: {doc['similarity']:.3f})")

            cache_manager.set("rag", cache_content, filtered_docs)
            return filtered_docs

        except Exception as e:
            logger.error(f"[검색] 검색 실패: {e}", exc_info=True)
            return []

    def search_documents_hybrid(
        self,
        query: str,
        k: int = 3,
        alpha: float = 0.5,
        similarity_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        하이브리드 검색 (BM25 + 벡터 검색, RRF 사용)

        Args:
            query: 검색 쿼리
            k: 반환할 문서 수
            alpha: 벡터 검색 가중치 (음수면 RRF 사용)
            similarity_threshold: 최소 유사도 임계값

        Returns:
            관련 문서 리스트
        """
        if not self.available:
            return []

        self._check_kb_changed()

        cache_manager = get_cache_manager()
        cache_content = f"hybrid|{query}|k={k}|alpha={alpha}|threshold={similarity_threshold}"
        cached_result = cache_manager.get("rag", cache_content)
        if cached_result is not None:
            return cached_result

        try:
            normalized_query = self._normalize_query(query)
            if normalized_query != query:
                logger.info(f"[하이브리드] 쿼리 정규화: '{query}' → '{normalized_query}'")
            else:
                logger.info(f"[하이브리드] 쿼리: '{query}'")

            try:
                total_docs = self.vectorstore._collection.count()
                logger.info(f"지식베이스: 총 {total_docs}개 문서 청크")
            except Exception as e:
                logger.warning(f"지식베이스 문서 수 확인 실패: {e}")

            # 1. 벡터 검색
            vector_results = {}
            if self.vectorstore is not None:
                vector_docs = self.vectorstore.similarity_search_with_score(normalized_query, k=k * 3)
                print(f"[VECTOR] {len(vector_docs)} results")

                # 진단: 실제 distance 값 확인
                if vector_docs:
                    print(f"[VECTOR] Top 3 (distance → similarity):")
                    for idx, (doc, distance) in enumerate(vector_docs[:3]):
                        filename = doc.metadata.get('filename', 'unknown')
                        similarity = 1.0 - distance
                        status = "HIGH" if similarity >= 0.7 else "MED" if similarity >= 0.5 else "LOW"
                        print(f"  - {filename[:60]}: dist={distance:.4f} → sim={similarity:.4f} [{status}]")

                for doc, distance in vector_docs:
                    doc_key = (doc.metadata.get('source', ''), doc.metadata.get('chunk_index', 0))
                    similarity = max(0.0, 1.0 - min(distance, 2.0))
                    vector_results[doc_key] = {
                        'doc': doc,
                        'score': similarity
                    }

            # 2. BM25 검색
            bm25_results = {}
            if self.bm25_index is not None and len(self._bm25_documents) > 0:
                tokenized_query = self._tokenize(normalized_query)
                bm25_scores = self.bm25_index.get_scores(tokenized_query)

                max_score = max(bm25_scores) if len(bm25_scores) > 0 and max(bm25_scores) > 0 else 1.0
                normalized_scores = [score / max_score for score in bm25_scores]

                top_indices = np.argsort(normalized_scores)[::-1][:k * 3]
                print(f"[BM25] {len(top_indices)} results")

                for idx in top_indices:
                    doc = self._bm25_documents[idx]
                    doc_key = (doc.metadata.get('source', ''), doc.metadata.get('chunk_index', 0))
                    bm25_results[doc_key] = {
                        'doc': doc,
                        'score': normalized_scores[idx]
                    }

            # 3. 점수 결합 (RRF 또는 가중 평균)
            combined_results = {}
            all_doc_keys = set(vector_results.keys()) | set(bm25_results.keys())

            use_rrf = alpha < 0  # 음수 alpha는 RRF 활성화 신호

            if use_rrf:
                # RRF 방식: 순위로 정렬, 점수는 vector+bm25 평균 사용
                k_rrf = 60

                # Vector 결과 순위 생성
                vector_sorted = sorted(
                    vector_results.items(),
                    key=lambda x: x[1]['score'],
                    reverse=True
                )
                vector_ranks = {doc_key: rank for rank, (doc_key, _) in enumerate(vector_sorted)}

                # BM25 결과 순위 생성
                bm25_sorted = sorted(
                    bm25_results.items(),
                    key=lambda x: x[1]['score'],
                    reverse=True
                )
                bm25_ranks = {doc_key: rank for rank, (doc_key, _) in enumerate(bm25_sorted)}

                # RRF로 순위 계산 (Numpy vectorization으로 최적화)
                all_doc_keys_list = list(all_doc_keys)

                # Vectorized rank extraction
                vector_ranks_array = np.array([
                    vector_ranks.get(doc_key, len(vector_results))
                    for doc_key in all_doc_keys_list
                ])
                bm25_ranks_array = np.array([
                    bm25_ranks.get(doc_key, len(bm25_results))
                    for doc_key in all_doc_keys_list
                ])

                # Vectorized RRF calculation: 1/(k + rank + 1)
                rrf_rank_scores = (1.0 / (k_rrf + vector_ranks_array + 1) +
                                   1.0 / (k_rrf + bm25_ranks_array + 1))

                # Vectorized score extraction
                vector_scores = np.array([
                    vector_results.get(doc_key, {}).get('score', 0.0)
                    for doc_key in all_doc_keys_list
                ])
                bm25_scores = np.array([
                    bm25_results.get(doc_key, {}).get('score', 0.0)
                    for doc_key in all_doc_keys_list
                ])

                # 최종 점수: vector와 bm25의 평균 (절대적 품질 유지)
                hybrid_scores = (vector_scores + bm25_scores) / 2.0

                # 결과 저장
                for idx, doc_key in enumerate(all_doc_keys_list):
                    doc = vector_results.get(doc_key, bm25_results.get(doc_key, {})).get('doc')

                    if doc is not None:
                        combined_results[doc_key] = {
                            'doc': doc,
                            'rrf_rank_score': float(rrf_rank_scores[idx]),  # 정렬용
                            'hybrid_score': float(hybrid_scores[idx]),  # 임계값 필터링용
                            'vector_score': float(vector_scores[idx]),
                            'bm25_score': float(bm25_scores[idx])
                        }
            else:
                # 가중 평균 방식
                for doc_key in all_doc_keys:
                    vector_score = vector_results.get(doc_key, {}).get('score', 0.0)
                    bm25_score = bm25_results.get(doc_key, {}).get('score', 0.0)

                    hybrid_score = alpha * vector_score + (1.0 - alpha) * bm25_score

                    doc = vector_results.get(doc_key, bm25_results.get(doc_key, {})).get('doc')

                    if doc is not None:
                        combined_results[doc_key] = {
                            'doc': doc,
                            'hybrid_score': hybrid_score,
                            'vector_score': vector_score,
                            'bm25_score': bm25_score
                        }

            # 4. 하이브리드 점수로 정렬
            if use_rrf:
                sorted_results = sorted(
                    combined_results.items(),
                    key=lambda x: x[1].get('rrf_rank_score', x[1]['hybrid_score']),
                    reverse=True
                )
            else:
                sorted_results = sorted(
                    combined_results.items(),
                    key=lambda x: x[1]['hybrid_score'],
                    reverse=True
                )

            # 5. 필터링 및 결과 생성
            filtered_docs = []
            rejected_count = 0
            for idx, (doc_key, result) in enumerate(sorted_results):
                hybrid_score = result['hybrid_score']

                if hybrid_score < similarity_threshold:
                    rejected_count += 1
                    continue

                doc = result['doc']
                filtered_docs.append({
                    'content': doc.page_content,
                    'source': doc.metadata.get('source', 'unknown'),
                    'filename': doc.metadata.get('filename', 'unknown'),
                    'chunk_index': doc.metadata.get('chunk_index', 0),
                    'similarity': float(hybrid_score),
                    'vector_score': float(result['vector_score']),
                    'bm25_score': float(result['bm25_score'])
                })

                if len(filtered_docs) >= k:
                    break

            if not filtered_docs:
                logger.warning(
                    f"임계값 {similarity_threshold} 미만: "
                    f"{len(sorted_results)}개 결과 모두 제외됨"
                )
                cache_manager.set("rag", cache_content, [], ttl=3600)
                return []

            logger.info(f"필터링 완료: {len(filtered_docs)}개 선택, {rejected_count}개 제외")

            logger.info(f"최종 결과 (하이브리드, alpha={alpha}): {len(filtered_docs)}개")
            for idx, doc in enumerate(filtered_docs[:5]):
                logger.info(
                    f"  #{idx+1}: {doc['filename']} "
                    f"(hybrid: {doc['similarity']:.3f} = vector: {doc['vector_score']:.3f} + bm25: {doc['bm25_score']:.3f})"
                )

            cache_manager.set("rag", cache_content, filtered_docs)
            return filtered_docs

        except Exception as e:
            logger.error(f"[하이브리드] 검색 실패: {e}", exc_info=True)
            return []


# 전역 RAG 도구 인스턴스
_rag_tool: Optional[RAGTool] = None


def get_rag_tool() -> RAGTool:
    """RAG 도구 싱글톤 인스턴스 반환"""
    global _rag_tool
    if _rag_tool is None:
        _rag_tool = RAGTool()
    return _rag_tool
