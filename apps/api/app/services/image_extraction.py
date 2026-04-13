import os
from pathlib import Path

import pytesseract
from loguru import logger
from PIL import Image

from app.exceptions import DocumentProcessingError
from app.services.vision import VisionResult, VisionService

# Configurable threshold: below this score, moondream2 is triggered for enhancement.
OCR_QUALITY_THRESHOLD = float(os.environ.get("OCR_QUALITY_THRESHOLD", "0.3"))


class ImageExtractionService:
    def __init__(self, ollama_base_url: str | None = None):
        """Initialize with optional Ollama URL for vision enhancement.

        If ollama_base_url is None, vision enhancement is disabled.
        """
        self._vision_service: VisionService | None = None
        if ollama_base_url:
            self._vision_service = VisionService(ollama_base_url)

    def assess_ocr_quality(
        self,
        text: str,
        file_path: Path,
        *,
        image_width: int | None = None,
        image_height: int | None = None,
    ) -> float:
        """Assess Tesseract OCR output quality. Returns 0.0-1.0.

        Heuristics:
        - Text density relative to image pixel area
        - Alphanumeric character ratio (gibberish detection)
        - Average word length sanity check

        Pass image_width/image_height to avoid re-opening the file.
        """
        if not text.strip():
            return 0.0

        # Factor 1: Text density relative to image size
        if image_width is not None and image_height is not None:
            pixel_area = image_width * image_height
        else:
            try:
                with Image.open(file_path) as img:
                    pixel_area = img.width * img.height
            except Exception:
                pixel_area = 1_000_000  # Default to 1MP if image can't be opened
        chars_per_megapixel = len(text) / (pixel_area / 1_000_000) if pixel_area > 0 else 0
        density_score = min(chars_per_megapixel / 500, 1.0)

        # Factor 2: Alphanumeric ratio (gibberish detection)
        alnum_count = sum(c.isalnum() or c.isspace() for c in text)
        alnum_ratio = alnum_count / len(text) if text else 0
        alnum_score = alnum_ratio

        # Factor 3: Average word length sanity
        words = text.split()
        if words:
            avg_len = sum(len(w) for w in words) / len(words)
            word_score = 1.0 if 2 <= avg_len <= 15 else 0.3
        else:
            word_score = 0.0

        return 0.4 * density_score + 0.4 * alnum_score + 0.2 * word_score

    def extract_text(
        self,
        file_path: Path,
        document_id: str = "",
        enhance_with_vision: bool = True,
    ) -> tuple[str, str, float]:
        """Extract text from an image file using Tesseract OCR.

        When vision enhancement is enabled and OCR quality is low,
        moondream2 is used to supplement or replace the Tesseract output.

        Returns (page_marked_text, ocr_method, ocr_confidence) where:
        - ocr_method is one of: "tesseract", "tesseract+moondream2", "moondream2"
        - ocr_confidence is the Tesseract quality score (0.0-1.0)
        Returns ("", "tesseract", 0.0) if no text is detected.
        """
        # Step 1: Run Tesseract OCR (open once, keep dimensions for quality scoring)
        try:
            with Image.open(file_path) as image:
                image_width, image_height = image.width, image.height
                tesseract_text = pytesseract.image_to_string(image)
        except pytesseract.TesseractNotFoundError as exc:
            logger.error(
                "Tesseract not installed or not found",
                document_id=document_id,
                error=str(exc),
            )
            raise DocumentProcessingError(document_id, "Tesseract OCR is not installed") from exc
        except pytesseract.TesseractError as exc:
            logger.error(
                "Tesseract OCR failed",
                document_id=document_id,
                error=str(exc),
            )
            raise DocumentProcessingError(document_id, f"Tesseract OCR error: {exc}") from exc

        # Step 2: Assess OCR quality (pass dimensions to avoid re-opening)
        quality_score = self.assess_ocr_quality(
            tesseract_text,
            file_path,
            image_width=image_width,
            image_height=image_height,
        )
        use_vision = (
            enhance_with_vision
            and self._vision_service is not None
            and quality_score < OCR_QUALITY_THRESHOLD
        )

        logger.info(
            "OCR quality assessed",
            document_id=document_id,
            quality_score=round(quality_score, 3),
            threshold=OCR_QUALITY_THRESHOLD,
            using_vision=use_vision,
            chars_extracted=len(tesseract_text.strip()),
        )

        # Step 3: Try moondream2 if quality is low
        vision_result: VisionResult | None = None
        if use_vision:
            if self._vision_service.check_available():
                vision_result = self._vision_service.analyze_image(
                    file_path, document_id=document_id
                )
            else:
                logger.warning(
                    "moondream2 unavailable, using Tesseract-only",
                    document_id=document_id,
                )

        # Step 4: Combine results
        text, ocr_method = self._combine_results(
            tesseract_text, vision_result, document_id, file_path
        )
        return text, ocr_method, quality_score

    def _combine_results(
        self,
        tesseract_text: str,
        vision_result: VisionResult | None,
        document_id: str,
        file_path: Path | None = None,
    ) -> tuple[str, str]:
        """Combine Tesseract and moondream2 outputs into page-marked text.

        Returns (page_marked_text, ocr_method).
        """
        has_tesseract = bool(tesseract_text.strip())
        has_vision = vision_result is not None

        if has_tesseract and has_vision:
            # Both sources available — combine with headers
            combined = f"[OCR Text]\n{tesseract_text.strip()}\n\n[Visual Analysis]\n{vision_result.description}"
            ocr_method = "tesseract+moondream2"

            logger.info(
                "Image processed with vision enhancement",
                document_id=document_id,
                ocr_chars=len(tesseract_text.strip()),
                vision_chars=len(vision_result.description),
                total_chars=len(combined),
            )

        elif has_vision:
            # Only vision (Tesseract returned empty/garbage)
            combined = f"[Visual Analysis]\n{vision_result.description}"
            ocr_method = "moondream2"

            logger.info(
                "Image processed with vision only (Tesseract empty)",
                document_id=document_id,
                vision_chars=len(vision_result.description),
            )

        elif has_tesseract:
            # Only Tesseract (no vision or vision failed)
            combined = tesseract_text.strip()
            ocr_method = "tesseract"

            logger.info(
                "Image OCR completed",
                document_id=document_id,
                chars_extracted=len(combined),
            )

        else:
            # Nothing extracted
            logger.info(
                "Image OCR completed with no text",
                document_id=document_id,
                chars_extracted=0,
                file_path=str(file_path) if file_path else "",
            )
            return "", "tesseract"

        result = f"--- Page 1 ---\n{combined}"
        return result, ocr_method
