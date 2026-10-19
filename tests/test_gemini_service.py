import asyncio
import logging
from types import SimpleNamespace
from datetime import datetime

import pytest

from app.core.config import GeminiSettings, get_gemini_settings
from app.services import gemini_service
from google.genai.errors import APIError, ClientError, ServerError

from app.services.gemini_service import (
    FALLBACK_MODELS,
    STREAM_FAILURE_MESSAGE,
    PRIMARY_MODEL,
    BookingSlots,
    GeminiChatResponse,
    GeminiService,
    GeminiServiceError,
)


def test_gemini_service_passes_trimmed_api_key_to_sdk(monkeypatch):
    captured = {}
    monkeypatch.setenv("GEMINI_API_KEY", "  test-api-key  ")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")

    def fake_client(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(gemini_service.genai, "Client", fake_client)

    service = GeminiService()

    assert captured["api_key"] == "test-api-key"
    assert captured["http_options"].timeout == 20_000
    assert service.client is not None
    assert service.model == "gemini-3.8-flash"


def test_gemini_settings_uses_gemini_key_and_current_default_model(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "  test-api-key  ")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    settings = get_gemini_settings()

    assert settings.api_key == "test-api-key"
    assert settings.model == "gemini-3.8-flash"


def test_gemini_settings_falls_back_when_primary_key_is_whitespace(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "   ")
    monkeypatch.setenv("GOOGLE_API_KEY", " legacy-key ")

    settings = get_gemini_settings()

    assert settings.api_key == "legacy-key"


def test_gemini_service_logs_when_api_key_is_missing(monkeypatch, caplog):
    monkeypatch.setattr(
        gemini_service,
        "get_gemini_settings",
        lambda: GeminiSettings(api_key=None, model="gemini-3.8-flash"),
    )
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    caplog.set_level(logging.ERROR, logger=gemini_service.__name__)

    with pytest.raises(GeminiServiceError, match="Gemini API is not configured"):
        GeminiService()

    assert "GEMINI_API_KEY and GOOGLE_API_KEY are empty" in caplog.text


def test_gemini_service_logs_sdk_exceptions(caplog):
    class FailingModels:
        @staticmethod
        def generate_content(**kwargs):
            raise RuntimeError(
                f"simulated Gemini outage during {', '.join(kwargs)}"
            )

    class FailingClient:
        models = FailingModels()

    service = GeminiService(client=FailingClient())
    caplog.set_level(logging.ERROR, logger=gemini_service.__name__)

    with pytest.raises(GeminiServiceError, match="could not process"):
        service.generate_chat_response(
            user_message="Xin chào",
            history=[],
            current_time=datetime(2026, 10, 12, 10, 0),
            available_rooms=[],
        )

    assert "Gemini chat generation failed" in caplog.text
    assert "simulated Gemini outage" in caplog.text
    assert "\033[91m" in caplog.records[-1].getMessage()


@pytest.mark.parametrize(
    "error",
    [
        ServerError(503, {"message": "UNAVAILABLE"}),
        APIError(429, {"message": "RESOURCE_EXHAUSTED"}),
    ],
)
def test_generate_chat_response_retries_transient_errors_then_uses_primary_model(
    monkeypatch,
    error,
):
    requested_models = []
    delays = []

    class FakeModels:
        def generate_content(self, *, model, **kwargs):
            requested_models.append(model)
            if model == "configured-model":
                raise error
            return SimpleNamespace(
                parsed=GeminiChatResponse(
                    intent="GENERAL_FAQ",
                    slots=BookingSlots(),
                    bot_message="Đã xử lý",
                )
            )

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(gemini_service.time_module, "sleep", delays.append)
    service = GeminiService(model="configured-model", client=FakeClient())

    result = service.generate_chat_response(
        user_message="Xin chào",
        history=[],
        current_time=datetime(2026, 10, 12, 10, 0),
        available_rooms=[],
    )

    assert result.bot_message == "Đã xử lý"
    assert error.code in (429, 503)
    assert requested_models == ["configured-model"] * 5 + [PRIMARY_MODEL]
    assert delays == [1, 2, 3, 4]


def test_generate_chat_response_does_not_retry_unavailable_model(caplog):
    requested_models = []

    class FakeModels:
        def generate_content(self, *, model, **kwargs):
            requested_models.append(model)
            raise ClientError(404, {"message": "model not found"})

    class FakeClient:
        models = FakeModels()

    service = GeminiService(model=PRIMARY_MODEL, client=FakeClient())
    caplog.set_level(logging.WARNING, logger=gemini_service.__name__)

    with pytest.raises(GeminiServiceError, match="could not process"):
        service.generate_chat_response(
            user_message="Xin chào",
            history=[],
            current_time=datetime(2026, 10, 12, 10, 0),
            available_rooms=[],
        )

    assert FALLBACK_MODELS == ()
    assert requested_models == [PRIMARY_MODEL]
    assert "code=404" in caplog.text


def test_stream_retries_transient_errors_then_uses_primary_model(monkeypatch):
    requested_models = []
    delays = []

    class FakeModels:
        def generate_content_stream(self, *, model, **kwargs):
            requested_models.append(model)

            def chunks():
                if model == "configured-model":
                    raise ServerError(503, {"message": "UNAVAILABLE"})
                yield SimpleNamespace(
                    candidates=[
                        SimpleNamespace(
                            content=gemini_service.types.Content(
                                role="model",
                                parts=[
                                    gemini_service.types.Part.from_text(
                                        text="fallback response"
                                    )
                                ],
                            )
                        )
                    ]
                )

            return chunks()

    class FakeClient:
        models = FakeModels()

    async def record_delay(delay):
        delays.append(delay)

    monkeypatch.setattr(gemini_service.asyncio, "sleep", record_delay)
    service = GeminiService(model="configured-model", client=FakeClient())

    async def collect():
        return [
            event
            async for event in service.stream_chat_response(
                messages={"current_user_message": "Xin chào"},
                history=[],
            )
        ]

    events = asyncio.run(collect())

    assert requested_models == ["configured-model"] * 5 + [PRIMARY_MODEL]
    assert delays == [1, 2, 3, 4]
    assert {"type": "chunk", "text": "fallback response"} in events


def test_stream_converts_unavailable_model_error_to_sse_event(caplog):
    requested_models = []

    class FakeModels:
        def generate_content_stream(self, *, model, **kwargs):
            requested_models.append(model)

            def chunks():
                if model == PRIMARY_MODEL:
                    raise ClientError(404, {"message": "model not found"})
                yield SimpleNamespace(
                    candidates=[
                        SimpleNamespace(
                            content=gemini_service.types.Content(
                                role="model",
                                parts=[
                                    gemini_service.types.Part.from_text(
                                        text="fallback response"
                                    )
                                ],
                            )
                        )
                    ]
                )

            return chunks()

    class FakeClient:
        models = FakeModels()

    service = GeminiService(model=PRIMARY_MODEL, client=FakeClient())
    caplog.set_level(logging.WARNING, logger=gemini_service.__name__)

    async def collect():
        return [
            event
            async for event in service.stream_chat_response(
                messages={"current_user_message": "Xin chào"},
                history=[],
            )
        ]

    events = asyncio.run(collect())

    assert requested_models == [PRIMARY_MODEL]
    assert events == [{"type": "error", "message": STREAM_FAILURE_MESSAGE}]
    assert "code=404" in caplog.text


def test_stream_emits_friendly_error_after_all_primary_retries_return_503(monkeypatch):
    requested_models = []
    delays = []

    class FakeModels:
        def generate_content_stream(self, *, model, **kwargs):
            requested_models.append(model)
            raise ServerError(503, {"message": "UNAVAILABLE"})

    class FakeClient:
        models = FakeModels()

    async def record_delay(delay):
        delays.append(delay)

    monkeypatch.setattr(gemini_service.asyncio, "sleep", record_delay)
    service = GeminiService(model=PRIMARY_MODEL, client=FakeClient())

    async def collect():
        return [
            event
            async for event in service.stream_chat_response(
                messages={"current_user_message": "Xin chào"},
                history=[],
            )
        ]

    events = asyncio.run(collect())

    assert requested_models == [PRIMARY_MODEL] * 5
    assert delays == [1, 2, 3, 4]
    assert events == [{"type": "error", "message": STREAM_FAILURE_MESSAGE}]


def test_stream_returns_friendly_error_when_llm_times_out(monkeypatch):
    class FakeClient:
        models = object()

    service = GeminiService(client=FakeClient())

    async def slow_request(**kwargs):
        await asyncio.sleep(1)

    monkeypatch.setattr(gemini_service, "LLM_REQUEST_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(service, "_generate_stream_with_fallback", slow_request)

    async def collect():
        return [
            event
            async for event in service.stream_chat_response(
                messages={"current_user_message": "Find a room"},
                history=[],
            )
        ]

    events = asyncio.run(collect())

    assert events == [{"type": "error", "message": STREAM_FAILURE_MESSAGE}]
