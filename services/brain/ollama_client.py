from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

import httpx

from shared.config import settings

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    pass


class OllamaConnectionError(OllamaError):
    pass


class OllamaGenerationError(OllamaError):
    pass


class OllamaEmbeddingError(OllamaError):
    pass


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        chat_model: str | None = None,
        embed_model: str | None = None,
        timeout: int | None = None,
    ):
        self.base_url = base_url or settings.ollama.base_url
        self.chat_model = chat_model or settings.ollama.model_chat
        self.embed_model = embed_model or settings.ollama.model_embed
        self.timeout = timeout or settings.ollama.timeout
        self.expected_dim = settings.ollama.embedding_dim
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in Ollama health check: {e}", exc_info=True)
            return False

    async def list_models(self) -> list[dict[str, Any]]:
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            response.raise_for_status()
            return response.json().get("models", [])
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        context: list[int] | None = None,
    ) -> str:
        model = model or self.chat_model

        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }

        if system:
            payload["system"] = system

        options = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if options:
            payload["options"] = options

        if context:
            payload["context"] = context

        try:
            client = await self._get_client()
            logger.debug(f"Generating with model={model}, prompt_len={len(prompt)}")

            response = await client.post("/api/generate", json=payload)
            response.raise_for_status()

            text = response.json().get("response", "")
            logger.debug(f"Generated text_len={len(text)}")
            return text

        except httpx.ConnectError as e:
            raise OllamaConnectionError(f"Cannot connect to Ollama at {self.base_url}: {e}")
        except httpx.HTTPStatusError as e:
            raise OllamaGenerationError(f"Ollama API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise OllamaGenerationError(f"Generation failed: {e}")

    async def generate_stream(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream tokens from Ollama. Yields each token as it arrives."""
        model = model or self.chat_model

        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": True,
        }

        if system:
            payload["system"] = system

        options = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if options:
            payload["options"] = options

        try:
            client = await self._get_client()
            async with client.stream("POST", "/api/generate", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = data.get("response", "")
                    if token:
                        yield token
                    if data.get("done"):
                        break
        except httpx.ConnectError as e:
            raise OllamaConnectionError(f"Cannot connect to Ollama at {self.base_url}: {e}")
        except httpx.HTTPStatusError as e:
            raise OllamaGenerationError(f"Ollama API error: {e.response.status_code}")
        except Exception as e:
            raise OllamaGenerationError(f"Stream generation failed: {e}")

    async def embed(self, text: str, model: str | None = None) -> list[float]:
        model = model or self.embed_model

        payload = {"model": model, "prompt": text}

        try:
            client = await self._get_client()
            response = await client.post("/api/embeddings", json=payload)
            response.raise_for_status()

            embedding = response.json().get("embedding", [])

            if not embedding:
                raise OllamaEmbeddingError(f"Empty embedding for text (len={len(text)})")

            if len(embedding) != self.expected_dim:
                logger.warning(f"Unexpected embedding dim: {len(embedding)}, expected {self.expected_dim}")

            return embedding

        except httpx.ConnectError as e:
            raise OllamaConnectionError(f"Cannot connect to Ollama at {self.base_url}: {e}")
        except httpx.HTTPStatusError as e:
            raise OllamaEmbeddingError(f"Ollama API error: {e.response.status_code}")
        except OllamaEmbeddingError:
            raise
        except Exception as e:
            raise OllamaEmbeddingError(f"Embedding failed: {e}")

    async def embed_batch(
        self,
        texts: list[str],
        model: str | None = None,
        max_concurrent: int = 5,
        raise_on_error: bool = False,
    ) -> list[list[float]]:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def embed_one(text: str) -> list[float]:
            async with semaphore:
                try:
                    return await self.embed(text, model)
                except Exception as e:
                    logger.error(f"Batch embed failed for text (len={len(text)}): {e}")
                    if raise_on_error:
                        raise
                    return []

        tasks = [embed_one(text) for text in texts]
        return await asyncio.gather(*tasks)


_ollama_client: OllamaClient | None = None


def get_ollama_client() -> OllamaClient:
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client


async def close_ollama_client():
    global _ollama_client
    if _ollama_client is not None:
        await _ollama_client.close()
        _ollama_client = None
