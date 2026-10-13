import logging
from datetime import datetime

import pytest

from app.core.config import GeminiSettings, get_gemini_settings
from app.services import gemini_service
from app.services.gemini_service import GeminiService, GeminiServiceError


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

    assert captured == {"api_key": "test-api-key"}
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
        lambda: GeminiSettings(api_key=None, model="gemini-2.5-flash"),
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
