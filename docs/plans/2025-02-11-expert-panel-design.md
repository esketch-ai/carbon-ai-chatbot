# Expert Panel 시스템 설계

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 국내외 온실가스 감축 정책 전문가 패널 시스템 구축

**Architecture:** 5명의 박사급 전문가 에이전트를 Manager 하위에 Expert Panel로 구성하여, 복잡한 정책 질문에 대해 단일 또는 다중 전문가 협업 응답 제공

**Tech Stack:** LangGraph, ChromaDB, Sentence Transformers, LangChain Text Splitters

---

## 1. 전문가 팀 구성

| 전문가 | 페르소나 | 핵심 역할 |
|--------|----------|-----------|
| 정책법규 전문가 | Dr. 김정책 | 국제협약, 국내법, 규제 해석 |
| 탄소배출권 전문가 | Dr. 한배출 | 배출권 종류, 할당, 거래 실무 |
| 시장거래 전문가 | Dr. 이시장 | 가격 분석, 시장 메커니즘, 투자 |
| 감축기술 전문가 | Dr. 박기술 | CCUS, 탈탄소 기술, 경제성 |
| MRV검증 전문가 | Dr. 최검증 | 산정, 보고, 검증, 인벤토리 |

## 2. 지식베이스 구조

```
knowledge_base/
├── 정책법규/
│   ├── 국제협약/ (파리협정, 교토의정서, UNFCCC COP 결정문)
│   ├── 한국/ (배출권거래법, 탄소중립기본법, 시행령)
│   ├── EU/ (EU ETS, CBAM, Fit for 55)
│   ├── 미국/ (IRA, EPA 규정)
│   └── 기타국가/ (중국, 일본, 영국)
│
├── 탄소배출권/
│   ├── 할당계획/ (1~4차 계획기간)
│   ├── 배출권종류/ (KAU, KCU, KOC)
│   ├── 거래규정/
│   ├── 외부사업/
│   └── 제출정산/
│
├── 시장거래/
│   ├── ETS시장/
│   ├── 자발적시장/
│   └── 분석보고서/
│
├── 감축기술/
│   ├── IPCC보고서/
│   ├── 기술가이드/
│   └── 산업별/
│
└── MRV검증/
    ├── 산정지침/
    ├── 검증기준/
    └── 보고양식/
```

## 3. 시맨틱 청킹 설정

| 항목 | 설정값 |
|------|--------|
| 청크 크기 | 512~1024 토큰 |
| 오버랩 | 128 토큰 (20%) |
| 분할 기준 | 문단 > 문장 경계 |
| 임베딩 모델 | paraphrase-multilingual-MiniLM-L12-v2 |

## 4. 메타데이터 스키마

```python
{
    "doc_id": str,
    "chunk_id": str,
    "source": str,
    "document_type": str,  # treaty, law, report, guideline
    "region": str,         # global, korea, eu, us, china
    "topic": str,          # policy, credit, market, technology, mrv
    "effective_date": str,
    "language": str,
    "expert_domain": list[str],
    "keywords": list[str],
    "hierarchy": dict
}
```

## 5. 시스템 아키텍처

```
사용자 질문
    │
    ▼
Manager Agent
    │
    ├─ Simple/Medium → 기존 Agents
    │
    └─ Complex/Expert → Expert Panel
                            │
                    ┌───────┴───────┐
                    ▼               ▼
              단일 전문가      다중 전문가 협업
```

## 6. 라우팅 기준

| 복잡도 | 라우팅 대상 | 예시 |
|--------|-------------|------|
| Simple | Simple Agent | "배출권이 뭐에요?" |
| Medium | 기존 Expert | "우리 회사 배출량" |
| Complex | Expert Panel (단일) | "4차 계획기간 할당 방식" |
| Expert+ | Expert Panel (다중) | "EU CBAM이 한국 철강에 미치는 영향" |

## 7. 구현 파일 목록

### 신규 파일
- `agents/expert_panel/__init__.py`
- `agents/expert_panel/experts.py` - 5명 전문가 정의
- `agents/expert_panel/prompts.py` - 박사급 페르소나 프롬프트
- `agents/expert_panel/router.py` - 전문가 라우팅 로직
- `agents/expert_panel/collaboration.py` - 다중 전문가 협업
- `tools/expert_tools.py` - 전문가 전용 도구
- `rag/chunking.py` - 시맨틱 청킹 파이프라인
- `rag/metadata.py` - 메타데이터 스키마

### 수정 파일
- `agents/config.py` - Expert Panel 에이전트 등록
- `agents/prompts.py` - Manager 프롬프트 수정
- `agents/nodes.py` - expert_panel_agent 노드 추가
- `graph_multi.py` - Expert Panel 노드 연결
- `rag/indexer.py` - 전문가별 컬렉션 인덱싱

## 8. 전문가별 도구

### 정책법규 전문가
- get_policy_timeline
- compare_regulations
- analyze_legal_implications

### 탄소배출권 전문가
- calculate_credit_demand
- compare_credit_types
- get_submission_deadline

### 시장거래 전문가
- analyze_market_trend
- compare_carbon_markets
- get_carbon_price

### 감축기술 전문가
- calculate_abatement_cost
- compare_technologies
- get_emission_factors

### MRV검증 전문가
- validate_methodology
- calculate_emissions
- get_verification_checklist
