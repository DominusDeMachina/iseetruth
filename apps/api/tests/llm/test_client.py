"""Tests for OllamaClient."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.llm.client import OllamaClient, OllamaUnavailableError


@pytest.fixture
def client():
    return OllamaClient(base_url="http://localhost:11434")


def _make_response(status_code: int, json_data: dict) -> MagicMock:
    """Create a mock httpx.Response with raise_for_status support."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


class TestOllamaChat:
    @patch("app.llm.client.httpx.Client")
    def test_chat_success(self, mock_client_cls, client):
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.post.return_value = _make_response(
            200,
            {
                "message": {"role": "assistant", "content": '{"entities": []}'},
                "done": True,
            },
        )

        result = client.chat(
            model="qwen3.5:9b",
            messages=[{"role": "user", "content": "extract entities"}],
            format="json",
        )

        assert result == {
            "message": {"role": "assistant", "content": '{"entities": []}'},
            "done": True,
        }
        mock_http.post.assert_called_once()
        call_kwargs = mock_http.post.call_args
        assert "/api/chat" in call_kwargs[0][0]

    @patch("app.llm.client.httpx.Client")
    def test_chat_with_temperature(self, mock_client_cls, client):
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.post.return_value = _make_response(
            200,
            {"message": {"role": "assistant", "content": "ok"}, "done": True},
        )

        client.chat(
            model="qwen3.5:9b",
            messages=[{"role": "user", "content": "test"}],
            temperature=0.5,
        )

        body = mock_http.post.call_args[1]["json"]
        assert body["options"]["temperature"] == 0.5

    @patch("app.llm.client.httpx.Client")
    def test_chat_connection_error(self, mock_client_cls, client):
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.post.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(OllamaUnavailableError, match="Ollama"):
            client.chat(
                model="qwen3.5:9b",
                messages=[{"role": "user", "content": "test"}],
            )

    @patch("app.llm.client.httpx.Client")
    def test_chat_timeout_error(self, mock_client_cls, client):
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.post.side_effect = httpx.TimeoutException("Timed out")

        with pytest.raises(OllamaUnavailableError, match="Ollama"):
            client.chat(
                model="qwen3.5:9b",
                messages=[{"role": "user", "content": "test"}],
            )

    @patch("app.llm.client.httpx.Client")
    def test_chat_http_error(self, mock_client_cls, client):
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.post.return_value = _make_response(500, {})

        with pytest.raises(OllamaUnavailableError, match="Ollama"):
            client.chat(
                model="qwen3.5:9b",
                messages=[{"role": "user", "content": "test"}],
            )


class TestOllamaGenerate:
    @patch("app.llm.client.httpx.Client")
    def test_generate_success(self, mock_client_cls, client):
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.post.return_value = _make_response(
            200,
            {"response": "Generated text here", "done": True},
        )

        result = client.generate(
            model="qwen3.5:9b",
            prompt="summarize this",
        )

        assert result == "Generated text here"
        call_kwargs = mock_http.post.call_args
        assert "/api/generate" in call_kwargs[0][0]

    @patch("app.llm.client.httpx.Client")
    def test_generate_connection_error(self, mock_client_cls, client):
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.post.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(OllamaUnavailableError):
            client.generate(model="qwen3.5:9b", prompt="test")

    @patch("app.llm.client.httpx.Client")
    def test_generate_timeout_error(self, mock_client_cls, client):
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.post.side_effect = httpx.TimeoutException("Timed out")

        with pytest.raises(OllamaUnavailableError):
            client.generate(model="qwen3.5:9b", prompt="test")

    @patch("app.llm.client.httpx.Client")
    def test_generate_http_error(self, mock_client_cls, client):
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.post.return_value = _make_response(500, {})

        with pytest.raises(OllamaUnavailableError):
            client.generate(model="qwen3.5:9b", prompt="test")


class TestOllamaCheckAvailable:
    @patch("app.llm.client.httpx.Client")
    def test_check_available_model_present(self, mock_client_cls, client):
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.get.return_value = _make_response(
            200,
            {"models": [{"name": "qwen3.5:9b"}, {"name": "other:latest"}]},
        )

        assert client.check_available() is True

    @patch("app.llm.client.httpx.Client")
    def test_check_available_model_missing(self, mock_client_cls, client):
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.get.return_value = _make_response(
            200,
            {"models": [{"name": "other:latest"}]},
        )

        assert client.check_available() is False

    @patch("app.llm.client.httpx.Client")
    def test_check_available_connection_error(self, mock_client_cls, client):
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.get.side_effect = httpx.ConnectError("Connection refused")

        assert client.check_available() is False

    @patch("app.llm.client.httpx.Client")
    def test_check_available_timeout(self, mock_client_cls, client):
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.get.side_effect = httpx.TimeoutException("Timed out")

        assert client.check_available() is False

    @patch("app.llm.client.httpx.Client")
    def test_check_available_http_error_returns_false(self, mock_client_cls, client):
        mock_http = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.get.return_value = _make_response(500, {})

        assert client.check_available() is False
