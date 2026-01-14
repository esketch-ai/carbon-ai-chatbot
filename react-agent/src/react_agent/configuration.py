"""Define the configurable parameters for the agent."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Annotated, Optional

from langchain_core.runnables import RunnableConfig, ensure_config
from langgraph.config import get_config

from react_agent import prompts


@dataclass(kw_only=True)
class Configuration:
    """The configuration for the agent."""

    system_prompt: str = field(
        default=prompts.SYSTEM_PROMPT,
        metadata={
            "description": "The system prompt to use for the agent's interactions. "
            "This prompt sets the context and behavior for the agent."
        },
    )

    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="claude-haiku-4-5",
        metadata={
            "description": "The name of the language model to use for the agent's main interactions. "
            "Available models: claude-haiku-4-5, claude-3-5-sonnet, claude-3-opus-20240229, claude-3-sonnet-20240229, claude-3-haiku-20240307"
        },
    )

    max_search_results: int = field(
        default=10,
        metadata={
            "description": "The maximum number of search results to return for each search query."
        },
    )

    category: Optional[str] = field(
        default=None,
        metadata={
            "description": "카테고리 (탄소배출권, 규제대응, 고객상담). 카테고리별 특화된 답변을 제공합니다."
        },
    )

    @classmethod
    def from_runnable_config(cls, config: RunnableConfig) -> Configuration:
        """Create a Configuration instance from a RunnableConfig object."""
        config = ensure_config(config)
        configurable = config.get("configurable") or {}
        _fields = {f.name for f in fields(cls) if f.init}
        return cls(**{k: v for k, v in configurable.items() if k in _fields})

    @classmethod
    def from_context(cls) -> Configuration:
        """Create a Configuration instance from the current context."""
        try:
            config = get_config()
        except RuntimeError:
            config = None
        config = ensure_config(config)
        configurable = config.get("configurable") or {}
        _fields = {f.name for f in fields(cls) if f.init}
        return cls(**{k: v for k, v in configurable.items() if k in _fields})
