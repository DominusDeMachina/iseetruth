from pathlib import Path

import pytesseract
from loguru import logger
from PIL import Image

from app.exceptions import DocumentProcessingError


class ImageExtractionService:
    def assess_ocr_quality(
        self,
        text: str,
        file_path: Path,
        *,
        image_width: int | None = None,
        image_height: int | None = None,
    ) -> float:
        """Assess OCR output quality and return a confidence score 0.0-1.0.

        Factors:
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
                # If we can't open image for dimensions, use a neutral score
                pixel_area = 1_000_000  # assume 1MP

        chars_per_megapixel = len(text) / (pixel_area / 1_000_000) if pixel_area > 0 else 0
        density_score = min(chars_per_megapixel / 500, 1.0)  # 500 chars/MP is "normal"

        # Factor 2: Alphanumeric ratio (gibberish detection)
        alnum_count = sum(c.isalnum() or c.isspace() for c in text)
        alnum_ratio = alnum_count / len(text) if text else 0
        alnum_score = alnum_ratio  # 0.0-1.0

        # Factor 3: Average word length sanity
        words = text.split()
        if words:
            avg_len = sum(len(w) for w in words) / len(words)
            word_score = 1.0 if 2 <= avg_len <= 15 else 0.3
        else:
            word_score = 0.0

        quality = 0.4 * density_score + 0.4 * alnum_score + 0.2 * word_score

        logger.info(
            "OCR quality assessed",
            document_id=str(file_path.stem),
            density_score=round(density_score, 3),
            alnum_score=round(alnum_score, 3),
            word_score=round(word_score, 3),
            quality=round(quality, 3),
        )

        return quality

    def extract_text(
        self, file_path: Path, document_id: str = ""
    ) -> tuple[str, float]:
        """Extract text from an image file using Tesseract OCR.

        Returns a tuple of (page-marked text, ocr_confidence).
        Empty OCR returns ("", 0.0).
        """
        try:
            with Image.open(file_path) as image:
                text = pytesseract.image_to_string(image)
                img_width = image.width
                img_height = image.height
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

        if not text.strip():
            logger.info(
                "Image OCR completed with no text",
                document_id=document_id,
                chars_extracted=0,
                file_path=str(file_path),
            )
            return ("", 0.0)

        # Assess OCR quality — pass dimensions to avoid re-opening file
        ocr_confidence = self.assess_ocr_quality(
            text, file_path, image_width=img_width, image_height=img_height
        )

        result = f"--- Page 1 ---\n{text}"
        logger.info(
            "Image OCR completed",
            document_id=document_id,
            chars_extracted=len(text),
            ocr_confidence=round(ocr_confidence, 3),
            file_path=str(file_path),
        )
        return (result, ocr_confidence)
