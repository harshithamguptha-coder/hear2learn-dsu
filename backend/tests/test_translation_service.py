"""Use focused mocks so automated tests never depend on an external service."""

import asyncio

import httpx

from app.services.translation_service import (
    TranslationService,
    TranslationServiceError,
    split_text,
)


def test_english_passthrough_does_not_call_provider():
    async def check():
        async with httpx.AsyncClient() as client:
            service = TranslationService(client)
            assert await service.translate("Hello", "en") == "Hello"
            await service.close()

    asyncio.run(check())


def test_translation_decodes_provider_html_and_caches_result():
    calls = []

    def provider(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "responseStatus": 200,
                "responseData": {"translatedText": "Hello &amp; welcome"},
            },
        )

    async def check():
        transport = httpx.MockTransport(provider)
        async with httpx.AsyncClient(transport=transport) as client:
            service = TranslationService(client)
            first = await service.translate("Hello", "kn")
            second = await service.translate("Hello", "kn")
            await service.close()

        assert first == "Hello & welcome"
        assert second == "Hello & welcome"
        assert len(calls) == 1
        assert calls[0].url.params["langpair"] == "en|kn"

    asyncio.run(check())


def test_provider_failure_raises_translation_error():
    def provider(_request):
        return httpx.Response(503)

    async def check():
        transport = httpx.MockTransport(provider)
        async with httpx.AsyncClient(transport=transport) as client:
            service = TranslationService(client)
            try:
                await service.translate("Hello", "hi")
            except TranslationServiceError:
                pass
            else:
                raise AssertionError("Expected TranslationServiceError")
            await service.close()

    asyncio.run(check())


def test_long_text_is_split_into_provider_safe_chunks():
    chunks = split_text("word " * 200)
    assert len(chunks) > 1
    assert all(len(chunk) <= 450 for chunk in chunks)
    assert " ".join(chunks) == ("word " * 200).strip()
