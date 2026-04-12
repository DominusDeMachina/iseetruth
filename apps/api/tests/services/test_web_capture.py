"""Tests for web capture service (Story 9.1)."""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.web_capture import _extract_text_from_html, fetch_and_store


class TestExtractTextFromHtml:
    """Unit tests for HTML-to-text conversion."""

    def test_extracts_body_text(self):
        html = "<html><body><p>Hello world</p></body></html>"
        text, title = _extract_text_from_html(html)
        assert "Hello world" in text

    def test_extracts_title(self):
        html = "<html><head><title>My Page</title></head><body>Content</body></html>"
        text, title = _extract_text_from_html(html)
        assert title == "My Page"

    def test_empty_title_returns_empty_string(self):
        html = "<html><body>Content</body></html>"
        text, title = _extract_text_from_html(html)
        assert title == ""

    def test_strips_script_tags(self):
        html = "<html><body><script>alert('xss')</script><p>Safe</p></body></html>"
        text, title = _extract_text_from_html(html)
        assert "alert" not in text
        assert "Safe" in text

    def test_strips_style_tags(self):
        html = "<html><body><style>body { color: red }</style><p>Visible</p></body></html>"
        text, title = _extract_text_from_html(html)
        assert "color" not in text
        assert "Visible" in text

    def test_strips_nav_tags(self):
        html = "<html><body><nav>Menu items</nav><article>Content</article></body></html>"
        text, title = _extract_text_from_html(html)
        assert "Menu" not in text
        assert "Content" in text

    def test_strips_header_and_footer(self):
        html = "<html><body><header>Site header</header><main>Main content</main><footer>Footer</footer></body></html>"
        text, title = _extract_text_from_html(html)
        assert "Site header" not in text
        assert "Footer" not in text
        assert "Main content" in text

    def test_preserves_article_structure(self):
        html = """<html><body>
        <article>
            <h1>Title</h1>
            <p>Paragraph one.</p>
            <p>Paragraph two.</p>
        </article>
        </body></html>"""
        text, title = _extract_text_from_html(html)
        assert "Title" in text
        assert "Paragraph one." in text
        assert "Paragraph two." in text


class TestFetchAndStore:
    """Tests for the fetch_and_store function."""

    def _make_document(self):
        doc = MagicMock()
        doc.source_url = "https://example.com/article"
        doc.status = "queued"
        doc.filename = "example.com"
        doc.size_bytes = 0
        doc.sha256_checksum = ""
        doc.extracted_text = None
        doc.page_count = None
        doc.error_message = None
        doc.failed_stage = None
        return doc

    @patch("app.services.web_capture.STORAGE_ROOT", Path("/tmp/test_storage"))
    def test_successful_fetch_updates_document(self, tmp_path):
        doc = self._make_document()
        session = MagicMock()
        session.get.return_value = doc

        html = b"<html><head><title>Test Page</title></head><body><p>Content</p></body></html>"
        mock_response = MagicMock()
        mock_response.text = html.decode()
        mock_response.content = html
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.web_capture.STORAGE_ROOT", tmp_path), \
             patch("app.services.web_capture.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            fetch_and_store("doc-123", "inv-456", "https://example.com/article", session)

        assert doc.filename == "Test Page"
        assert doc.size_bytes == len(html)
        assert doc.sha256_checksum == hashlib.sha256(html).hexdigest()
        assert doc.page_count == 1
        assert "--- Page 1 ---" in doc.extracted_text
        assert "Content" in doc.extracted_text
        session.commit.assert_called()

    @patch("app.services.web_capture.STORAGE_ROOT", Path("/tmp/test_storage"))
    def test_timeout_raises_web_capture_error(self, tmp_path):
        """Timeout raises WebCaptureError — caller handles failure state."""
        from app.exceptions import WebCaptureError

        doc = self._make_document()
        session = MagicMock()
        session.get.return_value = doc

        with patch("app.services.web_capture.STORAGE_ROOT", tmp_path), \
             patch("app.services.web_capture.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = httpx.TimeoutException("timed out")
            mock_client_cls.return_value = mock_client

            with pytest.raises(WebCaptureError, match="timed out"):
                fetch_and_store("doc-123", "inv-456", "https://example.com", session)

    @patch("app.services.web_capture.STORAGE_ROOT", Path("/tmp/test_storage"))
    def test_http_error_raises_web_capture_error(self, tmp_path):
        """HTTP errors raise WebCaptureError — caller handles failure state."""
        from app.exceptions import WebCaptureError

        doc = self._make_document()
        session = MagicMock()
        session.get.return_value = doc

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("app.services.web_capture.STORAGE_ROOT", tmp_path), \
             patch("app.services.web_capture.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_response
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404", request=MagicMock(), response=mock_response
            )
            mock_client_cls.return_value = mock_client

            with pytest.raises(WebCaptureError, match="HTTP 404"):
                fetch_and_store("doc-123", "inv-456", "https://example.com", session)

    def test_document_not_found_returns_early(self):
        session = MagicMock()
        session.get.return_value = None

        # Should not raise
        fetch_and_store("nonexistent", "inv-456", "https://example.com", session)

    @patch("app.services.web_capture.STORAGE_ROOT", Path("/tmp/test_storage"))
    def test_stores_html_file(self, tmp_path):
        doc = self._make_document()
        session = MagicMock()
        session.get.return_value = doc

        html = b"<html><body>Test</body></html>"
        mock_response = MagicMock()
        mock_response.text = html.decode()
        mock_response.content = html
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.web_capture.STORAGE_ROOT", tmp_path), \
             patch("app.services.web_capture.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            fetch_and_store("doc-123", "inv-456", "https://example.com", session)

        # Verify HTML file was stored
        html_file = tmp_path / "inv-456" / "doc-123.html"
        assert html_file.exists()
        assert html_file.read_bytes() == html

    @patch("app.services.web_capture.STORAGE_ROOT", Path("/tmp/test_storage"))
    def test_fallback_filename_to_hostname(self, tmp_path):
        doc = self._make_document()
        session = MagicMock()
        session.get.return_value = doc

        # HTML with no title tag
        html = b"<html><body>No title here</body></html>"
        mock_response = MagicMock()
        mock_response.text = html.decode()
        mock_response.content = html
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.web_capture.STORAGE_ROOT", tmp_path), \
             patch("app.services.web_capture.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value = mock_client

            fetch_and_store("doc-123", "inv-456", "https://example.com/page", session)

        assert doc.filename == "example.com"
