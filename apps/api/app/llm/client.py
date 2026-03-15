import httpx
from loguru import logger

from app.exceptions import OllamaUnavailableError

# Re-export for convenient importing
__all__ = ["OllamaClient", "OllamaUnavailableError"]

# Timeouts
# connect/write/pool are short — fail fast if Ollama is unreachable.
# read=None — no limit on response body; Ollama can take as long as it needs to generate.
INFERENCE_TIMEOUT = httpx.Timeout(connect=5.0, read=None, write=10.0, pool=5.0)
CHECK_TIMEOUT = 5.0

DEFAULT_MODEL = "qwen3.5:9b"


class OllamaClient:
    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")

    def chat(
        self,
        model: str,
        messages: list[dict],
        format: str | None = None,
        temperature: float = 0,
    ) -> dict:
        """Send a chat completion request to Ollama.

        Returns the full response dict from Ollama's /api/chat endpoint.
        Raises OllamaUnavailableError on connection/timeout errors.
        """
        body: dict = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if format is not None:
            body["format"] = format

        logger.debug("Ollama request | model={} messages={}", model, messages)
        try:
            with httpx.Client(timeout=INFERENCE_TIMEOUT) as http:
                response = http.post(f"{self._base_url}/api/chat", json=body)
                response.raise_for_status()
                data = response.json()
                content = data.get("message", {}).get("content", "")
                logger.debug("Ollama response | {}", content[:500])
                return data
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            logger.error("Ollama unavailable for chat", error=str(exc))
            raise OllamaUnavailableError(
                f"Ollama unavailable for chat: {exc}"
            ) from exc

    def generate(
        self,
        model: str,
        prompt: str,
        format: str | None = None,
        temperature: float = 0,
    ) -> str:
        """Send a generate request to Ollama.

        Returns the generated text string.
        Raises OllamaUnavailableError on connection/timeout errors.
        """
        body: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if format is not None:
            body["format"] = format

        try:
            with httpx.Client(timeout=INFERENCE_TIMEOUT) as http:
                response = http.post(f"{self._base_url}/api/generate", json=body)
                response.raise_for_status()
                return response.json()["response"]
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            logger.error("Ollama unavailable for generate", error=str(exc))
            raise OllamaUnavailableError(
                f"Ollama unavailable for generate: {exc}"
            ) from exc

    def check_available(self, model: str = DEFAULT_MODEL) -> bool:
        """Check if Ollama is running and the specified model is available.

        Returns True if the model is in the list, False otherwise.
        Never raises — returns False on any error.
        """
        try:
            with httpx.Client(timeout=CHECK_TIMEOUT) as http:
                response = http.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                available = model in models
                if not available:
                    logger.warning(
                        "Required model not found in Ollama",
                        required=model,
                        available=models,
                    )
                return available
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            logger.warning("Ollama health check failed", error=str(exc))
            return False
