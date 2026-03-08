from pathlib import Path

import pymupdf


class TextExtractionService:
    def extract_text(self, file_path: Path) -> str:
        """Extract text from a PDF file, returning page-marked content."""
        doc = pymupdf.open(str(file_path))
        try:
            pages = []
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                if text.strip():
                    pages.append(f"--- Page {page_num} ---\n{text}")
            return "\n\n".join(pages)
        finally:
            doc.close()
