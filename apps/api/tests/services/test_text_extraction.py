"""Tests for TextExtractionService."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.text_extraction import TextExtractionService


class TestExtractText:
    def test_extracts_text_from_valid_pdf(self, tmp_path):
        """Extract text returns joined page content with page markers."""
        mock_page1 = MagicMock()
        mock_page1.get_text.return_value = "Page one content"

        mock_page2 = MagicMock()
        mock_page2.get_text.return_value = "Page two content"

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page1, mock_page2]))
        mock_doc.__len__ = MagicMock(return_value=2)

        pdf_path = tmp_path / "test.pdf"
        pdf_path.touch()

        with patch("app.services.text_extraction.pymupdf") as mock_pymupdf:
            mock_pymupdf.open.return_value = mock_doc
            service = TextExtractionService()
            result = service.extract_text(pdf_path)

        assert "--- Page 1 ---" in result
        assert "Page one content" in result
        assert "--- Page 2 ---" in result
        assert "Page two content" in result
        mock_doc.close.assert_called_once()

    def test_skips_empty_pages(self, tmp_path):
        """Pages with only whitespace should be skipped."""
        mock_page1 = MagicMock()
        mock_page1.get_text.return_value = "Content here"

        mock_page2 = MagicMock()
        mock_page2.get_text.return_value = "   \n  "

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page1, mock_page2]))

        pdf_path = tmp_path / "test.pdf"
        pdf_path.touch()

        with patch("app.services.text_extraction.pymupdf") as mock_pymupdf:
            mock_pymupdf.open.return_value = mock_doc
            service = TextExtractionService()
            result = service.extract_text(pdf_path)

        assert "--- Page 1 ---" in result
        assert "--- Page 2 ---" not in result
        mock_doc.close.assert_called_once()

    def test_raises_on_corrupted_pdf(self, tmp_path):
        """Corrupted PDF should raise an exception."""
        pdf_path = tmp_path / "corrupt.pdf"
        pdf_path.write_bytes(b"not a real pdf")

        with patch("app.services.text_extraction.pymupdf") as mock_pymupdf:
            mock_pymupdf.open.side_effect = RuntimeError("cannot open broken doc")
            service = TextExtractionService()
            with pytest.raises(RuntimeError, match="cannot open broken doc"):
                service.extract_text(pdf_path)
