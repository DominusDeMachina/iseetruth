"""Tests for ImageExtractionService OCR quality assessment and vision enhancement."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.image_extraction import ImageExtractionService, OCR_QUALITY_THRESHOLD
from app.services.vision import VisionResult


def _make_pil_mock(width=800, height=600):
    """Create a mock PIL Image with given dimensions."""
    mock_img = MagicMock()
    mock_img.width = width
    mock_img.height = height
    mock_img.__enter__ = MagicMock(return_value=mock_img)
    mock_img.__exit__ = MagicMock(return_value=False)
    return mock_img


@pytest.fixture
def service_no_vision():
    """ImageExtractionService without vision enhancement."""
    return ImageExtractionService(ollama_base_url=None)


@pytest.fixture
def service_with_vision():
    """ImageExtractionService with vision enhancement enabled."""
    return ImageExtractionService(ollama_base_url="http://localhost:11434")


class TestAssessOcrQuality:
    def test_empty_text_returns_zero(self, service_no_vision, tmp_path):
        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"fake")
        assert service_no_vision.assess_ocr_quality("", img_path) == 0.0

    def test_whitespace_only_returns_zero(self, service_no_vision, tmp_path):
        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"fake")
        assert service_no_vision.assess_ocr_quality("   \n\t  ", img_path) == 0.0

    def test_good_quality_text_scores_above_threshold(self, service_no_vision, tmp_path):
        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"fake")

        good_text = "This is a well-formatted document with clear text. " * 20

        with patch("app.services.image_extraction.Image") as mock_pil:
            mock_pil.open.return_value = _make_pil_mock(800, 600)
            score = service_no_vision.assess_ocr_quality(good_text, img_path)

        assert score > OCR_QUALITY_THRESHOLD

    def test_short_garbage_scores_below_threshold(self, service_no_vision, tmp_path):
        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"fake")

        # Special chars only: low alnum ratio, short text from large image
        garbage_text = "!@#$%^&*()"

        with patch("app.services.image_extraction.Image") as mock_pil:
            mock_pil.open.return_value = _make_pil_mock(2000, 1500)
            score = service_no_vision.assess_ocr_quality(garbage_text, img_path)

        assert score < OCR_QUALITY_THRESHOLD

    def test_handles_image_open_failure_gracefully(self, service_no_vision, tmp_path):
        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"fake")

        with patch("app.services.image_extraction.Image") as mock_pil:
            mock_pil.open.side_effect = Exception("corrupt")
            score = service_no_vision.assess_ocr_quality("Some text here", img_path)

        # Should still return a score (uses fallback density_score=0.5)
        assert 0.0 <= score <= 1.0


class TestExtractTextWithVision:
    def test_tesseract_good_quality_no_vision_call(self, service_with_vision, tmp_path):
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        good_text = "This is a well-formatted document with clear text content here. " * 10

        with (
            patch("app.services.image_extraction.pytesseract") as mock_tess,
            patch("app.services.image_extraction.Image") as mock_pil,
            patch.object(service_with_vision._vision_service, "check_available") as mock_check,
        ):
            mock_tess.image_to_string.return_value = good_text
            mock_pil.open.return_value = _make_pil_mock(800, 600)

            text, method = service_with_vision.extract_text(img_path, document_id="doc-1")

        assert method == "tesseract"
        assert "--- Page 1 ---" in text
        assert good_text.strip() in text
        # Vision should not be called when quality is good
        mock_check.assert_not_called()

    def test_low_quality_triggers_vision_enhancement(self, service_with_vision, tmp_path):
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        # Short gibberish: low density + low alnum ratio = low quality
        low_quality_text = "!@#$"

        with (
            patch("app.services.image_extraction.pytesseract") as mock_tess,
            patch("app.services.image_extraction.Image") as mock_pil,
            patch.object(
                service_with_vision._vision_service,
                "check_available",
                return_value=True,
            ),
            patch.object(
                service_with_vision._vision_service,
                "analyze_image",
                return_value=VisionResult(description="Handwritten note: Meeting at 3pm"),
            ),
        ):
            mock_tess.image_to_string.return_value = low_quality_text
            mock_pil.open.return_value = _make_pil_mock(2000, 1500)

            text, method = service_with_vision.extract_text(img_path, document_id="doc-1")

        assert method == "tesseract+moondream2"
        assert "[OCR Text]" in text
        assert "[Visual Analysis]" in text
        assert "Handwritten note: Meeting at 3pm" in text

    def test_empty_tesseract_with_vision_uses_vision_only(self, service_with_vision, tmp_path):
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        with (
            patch("app.services.image_extraction.pytesseract") as mock_tess,
            patch("app.services.image_extraction.Image") as mock_pil,
            patch.object(
                service_with_vision._vision_service,
                "check_available",
                return_value=True,
            ),
            patch.object(
                service_with_vision._vision_service,
                "analyze_image",
                return_value=VisionResult(description="A photo of a building"),
            ),
        ):
            mock_tess.image_to_string.return_value = ""
            mock_pil.open.return_value = _make_pil_mock(800, 600)

            text, method = service_with_vision.extract_text(img_path, document_id="doc-1")

        assert method == "moondream2"
        assert "[Visual Analysis]" in text
        assert "[OCR Text]" not in text
        assert "A photo of a building" in text

    def test_fallback_when_moondream2_unavailable(self, service_with_vision, tmp_path):
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        low_quality_text = "!@#$"

        with (
            patch("app.services.image_extraction.pytesseract") as mock_tess,
            patch("app.services.image_extraction.Image") as mock_pil,
            patch.object(
                service_with_vision._vision_service,
                "check_available",
                return_value=False,
            ),
        ):
            mock_tess.image_to_string.return_value = low_quality_text
            mock_pil.open.return_value = _make_pil_mock(2000, 1500)

            text, method = service_with_vision.extract_text(img_path, document_id="doc-1")

        assert method == "tesseract"
        assert "--- Page 1 ---" in text
        assert "[Visual Analysis]" not in text

    def test_fallback_when_vision_returns_none(self, service_with_vision, tmp_path):
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        low_quality_text = "!@#$"

        with (
            patch("app.services.image_extraction.pytesseract") as mock_tess,
            patch("app.services.image_extraction.Image") as mock_pil,
            patch.object(
                service_with_vision._vision_service,
                "check_available",
                return_value=True,
            ),
            patch.object(
                service_with_vision._vision_service,
                "analyze_image",
                return_value=None,
            ),
        ):
            mock_tess.image_to_string.return_value = low_quality_text
            mock_pil.open.return_value = _make_pil_mock(2000, 1500)

            text, method = service_with_vision.extract_text(img_path, document_id="doc-1")

        assert method == "tesseract"

    def test_no_vision_service_skips_enhancement(self, service_no_vision, tmp_path):
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        with (
            patch("app.services.image_extraction.pytesseract") as mock_tess,
            patch("app.services.image_extraction.Image") as mock_pil,
        ):
            mock_tess.image_to_string.return_value = "Some OCR text"
            mock_pil.open.return_value = _make_pil_mock(800, 600)

            text, method = service_no_vision.extract_text(img_path, document_id="doc-1")

        assert method == "tesseract"

    def test_enhance_with_vision_disabled(self, service_with_vision, tmp_path):
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        low_quality_text = "!@#$"

        with (
            patch("app.services.image_extraction.pytesseract") as mock_tess,
            patch("app.services.image_extraction.Image") as mock_pil,
        ):
            mock_tess.image_to_string.return_value = low_quality_text
            mock_pil.open.return_value = _make_pil_mock(2000, 1500)

            text, method = service_with_vision.extract_text(
                img_path, document_id="doc-1", enhance_with_vision=False
            )

        assert method == "tesseract"

    def test_empty_text_both_sources_returns_empty(self, service_with_vision, tmp_path):
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        with (
            patch("app.services.image_extraction.pytesseract") as mock_tess,
            patch("app.services.image_extraction.Image") as mock_pil,
            patch.object(
                service_with_vision._vision_service,
                "check_available",
                return_value=True,
            ),
            patch.object(
                service_with_vision._vision_service,
                "analyze_image",
                return_value=None,
            ),
        ):
            mock_tess.image_to_string.return_value = ""
            mock_pil.open.return_value = _make_pil_mock(800, 600)

            text, method = service_with_vision.extract_text(img_path, document_id="doc-1")

        assert text == ""
        assert method == "tesseract"
