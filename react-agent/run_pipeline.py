#!/usr/bin/env python3
"""Manual script to run the weekly pipeline for testing."""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from react_agent.weekly_pipeline.pipeline import WeeklyPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Run the weekly pipeline."""
    logger.info("=" * 60)
    logger.info("Weekly Pipeline 수동 실행 시작")
    logger.info("=" * 60)

    # Create pipeline (look back 7 days, enable LLM meeting)
    pipeline = WeeklyPipeline(
        days_back=7,
        enable_llm_meeting=True
    )

    try:
        # Run the pipeline
        result = await pipeline.run()

        # Print results
        logger.info("=" * 60)
        logger.info("Pipeline 실행 완료")
        logger.info("=" * 60)
        logger.info(f"실행 시간: {result.start_time} ~ {result.end_time}")
        logger.info(f"크롤링된 콘텐츠: {result.crawled_count}개")
        logger.info(f"전처리된 콘텐츠: {result.preprocessed_count}개")
        logger.info(f"분석된 콘텐츠: {result.analyzed_count}개")
        logger.info(f"생성된 청크: {result.chunks_created}개")
        logger.info(f"새 전문가: {result.new_experts}")
        logger.info(f"보고서 경로: {result.report_path}")

        if result.errors:
            logger.warning(f"오류 발생: {len(result.errors)}개")
            for error in result.errors:
                logger.warning(f"  - {error}")

    except Exception as e:
        logger.error(f"Pipeline 실행 실패: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
