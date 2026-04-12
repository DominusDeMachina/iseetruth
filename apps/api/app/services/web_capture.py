import hashlib
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.exceptions import WebCaptureError
from app.models.document import Document

STORAGE_ROOT = Path(os.environ.get("STORAGE_ROOT", "storage"))
WEB_CAPTURE_TIMEOUT = 30  # seconds (NFR32)
MAX_CONTENT_SIZE = 50 * 1024 * 1024  # 50 MB — reasonable limit for web pages
USER_AGENT = "OSINT-WebCapture/1.0"

# Tags to remove before text extraction
STRIP_TAGS = {"script", "style", "nav", "header", "footer", "noscript", "svg", "iframe"}


def _extract_text_from_html(html_content: str) -> tuple[str, str]:
    """Extract clean text and page title from HTML.

    Returns (extracted_text, page_title).
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Extract title before stripping tags
    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else ""

    # Remove unwanted tags
    for tag in soup.find_all(STRIP_TAGS):
        tag.decompose()

    # Get clean text
    text = soup.get_text(separator="\n", strip=True)
    return text, page_title


def fetch_and_store(
    document_id: str,
    investigation_id: str,
    url: str,
    session,
) -> None:
    """Fetch URL, store HTML, convert to text, update document record.

    Called from Celery worker (synchronous context).
    """
    document = session.get(Document, document_id)
    if document is None:
        logger.error("Document not found for web capture", document_id=document_id)
        return

    try:
        # Fetch HTML
        with httpx.Client(
            timeout=WEB_CAPTURE_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            response = client.get(url)
            response.raise_for_status()

        html_bytes = response.content
        if len(html_bytes) > MAX_CONTENT_SIZE:
            size_mb = len(html_bytes) / (1024 * 1024)
            raise WebCaptureError(
                url, f"page too large ({size_mb:.1f} MB, limit {MAX_CONTENT_SIZE // (1024 * 1024)} MB)"
            )
        html_content = response.text

        # Store raw HTML immutably
        file_path = STORAGE_ROOT / investigation_id / f"{document_id}.html"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        sha256 = hashlib.sha256()
        with open(file_path, "wb") as f:
            f.write(html_bytes)
            sha256.update(html_bytes)

        checksum = sha256.hexdigest()

        # Convert HTML to text and extract title
        extracted_text, page_title = _extract_text_from_html(html_content)

        # Use page title as filename, fall back to URL hostname
        if not page_title:
            parsed = urlparse(url)
            page_title = parsed.hostname or "Untitled Web Page"

        # Format text with page marker for chunking service compatibility
        formatted_text = f"--- Page 1 ---\n{extracted_text}" if extracted_text else ""

        # Update document record
        document.filename = page_title
        document.size_bytes = len(html_bytes)
        document.sha256_checksum = checksum
        document.extracted_text = formatted_text
        document.page_count = 1
        session.commit()

        logger.info(
            "Web page captured",
            document_id=document_id,
            url=url,
            title=page_title,
            text_length=len(extracted_text),
        )

    except httpx.TimeoutException:
        # Don't set failure state here — let process_document_task's outer handler
        # do it consistently (sets status, publishes SSE event, commits).
        raise WebCaptureError(url, f"request timed out after {WEB_CAPTURE_TIMEOUT}s")

    except httpx.HTTPStatusError as exc:
        raise WebCaptureError(url, f"HTTP {exc.response.status_code}")

    except httpx.HTTPError as exc:
        raise WebCaptureError(url, str(exc))
