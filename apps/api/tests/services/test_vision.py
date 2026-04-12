"""Tests for VisionService (moondream2 integration)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.vision import MOONDREAM_MODEL, VisionResult, VisionService


@pytest.fixture
def vision_service():
    return VisionService(base_url="http://localhost:11434")


class TestCheckAvailable:
    def test_returns_true_when_moondream2_in_models(self, vision_service):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "qwen3.5:9b"},
                {"name": "moondream2"},
                {"name": "qwen3-embedding:8b"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            assert vision_service.check_available() is True

    def test_returns_false_when_moondream2_not_in_models(self, vision_service):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "qwen3.5:9b"},
                {"name": "qwen3-embedding:8b"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            assert vision_service.check_available() is False

    def test_returns_false_on_connection_error(self, vision_service):
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = httpx.ConnectError("connection refused")
            mock_client_cls.return_value = mock_client

            assert vision_service.check_available() is False


class TestAnalyzeImage:
    def test_returns_vision_result_on_success(self, vision_service, tmp_path):
        # Create a test image file
        image_path = tmp_path / "test.jpg"
        image_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "The image shows handwritten text saying 'Hello World'."}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            result = vision_service.analyze_image(image_path, document_id="doc-1")

        assert result is not None
        assert isinstance(result, VisionResult)
        assert "Hello World" in result.description
        assert result.source == "moondream2"

    def test_sends_base64_encoded_image(self, vision_service, tmp_path):
        image_path = tmp_path / "test.jpg"
        image_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 50)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "Some description"}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            vision_service.analyze_image(image_path, document_id="doc-1")

            # Verify the request body contains the correct model and images
            call_args = mock_client.post.call_args
            body = call_args[1]["json"]
            assert body["model"] == MOONDREAM_MODEL
            assert len(body["messages"]) == 1
            assert "images" in body["messages"][0]
            assert len(body["messages"][0]["images"]) == 1
            # Verify it's a valid base64 string
            import base64
            base64.b64decode(body["messages"][0]["images"][0])

    def test_returns_none_on_connection_error(self, vision_service, tmp_path):
        image_path = tmp_path / "test.jpg"
        image_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.ConnectError("connection refused")
            mock_client_cls.return_value = mock_client

            result = vision_service.analyze_image(image_path, document_id="doc-1")

        assert result is None

    def test_returns_none_on_timeout(self, vision_service, tmp_path):
        image_path = tmp_path / "test.jpg"
        image_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.TimeoutException("timeout")
            mock_client_cls.return_value = mock_client

            result = vision_service.analyze_image(image_path, document_id="doc-1")

        assert result is None

    def test_returns_none_for_oversized_image(self, vision_service, tmp_path):
        image_path = tmp_path / "huge.tiff"
        # Create a file larger than MAX_IMAGE_SIZE_BYTES (20MB)
        image_path.write_bytes(b"\x00" * (21 * 1024 * 1024))

        # Should return None without making any HTTP call
        result = vision_service.analyze_image(image_path, document_id="doc-1")
        assert result is None

    def test_returns_none_on_empty_description(self, vision_service, tmp_path):
        image_path = tmp_path / "test.jpg"
        image_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        mock_response = MagicMock()
        mock_response.json.return_value = {"message": {"content": "  "}}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            result = vision_service.analyze_image(image_path, document_id="doc-1")

        assert result is None
