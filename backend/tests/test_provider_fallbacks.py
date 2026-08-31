import asyncio

from app.core.config import settings
from app.services.climate_service import ClimateService
from app.integrations.climate.mock import MockClimateProvider
from app.services.ai_service import AIService


def test_uses_mock_provider_when_fortyguard_key_missing(monkeypatch):
    monkeypatch.setenv('CLIMATE_PROVIDER', 'fortyguard')
    monkeypatch.delenv('FORTYGUARD_API_KEY', raising=False)
    monkeypatch.setattr(settings, 'FORTYGUARD_API_KEY', None, raising=False)

    provider = ClimateService.get_provider()

    assert isinstance(provider, MockClimateProvider)


def test_call_llm_uses_fallback_when_ai_key_missing(monkeypatch):
    monkeypatch.delenv('AI_API_KEY', raising=False)
    monkeypatch.setattr(settings, 'AI_API_KEY', None, raising=False)

    result = asyncio.run(AIService._call_llm('Event: Demo Event\nOrganizer Question: Can we move the party earlier?', 'system'))

    assert 'AI is running in local fallback mode' in result
    assert 'AI_API_KEY' in result or 'Add AI_API_KEY' in result
