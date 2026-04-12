from pathlib import Path

import pytesseract
from loguru import logger
from PIL import Image

from app.exceptions import DocumentProcessingError


class ImageExtractionService:
    def extract_text(self, file_path: Path, document_id: str = "") -> str:
        """Extract text from an image file using Tesseract OCR.

        Returns page-marked text compatible with ChunkingService,
        or empty string if no text is detected.
        """
        try:
            with Image.open(file_path) as image:
                text = pytesseract.image_to_string(image)
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
            return ""

        result = f"--- Page 1 ---\n{text}"
        logger.info(
            "Image OCR completed",
            document_id=document_id,
            chars_extracted=len(text),
            file_path=str(file_path),
        )
        return result
