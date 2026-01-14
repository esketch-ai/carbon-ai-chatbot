# 📋 CarbonAI React-Agent 전체 코드 상세 설명

## 🏗️ 전체 아키텍처 개요

```
사용자 질문
    ↓
LangGraph (graph.py)
    ├─> call_model (Claude API 호출)
    │   ├─> 시스템 프롬프트 (prompts.py)
    │   ├─> 카테고리별 특화 프롬프트
    │   └─> 도구 선택 (tool_calls)
    │
    ├─> tools (도구 실행)
    │   ├─> search_knowledge_base (RAG)
    │   │   └─> rag_tool.py (Chroma DB 벡터 검색)
    │   │
    │   ├─> classify_customer_segment (고객 분류)
    │   │
    │   ├─> search (Tavily 웹 검색)
    │   │
    │   └─> MCP 도구 (19개)
    │       └─> sse_mcp_client.py
    │           ├─> SSE 리스너 (응답 수신)
    │           └─> POST 요청 (명령 전송)
    │
    ├─> Cache (cache_manager.py)
    │   ├─> Redis (선택)
    │   └─> Memory (기본)
    │
    └─> Mermaid 변환 (utils.py)
        └─> kroki.io API
```

---

## 📁 파일별 상세 설명

### 1. **state.py** - 대화 상태 관리

```python
@dataclass
class InputState:
    messages: Annotated[Sequence[AnyMessage], add_messages]
```

**역할**: LangGraph의 상태(state)를 정의합니다.

**핵심 개념**:
- `messages`: 대화 히스토리를 저장
- `add_messages`: LangGraph의 특수 어노테이션으로, 메시지를 "추가"하는 방식으로 상태를 업데이트
- 메시지 패턴:
  1. `HumanMessage` - 사용자 입력
  2. `AIMessage + tool_calls` - AI가 도구 선택
  3. `ToolMessage` - 도구 실행 결과
  4. `AIMessage` - 최종 답변
  5. (반복)

```python
@dataclass
class State(InputState):
    is_last_step: IsLastStep = field(default=False)
```

**추가 상태**:
- `is_last_step`: recursion_limit에 도달했는지 표시하는 관리 변수

---

### 2. **configuration.py** - 설정 관리

```python
@dataclass(kw_only=True)
class Configuration:
    system_prompt: str = prompts.SYSTEM_PROMPT
    model: str = "claude-haiku-4-5-20251001"
    max_search_results: int = 10
    category: Optional[str] = None  # 탄소배출권/규제대응/고객상담
```

**역할**: 에이전트의 설정을 정의하는 데이터 클래스

**주요 설정**:
1. `system_prompt`: AI의 행동 지침 (prompts.py에서 가져옴)
2. `model`: 사용할 Claude 모델
3. `max_search_results`: 웹 검색 결과 개수
4. **`category`**: 카테고리별 특화 답변 (중요!)
   - `탄소배출권`: 배출권 거래, NET-Z 플랫폼
   - `규제대응`: Scope 배출량, 법규, 보고서
   - `고객상담`: 서비스 안내, 솔루션 제안

**팩토리 메서드**:
```python
@classmethod
def from_runnable_config(cls, config: RunnableConfig):
    # RunnableConfig에서 Configuration 객체 생성
    configurable = config.get("configurable") or {}
    return cls(**{k: v for k, v in configurable.items() if k in _fields})
```

---

### 3. **prompts.py** - 시스템 프롬프트

```python
SYSTEM_PROMPT = """당신은 후시파트너스의 탄소 배출권 전문 상담 AI 어시스턴트 "CarbonAI"입니다.

**주요 역할:**
- 탄소 배출권 관련 질문에 정확하고 친절하게 답변
- 회사 지식베이스에서 관련 정보를 검색하여 제공
- 고객 유형별 맞춤형 상담 제공
```

**역할**: Claude가 따를 행동 지침

**주요 구성**:
1. **역할 정의**: 탄소 배출권 전문 상담 AI
2. **사용 가능한 도구 설명**:
   - `search_knowledge_base`: 벡터 검색
   - `classify_customer_segment`: 고객 분류
   - `search`: 웹 검색
   - MCP 도구들 (자동으로 추가됨)

3. **Mermaid 다이어그램 활용 가이드**:
   ```
   - flowchart: 프로세스/절차
   - sequenceDiagram: 시스템 상호작용
   - stateDiagram: 상태 변화
   - gantt: 일정
   - pie: 비율
   ```

4. **답변 규칙**:
   - 먼저 지식베이스 검색
   - 문서 기반 답변
   - 친절하고 전문적인 톤
   - 출처 명시
   - Mermaid 적극 활용

5. **고객 세그먼트별 맞춤 답변**:
   - 배출권_보유자: 활용 방법, 판매 전략
   - 배출권_구매자: 구매 절차, 가격 정보
   - 배출권_판매자: 판매 채널, 시장 분석
   - 배출권_생성_희망자: 프로젝트 개발
   - 일반: 기본 개념, 플랫폼 소개

---

### 4. **utils.py** - 유틸리티 함수

#### 4.1 메시지 텍스트 추출

```python
def get_message_text(msg: BaseMessage) -> str:
    """메시지에서 텍스트 추출"""
    content = msg.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    else:
        # 멀티모달 (리스트)
        txts = [c if isinstance(c, str) else (c.get("text") or "") for c in content]
        return "".join(txts).strip()
```

#### 4.2 Mermaid → 이미지 변환 (핵심!)

```python
def mermaid_to_image_url(mermaid_code: str, output_format: str = "svg") -> str:
    """Mermaid 코드를 kroki.io API로 이미지 URL 생성"""
    # 1. zlib으로 압축
    compressed = zlib.compress(mermaid_code.encode('utf-8'), level=9)

    # 2. base64 URL-safe 인코딩
    encoded = base64.urlsafe_b64encode(compressed).decode('ascii')

    # 3. kroki.io URL 생성
    url = f"https://kroki.io/mermaid/{output_format}/{encoded}"
    return url
```

**왜 이렇게 하나?**:
- Claude가 Mermaid 코드를 출력하면 자동으로 이미지로 변환
- 사용자가 시각적으로 보기 좋음
- kroki.io는 무료 다이어그램 렌더링 서비스

```python
def detect_and_convert_mermaid(content: str) -> str:
    """
    ```mermaid ... ``` 패턴을 찾아서
    ![Mermaid Diagram](kroki_url) 마크다운 이미지로 변환
    """
    mermaid_blocks = extract_mermaid_blocks(content)

    for full_match, mermaid_code, start_pos, end_pos in reversed(mermaid_blocks):
        image_url = mermaid_to_image_url(mermaid_code)
        markdown_image = f"![{diagram_type}]({image_url})"
        result = result[:start_pos] + markdown_image + result[end_pos:]

    return result
```

---

### 5. **cache_manager.py** - 캐시 관리

#### 5.1 캐시 구조

```python
class CacheManager:
    def __init__(self, redis_url=None, default_ttl=86400, use_redis=True):
        self._redis_client = None  # Redis 클라이언트
        self._memory_cache: Dict[str, tuple[Any, datetime]] = {}  # 메모리 캐시
```

**2단계 캐싱**:
1. **Redis** (선택적): 분산 환경에서 공유 캐시
2. **Memory** (기본): 단일 프로세스 내 빠른 캐시

#### 5.2 캐시 키 생성

```python
def _generate_cache_key(self, prefix: str, content: str) -> str:
    """SHA256 해시 기반 캐시 키"""
    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    return f"{prefix}:{content_hash}"
```

**예시**:
- `rag:a1b2c3d4e5f6g7h8` - RAG 검색 결과
- `llm:9i8j7k6l5m4n3o2p` - LLM 응답

#### 5.3 캐시 사용 플로우

```python
# 1. 캐시 조회
cached = cache_manager.get("rag", query)
if cached:
    return cached  # 캐시 HIT

# 2. 실제 작업 수행
result = expensive_operation(query)

# 3. 캐시 저장 (24시간)
cache_manager.set("rag", query, result, ttl=86400)
```

**장점**:
- 동일한 질문에 즉시 응답
- LLM API 비용 절감
- 벡터 검색 부하 감소

---

### 6. **rag_tool.py** - RAG 검색 도구

#### 6.1 초기화

```python
class RAGTool:
    def __init__(self, knowledge_base_path=None, chroma_db_path=None):
        # 한국어 임베딩 모델
        self.embeddings = HuggingFaceEmbeddings(
            model_name="jhgan/ko-sroberta-multitask",  # 한국어 특화
            model_kwargs={'device': 'cpu'}
        )

        # 텍스트 분할기 (청킹)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # 1000자 단위
            chunk_overlap=200  # 200자 겹침
        )

        # 벡터 스토어 (지연 로딩)
        self._vectorstore: Optional[Chroma] = None
```

**임베딩 모델 선택 이유**:
- `jhgan/ko-sroberta-multitask`: 한국어 문서에 최적화
- 대안: `sentence-transformers/all-MiniLM-L6-v2` (영어/다국어)

#### 6.2 문서 로드 및 청킹

```python
def _load_documents(self) -> List[Document]:
    """지식베이스에서 문서 로드"""
    # 지원 파일: .txt, .md, .pdf, .docx
    parsers = {
        '.txt': parse_text_file,
        '.md': parse_text_file,
        '.pdf': parse_pdf,  # pypdf 사용
        '.docx': parse_docx,  # python-docx 사용
    }

    for ext, parser_func in parsers.items():
        for file_path in self.knowledge_base_path.rglob(f"*{ext}"):
            # 파싱
            content = parser_func(file_path)

            # 청킹 (1000자 단위, 200자 겹침)
            chunks = self.text_splitter.split_text(content)

            # Document 객체 생성
            for i, chunk in enumerate(chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        'source': str(file_path),
                        'filename': file_path.name,
                        'chunk_index': i,
                        'total_chunks': len(chunks)
                    }
                )
                documents.append(doc)
```

**왜 청킹이 필요한가?**:
- 긴 문서를 통째로 임베딩하면 정보 손실
- 1000자 정도가 적당한 단위
- 200자 겹침으로 문맥 유지

#### 6.3 벡터 DB 자동 구축

```python
def _build_vectorstore_if_needed(self) -> bool:
    """벡터 DB가 없으면 자동 구축"""
    if self.chroma_db_path.exists():
        return False  # 이미 있음

    documents = self._load_documents()

    # Chroma DB 생성
    self._vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=self.embeddings,
        persist_directory=str(self.chroma_db_path)
    )
```

**자동화의 장점**:
- 처음 실행 시 자동으로 벡터 DB 구축
- 지식베이스 추가/수정 시 자동 감지 및 갱신

#### 6.4 키워드 추출 (중요!)

```python
def _extract_keywords(self, query: str) -> str:
    """LLM으로 쿼리에서 핵심 키워드 추출"""
    llm = ChatAnthropic(model="claude-haiku-4-5", temperature=0)

    prompt = f"""다음 질문에서 핵심 키워드를 추출하세요. 조사, 의문사, 요청어는 제거하고 명사 위주로 추출하세요.
중요한 키워드는 모두 포함하세요. 최소 3-5개 이상의 키워드를 추출하세요.

질문: {query}

핵심 키워드 (공백으로 구분, 최소 3개 이상):"""

    response = llm.invoke([HumanMessage(content=prompt)])
    keywords = response.content.strip()
    return keywords
```

**왜 키워드 추출이 필요한가?**:
- 원본 질문: "배출권을 구매하려면 어떤 절차를 거쳐야 하나요?"
- 키워드: "배출권 구매 절차"
- 벡터 검색 시 더 정확한 매칭

#### 6.5 문서 검색 (핵심 알고리즘)

```python
def search_documents(self, query: str, k: int = 3, similarity_threshold: float = 0.5):
    """
    1. 캐시 확인
    2. 키워드 추출
    3. 벡터 검색 (키워드 + 원본 모두)
    4. 유사도 필터링
    5. 중복 제거
    6. 상위 k개 반환
    7. 결과 캐싱
    """

    # 1. 캐시 확인
    cached_result = cache_manager.get("rag", cache_content)
    if cached_result:
        return cached_result

    # 2. 키워드 추출
    keyword_query = self._extract_keywords(query)

    # 3. 벡터 검색 (키워드)
    keyword_docs = self.vectorstore.similarity_search_with_score(keyword_query, k=k*3)

    # 4. 벡터 검색 (원본, 키워드와 다르면)
    if keyword_query != query:
        original_docs = self.vectorstore.similarity_search_with_score(query, k=k*3)
        all_docs_with_scores.extend(original_docs)

    # 5. 유사도 정렬 및 필터링
    for doc, distance in docs_with_scores:
        similarity = 1.0 - distance  # 코사인 거리 → 유사도 변환

        if similarity < similarity_threshold:  # 0.5 미만 제외
            continue

        # 중복 제거
        doc_key = (source, chunk_index)
        if doc_key in seen_keys:
            continue

        filtered_docs.append({
            'content': doc.page_content,
            'source': source,
            'filename': filename,
            'chunk_index': chunk_index,
            'similarity': similarity
        })

        if len(filtered_docs) >= k:
            break

    # 6. 캐싱
    cache_manager.set("rag", cache_content, filtered_docs)
    return filtered_docs
```

**유사도 계산**:
- Chroma DB는 L2 거리 또는 코사인 거리 사용
- 거리 (distance): 0 ~ 2 (작을수록 유사)
- 유사도 (similarity): `1.0 - distance`
- 임계값 0.5: 50% 이상 유사한 문서만 반환

---

### 7. **graph.py** - LangGraph 워크플로우 (핵심!)

#### 7.1 카테고리별 프롬프트 생성

```python
def _get_category_prompt(base_prompt: str, category: str) -> str:
    """카테고리별 특화 프롬프트 추가"""
    category_prompts = {
        "탄소배출권": """
**카테고리: 탄소배출권 전문 상담**

**특화 답변 포인트:**
- 배출권 유형별 상세 설명 (KOC, KCU, KAU 등)
- 배출권 거래 절차 및 시장 동향
- NET-Z 플랫폼 사용법 및 기능
- 배출권 가격 정보 및 시장 분석
- 프로세스는 Mermaid 다이어그램으로 시각화
""",
        "규제대응": """
**카테고리: 규제대응 전문 상담**

**특화 답변 포인트:**
- Scope 1, 2, 3 배출량 측정 방법
- 탄소 배출량 보고 의무 및 절차
- 규제 변경사항 및 대응 방안
- ESG 보고서 작성 가이드
- 프로세스는 Mermaid 다이어그램으로 시각화
""",
        "고객상담": """
**카테고리: 고객상담 전문 상담**

**특화 답변 포인트:**
- 후시파트너스 서비스 소개
- 기업 규모별 추천 솔루션
- 서비스 이용 절차 안내
- 비용 및 요금제 정보
- 비교는 Mermaid 다이어그램으로 시각화
"""
    }

    category_prompt = category_prompts.get(category, "")
    if category_prompt:
        return base_prompt + "\n\n" + category_prompt
    return base_prompt
```

**효과**:
- "탄소배출권" 카테고리: 거래 중심 답변
- "규제대응" 카테고리: 법규/보고서 중심 답변
- "고객상담" 카테고리: 서비스 안내 중심 답변

#### 7.2 LLM 응답 캐싱

```python
def _serialize_messages_for_cache(messages, system_message, category):
    """메시지 히스토리를 캐시 키로 직렬화"""
    simplified = []
    for msg in messages:
        if isinstance(msg, (HumanMessage, AIMessage, SystemMessage)):
            simplified.append({
                "type": msg.__class__.__name__,
                "content": str(msg.content)[:500]  # 500자만
            })
        elif isinstance(msg, ToolMessage):
            return None  # 툴 메시지 있으면 캐싱 안 함

    cache_data = {
        "system": system_message[:200],
        "category": category,
        "messages": simplified
    }
    return json.dumps(cache_data, ensure_ascii=False, sort_keys=True)
```

**왜 툴 메시지가 있으면 캐싱 안 하나?**:
- 툴 호출 결과는 동적 (시간에 따라 변함)
- 예: "오늘 배출권 가격은?" → 매일 다른 결과

#### 7.3 call_model - LLM 호출

```python
async def call_model(state: State, config: RunnableConfig):
    """LLM 호출 및 응답 처리"""

    # 1. 설정 로드
    configuration = Configuration.from_runnable_config(config)

    # 2. MCP 도구 포함한 전체 도구 로드
    all_tools = await get_all_tools()

    # 3. Claude 모델 초기화
    llm = ChatAnthropic(temperature=0.1, model=configuration.model)
    model = llm.bind_tools(all_tools)  # 도구 바인딩

    # 4. 카테고리별 프롬프트 적용
    base_prompt = configuration.system_prompt
    if configuration.category:
        base_prompt = _get_category_prompt(base_prompt, configuration.category)

    system_message = base_prompt.format(system_time=datetime.now(tz=UTC).isoformat())

    # 5. 캐시 확인
    cache_key_content = _serialize_messages_for_cache(
        state.messages, system_message, configuration.category or ""
    )

    if cache_key_content:
        cached_response = cache_manager.get("llm", cache_key_content)
        if cached_response:
            return {"messages": [AIMessage(**cached_response)]}

    # 6. LLM 호출
    response = await model.ainvoke([
        {"role": "system", "content": system_message},
        *state.messages
    ])

    # 7. 마지막 단계인데 아직 툴 호출하려고 하면 종료
    if state.is_last_step and response.tool_calls:
        return {
            "messages": [AIMessage(
                id=response.id,
                content="Sorry, I could not find an answer to your question in the specified number of steps."
            )]
        }

    # 8. Mermaid 코드 자동 변환
    if response.content and isinstance(response.content, str):
        converted_content = detect_and_convert_mermaid(response.content)
        if converted_content != response.content:
            response = AIMessage(
                id=response.id,
                content=converted_content,
                tool_calls=response.tool_calls,
                additional_kwargs=response.additional_kwargs,
            )

    # 9. LLM 응답 캐싱 (툴 호출 없는 최종 응답만)
    if cache_key_content and not response.tool_calls:
        cache_data = {
            "content": response.content,
            "additional_kwargs": response.additional_kwargs,
            "id": response.id
        }
        cache_manager.set("llm", cache_key_content, cache_data)

    return {"messages": [response]}
```

#### 7.4 call_tools - 도구 실행

```python
async def call_tools(state: State):
    """동적으로 도구 로드 및 실행"""
    all_tools = await get_all_tools()  # MCP 도구 포함
    tool_node = ToolNode(all_tools)
    return await tool_node.ainvoke(state)
```

**ToolNode란?**:
- LangGraph의 내장 노드
- `state.messages`에서 `tool_calls` 추출
- 해당 도구 실행
- 결과를 `ToolMessage`로 반환

#### 7.5 그래프 구축

```python
# StateGraph 생성
builder = StateGraph(State, input=InputState, config_schema=Configuration)

# 노드 추가
builder.add_node(call_model)  # LLM 호출
builder.add_node("tools", call_tools)  # 도구 실행

# 엔트리포인트
builder.add_edge("__start__", "call_model")

# 조건부 엣지
def route_model_output(state: State):
    """LLM 응답에 따라 다음 노드 결정"""
    last_message = state.messages[-1]

    if not last_message.tool_calls:
        return "__end__"  # 툴 호출 없으면 종료

    return "tools"  # 툴 호출 있으면 tools 노드로

builder.add_conditional_edges("call_model", route_model_output)

# 사이클 생성
builder.add_edge("tools", "call_model")  # 툴 실행 후 다시 LLM으로

# 컴파일
graph = builder.compile(name="ReAct Agent")
```

**실행 흐름**:
```
__start__
  → call_model (LLM 호출)
     ├─> 툴 호출 없음 → __end__
     └─> 툴 호출 있음 → tools
           → call_model
              ├─> 툴 호출 없음 → __end__
              └─> 툴 호출 있음 → tools (반복)
```

---

### 8. **tools.py** - 도구 정의 및 MCP 통합

#### 8.1 기본 도구들

##### 8.1.1 search - Tavily 웹 검색

```python
async def search(query: str) -> Optional[dict[str, Any]]:
    """Tavily 검색 엔진으로 웹 검색"""
    configuration = Configuration.from_context()
    wrapped = TavilySearch(max_results=configuration.max_search_results)
    return await wrapped.ainvoke({"query": query})
```

**용도**: 최신 정보, 시장 가격 등

##### 8.1.2 search_knowledge_base - RAG 검색

```python
@tool
def search_knowledge_base(query: str, k: int = 3):
    """회사 지식베이스에서 관련 문서 검색

    **검색 방식**:
    - LLM으로 쿼리에서 핵심 키워드 추출
    - 키워드와 원본 모두로 검색
    - 코사인 유사도 0.5 이상만 반환
    - 중복 제거

    **중요**: query에는 전체 질문을 그대로 전달!
    """
    rag_tool = get_rag_tool()
    results = rag_tool.search_documents(query, k=k, similarity_threshold=0.5)

    if not results:
        return {
            "status": "no_results",
            "message": "유사도 0.5 이상인 관련 문서를 찾을 수 없습니다.",
            "results": []
        }

    return {
        "status": "success",
        "message": f"{len(results)}개의 관련 문서를 찾았습니다.",
        "results": results
    }
```

##### 8.1.3 classify_customer_segment - 고객 분류

```python
@tool
def classify_customer_segment(question: str):
    """키워드 기반 고객 세그먼트 분류"""
    question_lower = question.lower()

    if any(kw in question_lower for kw in ['보유', '가지고', '소유']):
        segment = "배출권_보유자"
    elif any(kw in question_lower for kw in ['구매', '사고 싶']):
        segment = "배출권_구매자"
    elif any(kw in question_lower for kw in ['판매', '팔고 싶']):
        segment = "배출권_판매자"
    elif any(kw in question_lower for kw in ['생성', '만들', '프로젝트']):
        segment = "배출권_생성_희망자"
    else:
        segment = "일반"

    return {"segment": segment, "confidence": "high" if segment != "일반" else "medium"}
```

#### 8.2 MCP 통합 (핵심!)

##### 8.2.1 MCP 클라이언트 관리

```python
_netz_mcp_client: Optional[SSEMCPClient] = None

async def _get_mcp_client():
    """MCP 클라이언트 lazy 초기화 및 자동 재연결"""
    global _netz_mcp_client

    # 환경 변수 확인
    netz_enabled = os.getenv("NETZ_MCP_ENABLED", "false").lower() == "true"
    netz_url = os.getenv("NETZ_MCP_URL")

    if not netz_enabled or not netz_url:
        return None

    # 기존 클라이언트가 있으면 상태 확인
    if _netz_mcp_client is not None:
        # SSE 리스너가 살아있는지 확인
        if (_netz_mcp_client.running and
            _netz_mcp_client.sse_task and
            not _netz_mcp_client.sse_task.done()):
            return _netz_mcp_client  # 정상 동작 중
        else:
            # 연결 끊어짐 → 재초기화
            logger.warning("[NET-Z MCP] 클라이언트 연결 끊어짐, 재초기화 중...")
            await _netz_mcp_client.close()
            _netz_mcp_client = None

    # 새 클라이언트 생성
    try:
        _netz_mcp_client = SSEMCPClient(base_url=netz_url)
        await _netz_mcp_client.initialize()
        logger.info("[NET-Z MCP] ✓ 클라이언트 초기화 완료")
        return _netz_mcp_client
    except Exception as e:
        logger.error(f"[NET-Z MCP] 초기화 실패: {e}")
        _netz_mcp_client = None
        return None
```

**자동 재연결 로직**:
1. SSE 리스너 상태 확인
2. 끊어졌으면 자동 재연결
3. 실패해도 에러 안 냄 (None 반환)

##### 8.2.2 MCP 도구 변환 (핵심!)

```python
def _create_mcp_tool(mcp_tool_def: Dict[str, Any]):
    """MCP 도구 정의 → LangChain 도구 변환"""

    tool_name = mcp_tool_def["name"]
    tool_description = mcp_tool_def.get("description", "")
    input_schema = mcp_tool_def.get("inputSchema", {})

    # 동적 함수 생성
    async def mcp_tool_wrapper(**kwargs):
        max_retries = 2
        for attempt in range(max_retries):
            try:
                client = await _get_mcp_client()

                if client is None:
                    return "오류: NET-Z MCP 서버에 연결할 수 없습니다."

                # MCP 도구 호출
                result = await client.call_tool(tool_name, kwargs)

                # 결과 파싱 (data만 직접 반환)
                content = result.get("content", [])
                if content and len(content) > 0:
                    text_content = content[0].get("text", "{}")
                    data = json.loads(text_content) if isinstance(text_content, str) else text_content
                    return data  # {"year": "2025", "totalEmission": "31.743", ...}

                return result

            except Exception as e:
                # 재시도 로직
                if attempt < max_retries - 1:
                    # 클라이언트 재설정
                    global _netz_mcp_client
                    if _netz_mcp_client:
                        await _netz_mcp_client.close()
                        _netz_mcp_client = None
                    await asyncio.sleep(0.5)
                else:
                    return f"오류: MCP 도구 호출 실패 - {str(e)}"

    mcp_tool_wrapper.__name__ = tool_name
    mcp_tool_wrapper.__doc__ = tool_description

    # Pydantic 스키마 생성 (파라미터 이름 보존!)
    properties = input_schema.get("properties", {})
    required_fields = input_schema.get("required", [])

    fields = {}
    for param_name, param_info in properties.items():
        param_type = param_info.get("type", "string")
        param_desc = param_info.get("description", "")

        # 타입 변환
        python_type = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool
        }.get(param_type, Any)

        # 필수/선택 구분
        if param_name in required_fields:
            fields[param_name] = (python_type, Field(description=param_desc))
        else:
            fields[param_name] = (python_type, Field(default=None, description=param_desc))

    # Pydantic 모델 생성
    if fields:
        ArgsSchema = create_model(f"{tool_name}Schema", **fields)
        return tool(args_schema=ArgsSchema)(mcp_tool_wrapper)
    else:
        return tool(mcp_tool_wrapper)
```

**핵심 포인트**:

1. **파라미터 이름 보존**:
   - MCP 서버: `enterpriseName` (카멜케이스)
   - Pydantic 스키마: `enterpriseName` (그대로 유지)
   - Claude: `enterpriseName`로 호출

2. **반환 값 단순화**:
   - MCP 응답: `{"content": [{"text": "{...}"}]}`
   - LangChain 반환: `{...}` (데이터만)

3. **재시도 로직**:
   - 연결 실패 시 2회까지 재시도
   - 실패해도 에러 문자열 반환 (예외 안 냄)

##### 8.2.3 MCP 도구 로드

```python
async def _load_mcp_tools():
    """MCP 서버에서 도구 목록 가져와 LangChain 도구로 변환"""
    global _mcp_tools_cache, _mcp_tools_loaded

    # 캐시 확인
    if _mcp_tools_loaded and _mcp_tools_cache is not None:
        return _mcp_tools_cache

    mcp_tools = []

    try:
        client = await _get_mcp_client()

        if client is None:
            logger.warning("[NET-Z MCP] 클라이언트 초기화 실패")
            _mcp_tools_loaded = True
            _mcp_tools_cache = []
            return []

        # 도구 목록 가져오기
        tools_list = await client.list_tools()
        logger.info(f"[NET-Z MCP] {len(tools_list)}개 도구 발견")

        # 각 MCP 도구를 LangChain 도구로 변환
        for mcp_tool in tools_list:
            try:
                langchain_tool = _create_mcp_tool(mcp_tool)
                mcp_tools.append(langchain_tool)
                logger.info(f"  ✓ {mcp_tool['name']}")
            except Exception as e:
                logger.error(f"  ✗ {mcp_tool['name']} 로드 실패: {e}")

        _mcp_tools_cache = mcp_tools
        _mcp_tools_loaded = True

        logger.info(f"[NET-Z MCP] ✓ {len(mcp_tools)}개 도구 로드 완료")

    except Exception as e:
        logger.error(f"[NET-Z MCP] 도구 로드 실패: {e}")
        _mcp_tools_loaded = True
        _mcp_tools_cache = []

    return mcp_tools
```

##### 8.2.4 전체 도구 반환

```python
async def get_all_tools():
    """기본 도구 + MCP 도구 반환"""

    # MCP 도구 로드 (캐시됨)
    mcp_tools = await _load_mcp_tools()

    # 전체 도구 목록
    all_tools = _BASE_TOOLS + mcp_tools

    logger.info(f"[도구 목록] 총 {len(all_tools)}개 도구 사용 가능:")
    logger.info(f"  - 기본 도구: {len(_BASE_TOOLS)}개")
    logger.info(f"  - NET-Z MCP 도구: {len(mcp_tools)}개")

    return all_tools
```

**결과**:
- 기본 도구: 3개 (search, search_knowledge_base, classify_customer_segment)
- NET-Z MCP 도구: 19개
- 총: 22개 도구

---

### 9. **sse_mcp_client.py** - SSE 기반 MCP 클라이언트

#### 9.1 MCP 프로토콜 이해

**MCP (Model Context Protocol)**:
- 서버-클라이언트 아키텍처
- JSON-RPC 2.0 기반
- SSE (Server-Sent Events)로 양방향 통신

**통신 방식**:
```
클라이언트                    서버
    |                           |
    | GET /mcp/sse              |
    |-------------------------->|
    |                           |
    | <-- SSE 스트림 시작       |
    | event: endpoint           |
    | data: /mcp/message?sessionId=xxx
    |                           |
    | POST /mcp/message         |
    | {"method": "initialize"}  |
    |-------------------------->|
    |                           |
    | (SSE로 응답 수신)         |
    | event: message            |
    | data: {"result": {...}}   |
    | <-------------------------|
```

#### 9.2 클라이언트 구조

```python
class SSEMCPClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session_id = None
        self.request_id = 0

        # 백그라운드 SSE 리스너
        self.sse_task: Optional[asyncio.Task] = None
        self.sse_client: Optional[httpx.AsyncClient] = None

        # 요청-응답 매칭
        self.pending_requests: Dict[int, asyncio.Future] = {}
        self.running = False
```

**핵심 구성 요소**:
1. `sse_task`: 백그라운드에서 SSE 스트림 수신
2. `pending_requests`: 요청 ID → Future 매핑
3. `running`: SSE 리스너 실행 상태

#### 9.3 SSE 리스너 (백그라운드)

```python
async def _sse_listener(self):
    """백그라운드 SSE 리스너 (응답 수신)"""

    headers = {
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    }

    self.sse_client = httpx.AsyncClient(timeout=None)

    async with self.sse_client.stream("GET", f"{self.base_url}/mcp/sse", headers=headers) as response:
        logger.info("[SSE-MCP] SSE 스트림 연결됨")

        current_event = None

        async for line in response.aiter_lines():
            if not self.running:
                break

            line = line.strip()
            if not line:
                continue

            # event: 필드
            if line.startswith("event:"):
                current_event = line[6:].strip()
                continue

            # data: 필드
            if line.startswith("data:"):
                data_str = line[5:].strip()

                # endpoint 이벤트: 세션 ID 추출
                if current_event == "endpoint" and "sessionId=" in data_str:
                    self.session_id = data_str.split("sessionId=")[1].split("&")[0]
                    logger.info(f"[SSE-MCP] 세션 ID 획득: {self.session_id}")
                    continue

                # message 이벤트: JSON-RPC 응답
                if current_event == "message":
                    msg = json.loads(data_str)

                    # ping 무시
                    if msg.get("method") == "ping":
                        continue

                    # 응답 매칭
                    msg_id = msg.get("id")
                    if msg_id and msg_id in self.pending_requests:
                        future = self.pending_requests.pop(msg_id)

                        if "error" in msg:
                            future.set_exception(Exception(f"MCP Error: {msg['error']}"))
                        else:
                            future.set_result(msg.get("result", {}))
```

**동작 원리**:
1. SSE 스트림 연결 유지
2. `event:` 라인에서 이벤트 타입 읽기
3. `data:` 라인에서 데이터 읽기
4. 이벤트 타입에 따라 처리:
   - `endpoint`: 세션 ID 추출
   - `message`: JSON-RPC 응답 파싱 및 Future 완료

#### 9.4 초기화

```python
async def initialize(self):
    """MCP 서버 초기화"""

    # 1단계: SSE 리스너 시작
    self.running = True
    self.sse_task = asyncio.create_task(self._sse_listener())

    # 세션 ID 획득 대기 (최대 5초)
    for _ in range(50):
        if self.session_id:
            break
        await asyncio.sleep(0.1)

    if not self.session_id:
        raise Exception("세션 ID 획득 실패")

    # 2단계: initialize 메시지 전송
    request = {
        "jsonrpc": "2.0",
        "id": self._next_id(),
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "carbon-ai", "version": "1.0.0"}
        }
    }

    result = await self._send_request(request)

    # 3단계: initialized 알림 전송 (MCP 프로토콜 필수!)
    notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }

    async with httpx.AsyncClient(timeout=5.0) as client:
        url = f"{self.base_url}/mcp/message?sessionId={self.session_id}"
        await client.post(url, json=notification, headers=self._get_headers())

    logger.info("[SSE-MCP] 초기화 완료")
    return result
```

**왜 initialized 알림이 필요한가?**:
- MCP 프로토콜 규격 (3-way handshake)
- 서버가 이 알림을 받기 전까지 다른 요청 처리 안 함

#### 9.5 요청 전송 및 응답 대기

```python
async def _send_request(self, request: Dict[str, Any], timeout: float = 10.0):
    """요청 전송 및 SSE로 응답 대기"""

    req_id = request["id"]

    # SSE 리스너 상태 확인 (끊어졌으면 재시작)
    if not self.running or not self.sse_task or self.sse_task.done():
        logger.warning("[SSE-MCP] SSE 리스너 재시작 중...")
        self.running = True
        self.sse_task = asyncio.create_task(self._sse_listener())
        await asyncio.sleep(0.5)

    # Future 생성
    future = asyncio.Future()
    self.pending_requests[req_id] = future

    try:
        # POST 요청 전송 (응답 본문은 비어있음)
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{self.base_url}/mcp/message?sessionId={self.session_id}"

            response = await client.post(url, json=request, headers=self._get_headers())

            if response.status_code != 200:
                raise Exception(f"Request failed: {response.status_code}")

        # SSE로 응답이 올 때까지 대기
        result = await asyncio.wait_for(future, timeout=timeout)
        return result

    except asyncio.TimeoutError:
        self.pending_requests.pop(req_id, None)
        raise Exception(f"Request timeout (ID={req_id})")
```

**동작 플로우**:
1. Future 생성 및 `pending_requests`에 등록
2. POST 요청 전송 (본문은 비어있음, 200 OK만 받음)
3. SSE 리스너가 응답 수신할 때까지 Future 대기
4. SSE 리스너가 `future.set_result()` 호출
5. Future 완료, 결과 반환

#### 9.6 도구 호출

```python
async def call_tool(self, tool_name: str, arguments: Dict[str, Any], timeout: float = 30.0):
    """도구 호출"""

    if not self.session_id:
        await self.initialize()

    request = {
        "jsonrpc": "2.0",
        "id": self._next_id(),
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }

    result = await self._send_request(request, timeout=timeout)
    return result
```

**결과 형식**:
```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"year\":\"2025\",\"totalEmission\":\"31.743\"}"
    }
  ],
  "isError": false
}
```

---

## 🔄 전체 실행 흐름

### 사용자 질문: "후시파트너스111 회사의 2025년 배출 정보를 알려줘"

```
1. 사용자 입력
   ↓
2. LangGraph: call_model
   ├─> 시스템 프롬프트 로드
   ├─> 카테고리별 프롬프트 추가 (규제대응)
   ├─> 캐시 확인 (없음)
   ├─> Claude API 호출 (22개 도구 전달)
   └─> 응답: tool_calls = [get_company_id_by_name]
   ↓
3. LangGraph: tools
   ├─> get_company_id_by_name 실행
   │   ├─> MCP 클라이언트 확인 (연결됨)
   │   ├─> POST /mcp/message (enterpriseName="후시파트너스111")
   │   ├─> SSE로 응답 수신
   │   └─> 반환: 1
   └─> ToolMessage(content=1)
   ↓
4. LangGraph: call_model
   ├─> 대화 히스토리에 ToolMessage 추가
   ├─> Claude API 재호출
   └─> 응답: tool_calls = [get_total_emission]
   ↓
5. LangGraph: tools
   ├─> get_total_emission 실행
   │   ├─> MCP 클라이언트 확인
   │   ├─> POST /mcp/message (enterpriseId=1, year="2025")
   │   ├─> SSE로 응답 수신
   │   └─> 반환: {"totalEmission": "31.743", ...}
   └─> ToolMessage(content={...})
   ↓
6. LangGraph: call_model
   ├─> 대화 히스토리에 ToolMessage 추가
   ├─> Claude API 재호출
   └─> 응답: AIMessage (툴 호출 없음, 최종 답변)
        "후시파트너스111의 2025년 총 배출량은 31.743 tCO2eq입니다..."
   ↓
7. Mermaid 변환 (있으면)
   ├─> ```mermaid ... ``` 감지
   ├─> kroki.io URL 생성
   └─> ![다이어그램](https://kroki.io/...)로 변환
   ↓
8. 캐싱
   ├─> LLM 응답 캐싱 (24시간)
   └─> 다음 동일 질문 시 즉시 반환
   ↓
9. 사용자에게 최종 답변 반환
```

---

## 💡 핵심 기술 정리

### 1. **LangGraph의 상태 관리**
- `messages`: 대화 히스토리 (append-only)
- `add_messages`: 메시지 ID 기반 업데이트
- `is_last_step`: recursion_limit 도달 감지

### 2. **ReAct 패턴**
```
Reasoning (생각) → Action (도구 호출) → Observation (결과) → Reasoning → ...
```

### 3. **MCP 양방향 통신**
- **송신**: POST `/mcp/message` (명령)
- **수신**: SSE `/mcp/sse` (응답)
- **매칭**: JSON-RPC ID로 요청-응답 연결

### 4. **RAG 검색 최적화**
- LLM 키워드 추출
- 키워드 + 원본 이중 검색
- 유사도 임계값 0.5
- 중복 제거
- 캐싱

### 5. **Mermaid 자동 변환**
- zlib 압축 + base64 인코딩
- kroki.io API 활용
- 코드 블록 → 마크다운 이미지

### 6. **2단계 캐싱**
- Redis (분산 환경)
- Memory (단일 프로세스)
- TTL 24시간
- 캐시 키: SHA256 해시

---

## 📊 도구 목록 (총 22개)

### 기본 도구 (3개)
1. `search` - Tavily 웹 검색
2. `search_knowledge_base` - RAG 벡터 검색
3. `classify_customer_segment` - 고객 세그먼트 분류

### NET-Z MCP 도구 (19개)

#### 배출량 조회
1. `get_total_emission` - 총 배출량 조회
2. `get_emission_type_ratio` - 배출종류 비율 조회
3. `get_scope_emission_comparison` - Scope별 배출량 비교
4. `get_top10_facilities_by_scope` - Top 10 시설 조회
5. `get_total_emission_comparison` - 총 배출량 비교

#### 공통 코드
6. `get_common_code` - 공통 코드 조회
7. `list_enum_keys` - Enum 키 목록 조회

#### 대시보드
8. `get_dashboard_emission_comparison` - 대시보드 배출량 비교
9. `get_dashboard_emission_type_ratio` - 대시보드 배출 비율
10. `get_dashboard_input_status` - 대시보드 입력 현황

#### 배출활동
11. `list_emission_activities` - 배출활동원 목록
12. `list_energy_by_activity` - 활동별 에너지 목록

#### 에너지
13. `get_energy_id_by_name` - 에너지 ID 조회
14. `get_energy_info` - 에너지 정보 조회
15. `get_energy_name_by_id` - 에너지 이름 조회
16. `list_all_energies` - 모든 에너지 목록

#### 기업
17. `get_company_id_by_name` - 기업 ID 조회
18. `get_company_name_by_id` - 기업 이름 조회
19. `list_all_companies` - 모든 기업 목록

---

## 🚀 성능 최적화 기법

### 1. 캐싱 전략
```python
# RAG 검색 캐싱 (24시간)
cached = cache_manager.get("rag", query)
if cached:
    return cached  # 벡터 검색 생략

# LLM 응답 캐싱 (툴 호출 없는 경우만)
if not response.tool_calls:
    cache_manager.set("llm", cache_key, response)
```

### 2. 지연 로딩
```python
# 벡터 스토어 지연 로딩
@property
def vectorstore(self):
    if self._vectorstore is None:
        self._vectorstore = Chroma(...)
    return self._vectorstore
```

### 3. 백그라운드 처리
```python
# SSE 리스너를 백그라운드 태스크로 실행
self.sse_task = asyncio.create_task(self._sse_listener())

# POST 요청과 SSE 응답 수신을 병렬 처리
```

### 4. 자동 재연결
```python
# MCP 클라이언트 자동 재연결
if not client.running or client.sse_task.done():
    client = await _get_mcp_client()  # 재초기화
```

---

## 🔒 에러 처리 및 복원력

### 1. MCP 연결 실패
```python
try:
    result = await client.call_tool(tool_name, kwargs)
except Exception as e:
    if attempt < max_retries - 1:
        # 클라이언트 재설정 후 재시도
        _netz_mcp_client = None
        await asyncio.sleep(0.5)
    else:
        return f"오류: MCP 도구 호출 실패 - {str(e)}"
```

### 2. SSE 연결 끊김
```python
# SSE 리스너 상태 자동 확인 및 재시작
if not self.running or self.sse_task.done():
    self.running = True
    self.sse_task = asyncio.create_task(self._sse_listener())
```

### 3. 타임아웃 처리
```python
# Future 대기 시 타임아웃 설정
result = await asyncio.wait_for(future, timeout=timeout)
```

---

## 📝 환경 변수 설정

```bash
# Claude API
ANTHROPIC_API_KEY=sk-ant-api03-...

# LangSmith (선택)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=ReAct-Agent-Template

# Tavily 검색
TAVILY_API_KEY=tvly-dev-...

# 캐시 (선택)
USE_REDIS_CACHE=false
CACHE_TTL=86400
REDIS_URL=redis://localhost:6379/0

# NET-Z MCP
NETZ_MCP_URL=https://hooxi.shinssy.com
NETZ_MCP_ENABLED=true
```

---

## 🎯 핵심 특징 요약

1. **ReAct 패턴**: 생각 → 행동 → 관찰 반복
2. **MCP 통합**: 19개 NET-Z 도구 자동 로드
3. **RAG 검색**: 한국어 임베딩 + 키워드 추출
4. **카테고리별 답변**: 탄소배출권/규제대응/고객상담
5. **Mermaid 자동 변환**: 코드 → 이미지
6. **2단계 캐싱**: Redis + Memory
7. **자동 재연결**: MCP 클라이언트 복원력
8. **비동기 처리**: asyncio 기반 고성능

---

이것이 CarbonAI React-Agent의 전체 아키텍처입니다! 🎉
