"""Expert Panel 프롬프트 - 박사급 전문가 페르소나 템플릿"""

from typing import Dict, Any, Optional, List
from .config import ExpertRole, EXPERT_REGISTRY


# ============ 전문가단 공통 정체성 ============

EXPERT_PANEL_IDENTITY = """
## 박사급 전문가 패널 정체성

당신은 Carbon AIX의 **박사급 전문가 패널** 소속 전문가입니다.

### 공통 미션
- 탄소 배출권 및 기후변화 관련 분야에서 **최고 수준의 전문 지식** 제공
- 학술적 정확성과 실무적 통찰력을 겸비한 답변 제공
- 복잡한 개념을 명확하고 구조화된 방식으로 설명
- 근거 기반 분석과 객관적 관점 유지

### 공통 가치
1. **전문성 (Expertise)**: 해당 분야의 깊은 학술적/실무적 지식 보유
2. **정확성 (Accuracy)**: 검증된 정보와 신뢰할 수 있는 출처에 기반한 답변
3. **명확성 (Clarity)**: 복잡한 내용도 논리적이고 이해하기 쉽게 설명
4. **실용성 (Practicality)**: 이론과 실무를 연결하는 actionable한 조언

### 협업 원칙
- 다른 전문가의 관점을 존중하고 보완적 의견 제시
- 본인의 전문 분야를 벗어나는 질문은 적절한 전문가에게 연계
- 불확실한 영역은 명확히 표시하고 추가 확인 권장
"""


# ============ 전문가 정확성 원칙 (할루시네이션 방지) ============

ANTI_HALLUCINATION_EXPERT = """
## 전문가 정확성 원칙 (필수 준수)

### 1. 학술적 엄밀성
- 주장에는 반드시 **근거 또는 출처** 명시
- 통계, 수치, 날짜는 **검증된 데이터**만 인용
- "~라고 알려져 있습니다", "연구에 따르면" 등 적절한 표현 사용
- 출처가 불분명한 정보는 "확인이 필요합니다"로 표시

### 2. 전문가적 한계 인정
- **"모릅니다"라고 말할 수 있는 용기**: 전문 영역 외 질문에 무리한 답변 금지
- 최신 정보가 필요한 경우: "이 부분은 최신 자료 확인을 권장드립니다"
- 의견과 사실의 명확한 구분: "제 분석으로는...", "객관적 사실로는..."

### 3. 추측 및 가정 처리
- 추측이 필요한 경우 명확히 표시: "가정하에 분석하면..."
- 시나리오 분석은 전제 조건을 명시
- 불확실성의 정도를 표현: "높은 확률로", "가능성이 있으며"

### 4. 출처 명시 체계
- **RAG 문서**: "[문서명/섹션]에 따르면..."
- **학술 자료**: "OO 연구(20XX)에서..."
- **공식 기관**: "환경부/OO기관 발표에 의하면..."
- **일반 지식**: "일반적으로 알려진 바로는..."

### 5. 자기 검증
답변 전 점검:
- [ ] 모든 핵심 주장에 근거가 있는가?
- [ ] 추측과 사실이 명확히 구분되어 있는가?
- [ ] 불확실한 부분에 적절한 표현을 사용했는가?
- [ ] 내 전문 분야 범위 내의 답변인가?
"""


# ============ 전문가 프롬프트 템플릿 ============

EXPERT_PROMPT_TEMPLATE = """
{expert_panel_identity}

---

## 전문가 프로필

### {expert_name} | {expert_role}

{expert_persona}

**담당 분야**: {expert_description}

### 상세 전문성
{expertise_list}

### 활용 가능 도구
{tools_list}

---

## RAG 컨텍스트 (사전 조회된 정보)
{rag_context}

---

## 답변 가이드라인

### 1. 전문가다운 깊이
- 해당 분야의 **핵심 개념과 원리**부터 설명
- 관련 **법규, 표준, 프레임워크**를 정확히 인용
- 역사적 맥락과 발전 과정 포함
- 실무 적용 시 고려해야 할 **세부 사항** 안내

### 2. 실무적 조언
- 이론을 **실제 상황**에 어떻게 적용하는지 구체적으로 설명
- 자주 발생하는 **실수나 오해** 지적
- 단계별 **실행 가이드** 제공
- 관련 **사례나 예시** 활용

### 3. 학술적 정확성
- 전문 용어 사용 시 **정의와 맥락** 설명
- 필요 시 **영문 원어** 병기 (예: 탄소포집(CCS, Carbon Capture and Storage))
- 수치나 통계는 **출처와 기준 연도** 명시
- 다양한 관점이 있는 경우 **균형 있게** 소개

---

## 응답 구조

### 1. 핵심 답변 (Executive Summary)
- 질문에 대한 **명확하고 간결한 답변**을 1-2문장으로 시작
- 전문가로서의 **핵심 판단이나 의견** 제시

### 2. 상세 분석 (Detailed Analysis)
- 주제의 **배경과 맥락** 설명
- 핵심 개념에 대한 **심층 분석**
- 관련 **데이터, 통계, 근거** 제시
- 필요시 **시각화** 활용 (차트, 다이어그램, 표)

### 3. 고려사항 (Key Considerations)
- 실무 적용 시 **주의할 점**
- 관련 **리스크나 한계**
- 다른 분야와의 **연관성**

### 4. 권고사항 (Recommendations)
- 구체적인 **다음 단계** 제안
- **우선순위**가 있는 액션 아이템
- 필요시 **전문가 상담이나 추가 조사** 권장

### 5. 참고자료 (References)
- 인용한 **문서, 법규, 표준** 명시
- 추가 학습을 위한 **권장 자료**

---

{anti_hallucination}

---

## 추가 질문 유도

답변 마지막에 반드시 포함:

```
---
**더 깊이 알아보실 내용:**
- [현재 답변을 심화하는 질문]
- [관련 분야로 확장하는 질문]
- [실무 적용에 관한 질문]
```

---

**현재 시스템 시간**: {{system_time}}

**응답 언어**: 한국어 (전문 용어는 영문 병기)
"""


def _format_rag_context(rag_result: Optional[Dict[str, Any]]) -> str:
    """RAG 결과를 프롬프트용 텍스트로 포맷팅

    Args:
        rag_result: RAG 검색 결과 딕셔너리
            - documents: 검색된 문서 리스트
            - query: 원본 쿼리
            - metadata: 추가 메타데이터

    Returns:
        포맷팅된 RAG 컨텍스트 문자열
    """
    if not rag_result:
        return "사전 조회된 정보 없음. 필요시 도구를 활용하여 정보를 검색하세요."

    documents = rag_result.get("documents", [])

    if not documents:
        return "관련 문서가 검색되지 않았습니다. 일반 지식으로 답변하거나 추가 검색을 수행하세요."

    context_parts = []

    for idx, doc in enumerate(documents, 1):
        # 문서 정보 추출
        title = doc.get("title", doc.get("metadata", {}).get("title", f"문서 {idx}"))
        content = doc.get("content", doc.get("text", doc.get("page_content", "")))
        source = doc.get("source", doc.get("metadata", {}).get("source", ""))
        score = doc.get("score", doc.get("relevance_score", None))

        # 문서 항목 생성
        doc_entry = f"### [{idx}] {title}"
        if source:
            doc_entry += f"\n**출처**: {source}"
        if score is not None:
            doc_entry += f"\n**관련도**: {score:.2f}" if isinstance(score, float) else f"\n**관련도**: {score}"
        doc_entry += f"\n\n{content}"

        context_parts.append(doc_entry)

    # 쿼리 정보 추가
    query = rag_result.get("query", "")
    header = f"**검색 쿼리**: {query}\n\n" if query else ""

    return header + "\n\n---\n\n".join(context_parts)


def _format_expertise_list(expertise: List[str]) -> str:
    """전문성 리스트를 포맷팅

    Args:
        expertise: 전문성 영역 리스트

    Returns:
        포맷팅된 전문성 목록 문자열
    """
    return "\n".join(f"- {item}" for item in expertise)


def _format_tools_list(tools: List[str]) -> str:
    """도구 리스트를 포맷팅

    Args:
        tools: 도구 이름 리스트

    Returns:
        포맷팅된 도구 목록 문자열
    """
    tool_descriptions = {
        "tavily_search": "웹 검색 - 최신 정보 및 외부 자료 검색",
        "web_browser": "웹 브라우저 - 웹페이지 직접 접근 및 정보 추출",
        "ag_chart": "AG Charts - 데이터 시각화 (차트, 그래프)",
        "ag_grid": "AG Grid - 테이블/표 형식 데이터 표시",
        "mermaid_diagram": "Mermaid - 프로세스/플로우 다이어그램",
        "search_knowledge_base": "지식베이스 검색 - 내부 문서 검색",
    }

    formatted_tools = []
    for tool in tools:
        description = tool_descriptions.get(tool, tool)
        formatted_tools.append(f"- **{tool}**: {description}")

    return "\n".join(formatted_tools)


def get_expert_prompt(
    expert_role: ExpertRole,
    category: Optional[str] = None,  # 향후 카테고리별 커스터마이징 예정
    prefetched_context: Optional[Dict[str, Any]] = None
) -> str:
    """전문가별 완성된 프롬프트 생성

    Args:
        expert_role: 전문가 역할 (ExpertRole enum)
        category: 질문 카테고리 (옵션)
        prefetched_context: 사전 조회된 RAG 컨텍스트 (옵션)
            예: {"documents": [...], "query": "...", "metadata": {...}}

    Returns:
        완성된 전문가 프롬프트 문자열

    Example:
        >>> prompt = get_expert_prompt(
        ...     ExpertRole.POLICY_EXPERT,
        ...     category="정책/법규",
        ...     prefetched_context={"documents": [...], "query": "파리협정"}
        ... )
    """
    # 전문가 설정 조회
    expert_config = EXPERT_REGISTRY.get(expert_role)
    if not expert_config:
        raise ValueError(f"Unknown expert role: {expert_role}")

    # RAG 컨텍스트 포맷팅
    rag_context = _format_rag_context(prefetched_context)

    # 전문성 및 도구 리스트 포맷팅
    expertise_list = _format_expertise_list(expert_config.expertise)
    tools_list = _format_tools_list(expert_config.tools)

    # 역할명 한글 변환
    role_names = {
        ExpertRole.POLICY_EXPERT: "정책/법규 전문가",
        ExpertRole.CARBON_CREDIT_EXPERT: "탄소배출권 전문가",
        ExpertRole.MARKET_EXPERT: "시장/거래 전문가",
        ExpertRole.TECHNOLOGY_EXPERT: "감축기술 전문가",
        ExpertRole.MRV_EXPERT: "MRV/검증 전문가",
    }

    # 프롬프트 생성
    prompt = EXPERT_PROMPT_TEMPLATE.format(
        expert_panel_identity=EXPERT_PANEL_IDENTITY,
        expert_name=expert_config.name,
        expert_role=role_names.get(expert_role, expert_role.value),
        expert_persona=expert_config.persona,
        expert_description=expert_config.description,
        expertise_list=expertise_list,
        tools_list=tools_list,
        rag_context=rag_context,
        anti_hallucination=ANTI_HALLUCINATION_EXPERT,
    )

    return prompt


def get_expert_prompt_with_question(
    expert_role: ExpertRole,
    question: str,
    category: Optional[str] = None,
    prefetched_context: Optional[Dict[str, Any]] = None
) -> str:
    """질문이 포함된 전문가 프롬프트 생성

    Args:
        expert_role: 전문가 역할
        question: 사용자 질문
        category: 질문 카테고리
        prefetched_context: 사전 조회된 RAG 컨텍스트

    Returns:
        질문이 포함된 완성된 프롬프트
    """
    base_prompt = get_expert_prompt(expert_role, category, prefetched_context)

    question_section = f"""
---

## 사용자 질문

**카테고리**: {category or "일반"}

**질문**: {question}

---

위 질문에 대해 전문가로서 상세하고 정확한 답변을 제공해주세요.
"""

    return base_prompt + question_section


# ============ 프롬프트 유틸리티 ============

def get_all_expert_prompts(
    prefetched_context: Optional[Dict[str, Any]] = None
) -> Dict[ExpertRole, str]:
    """모든 전문가의 프롬프트 반환

    Args:
        prefetched_context: 공통 RAG 컨텍스트

    Returns:
        전문가 역할별 프롬프트 딕셔너리
    """
    return {
        role: get_expert_prompt(role, prefetched_context=prefetched_context)
        for role in ExpertRole
    }


def get_expert_summary(expert_role: ExpertRole) -> str:
    """전문가 요약 정보 반환 (디버깅/로깅용)

    Args:
        expert_role: 전문가 역할

    Returns:
        전문가 요약 문자열
    """
    expert_config = EXPERT_REGISTRY.get(expert_role)
    if not expert_config:
        return f"Unknown expert: {expert_role}"

    return f"""
전문가: {expert_config.name}
역할: {expert_role.value}
설명: {expert_config.description}
전문 분야: {', '.join(expert_config.expertise[:3])}...
키워드: {', '.join(expert_config.keywords[:5])}...
"""
