# Weekly Analysis Pipeline Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 매주 국내외 정책/뉴스를 크롤링하여 5명의 PhD 전문가가 분석하고, 지식베이스를 자동으로 발전시키는 파이프라인 구축

**Architecture:** 하이브리드 분류 시스템 (규칙 기반 + LLM 회의) + 완전 자동화 주간 파이프라인 + 동적 전문가 생성

**Tech Stack:** Python, LangGraph, APScheduler, BeautifulSoup/httpx, ChromaDB

---

## 1. 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    Weekly Analysis Pipeline                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────────────┐   │
│  │ Crawler  │───▶│ Rule-based   │───▶│ Expert Panel        │   │
│  │ (Weekly) │    │ Classifier   │    │ Analysis            │   │
│  └──────────┘    └──────────────┘    └─────────────────────┘   │
│       │                │                       │                │
│       ▼                ▼                       ▼                │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────────────┐   │
│  │ Sources  │    │ Expert       │    │ Outputs             │   │
│  │ - 환경부  │    │ Assignment   │    │ - 주간 브리핑        │   │
│  │ - UNFCCC │    │ - 기존 5명    │    │ - 지식베이스 청크    │   │
│  │ - EU     │    │ - 신규 자동   │    │ - 신규 전문가 등록   │   │
│  │ - 언론   │    │   생성        │    │                     │   │
│  └──────────┘    └──────────────┘    └─────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 2. 크롤링 소스

### 국내 공식 소스
| 소스 | URL | 수집 대상 |
|------|-----|----------|
| 환경부 | me.go.kr | 보도자료, 정책공고 |
| 산업통상자원부 | motie.go.kr | 에너지정책, 산업정책 |
| 한국환경공단 | keco.or.kr | 배출권 공고, 검증 안내 |
| 온실가스종합정보센터 | gir.go.kr | 통계, 인벤토리 |

### 국제 공식 소스
| 소스 | URL | 수집 대상 |
|------|-----|----------|
| UNFCCC | unfccc.int | 협상 결과, NDC 갱신 |
| EU Commission | ec.europa.eu | ETS 정책, CBAM 업데이트 |
| IPCC | ipcc.ch | 보고서, 가이드라인 |
| IEA | iea.org | 에너지 전망, 기술 리포트 |

### 주요 언론
| 소스 | 유형 | 특화 분야 |
|------|------|----------|
| Reuters Climate | 국제 | 글로벌 탄소시장 |
| Bloomberg Green | 국제 | 금융/투자 |
| 에너지경제 | 국내 | 에너지/환경 전문 |
| 전기신문 | 국내 | 전력/에너지 |

## 3. 분류 및 회의 로직

### 1단계: 규칙 기반 분류
- 키워드 매칭으로 담당 전문가 자동 배정
- 매칭률 기반 주/부 전문가 결정

### 2단계: LLM 회의 트리거 조건
- 기존 전문가 키워드 매칭률 < 30%
- 새로운 용어/개념 3개 이상 감지
- 복합 분야 (3개 이상 전문가 관련)

### 3단계: 전문가 회의 프로세스
1. 각 전문가가 콘텐츠 관련성 평가 (0-100점)
2. 담당 불가 분야 식별 및 신규 전문가 제안
3. 합의: 분석 담당자 + 신규 전문가 프로필 도출

### 신규 전문가 자동 생성
- 회의에서 도출된 전문 분야 기반
- 자동 role, name, expertise, keywords 생성
- EXPERT_REGISTRY에 동적 등록

## 4. 주간 브리핑 리포트 구조

```markdown
# 주간 탄소정책 브리핑 (YYYY-MM-DD ~ MM-DD)

## 요약 대시보드
- 수집/분석 통계
- 신규 청크/전문가 현황

## 전문가별 섹션
- 주요 발견
- 시사점

## 상호 연관 분석
- 분야간 연결고리

## 지식베이스 업데이트 요약
```

## 5. 청크 메타데이터 확장

```python
ChunkMetadata(
    # 기존 필드
    doc_id, chunk_id, source, document_type, region, topic, language,
    expert_domain, keywords,
    # 신규 필드
    date_collected: str,        # 수집 일자
    analyzed_by: List[str],     # 분석 전문가
    confidence_score: float,    # 분석 신뢰도
    related_chunks: List[str],  # 연관 청크 ID
)
```

## 6. 자동화 스케줄

- **실행 시간:** 매주 월요일 00:00 (KST)
- **파이프라인 단계:**
  1. 00:00 크롤링
  2. 01:00 전처리
  3. 02:00 규칙 분류
  4. 02:30 LLM 회의 (필요시)
  5. 03:00 전문가 분석
  6. 05:00 청킹 & 저장
  7. 06:00 리포트 생성
  8. 06:30 알림 발송

## 7. 파일 구조

```
react-agent/src/react_agent/
├── weekly_pipeline/
│   ├── __init__.py
│   ├── crawler.py
│   ├── preprocessor.py
│   ├── classifier.py
│   ├── expert_meeting.py
│   ├── analyzer.py
│   ├── report_generator.py
│   └── scheduler.py
├── agents/expert_panel/
│   └── config.py (수정)
└── rag/
    ├── chunking.py (수정)
    └── knowledge_base.py (신규)
```

## 8. 구현 태스크

### Phase 1: 크롤링 인프라
1. 크롤러 기본 구조
2. 전처리 파이프라인
3. 소스 레지스트리

### Phase 2: 분류 및 회의 시스템
4. 규칙 기반 분류기
5. LLM 회의 엔진
6. 동적 전문가 생성

### Phase 3: 분석 및 저장
7. 전문가 분석 러너
8. 청크 메타데이터 강화
9. 지식베이스 저장소

### Phase 4: 리포트 및 자동화
10. 주간 브리핑 생성기
11. 스케줄러 설정
12. 알림 시스템
