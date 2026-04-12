"""Vision service for moondream2 enhanced image understanding via Ollama."""

import base64
from dataclasses import dataclass
from pathlib import Path

import httpx
from loguru import logger

# Reuse the same timeout pattern as OllamaClient:
# connect/write/pool are short — fail fast if Ollama is unreachable.
# read=None — no limit; moondream2 can take time to process images.
VISION_TIMEOUT = httpx.Timeout(connect=5.0, read=None, write=10.0, pool=5.0)
CHECK_TIMEOUT = 5.0

MOONDREAM_MODEL = "moondream2"

# Maximum image file size for vision analysis (20MB).
# Larger images would consume excessive memory when base64-encoded.
MAX_IMAGE_SIZE_BYTES = 20 * 1024 * 1024

DEFAULT_PROMPT = (
    "Describe all text and content visible in this image in detail. "
    "If there is handwritten text, transcribe it. "
    "If there are diagrams, charts, or tables, describe their structure and content."
)


@dataclass
class VisionResult:
    """Result from moondream2 visual analysis."""

    description: str
    source: str = "moondream2"


class VisionService:
    """Calls moondream2 via Ollama for visual image understanding.

    Designed for graceful degradation: all methods return None on failure
    rather than raising exceptions.
    """

    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")

    def check_available(self) -> bool:
        """Check if moondream2 is loaded in Ollama.

        Returns True if the model is in the list, False otherwise.
        Never raises.
        """
        try:
            with httpx.Client(timeout=CHECK_TIMEOUT) as http:
                response = http.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                available = MOONDREAM_MODEL in models
                if not available:
                    logger.debug(
                        "moondream2 not found in Ollama",
                        available_models=models,
                    )
                return available
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            logger.warning("Ollama check failed for moondream2", error=str(exc))
            return False

    def analyze_image(
        self,
        file_path: Path,
        prompt: str = DEFAULT_PROMPT,
        document_id: str = "",
    ) -> VisionResult | None:
        """Analyze an image using moondream2 via Ollama multimodal API.

        Returns VisionResult on success, None on any failure.
        Never raises — moondream2 failure is non-fatal.
        """
        try:
            file_size = file_path.stat().st_size
            if file_size > MAX_IMAGE_SIZE_BYTES:
                logger.warning(
                    "Image too large for vision analysis, skipping",
                    document_id=document_id,
                    file_size_mb=round(file_size / (1024 * 1024), 1),
                    max_mb=MAX_IMAGE_SIZE_BYTES // (1024 * 1024),
                )
                return None

            image_bytes = file_path.read_bytes()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            body = {
                "model": MOONDREAM_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [image_b64],
                    }
                ],
                "stream": False,
                "options": {"temperature": 0},
            }

            with httpx.Client(timeout=VISION_TIMEOUT) as http:
                response = http.post(f"{self._base_url}/api/chat", json=body)
                response.raise_for_status()
                data = response.json()

            description = data.get("message", {}).get("content", "")

            if not description.strip():
                logger.info(
                    "moondream2 returned empty description",
                    document_id=document_id,
                    file_path=str(file_path),
                )
                return None

            logger.info(
                "moondream2 analysis complete",
                document_id=document_id,
                description_chars=len(description),
                file_path=str(file_path),
            )

            return VisionResult(description=description.strip())

        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            logger.warning(
                "moondream2 unavailable, skipping vision enhancement",
                document_id=document_id,
                error=str(exc),
            )
            return None
        except Exception as exc:
            logger.warning(
                "moondream2 analysis failed unexpectedly",
                document_id=document_id,
                error=str(exc),
            )
            return None
