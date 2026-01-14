#!/usr/bin/env python3
"""캐시 관리 유틸리티 스크립트

캐시를 클리어하거나 통계를 확인할 수 있는 CLI 도구
"""

import argparse
import logging
from react_agent.cache_manager import get_cache_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="CarbonAI 캐시 관리 도구"
    )
    parser.add_argument(
        "action",
        choices=["clear", "stats", "clear-rag", "clear-llm"],
        help="수행할 작업 (clear: 전체 캐시 클리어, clear-rag: RAG 캐시만, clear-llm: LLM 캐시만, stats: 통계 확인)"
    )

    args = parser.parse_args()
    cache_manager = get_cache_manager()

    if args.action == "clear":
        count = cache_manager.clear()
        logger.info(f"✓ 전체 캐시 클리어 완료: {count}개 항목 삭제")

    elif args.action == "clear-rag":
        count = cache_manager.clear(prefix="rag")
        logger.info(f"✓ RAG 캐시 클리어 완료: {count}개 항목 삭제")

    elif args.action == "clear-llm":
        count = cache_manager.clear(prefix="llm")
        logger.info(f"✓ LLM 캐시 클리어 완료: {count}개 항목 삭제")

    elif args.action == "stats":
        stats = cache_manager.get_stats()
        logger.info("=== 캐시 통계 ===")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")


if __name__ == "__main__":
    main()
