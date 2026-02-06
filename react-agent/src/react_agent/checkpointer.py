"""Checkpointer factory for LangGraph.

This module provides a factory function to create checkpointers based on
environment configuration. It supports both in-memory (development) and
PostgreSQL (production) checkpointers.

Usage:
    from react_agent.checkpointer import get_checkpointer

    checkpointer = get_checkpointer()
    graph = builder.compile(checkpointer=checkpointer)
"""

import os
import logging
from typing import Union

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


def get_checkpointer() -> Union[MemorySaver, "PostgresSaver"]:
    """환경에 따라 적절한 체크포인터를 반환합니다.

    환경 변수:
        USE_POSTGRES_CHECKPOINT: "true"로 설정하면 PostgreSQL 체크포인터 사용
        POSTGRES_URL: PostgreSQL 연결 URL (USE_POSTGRES_CHECKPOINT=true일 때 필수)

    Returns:
        MemorySaver 또는 PostgresSaver 인스턴스

    Raises:
        ValueError: PostgreSQL 모드인데 POSTGRES_URL이 설정되지 않은 경우
        ImportError: langgraph-checkpoint-postgres 패키지가 설치되지 않은 경우

    Examples:
        >>> # 기본값: 메모리 체크포인터
        >>> checkpointer = get_checkpointer()

        >>> # PostgreSQL 사용 (환경 변수 설정 필요)
        >>> # USE_POSTGRES_CHECKPOINT=true
        >>> # POSTGRES_URL=postgresql://user:pass@localhost:5432/dbname
        >>> checkpointer = get_checkpointer()
    """
    use_postgres = os.getenv("USE_POSTGRES_CHECKPOINT", "false").lower() == "true"

    if use_postgres:
        postgres_url = os.getenv("POSTGRES_URL")
        if not postgres_url:
            raise ValueError(
                "POSTGRES_URL 환경 변수가 설정되지 않았습니다. "
                "PostgreSQL 체크포인터를 사용하려면 연결 URL을 설정해주세요. "
                "예: POSTGRES_URL=postgresql://user:password@localhost:5432/dbname"
            )

        try:
            from langgraph.checkpoint.postgres import PostgresSaver
        except ImportError as e:
            raise ImportError(
                "langgraph-checkpoint-postgres 패키지가 설치되지 않았습니다. "
                "다음 명령어로 설치해주세요: pip install langgraph-checkpoint-postgres"
            ) from e

        logger.info("PostgreSQL 체크포인터를 사용합니다.")
        return PostgresSaver.from_conn_string(postgres_url)

    logger.info("메모리 체크포인터를 사용합니다.")
    return MemorySaver()


def get_async_checkpointer() -> Union[MemorySaver, "AsyncPostgresSaver"]:
    """비동기 환경을 위한 체크포인터를 반환합니다.

    PostgreSQL의 경우 AsyncPostgresSaver를 반환하여 비동기 연결을 지원합니다.

    환경 변수:
        USE_POSTGRES_CHECKPOINT: "true"로 설정하면 PostgreSQL 체크포인터 사용
        POSTGRES_URL: PostgreSQL 연결 URL (USE_POSTGRES_CHECKPOINT=true일 때 필수)

    Returns:
        MemorySaver 또는 AsyncPostgresSaver 인스턴스

    Raises:
        ValueError: PostgreSQL 모드인데 POSTGRES_URL이 설정되지 않은 경우
        ImportError: langgraph-checkpoint-postgres 패키지가 설치되지 않은 경우
    """
    use_postgres = os.getenv("USE_POSTGRES_CHECKPOINT", "false").lower() == "true"

    if use_postgres:
        postgres_url = os.getenv("POSTGRES_URL")
        if not postgres_url:
            raise ValueError(
                "POSTGRES_URL 환경 변수가 설정되지 않았습니다. "
                "PostgreSQL 체크포인터를 사용하려면 연결 URL을 설정해주세요."
            )

        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        except ImportError as e:
            raise ImportError(
                "langgraph-checkpoint-postgres 패키지가 설치되지 않았습니다. "
                "다음 명령어로 설치해주세요: pip install langgraph-checkpoint-postgres"
            ) from e

        logger.info("비동기 PostgreSQL 체크포인터를 사용합니다.")
        return AsyncPostgresSaver.from_conn_string(postgres_url)

    logger.info("메모리 체크포인터를 사용합니다.")
    return MemorySaver()
