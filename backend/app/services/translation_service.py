"""Lightweight English-to-Kannada, Hindi, and Telugu translation service.

MyMemory provides a simple no-key HTTP API, so this MVP does not need a large
local model or another heavy dependency. The API remains replaceable because
all provider-specific code lives in this module.
"""

import html
import os

import httpx

TRANSLATION_API_URL = os.getenv(
    "TRANSLATION_API_URL",
    "https://api.mymemory.translated.net/get",
)
MAX_CHUNK_CHARACTERS = 450


class TranslationServiceError(Exception):
    """Raised when the external translation provider cannot translate text."""


def split_text(text: str) -> list[str]:
    """Split long text at word boundaries for providers with query limits."""
    chunks = []
    remaining = text.strip()

    while len(remaining) > MAX_CHUNK_CHARACTERS:
        split_at = remaining.rfind(" ", 0, MAX_CHUNK_CHARACTERS)
        if split_at <= 0:
            split_at = MAX_CHUNK_CHARACTERS
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()

    if remaining:
        chunks.append(remaining)
    return chunks


class TranslationService:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=10.0)
        self._owns_client = client is None
        self._cache: dict[tuple[str, str, str], str] = {}

    async def translate(self, text: str, target_language: str) -> str:
        original_text = text.strip()
        if not original_text:
            raise TranslationServiceError("Text to translate cannot be empty.")
        if target_language == "en":
            return original_text

        cache_key = (target_language, original_text.casefold(), original_text)
        if cache_key in self._cache:
            return self._cache[cache_key]

        translated_chunks = []
        for chunk in split_text(original_text):
            try:
                response = await self._client.get(
                    TRANSLATION_API_URL,
                    params={"q": chunk, "langpair": f"en|{target_language}"},
                )
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError("Translation provider returned an invalid response.")
            except (httpx.HTTPError, ValueError) as error:
                raise TranslationServiceError(
                    "The translation provider is temporarily unavailable."
                ) from error

            try:
                response_status = int(data.get("responseStatus", 200))
            except (TypeError, ValueError) as error:
                raise TranslationServiceError(
                    "The translation provider returned an invalid status."
                ) from error
            translated_text = data.get("responseData", {}).get("translatedText", "")
            if response_status >= 400:
                raise TranslationServiceError("The translation provider rejected the request.")
            if not translated_text:
                raise TranslationServiceError("The translation provider returned no text.")

            translated_chunks.append(html.unescape(translated_text).strip())

        result = " ".join(part for part in translated_chunks if part)
        if not result:
            raise TranslationServiceError("The translation provider returned no text.")

        # A small cache avoids translating the same saved segment again when a
        # student switches languages back and forth.
        if len(self._cache) >= 500:
            self._cache.clear()
        self._cache[cache_key] = result
        return result

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
