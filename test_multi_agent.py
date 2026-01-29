"""멀티 에이전트 시스템 성능 테스트

간단한 질문 vs 복잡한 질문의 에이전트 라우팅 및 성능 비교
"""

import asyncio
import time
from langchain_core.messages import HumanMessage
from react_agent.graph_multi import graph

# 테스트 케이스
TEST_CASES = [
    {
        "name": "간단한 질문 1 - 기본 개념",
        "query": "배출권이 뭐에요?",
        "category": "탄소배출권",
        "expected_agent": "simple",
        "description": "기본 개념 설명 - Simple Agent 기대"
    },
    {
        "name": "간단한 질문 2 - 플랫폼 정보",
        "query": "NET-Z 플랫폼이 뭐에요?",
        "category": "고객상담",
        "expected_agent": "simple",
        "description": "플랫폼 일반 정보 - Simple Agent 기대"
    },
    {
        "name": "복잡한 질문 1 - 데이터 조회",
        "query": "오늘 배출권 거래량 조회해줘",
        "category": "탄소배출권",
        "expected_agent": "carbon_expert",
        "description": "실시간 데이터 조회 - Carbon Expert 기대"
    },
    {
        "name": "복잡한 질문 2 - 계산",
        "query": "우리 회사 2025년 Scope 1 배출량 계산해줘",
        "category": "규제대응",
        "expected_agent": "regulation_expert",
        "description": "배출량 계산 - Regulation Expert 기대"
    },
    {
        "name": "복잡한 질문 3 - 다단계 작업",
        "query": "배출량 계산하고 부족분 알려줘",
        "category": "규제대응",
        "expected_agent": "regulation_expert",
        "description": "다단계 처리 - Regulation Expert 기대"
    }
]


async def test_single_case(test_case):
    """단일 테스트 케이스 실행"""
    print("\n" + "=" * 80)
    print(f"[TEST] {test_case['name']}")
    print(f"[QUERY] {test_case['query']}")
    print(f"[CATEGORY] {test_case['category']}")
    print(f"[EXPECTED] {test_case['expected_agent']}")
    print("=" * 80)

    config = {
        "configurable": {
            "category": test_case['category'],
            "model": "claude-haiku-4-5",
            "thread_id": f"test-{time.time()}"
        }
    }

    input_data = {
        "messages": [HumanMessage(content=test_case['query'])]
    }

    # 시작 시간
    start_time = time.time()

    try:
        # 스트리밍으로 실행 (노드별 진행 확인)
        async for chunk in graph.astream(input_data, config=config, stream_mode="values"):
            # Manager 결정 확인
            if "manager_decision" in chunk:
                decision = chunk["manager_decision"]
                print(f"\n[MANAGER DECISION]")
                print(f"  - Complexity: {decision.get('complexity')}")
                print(f"  - Assigned Agent: {decision.get('assigned_agent')}")
                print(f"  - Reasoning: {decision.get('reasoning')}")
                print(f"  - Confidence: {decision.get('confidence')}")

            # 에이전트 사용 확인
            if "agent_used" in chunk and chunk["agent_used"]:
                print(f"\n[AGENT USED] {chunk['agent_used']}")

            # 최종 메시지
            if "messages" in chunk and len(chunk["messages"]) > 0:
                last_message = chunk["messages"][-1]
                if hasattr(last_message, 'content') and last_message.content:
                    content = last_message.content
                    # 도구 호출이 있으면 표시
                    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                        tool_names = [tc.get('name', 'unknown') for tc in last_message.tool_calls]
                        print(f"\n[TOOL CALLS] {', '.join(tool_names)}")
                    # 최종 답변이면 표시
                    elif isinstance(content, str) and len(content) > 50:
                        print(f"\n[RESPONSE] (first 200 chars):")
                        print(f"  {content[:200]}...")

        # 종료 시간
        end_time = time.time()
        elapsed = end_time - start_time

        print(f"\n[TIME] {elapsed:.2f}s")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


async def run_all_tests():
    """모든 테스트 실행"""
    print("\n" + "=" * 80)
    print("멀티 에이전트 시스템 성능 평가 시작")
    print("=" * 80)

    for i, test_case in enumerate(TEST_CASES, 1):
        await test_single_case(test_case)

        # 마지막 케이스가 아니면 대기
        if i < len(TEST_CASES):
            print("\n다음 테스트까지 2초 대기...")
            await asyncio.sleep(2)

    print("\n" + "=" * 80)
    print("테스트 완료!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
