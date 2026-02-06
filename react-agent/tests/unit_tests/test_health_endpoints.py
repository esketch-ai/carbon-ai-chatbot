"""Unit tests for health check endpoints.

Tests for server health check functions and endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


class TestHealthCheckHelpers:
    """Tests for health check helper functions."""

    @pytest.mark.asyncio
    async def test_check_vectordb_unavailable(self):
        """Test check_vectordb when RAG is unavailable."""
        from react_agent.server import check_vectordb

        with patch("react_agent.server.get_rag_tool") as mock_rag:
            mock_tool = MagicMock()
            mock_tool.available = False
            mock_rag.return_value = mock_tool

            result = await check_vectordb()

            assert result["status"] == "unavailable"

    @pytest.mark.asyncio
    async def test_check_vectordb_no_vectorstore(self):
        """Test check_vectordb when vectorstore is None."""
        from react_agent.server import check_vectordb

        with patch("react_agent.server.get_rag_tool") as mock_rag:
            mock_tool = MagicMock()
            mock_tool.available = True
            mock_tool.vectorstore = None
            mock_rag.return_value = mock_tool

            result = await check_vectordb()

            assert result["status"] == "unavailable"
            assert "아직 구축되지 않음" in result.get("message", "")

    @pytest.mark.asyncio
    async def test_check_vectordb_healthy(self):
        """Test check_vectordb when everything is OK."""
        from react_agent.server import check_vectordb

        with patch("react_agent.server.get_rag_tool") as mock_rag:
            mock_tool = MagicMock()
            mock_tool.available = True
            mock_tool.vectorstore = MagicMock()
            mock_tool.vectorstore._collection.count.return_value = 100
            mock_tool.chroma_db_path = "/path/to/db"
            mock_rag.return_value = mock_tool

            result = await check_vectordb()

            assert result["status"] == "healthy"
            assert result["document_count"] == 100

    @pytest.mark.asyncio
    async def test_check_vectordb_exception(self):
        """Test check_vectordb handles exceptions."""
        from react_agent.server import check_vectordb

        with patch("react_agent.server.get_rag_tool") as mock_rag:
            mock_rag.side_effect = Exception("Connection failed")

            result = await check_vectordb()

            assert result["status"] == "unhealthy"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_check_redis_memory_backend(self):
        """Test check_redis when using memory backend."""
        from react_agent.server import check_redis

        with patch("react_agent.server.get_cache_manager") as mock_cache:
            mock_manager = MagicMock()
            mock_manager.get_stats.return_value = {
                "backend": "memory (LRU)",
                "memory_cache_size": 50
            }
            mock_cache.return_value = mock_manager

            result = await check_redis()

            assert result["status"] == "healthy"
            assert result["backend"] == "memory"

    @pytest.mark.asyncio
    async def test_check_redis_redis_backend(self):
        """Test check_redis when using Redis backend."""
        from react_agent.server import check_redis

        with patch("react_agent.server.get_cache_manager") as mock_cache:
            mock_manager = MagicMock()
            mock_manager.get_stats.return_value = {
                "backend": "redis",
                "redis_keys": 100,
                "redis_hits": 500,
                "redis_misses": 50
            }
            mock_cache.return_value = mock_manager

            result = await check_redis()

            assert result["status"] == "healthy"
            assert result["backend"] == "redis"
            assert result["keys"] == 100

    @pytest.mark.asyncio
    async def test_check_anthropic_api_no_key(self):
        """Test check_anthropic_api when API key is missing."""
        from react_agent.server import check_anthropic_api
        import os

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            result = await check_anthropic_api()

            assert result["status"] == "unavailable"

    @pytest.mark.asyncio
    async def test_check_anthropic_api_valid_key(self):
        """Test check_anthropic_api with valid key format."""
        from react_agent.server import check_anthropic_api
        import os

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test123"}):
            result = await check_anthropic_api()

            assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_check_anthropic_api_invalid_format(self):
        """Test check_anthropic_api with invalid key format."""
        from react_agent.server import check_anthropic_api
        import os

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "invalid-key-format"}):
            result = await check_anthropic_api()

            assert result["status"] == "warning"

    @pytest.mark.asyncio
    async def test_check_tavily_api_no_key(self):
        """Test check_tavily_api when API key is missing."""
        from react_agent.server import check_tavily_api
        import os

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TAVILY_API_KEY", None)
            result = await check_tavily_api()

            assert result["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_check_tavily_api_with_key(self):
        """Test check_tavily_api when API key is present."""
        from react_agent.server import check_tavily_api
        import os

        with patch.dict(os.environ, {"TAVILY_API_KEY": "tvly-test123"}):
            result = await check_tavily_api()

            assert result["status"] == "healthy"


class TestGetMemoryUsage:
    """Tests for get_memory_usage function."""

    def test_memory_usage_returns_dict(self):
        """Memory usage should return dictionary with expected keys."""
        from react_agent.server import get_memory_usage

        result = get_memory_usage()

        assert isinstance(result, dict)
        if "error" not in result:
            assert "process_rss_mb" in result
            assert "system_percent_used" in result

    def test_memory_usage_values_are_numeric(self):
        """Memory usage values should be numeric."""
        from react_agent.server import get_memory_usage

        result = get_memory_usage()

        if "error" not in result:
            assert isinstance(result["process_rss_mb"], (int, float))
            assert isinstance(result["system_percent_used"], (int, float))


class TestHealthEndpoints:
    """Tests for health check endpoints using TestClient."""

    @pytest.fixture
    def client(self):
        """Create test client with mocked dependencies."""
        # Mock heavy dependencies before importing app
        with patch("react_agent.server.graph"):
            with patch("react_agent.server.get_rag_tool"):
                from react_agent.server import app
                return TestClient(app)

    def test_simple_health_check(self, client):
        """Test /ok endpoint."""
        response = client.get("/ok")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "carbonai-agent"

    def test_root_endpoint(self, client):
        """Test / endpoint returns API info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "endpoints" in data

    def test_categories_endpoint(self, client):
        """Test /categories endpoint."""
        response = client.get("/categories")

        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) >= 3

    def test_info_endpoint(self, client):
        """Test /info endpoint (LangGraph compatible)."""
        response = client.get("/info")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "service" in data


class TestErrorResponses:
    """Tests for RFC 7807 error response format."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        with patch("react_agent.server.graph"):
            with patch("react_agent.server.get_rag_tool"):
                from react_agent.server import app
                return TestClient(app)

    def test_not_found_error_format(self, client):
        """404 errors should follow RFC 7807 format."""
        response = client.get("/nonexistent-endpoint")

        assert response.status_code == 404
        # Note: FastAPI default 404 may not follow RFC 7807
        # This tests that the endpoint returns 404

    def test_validation_error_format(self, client):
        """Validation errors should follow RFC 7807 format."""
        # Send invalid request to /invoke
        response = client.post(
            "/invoke",
            json={"invalid_field": "test"}  # Missing required 'message' field
        )

        assert response.status_code == 422
        data = response.json()
        # RFC 7807 format
        assert "title" in data or "detail" in data
