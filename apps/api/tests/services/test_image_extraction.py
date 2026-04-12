"""Tests for ImageExtractionService — OCR quality assessment and text extraction."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestAssessOcrQuality:
    """Test the OCR quality assessment heuristics."""

    def _make_service(self):
        from app.services.image_extraction import ImageExtractionService

        return ImageExtractionService()

    def test_empty_text_returns_zero(self):
        """Empty/whitespace-only text should return 0.0 quality."""
        service = self._make_service()
        with patch("app.services.image_extraction.Image") as mock_pil:
            mock_img = MagicMock()
            mock_img.width = 1000
            mock_img.height = 1000
            mock_img.__enter__ = MagicMock(return_value=mock_img)
            mock_img.__exit__ = MagicMock(return_value=False)
            mock_pil.open.return_value = mock_img

            assert service.assess_ocr_quality("", Path("/fake.jpg")) == 0.0
            assert service.assess_ocr_quality("   \n  ", Path("/fake.jpg")) == 0.0

    def test_good_quality_text_returns_high_score(self):
        """Well-formed text from a normal-sized image should score high."""
        service = self._make_service()
        # 1000x1000 = 1 megapixel, 500 chars = density_score 1.0
        # Good alphanumeric ratio, normal word lengths
        good_text = "The quick brown fox jumps over the lazy dog. " * 12  # ~540 chars
        with patch("app.services.image_extraction.Image") as mock_pil:
            mock_img = MagicMock()
            mock_img.width = 1000
            mock_img.height = 1000
            mock_img.__enter__ = MagicMock(return_value=mock_img)
            mock_img.__exit__ = MagicMock(return_value=False)
            mock_pil.open.return_value = mock_img

            score = service.assess_ocr_quality(good_text, Path("/fake.jpg"))
            assert score >= 0.7, f"Good text should score >= 0.7, got {score}"

    def test_gibberish_text_returns_low_score(self):
        """Gibberish/symbolic text should score low."""
        service = self._make_service()
        gibberish = "!@#$%^&*()_+{}[]|\\:\";<>?,./~`" * 3  # mostly non-alnum
        with patch("app.services.image_extraction.Image") as mock_pil:
            mock_img = MagicMock()
            mock_img.width = 2000
            mock_img.height = 2000  # 4 megapixels, very low density
            mock_img.__enter__ = MagicMock(return_value=mock_img)
            mock_img.__exit__ = MagicMock(return_value=False)
            mock_pil.open.return_value = mock_img

            score = service.assess_ocr_quality(gibberish, Path("/fake.jpg"))
            assert score < 0.4, f"Gibberish text should score < 0.4, got {score}"

    def test_short_text_from_large_image_has_low_density_factor(self):
        """Very short text from a large image = low text density factor contributes to lower overall score."""
        service = self._make_service()
        short_text = "Hi"
        with patch("app.services.image_extraction.Image") as mock_pil:
            mock_img = MagicMock()
            mock_img.width = 4000
            mock_img.height = 4000  # 16 megapixels
            mock_img.__enter__ = MagicMock(return_value=mock_img)
            mock_img.__exit__ = MagicMock(return_value=False)
            mock_pil.open.return_value = mock_img

            score = service.assess_ocr_quality(short_text, Path("/fake.jpg"))
            # Even though alnum ratio is high, the density is very low (~0.0)
            # So overall score should be lower than good text
            assert score < 0.7, f"Short text from large image should not score 'high', got {score}"

    def test_score_is_between_zero_and_one(self):
        """Quality score should always be in [0.0, 1.0] range."""
        service = self._make_service()
        text = "Normal text with several words that make sense in English."
        with patch("app.services.image_extraction.Image") as mock_pil:
            mock_img = MagicMock()
            mock_img.width = 800
            mock_img.height = 600
            mock_img.__enter__ = MagicMock(return_value=mock_img)
            mock_img.__exit__ = MagicMock(return_value=False)
            mock_pil.open.return_value = mock_img

            score = service.assess_ocr_quality(text, Path("/fake.jpg"))
            assert 0.0 <= score <= 1.0

    def test_image_open_failure_uses_neutral_score(self):
        """If Image.open fails, should still return a score (not crash)."""
        service = self._make_service()
        text = "Some OCR text extracted successfully"
        with patch("app.services.image_extraction.Image") as mock_pil:
            mock_pil.open.side_effect = Exception("File not found")

            score = service.assess_ocr_quality(text, Path("/nonexistent.jpg"))
            assert 0.0 <= score <= 1.0


class TestExtractText:
    """Test the extract_text method returns (text, confidence) tuple."""

    def _make_service(self):
        from app.services.image_extraction import ImageExtractionService

        return ImageExtractionService()

    def test_returns_tuple_with_text_and_confidence(self):
        """extract_text should return a (text, confidence) tuple."""
        with patch("app.services.image_extraction.Image") as mock_pil, \
             patch("app.services.image_extraction.pytesseract") as mock_tess:
            mock_img = MagicMock()
            mock_img.width = 1000
            mock_img.height = 1000
            mock_img.__enter__ = MagicMock(return_value=mock_img)
            mock_img.__exit__ = MagicMock(return_value=False)
            mock_pil.open.return_value = mock_img
            mock_tess.image_to_string.return_value = "Hello World from OCR"

            service = self._make_service()
            result = service.extract_text(Path("/fake/image.jpg"), document_id="test-id")

            assert isinstance(result, tuple)
            assert len(result) == 2
            text, confidence = result
            assert isinstance(text, str)
            assert isinstance(confidence, float)
            assert text.startswith("--- Page 1 ---\n")
            assert 0.0 <= confidence <= 1.0

    def test_empty_ocr_returns_empty_with_zero_confidence(self):
        """Empty OCR output returns ('', 0.0)."""
        with patch("app.services.image_extraction.Image") as mock_pil, \
             patch("app.services.image_extraction.pytesseract") as mock_tess:
            mock_img = MagicMock()
            mock_img.__enter__ = MagicMock(return_value=mock_img)
            mock_img.__exit__ = MagicMock(return_value=False)
            mock_pil.open.return_value = mock_img
            mock_tess.image_to_string.return_value = "   \n  "

            service = self._make_service()
            text, confidence = service.extract_text(Path("/fake/blank.png"), document_id="test-id")

            assert text == ""
            assert confidence == 0.0

    def test_good_text_has_high_confidence(self):
        """Well-extracted text from reasonable image dimensions should have high confidence."""
        with patch("app.services.image_extraction.Image") as mock_pil, \
             patch("app.services.image_extraction.pytesseract") as mock_tess:
            mock_img = MagicMock()
            mock_img.width = 1000
            mock_img.height = 1000
            mock_img.__enter__ = MagicMock(return_value=mock_img)
            mock_img.__exit__ = MagicMock(return_value=False)
            mock_pil.open.return_value = mock_img
            # 500+ chars of clean text for a 1MP image = high density
            mock_tess.image_to_string.return_value = "The quick brown fox jumps over the lazy dog. " * 12

            service = self._make_service()
            text, confidence = service.extract_text(Path("/fake/clear.jpg"), document_id="test-id")

            assert text != ""
            assert confidence >= 0.7


class TestOcrQualityComputedField:
    """Test the ocr_quality computed field on DocumentResponse schema."""

    def test_high_quality(self):
        from app.schemas.document import DocumentResponse
        from datetime import datetime

        resp = DocumentResponse(
            id="00000000-0000-0000-0000-000000000000",
            investigation_id="00000000-0000-0000-0000-000000000001",
            filename="test.jpg",
            size_bytes=1000,
            sha256_checksum="a" * 64,
            status="complete",
            page_count=1,
            ocr_confidence=0.85,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert resp.ocr_quality == "high"

    def test_medium_quality(self):
        from app.schemas.document import DocumentResponse
        from datetime import datetime

        resp = DocumentResponse(
            id="00000000-0000-0000-0000-000000000000",
            investigation_id="00000000-0000-0000-0000-000000000001",
            filename="test.jpg",
            size_bytes=1000,
            sha256_checksum="a" * 64,
            status="complete",
            page_count=1,
            ocr_confidence=0.5,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert resp.ocr_quality == "medium"

    def test_low_quality(self):
        from app.schemas.document import DocumentResponse
        from datetime import datetime

        resp = DocumentResponse(
            id="00000000-0000-0000-0000-000000000000",
            investigation_id="00000000-0000-0000-0000-000000000001",
            filename="test.jpg",
            size_bytes=1000,
            sha256_checksum="a" * 64,
            status="complete",
            page_count=1,
            ocr_confidence=0.2,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert resp.ocr_quality == "low"

    def test_none_quality(self):
        from app.schemas.document import DocumentResponse
        from datetime import datetime

        resp = DocumentResponse(
            id="00000000-0000-0000-0000-000000000000",
            investigation_id="00000000-0000-0000-0000-000000000001",
            filename="test.pdf",
            size_bytes=1000,
            sha256_checksum="a" * 64,
            status="complete",
            page_count=1,
            ocr_confidence=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert resp.ocr_quality is None

    def test_boundary_at_0_7(self):
        from app.schemas.document import DocumentResponse
        from datetime import datetime

        resp = DocumentResponse(
            id="00000000-0000-0000-0000-000000000000",
            investigation_id="00000000-0000-0000-0000-000000000001",
            filename="test.jpg",
            size_bytes=1000,
            sha256_checksum="a" * 64,
            status="complete",
            page_count=1,
            ocr_confidence=0.7,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert resp.ocr_quality == "high"

    def test_boundary_at_0_4(self):
        from app.schemas.document import DocumentResponse
        from datetime import datetime

        resp = DocumentResponse(
            id="00000000-0000-0000-0000-000000000000",
            investigation_id="00000000-0000-0000-0000-000000000001",
            filename="test.jpg",
            size_bytes=1000,
            sha256_checksum="a" * 64,
            status="complete",
            page_count=1,
            ocr_confidence=0.4,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert resp.ocr_quality == "medium"
