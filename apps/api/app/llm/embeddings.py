import httpx
from loguru import logger

from app.exceptions import OllamaUnavailableError
from app.llm.client import INFERENCE_TIMEOUT

EMBEDDING_MODEL = "qwen3-embedding:8b"


class OllamaEmbeddingClient:
    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")

    def embed(self, text: str) -> list[float]:
        body = {"model": EMBEDDING_MODEL, "input": text}
        try:
            with httpx.Client(timeout=INFERENCE_TIMEOUT) as http:
                response = http.post(f"{self._base_url}/api/embed", json=body)
                response.raise_for_status()
                data = response.json()
                try:
                    vector = data["embeddings"][0]
                except (KeyError, IndexError) as exc:
                    raise OllamaUnavailableError(
                        f"Unexpected Ollama embed response format: {exc}"
                    ) from exc
                logger.debug("Embedding generated", model=EMBEDDING_MODEL, dimension=len(vector))
                return vector
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            logger.error("Ollama unavailable for embedding", error=str(exc))
            raise OllamaUnavailableError(f"Ollama unavailable for embedding: {exc}") from exc
