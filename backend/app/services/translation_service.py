"""Lightweight English-to-Kannada, Hindi, and Telugu translation service.

MyMemory provides a simple no-key HTTP API, so this MVP does not need a large
local model or another heavy dependency. The API remains replaceable because
all provider-specific code lives in this module.
"""

import html
import os
import re

import httpx

TRANSLATION_API_URL = os.getenv(
    "TRANSLATION_API_URL",
    "https://api.mymemory.translated.net/get",
)
MAX_CHUNK_CHARACTERS = 450

# Unicode script ranges for target Indian languages
LANGUAGE_SCRIPTS = {
    "kn": (0x0C80, 0x0CFF),  # Kannada
    "hi": (0x0900, 0x097F),  # Devanagari (Hindi)
    "te": (0x0C00, 0x0C7F),  # Telugu
}

DISALLOWED_SCRIPTS_FOR_KANNADA = [
    (0x0B80, 0x0BFF),  # Tamil script improperly tagged as kn in crowd-sourced datasets
]

# Standard authentic classroom phrases to prevent corrupted crowd-sourced matches
KNOWN_CLASSROOM_FALLBACKS: dict[str, dict[str, str]] = {
    "good morning": {
        "kn": "ಶುಭೋದಯ",
        "hi": "शुभ प्रभात",
        "te": "శుభోదయం",
    },
    "good morning students": {
        "kn": "ಶುಭೋದಯ ವಿದ್ಯಾರ್ಥಿಗಳು",
        "hi": "शुभ प्रभात छात्रों",
        "te": "శుభోదయం విద్యార్థులు",
    },
    "open your book": {
        "kn": "ನಿಮ್ಮ ಪುಸ್ತಕವನ್ನು ತೆರೆಯಿರಿ",
        "hi": "अपनी किताब खोलें",
        "te": "మీ పుస్తకాన్ని తెరవండి",
    },
    "pay attention": {
        "kn": "ಗಮನ ಕೊಡಿ",
        "hi": "ध्यान दें",
        "te": "శ్రద్ధ వహించండి",
    },
    "any questions": {
        "kn": "ಯಾವುದಾದರೂ ಪ್ರಶ್ನೆಗಳಿವೆಯೇ?",
        "hi": "कोई प्रश्न?",
        "te": "ఏవైనా ప్రశ్నలు ఉన్నాయా?",
    },
    "thank you": {
        "kn": "ಧನ್ಯವಾದಗಳು",
        "hi": "धन्यवाद",
        "te": "ధన్యవాదాలు",
    },
}


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


def clean_candidate(val: str) -> str:
    cleaned = re.sub(r"<[^>]+>", "", val)
    return html.unescape(cleaned).strip()


def has_script(text: str, rng: tuple[int, int]) -> bool:
    start, end = rng
    return any(start <= ord(c) <= end for c in text)


def select_valid_translation(data: dict, chunk: str, target_lang: str) -> str:
    top = clean_candidate(data.get("responseData", {}).get("translatedText", ""))
    candidates = []
    if top:
        candidates.append(top)

    for m in data.get("matches", []):
        trans = m.get("translation")
        if trans:
            c = clean_candidate(trans)
            if c and c not in candidates:
                candidates.append(c)

    # When Kannada is requested, if the provider returns corrupt Tamil text,
    # find an authentic Kannada match or clean fallback.
    if target_lang == "kn" and has_script(top, (0x0B80, 0x0BFF)):
        kannada_candidates = [
            c for c in candidates
            if has_script(c, LANGUAGE_SCRIPTS["kn"]) and not any(has_script(c, dis) for dis in DISALLOWED_SCRIPTS_FOR_KANNADA)
        ]
        if kannada_candidates:
            kannada_candidates.sort(key=len)
            return kannada_candidates[0]

        norm = chunk.strip().lower().rstrip(".!?")
        if norm in KNOWN_CLASSROOM_FALLBACKS and "kn" in KNOWN_CLASSROOM_FALLBACKS[norm]:
            return KNOWN_CLASSROOM_FALLBACKS[norm]["kn"]

    return candidates[0] if candidates else ""


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

            translated_text = select_valid_translation(data, chunk, target_language)
            if response_status >= 400:
                raise TranslationServiceError("The translation provider rejected the request.")
            if not translated_text:
                raise TranslationServiceError("The translation provider returned no text.")

            translated_chunks.append(translated_text)

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
