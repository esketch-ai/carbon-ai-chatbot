# Expert Panel 시스템 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 5명의 박사급 전문가 에이전트로 구성된 Expert Panel 시스템 구현

**Architecture:** Manager가 복잡한 질문을 Expert Panel로 라우팅하고, 단일 또는 다중 전문가가 협업하여 답변 생성

**Tech Stack:** LangGraph, LangChain, ChromaDB, Sentence Transformers

---

## Task 1: Expert Panel 설정 및 역할 정의

**Files:**
- Create: `react-agent/src/react_agent/agents/expert_panel/__init__.py`
- Create: `react-agent/src/react_agent/agents/expert_panel/config.py`

**Step 1: 디렉토리 및 __init__.py 생성**

```python
# react-agent/src/react_agent/agents/expert_panel/__init__.py
"""Expert Panel - 박사급 전문가 에이전트 패널"""

from .config import ExpertRole, ExpertConfig, EXPERT_REGISTRY
from .prompts import get_expert_prompt
from .router import route_to_expert
from .collaboration import collaborate_experts

__all__ = [
    "ExpertRole",
    "ExpertConfig",
    "EXPERT_REGISTRY",
    "get_expert_prompt",
    "route_to_expert",
    "collaborate_experts",
]
```

**Step 2: Expert Panel config.py 생성**

```python
# react-agent/src/react_agent/agents/expert_panel/config.py
"""Expert Panel 설정 및 레지스트리"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class ExpertRole(str, Enum):
    """Expert Panel 전문가 역할"""
    POLICY_EXPERT = "policy_expert"           # 정책법규 전문가
    CARBON_CREDIT_EXPERT = "carbon_credit_expert"  # 탄소배출권 전문가
    MARKET_EXPERT = "market_expert"           # 시장거래 전문가
    TECHNOLOGY_EXPERT = "technology_expert"   # 감축기술 전문가
    MRV_EXPERT = "mrv_expert"                 # MRV검증 전문가


@dataclass
class ExpertConfig:
    """전문가 설정"""
    role: ExpertRole
    name: str
    persona: str
    description: str
    expertise: List[str]
    tools: List[str]
    keywords: List[str]  # 라우팅용 키워드


EXPERT_REGISTRY = {
    ExpertRole.POLICY_EXPERT: ExpertConfig(
        role=ExpertRole.POLICY_EXPERT,
        name="Dr. 김정책",
        persona="UNFCCC COP 협상 30년 참여, 환경부 기후변화정책과장 역임, 파리협정 한국 협상단 자문위원",
        description="국제협약 및 국내 기후변화 정책/법규 전문가",
        expertise=[
            "국제협약 해석 및 국내 이행",
            "배출권거래제 법적 프레임워크",
            "NDC 수립 및 이행 점검",
            "신규 규제 영향 분석",
        ],
        tools=[
            "search_knowledge_base",
            "search",
            "get_policy_timeline",
            "compare_regulations",
        ],
        keywords=["파리협정", "NDC", "법률", "규제", "정책", "협약", "기본법", "시행령", "UNFCCC", "COP"],
    ),

    ExpertRole.CARBON_CREDIT_EXPERT: ExpertConfig(
        role=ExpertRole.CARBON_CREDIT_EXPERT,
        name="Dr. 한배출",
        persona="한국거래소 배출권시장 설계 참여 15년, 환경부 배출권거래제 운영위원회 위원, CDM/JI 사업 100건 이상 개발",
        description="배출권 종류, 할당, 거래 실무 전문가",
        expertise=[
            "배출권 종류 및 특성 (KAU, KCU, KOC)",
            "할당 방식 (무상/유상, BM/GF)",
            "거래 실무 (매수/매도, 이월/차입, 상쇄)",
            "외부사업 크레딧 인증",
        ],
        tools=[
            "search_knowledge_base",
            "search",
            "get_total_emission",
            "calculate_credit_demand",
            "compare_credit_types",
        ],
        keywords=["KAU", "KCU", "KOC", "할당", "배출권", "거래", "이월", "차입", "상쇄", "외부사업"],
    ),

    ExpertRole.MARKET_EXPERT: ExpertConfig(
        role=ExpertRole.MARKET_EXPERT,
        name="Dr. 이시장",
        persona="EU ETS 설계 자문 25년, 글로벌 탄소펀드 운용 경험, 배출권 가격 예측 모델 개발",
        description="탄소시장 메커니즘 및 가격 분석 전문가",
        expertise=[
            "ETS/자발적 시장 메커니즘",
            "탄소 가격 동향 및 전망",
            "헤징 전략 및 포트폴리오",
            "국제 탄소시장 연계",
        ],
        tools=[
            "search_knowledge_base",
            "search",
            "get_market_price",
            "analyze_market_trend",
            "compare_carbon_markets",
        ],
        keywords=["시장", "가격", "시세", "ETS", "EU", "CBAM", "투자", "전망", "트렌드", "자발적"],
    ),

    ExpertRole.TECHNOLOGY_EXPERT: ExpertConfig(
        role=ExpertRole.TECHNOLOGY_EXPERT,
        name="Dr. 박기술",
        persona="IPCC AR6 WG3 주저자, 탄소중립 기술 R&D 총괄 30년, CCUS 상용화 프로젝트 다수",
        description="온실가스 감축기술 및 탈탄소화 전문가",
        expertise=[
            "산업별 탈탄소화 경로",
            "CCUS, 수소, 재생에너지",
            "기술 경제성 분석",
            "BAT(최적가용기술) 평가",
        ],
        tools=[
            "search_knowledge_base",
            "search",
            "calculate_abatement_cost",
            "compare_technologies",
            "get_emission_factors",
        ],
        keywords=["CCUS", "수소", "재생에너지", "기술", "감축", "탈탄소", "IPCC", "BAT", "경제성", "효율"],
    ),

    ExpertRole.MRV_EXPERT: ExpertConfig(
        role=ExpertRole.MRV_EXPERT,
        name="Dr. 최검증",
        persona="국가 온실가스 인벤토리 책임자 20년, ISO 14064 선임심사원, IPCC 인벤토리 태스크포스 위원",
        description="온실가스 측정·보고·검증(MRV) 전문가",
        expertise=[
            "Scope 1/2/3 산정 방법론",
            "제3자 검증 절차",
            "불확도 분석",
            "보고서 품질관리",
        ],
        tools=[
            "search_knowledge_base",
            "search",
            "calculate_emissions",
            "validate_methodology",
            "get_emission_factors",
        ],
        keywords=["Scope", "산정", "검증", "MRV", "인벤토리", "보고", "ISO", "배출량", "측정", "명세서"],
    ),
}


def get_expert_config(role: ExpertRole) -> ExpertConfig:
    """전문가 설정 가져오기"""
    return EXPERT_REGISTRY[role]


def get_all_experts() -> List[ExpertRole]:
    """모든 전문가 역할 반환"""
    return list(ExpertRole)
```

**Step 3: 커밋**

```bash
git add react-agent/src/react_agent/agents/expert_panel/
git commit -m "feat: add Expert Panel config and role definitions"
```

---

## Task 2: Expert Panel 프롬프트 생성

**Files:**
- Create: `react-agent/src/react_agent/agents/expert_panel/prompts.py`

**Step 1: 전문가 프롬프트 템플릿 생성**

```python
# react-agent/src/react_agent/agents/expert_panel/prompts.py
"""Expert Panel 프롬프트 템플릿"""

from typing import Dict, Any
from .config import ExpertRole, EXPERT_REGISTRY


# 박사급 전문가 공통 정체성
EXPERT_PANEL_IDENTITY = """
🎓 **Expert Panel - 박사급 전문가 자문단**

저희는 국내외 온실가스 감축 정책 분야에서 30년 이상 경력을 가진 박사급 전문가로 구성된 자문단입니다.
복잡한 정책 질문에 대해 깊이 있는 분석과 실무적 조언을 제공합니다.

**우리의 원칙:**
- 학술적 정확성과 실무 경험을 바탕으로 답변
- 불확실한 정보는 명확히 구분하여 표시
- 최신 정책 동향과 역사적 맥락을 함께 제공
- 출처를 명확히 밝히고 추가 참고자료 안내

**출처 표기 (필수):**
- 국제협약/법률: 조항 번호와 함께 인용
- 연구보고서: 저자, 발행기관, 연도 표기
- 웹 검색 결과: URL 포함
"""

# 전문가별 프롬프트 템플릿
EXPERT_PROMPT_TEMPLATE = """당신은 **{name}** ({persona})입니다.

{expert_panel_identity}

**당신의 전문 분야:**
{description}

**상세 전문성:**
{expertise_list}

**현재 맥락:**
- 사용자 질문 카테고리: {category}
- 관련 문서 정보:
{rag_context}

**사용 가능한 도구:**
{tools_description}

**답변 가이드라인:**

1. **전문가다운 깊이**
   - 단순 설명이 아닌 맥락과 함의 분석
   - 역사적 배경 → 현재 상황 → 미래 전망 구조
   - 관련 사례와 선례 인용

2. **실무적 조언**
   - 이론과 실무의 균형
   - 구체적인 행동 지침 제시
   - 주의사항 및 리스크 안내

3. **학술적 정확성**
   - 용어의 정확한 사용
   - 법률/규정 인용 시 조항 명시
   - 불확실한 부분은 "~로 해석됩니다", "확인이 필요합니다" 표현

4. **시각화 활용**
   - 복잡한 프로세스 → Mermaid 플로우차트
   - 비교 분석 → AG Grid 테이블
   - 수치 데이터 → AG Charts

**응답 구조:**
1. 💡 **핵심 답변** - 전문가 관점에서의 명확한 결론
2. 📚 **상세 분석** - 근거와 맥락을 포함한 깊이 있는 설명
3. ⚖️ **고려사항** - 주의점, 리스크, 대안
4. ✅ **권고사항** - 실무적 다음 단계
5. 📖 **참고자료** - 추가 학습을 위한 자료 안내

{anti_hallucination_guidelines}
"""


ANTI_HALLUCINATION_EXPERT = """
**🚨 전문가 정확성 원칙:**

1. **법률/규정 인용**
   - 정확한 조항 번호 필수 (예: "배출권거래법 제12조 제1항")
   - 최신 개정 여부 확인 안내
   - 해석이 필요한 경우 "법률 자문 권장" 명시

2. **수치/통계**
   - 출처와 기준연도 명시
   - 추정치는 "약", "추정" 표현 사용
   - 실시간 데이터는 "확인 필요" 안내

3. **예측/전망**
   - 근거가 되는 분석/보고서 인용
   - 불확실성 범위 표시
   - "개인적 견해"와 "객관적 분석" 구분

4. **한계 인정**
   - 전문 영역 외 질문: "해당 분야 전문가 상담 권장"
   - 최신 정보 필요: "공식 채널 확인 바랍니다"
   - 개별 사례: "구체적 상황에 따라 다를 수 있습니다"
"""


def get_expert_prompt(
    expert_role: ExpertRole,
    category: str,
    prefetched_context: Dict[str, Any]
) -> str:
    """전문가별 프롬프트 생성"""

    config = EXPERT_REGISTRY[expert_role]

    # 전문성 목록 포맷
    expertise_list = "\n".join([f"- {exp}" for exp in config.expertise])

    # 도구 설명 포맷
    tools_desc = "\n".join([f"- **{tool}**" for tool in config.tools])

    # RAG 컨텍스트 포맷
    rag_context = _format_rag_context(prefetched_context.get("RAG", {}))

    return EXPERT_PROMPT_TEMPLATE.format(
        name=config.name,
        persona=config.persona,
        expert_panel_identity=EXPERT_PANEL_IDENTITY,
        description=config.description,
        expertise_list=expertise_list,
        category=category,
        rag_context=rag_context,
        tools_description=tools_desc,
        anti_hallucination_guidelines=ANTI_HALLUCINATION_EXPERT,
    )


def _format_rag_context(rag_result: Dict) -> str:
    """RAG 결과를 프롬프트에 맞게 포맷"""
    if not rag_result or rag_result.get("status") != "success":
        return "관련 문서 없음"

    results = rag_result.get("results", [])
    if not results:
        return "관련 문서 없음"

    formatted = []
    for i, doc in enumerate(results[:3], 1):
        content = doc.get("content", "")[:500]  # 500자로 제한
        filename = doc.get("filename", "unknown")
        similarity = doc.get("similarity", 0)
        formatted.append(
            f"[문서 {i}] (유사도: {similarity:.2f}, 출처: {filename})\n{content}..."
        )

    return "\n\n".join(formatted)
```

**Step 2: 커밋**

```bash
git add react-agent/src/react_agent/agents/expert_panel/prompts.py
git commit -m "feat: add Expert Panel prompt templates with PhD personas"
```

---

## Task 3: Expert Panel 라우터 구현

**Files:**
- Create: `react-agent/src/react_agent/agents/expert_panel/router.py`

**Step 1: 전문가 라우팅 로직 구현**

```python
# react-agent/src/react_agent/agents/expert_panel/router.py
"""Expert Panel 라우터 - 질문을 적합한 전문가에게 라우팅"""

import logging
from typing import List, Tuple, Optional
from .config import ExpertRole, EXPERT_REGISTRY, ExpertConfig

logger = logging.getLogger(__name__)


def route_to_expert(
    query: str,
    category: str = None,
    top_k: int = 1
) -> List[Tuple[ExpertRole, float]]:
    """
    질문을 분석하여 적합한 전문가 선정

    Args:
        query: 사용자 질문
        category: 질문 카테고리 (힌트)
        top_k: 반환할 전문가 수 (다중 전문가 협업용)

    Returns:
        (ExpertRole, 매칭점수) 튜플 리스트
    """
    query_lower = query.lower()
    scores = []

    for role, config in EXPERT_REGISTRY.items():
        score = _calculate_match_score(query_lower, config, category)
        scores.append((role, score))

    # 점수순 정렬
    scores.sort(key=lambda x: x[1], reverse=True)

    top_experts = scores[:top_k]

    logger.info(
        f"[Expert Router] 질문: '{query[:50]}...' → "
        f"전문가: {[(e.value, f'{s:.2f}') for e, s in top_experts]}"
    )

    return top_experts


def _calculate_match_score(
    query_lower: str,
    config: ExpertConfig,
    category: str = None
) -> float:
    """전문가 매칭 점수 계산"""
    score = 0.0

    # 1. 키워드 매칭 (최대 0.6점)
    keyword_matches = sum(1 for kw in config.keywords if kw.lower() in query_lower)
    keyword_score = min(keyword_matches * 0.15, 0.6)
    score += keyword_score

    # 2. 전문성 매칭 (최대 0.3점)
    expertise_matches = sum(
        1 for exp in config.expertise
        if any(word in query_lower for word in exp.lower().split())
    )
    expertise_score = min(expertise_matches * 0.1, 0.3)
    score += expertise_score

    # 3. 카테고리 보너스 (0.1점)
    if category:
        category_expert_map = {
            "탄소배출권": [ExpertRole.CARBON_CREDIT_EXPERT, ExpertRole.MARKET_EXPERT],
            "규제대응": [ExpertRole.POLICY_EXPERT, ExpertRole.MRV_EXPERT],
            "기술": [ExpertRole.TECHNOLOGY_EXPERT],
        }
        if config.role in category_expert_map.get(category, []):
            score += 0.1

    return score


def should_use_expert_panel(
    complexity: str,
    confidence: float,
    query: str
) -> bool:
    """
    Expert Panel 사용 여부 결정

    조건:
    - 복잡도가 complex 이상
    - 또는 특정 키워드 포함 (정책, 법규, 국제, IPCC 등)
    """
    # 복잡도 기반
    if complexity == "complex":
        return True

    # 키워드 기반
    expert_keywords = [
        "파리협정", "UNFCCC", "NDC", "IPCC", "교토의정서",
        "법률", "시행령", "제도", "정책 분석",
        "EU ETS", "CBAM", "국제", "글로벌",
        "MRV", "검증", "인벤토리",
    ]

    query_lower = query.lower()
    if any(kw.lower() in query_lower for kw in expert_keywords):
        return True

    return False


def needs_collaboration(
    query: str,
    primary_expert: ExpertRole
) -> Optional[List[ExpertRole]]:
    """
    다중 전문가 협업 필요 여부 판단

    Returns:
        협업이 필요한 추가 전문가 목록, 불필요시 None
    """
    # 협업 트리거 패턴
    collaboration_patterns = {
        # 정책 + 시장 연계
        ("정책", "시장"): [ExpertRole.POLICY_EXPERT, ExpertRole.MARKET_EXPERT],
        ("규제", "가격"): [ExpertRole.POLICY_EXPERT, ExpertRole.MARKET_EXPERT],
        ("CBAM", "영향"): [ExpertRole.POLICY_EXPERT, ExpertRole.MARKET_EXPERT],

        # 기술 + MRV 연계
        ("감축", "산정"): [ExpertRole.TECHNOLOGY_EXPERT, ExpertRole.MRV_EXPERT],
        ("CCUS", "검증"): [ExpertRole.TECHNOLOGY_EXPERT, ExpertRole.MRV_EXPERT],

        # 배출권 + 시장 연계
        ("할당", "전략"): [ExpertRole.CARBON_CREDIT_EXPERT, ExpertRole.MARKET_EXPERT],
        ("배출권", "투자"): [ExpertRole.CARBON_CREDIT_EXPERT, ExpertRole.MARKET_EXPERT],
    }

    query_lower = query.lower()

    for (kw1, kw2), experts in collaboration_patterns.items():
        if kw1.lower() in query_lower and kw2.lower() in query_lower:
            # 현재 전문가 제외한 추가 전문가 반환
            additional = [e for e in experts if e != primary_expert]
            if additional:
                logger.info(
                    f"[Expert Router] 협업 감지: {kw1}+{kw2} → "
                    f"추가 전문가: {[e.value for e in additional]}"
                )
                return additional

    return None
```

**Step 2: 커밋**

```bash
git add react-agent/src/react_agent/agents/expert_panel/router.py
git commit -m "feat: add Expert Panel router with keyword matching"
```

---

## Task 4: Expert Panel 협업 로직 구현

**Files:**
- Create: `react-agent/src/react_agent/agents/expert_panel/collaboration.py`

**Step 1: 다중 전문가 협업 로직 구현**

```python
# react-agent/src/react_agent/agents/expert_panel/collaboration.py
"""Expert Panel 협업 - 다중 전문가 응답 통합"""

import logging
from typing import List, Dict, Any
from langchain_core.messages import AIMessage
from .config import ExpertRole, EXPERT_REGISTRY

logger = logging.getLogger(__name__)


async def collaborate_experts(
    expert_responses: Dict[ExpertRole, str],
    query: str,
    category: str
) -> str:
    """
    다중 전문가 응답을 통합하여 최종 답변 생성

    Args:
        expert_responses: {전문가역할: 응답내용} 딕셔너리
        query: 원본 질문
        category: 질문 카테고리

    Returns:
        통합된 최종 답변
    """
    if len(expert_responses) == 1:
        # 단일 전문가면 그대로 반환
        return list(expert_responses.values())[0]

    # 다중 전문가 응답 통합
    integrated_response = _integrate_responses(expert_responses, query)

    logger.info(
        f"[Expert Collaboration] {len(expert_responses)}명 전문가 응답 통합: "
        f"{[e.value for e in expert_responses.keys()]}"
    )

    return integrated_response


def _integrate_responses(
    expert_responses: Dict[ExpertRole, str],
    query: str
) -> str:
    """다중 전문가 응답을 구조화된 형식으로 통합"""

    sections = []

    # 헤더
    expert_names = [EXPERT_REGISTRY[role].name for role in expert_responses.keys()]
    sections.append(
        f"## 🎓 Expert Panel 종합 분석\n\n"
        f"**참여 전문가:** {', '.join(expert_names)}\n\n"
        f"---\n"
    )

    # 각 전문가 의견
    for role, response in expert_responses.items():
        config = EXPERT_REGISTRY[role]
        sections.append(
            f"### 📌 {config.name} ({config.description})\n\n"
            f"{response}\n\n"
            f"---\n"
        )

    # 종합 섹션
    sections.append(
        "### 💡 종합 의견\n\n"
        "위 전문가들의 분석을 종합하면, 다각적인 관점에서의 검토가 필요한 사안입니다. "
        "각 전문가의 의견을 참고하여 상황에 맞는 판단을 하시기 바랍니다.\n\n"
        "**추가 상담이 필요하시면 구체적인 질문을 해주세요.**"
    )

    return "\n".join(sections)


def format_expert_header(role: ExpertRole) -> str:
    """전문가 응답 헤더 포맷"""
    config = EXPERT_REGISTRY[role]
    return (
        f"🎓 **{config.name}** | {config.description}\n"
        f"*{config.persona}*\n\n"
    )


def get_collaboration_summary(
    experts: List[ExpertRole],
    query: str
) -> str:
    """협업 요약 생성"""
    names = [EXPERT_REGISTRY[e].name for e in experts]
    return (
        f"이 질문은 {', '.join(names)} 전문가의 협업이 필요합니다. "
        f"각 전문가의 관점에서 분석을 진행합니다."
    )
```

**Step 2: 커밋**

```bash
git add react-agent/src/react_agent/agents/expert_panel/collaboration.py
git commit -m "feat: add Expert Panel collaboration logic"
```

---

## Task 5: Expert Panel 노드 구현

**Files:**
- Create: `react-agent/src/react_agent/agents/expert_panel/nodes.py`

**Step 1: Expert Panel 에이전트 노드 구현**

```python
# react-agent/src/react_agent/agents/expert_panel/nodes.py
"""Expert Panel 노드 - LangGraph 노드 구현"""

import time
import logging
from typing import Dict, Any, List
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from react_agent.state import State
from react_agent.configuration import Configuration
from react_agent.utils import detect_and_convert_mermaid

from .config import ExpertRole, EXPERT_REGISTRY, get_expert_config
from .prompts import get_expert_prompt
from .router import route_to_expert, needs_collaboration
from .collaboration import collaborate_experts, format_expert_header

logger = logging.getLogger(__name__)


async def expert_panel_router(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """
    Expert Panel 라우터 노드

    질문을 분석하여 적합한 전문가 선정
    """
    # 마지막 사용자 메시지 추출
    last_human_msg = None
    for msg in reversed(state.messages):
        if hasattr(msg, 'type') and msg.type == 'human':
            last_human_msg = msg.content
            break
        elif hasattr(msg, 'content') and not hasattr(msg, 'tool_calls'):
            last_human_msg = msg.content
            break

    if not last_human_msg:
        last_human_msg = str(state.messages[-1].content) if state.messages else ""

    configuration = Configuration.from_runnable_config(config)
    category = configuration.category or "탄소배출권"

    # 전문가 선정
    experts = route_to_expert(last_human_msg, category, top_k=1)
    primary_expert = experts[0][0] if experts else ExpertRole.POLICY_EXPERT

    # 협업 필요 여부 확인
    additional_experts = needs_collaboration(last_human_msg, primary_expert)

    selected_experts = [primary_expert]
    if additional_experts:
        selected_experts.extend(additional_experts)

    logger.info(
        f"[Expert Panel Router] 선정된 전문가: {[e.value for e in selected_experts]}"
    )

    return {
        "expert_panel_decision": {
            "primary_expert": primary_expert.value,
            "all_experts": [e.value for e in selected_experts],
            "needs_collaboration": len(selected_experts) > 1,
        }
    }


async def expert_panel_agent(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """
    Expert Panel 에이전트 노드

    선정된 전문가(들)가 응답 생성
    """
    configuration = Configuration.from_runnable_config(config)
    category = configuration.category or "탄소배출권"

    # 라우터 결정 가져오기
    panel_decision = getattr(state, 'expert_panel_decision', {})
    expert_values = panel_decision.get('all_experts', ['policy_expert'])

    # 전문가 역할로 변환
    selected_experts = []
    for ev in expert_values:
        try:
            selected_experts.append(ExpertRole(ev))
        except ValueError:
            selected_experts.append(ExpertRole.POLICY_EXPERT)

    # 단일 전문가 또는 다중 전문가 처리
    if len(selected_experts) == 1:
        response = await _run_single_expert(
            selected_experts[0], state, category
        )
    else:
        response = await _run_multiple_experts(
            selected_experts, state, category
        )

    # Mermaid 변환
    if response.content and isinstance(response.content, str):
        converted = detect_and_convert_mermaid(response.content)
        if converted != response.content:
            response = AIMessage(
                id=response.id,
                content=converted,
                tool_calls=getattr(response, 'tool_calls', []),
            )

    return {
        "messages": [response],
        "agent_used": f"expert_panel:{','.join(expert_values)}"
    }


async def _run_single_expert(
    expert_role: ExpertRole,
    state: State,
    category: str
) -> AIMessage:
    """단일 전문가 실행"""
    config = get_expert_config(expert_role)

    system_prompt = get_expert_prompt(
        expert_role,
        category,
        state.prefetched_context
    )

    # 도구 로드
    from react_agent.tools import get_all_tools
    all_tools = await get_all_tools()

    # 허용된 도구만 필터링
    allowed_tools = [
        tool for tool in all_tools
        if tool.name in config.tools
    ]

    # Sonnet 모델 사용 (전문가는 더 강력한 모델)
    llm = ChatAnthropic(
        temperature=0.1,
        model="claude-sonnet-4-20250514"
    )
    model = llm.bind_tools(allowed_tools) if allowed_tools else llm

    t0 = time.perf_counter()
    response = await model.ainvoke([
        {"role": "system", "content": system_prompt},
        *state.messages
    ])
    elapsed = time.perf_counter() - t0

    logger.info(
        f"⏱️ [Expert Panel: {config.name}] {elapsed:.2f}초"
    )

    # 헤더 추가
    if isinstance(response.content, str):
        header = format_expert_header(expert_role)
        response = AIMessage(
            id=response.id,
            content=header + response.content,
            tool_calls=getattr(response, 'tool_calls', []),
        )

    return response


async def _run_multiple_experts(
    experts: List[ExpertRole],
    state: State,
    category: str
) -> AIMessage:
    """다중 전문가 병렬 실행 및 통합"""
    import asyncio

    async def run_expert(role: ExpertRole) -> tuple:
        response = await _run_single_expert(role, state, category)
        return (role, response.content if isinstance(response.content, str) else "")

    # 병렬 실행
    t0 = time.perf_counter()
    results = await asyncio.gather(*[run_expert(e) for e in experts])
    elapsed = time.perf_counter() - t0

    # 결과 딕셔너리 변환
    expert_responses = {role: content for role, content in results}

    # 마지막 사용자 메시지
    last_msg = ""
    for msg in reversed(state.messages):
        if hasattr(msg, 'content'):
            last_msg = str(msg.content)
            break

    # 통합
    integrated = await collaborate_experts(expert_responses, last_msg, category)

    logger.info(
        f"⏱️ [Expert Panel Collaboration] {len(experts)}명 전문가 → {elapsed:.2f}초"
    )

    return AIMessage(content=integrated)
```

**Step 2: 커밋**

```bash
git add react-agent/src/react_agent/agents/expert_panel/nodes.py
git commit -m "feat: add Expert Panel agent nodes for LangGraph"
```

---

## Task 6: 기존 에이전트 설정 업데이트

**Files:**
- Modify: `react-agent/src/react_agent/agents/config.py`

**Step 1: AgentRole에 EXPERT_PANEL 추가**

```python
# config.py의 AgentRole enum에 추가
class AgentRole(str, Enum):
    """에이전트 역할 정의"""
    MANAGER = "manager"
    SIMPLE = "simple"
    CARBON_EXPERT = "carbon_expert"
    REGULATION_EXPERT = "regulation_expert"
    SUPPORT_EXPERT = "support_expert"
    EXPERT_PANEL = "expert_panel"  # 신규 추가
```

**Step 2: AGENT_REGISTRY에 EXPERT_PANEL 추가**

```python
# AGENT_REGISTRY에 추가
AgentRole.EXPERT_PANEL: AgentConfig(
    role=AgentRole.EXPERT_PANEL,
    name="Expert Panel (박사급 전문가단)",
    description="국내외 온실가스 정책 박사급 전문가 자문",
    model="claude-sonnet-4-20250514",  # 전문가는 Sonnet
    temperature=0.1,
    tools=[
        "search_knowledge_base",
        "search",
    ],
    min_complexity="complex",
    max_complexity="expert"
),
```

**Step 3: 커밋**

```bash
git add react-agent/src/react_agent/agents/config.py
git commit -m "feat: add EXPERT_PANEL to AgentRole enum"
```

---

## Task 7: State 업데이트

**Files:**
- Modify: `react-agent/src/react_agent/state.py`

**Step 1: expert_panel_decision 필드 추가**

state.py 파일에서 State 클래스에 다음 필드를 추가:

```python
# State 클래스에 추가
expert_panel_decision: Dict[str, Any] = field(default_factory=dict)
```

**Step 2: 커밋**

```bash
git add react-agent/src/react_agent/state.py
git commit -m "feat: add expert_panel_decision to State"
```

---

## Task 8: graph_multi.py 업데이트

**Files:**
- Modify: `react-agent/src/react_agent/graph_multi.py`

**Step 1: Expert Panel 노드 임포트 및 추가**

```python
# 임포트 추가
from react_agent.agents.expert_panel.nodes import (
    expert_panel_router,
    expert_panel_agent
)
from react_agent.agents.expert_panel.router import should_use_expert_panel

# 노드 추가
builder.add_node("expert_panel_router", expert_panel_router)
builder.add_node("expert_panel_agent", expert_panel_agent)
```

**Step 2: 라우팅 함수 수정**

```python
def route_after_manager(state: State) -> Literal[
    "simple_agent", "expert_agent", "expert_panel_router", "clarification_agent"
]:
    """Manager 판단 후 라우팅 - Expert Panel 추가"""
    decision = state.manager_decision
    assigned = decision.get("assigned_agent", "simple")
    confidence = decision.get("confidence", 0.5)
    complexity = decision.get("complexity", "unknown")

    # 신뢰도 낮으면 명확화 요청
    if confidence < CONFIDENCE_THRESHOLD:
        return "clarification_agent"

    # Expert Panel 사용 여부 확인
    last_msg = ""
    for msg in reversed(state.messages):
        if hasattr(msg, 'content'):
            last_msg = str(msg.content)
            break

    if should_use_expert_panel(complexity, confidence, last_msg):
        logger.info(f"[ROUTE] Expert Panel 사용 (복잡도: {complexity})")
        return "expert_panel_router"

    # 기존 라우팅
    if assigned == "simple":
        return "simple_agent"
    else:
        return "expert_agent"
```

**Step 3: 엣지 추가**

```python
# Manager 조건부 엣지 수정
builder.add_conditional_edges(
    "manager_agent",
    route_after_manager,
    {
        "simple_agent": "simple_agent",
        "expert_agent": "expert_agent",
        "expert_panel_router": "expert_panel_router",
        "clarification_agent": "clarification_agent"
    }
)

# Expert Panel 라우터 → Agent
builder.add_edge("expert_panel_router", "expert_panel_agent")

# Expert Panel Agent → Tools or End
builder.add_conditional_edges(
    "expert_panel_agent",
    route_after_agent,
    {
        "tools": "tools",
        "__end__": "__end__"
    }
)

# Tools에서 Expert Panel로 복귀 추가
def route_after_tools(state: State) -> Literal["simple_agent", "expert_agent", "expert_panel_agent"]:
    agent_used = state.agent_used

    if agent_used == "simple":
        return "simple_agent"
    elif agent_used and agent_used.startswith("expert_panel"):
        return "expert_panel_agent"
    else:
        return "expert_agent"
```

**Step 4: 커밋**

```bash
git add react-agent/src/react_agent/graph_multi.py
git commit -m "feat: integrate Expert Panel into multi-agent graph"
```

---

## Task 9: 지식베이스 폴더 구조 생성

**Files:**
- Create: `react-agent/knowledge_base/정책법규/.gitkeep`
- Create: `react-agent/knowledge_base/탄소배출권/.gitkeep`
- Create: `react-agent/knowledge_base/시장거래/.gitkeep`
- Create: `react-agent/knowledge_base/감축기술/.gitkeep`
- Create: `react-agent/knowledge_base/MRV검증/.gitkeep`

**Step 1: 디렉토리 생성**

```bash
mkdir -p react-agent/knowledge_base/{정책법규,탄소배출권,시장거래,감축기술,MRV검증}
touch react-agent/knowledge_base/정책법규/.gitkeep
touch react-agent/knowledge_base/탄소배출권/.gitkeep
touch react-agent/knowledge_base/시장거래/.gitkeep
touch react-agent/knowledge_base/감축기술/.gitkeep
touch react-agent/knowledge_base/MRV검증/.gitkeep
```

**Step 2: 커밋**

```bash
git add react-agent/knowledge_base/
git commit -m "feat: create knowledge base folder structure for Expert Panel"
```

---

## Task 10: 시맨틱 청킹 파이프라인 구현

**Files:**
- Create: `react-agent/src/react_agent/rag/chunking.py`

**Step 1: 시맨틱 청킹 구현**

```python
# react-agent/src/react_agent/rag/chunking.py
"""시맨틱 청킹 파이프라인"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ChunkMetadata:
    """청크 메타데이터"""
    doc_id: str
    chunk_id: str
    source: str
    document_type: str  # treaty, law, report, guideline
    region: str  # global, korea, eu, us, china
    topic: str  # policy, credit, market, technology, mrv
    language: str = "ko"
    expert_domain: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    hierarchy: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """문서 청크"""
    content: str
    metadata: ChunkMetadata


class SemanticChunker:
    """시맨틱 기반 문서 청킹"""

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        min_chunk_size: int = 100,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_document(
        self,
        text: str,
        doc_id: str,
        source: str,
        document_type: str = "report",
        region: str = "korea",
        topic: str = "policy",
    ) -> List[Chunk]:
        """문서를 시맨틱 청크로 분할"""

        # 1. 문단 단위로 분할
        paragraphs = self._split_paragraphs(text)

        # 2. 청크 생성
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_idx = 0

        for para in paragraphs:
            para_size = len(para)

            if current_size + para_size > self.chunk_size and current_chunk:
                # 현재 청크 저장
                chunk_text = "\n\n".join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    metadata = ChunkMetadata(
                        doc_id=doc_id,
                        chunk_id=f"{doc_id}_{chunk_idx:04d}",
                        source=source,
                        document_type=document_type,
                        region=region,
                        topic=topic,
                        expert_domain=self._detect_expert_domain(chunk_text),
                        keywords=self._extract_keywords(chunk_text),
                    )
                    chunks.append(Chunk(content=chunk_text, metadata=metadata))
                    chunk_idx += 1

                # 오버랩 처리
                overlap_text = current_chunk[-1] if current_chunk else ""
                current_chunk = [overlap_text, para] if overlap_text else [para]
                current_size = len(overlap_text) + para_size
            else:
                current_chunk.append(para)
                current_size += para_size

        # 마지막 청크 처리
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                metadata = ChunkMetadata(
                    doc_id=doc_id,
                    chunk_id=f"{doc_id}_{chunk_idx:04d}",
                    source=source,
                    document_type=document_type,
                    region=region,
                    topic=topic,
                    expert_domain=self._detect_expert_domain(chunk_text),
                    keywords=self._extract_keywords(chunk_text),
                )
                chunks.append(Chunk(content=chunk_text, metadata=metadata))

        logger.info(f"[Chunker] {doc_id}: {len(chunks)}개 청크 생성")
        return chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """문단 단위로 분할"""
        # 연속된 줄바꿈으로 분할
        paragraphs = re.split(r'\n\s*\n', text)
        # 빈 문단 제거 및 정리
        return [p.strip() for p in paragraphs if p.strip()]

    def _detect_expert_domain(self, text: str) -> List[str]:
        """텍스트에서 전문가 도메인 감지"""
        domains = []
        text_lower = text.lower()

        domain_keywords = {
            "policy_expert": ["법", "규정", "정책", "협약", "시행령", "법률"],
            "carbon_credit_expert": ["배출권", "KAU", "KCU", "할당", "거래"],
            "market_expert": ["시장", "가격", "거래소", "시세", "투자"],
            "technology_expert": ["기술", "감축", "CCUS", "수소", "재생"],
            "mrv_expert": ["산정", "검증", "MRV", "보고", "인벤토리"],
        }

        for domain, keywords in domain_keywords.items():
            if any(kw in text_lower for kw in keywords):
                domains.append(domain)

        return domains if domains else ["policy_expert"]

    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """키워드 추출 (간단한 규칙 기반)"""
        # 주요 용어 패턴
        patterns = [
            r'배출권[가-힣]*',
            r'탄소[가-힣]*',
            r'온실가스[가-힣]*',
            r'Scope\s*[123]',
            r'NDC',
            r'UNFCCC',
            r'파리협정',
            r'EU\s*ETS',
            r'CBAM',
            r'MRV',
            r'[A-Z]{2,5}',  # 약어
        ]

        keywords = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            keywords.update(matches[:3])  # 패턴당 최대 3개

        return list(keywords)[:max_keywords]


# 싱글톤 인스턴스
_chunker = None

def get_chunker() -> SemanticChunker:
    """청커 인스턴스 반환"""
    global _chunker
    if _chunker is None:
        _chunker = SemanticChunker()
    return _chunker
```

**Step 2: 커밋**

```bash
git add react-agent/src/react_agent/rag/chunking.py
git commit -m "feat: add semantic chunking pipeline for Expert Panel"
```

---

## Task 11: __init__.py 업데이트

**Files:**
- Modify: `react-agent/src/react_agent/agents/__init__.py`

**Step 1: Expert Panel 임포트 추가**

```python
# react-agent/src/react_agent/agents/__init__.py
"""멀티 에이전트 모듈"""

from .config import AgentRole, AgentConfig, AGENT_REGISTRY
from .nodes import manager_agent, simple_agent, expert_agent
from .prompts import get_agent_prompt

# Expert Panel 추가
from .expert_panel import (
    ExpertRole,
    ExpertConfig as ExpertPanelConfig,
    EXPERT_REGISTRY as EXPERT_PANEL_REGISTRY,
    get_expert_prompt,
    route_to_expert,
    collaborate_experts,
)
from .expert_panel.nodes import expert_panel_router, expert_panel_agent

__all__ = [
    # 기존
    "AgentRole",
    "AgentConfig",
    "AGENT_REGISTRY",
    "manager_agent",
    "simple_agent",
    "expert_agent",
    "get_agent_prompt",
    # Expert Panel
    "ExpertRole",
    "ExpertPanelConfig",
    "EXPERT_PANEL_REGISTRY",
    "get_expert_prompt",
    "route_to_expert",
    "collaborate_experts",
    "expert_panel_router",
    "expert_panel_agent",
]
```

**Step 2: 커밋**

```bash
git add react-agent/src/react_agent/agents/__init__.py
git commit -m "feat: export Expert Panel from agents module"
```

---

## Task 12: 최종 통합 테스트

**Step 1: 서버 시작 테스트**

```bash
cd react-agent
uv run python -c "from react_agent.graph_multi import graph; print('Graph loaded:', graph.name)"
```

**Step 2: Expert Panel 임포트 테스트**

```bash
cd react-agent
uv run python -c "
from react_agent.agents.expert_panel import ExpertRole, EXPERT_REGISTRY
print('Expert Roles:', [e.value for e in ExpertRole])
print('Experts:', [c.name for c in EXPERT_REGISTRY.values()])
"
```

**Step 3: 최종 커밋**

```bash
git add .
git commit -m "feat: complete Expert Panel integration

- 5 PhD-level expert agents (Policy, Carbon Credit, Market, Technology, MRV)
- Keyword-based routing to appropriate expert
- Multi-expert collaboration for complex questions
- Semantic chunking pipeline for knowledge base
- Knowledge base folder structure by topic

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## 요약

| Task | 설명 | 파일 수 |
|------|------|---------|
| 1 | Expert Panel 설정 및 역할 정의 | 2 |
| 2 | Expert Panel 프롬프트 생성 | 1 |
| 3 | Expert Panel 라우터 구현 | 1 |
| 4 | Expert Panel 협업 로직 구현 | 1 |
| 5 | Expert Panel 노드 구현 | 1 |
| 6 | 기존 에이전트 설정 업데이트 | 1 |
| 7 | State 업데이트 | 1 |
| 8 | graph_multi.py 업데이트 | 1 |
| 9 | 지식베이스 폴더 구조 생성 | 5 |
| 10 | 시맨틱 청킹 파이프라인 | 1 |
| 11 | __init__.py 업데이트 | 1 |
| 12 | 최종 통합 테스트 | 0 |

**총 12개 Task, 신규 파일 13개, 수정 파일 4개**
