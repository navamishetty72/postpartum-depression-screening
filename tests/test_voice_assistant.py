"""Tests for the standalone Gemini-powered Voice Assistant module.

Validates:
- Non-blocking configuration and startup safety
- Deterministic emergency safety evaluation and crisis helpline escalation
- Differentiation of ordinary postpartum distress from emergency crisis
- Complete emergency bypass of the Gemini LLM
- Mocked multi-turn conversation support
- Graceful handling of missing credentials and upstream provider failures
- Privacy-safe logging (zero persistence or logging of raw patient narratives)
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.services.voice_assistant.config import (
    DEFAULT_GEMINI_MODEL,
    VoiceAssistantConfig,
    get_voice_assistant_config,
)
from backend.services.voice_assistant.gemini_service import (
    FALLBACK_SUPPORT_MESSAGE,
    GeminiCredentialsMissingError,
    GeminiProviderError,
    GeminiVoiceAssistantService,
    VoiceAssistantResponse,
)
from backend.services.voice_assistant.safety_guard import (
    SafetyGuard,
)


# =============================================================================
# 1. Configuration & Startup Tests
# =============================================================================

def test_config_defaults(monkeypatch):
    """Verify default configuration without requiring environment variables."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    config = VoiceAssistantConfig()
    assert config.model == DEFAULT_GEMINI_MODEL
    assert config.is_configured is False
    assert config.api_key is None
    assert config.temperature == 0.7
    assert config.max_output_tokens == 300


def test_config_env_overrides(monkeypatch):
    """Verify environment variables override defaults cleanly."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-secret-api-key-12345")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    config = get_voice_assistant_config()
    assert config.is_configured is True
    assert config.api_key == "test-secret-api-key-12345"
    assert config.model == "gemini-3.5-flash-lite"


def test_config_repr_masks_credentials(monkeypatch):
    """Confirm __repr__ never leaks raw API credentials into logs or debuggers."""
    secret_key = "super_secret_raw_key_xyz_999"
    config = VoiceAssistantConfig(api_key=secret_key, model="gemini-3.8-flash")
    repr_str = repr(config)

    assert secret_key not in repr_str
    assert "api_key=[configured]" in repr_str


def test_config_system_prompt_loading():
    """Verify the system prompt file exists and can be loaded cleanly."""
    config = VoiceAssistantConfig()
    prompt = config.get_system_prompt()
    assert len(prompt) > 50
    assert "postpartum" in prompt.lower()


def test_config_invalid_prompt_path_raises_file_not_found(tmp_path):
    """Verify FileNotFoundError is raised if system prompt path is invalid."""
    missing_path = tmp_path / "non_existent_prompt.txt"
    config = VoiceAssistantConfig(system_prompt_path=missing_path)
    with pytest.raises(FileNotFoundError):
        config.get_system_prompt()


# =============================================================================
# 2. Safety Guard Tests: Ordinary Distress vs Acute Emergency
# =============================================================================

@pytest.mark.parametrize(
    "benign_message",
    [
        "I am so exhausted and haven't slept more than two hours in days.",
        "I have been crying all morning and I don't even know why.",
        "I feel completely overwhelmed by breastfeeding and the diaper changes.",
        "I'm feeling very anxious whenever the baby is sleeping.",
        "I feel like such a bad mother today.",
        "I feel sad and alone, even when my partner is in the room.",
        "The baby was crying for an hour straight and I felt so helpless.",
        "I am tired of feeling this drained and anxious all the time.",
    ],
)
def test_safety_guard_normal_postpartum_feelings_not_escalated(benign_message):
    """Ordinary postpartum crying, fatigue, anxiety, and distress must NOT trigger emergencies."""
    guard = SafetyGuard()
    result = guard.evaluate(benign_message)

    assert result.is_safe is True
    assert result.category is None
    assert result.emergency_response is None
    assert len(result.matched_rules) == 0


@pytest.mark.parametrize(
    "crisis_message",
    [
        "I want to kill myself",
        "I am thinking of ending my own life",
        "Everyone would be better off without me, I want to die",
        "I feel like committing suicide tonight",
        "I want to take all the pills and end it all",
        "I have suicidal thoughts and I can't keep going on living",
    ],
)
def test_safety_guard_self_harm_emergency_escalation(crisis_message):
    """Active suicidal ideation or self-harm intent must trigger immediate escalation."""
    guard = SafetyGuard()
    result = guard.evaluate(crisis_message)

    assert result.is_safe is False
    assert result.category == "self_harm"
    assert result.emergency_response is not None
    assert "14416" in result.emergency_response  # Tele-MANAS (India)
    assert "112" in result.emergency_response    # Emergency (India)
    assert "988" in result.emergency_response    # Lifeline (US/Canada)
    assert "1-833-852-6262" in result.emergency_response
    assert "SELF_HARM_OR_SUICIDAL_INTENT" in result.matched_rules


@pytest.mark.parametrize(
    "infant_harm_message",
    [
        "I have thoughts of hurting my baby",
        "I feel like smothering my newborn",
        "I want to throw my baby against the wall",
        "I'm afraid I might shake my baby because he won't stop crying",
        "I feel tempted to harm my infant",
    ],
)
def test_safety_guard_infant_harm_emergency_escalation(infant_harm_message):
    """Thoughts or urges of infant harm must trigger infant-safe crisis escalation."""
    guard = SafetyGuard()
    result = guard.evaluate(infant_harm_message)

    assert result.is_safe is False
    assert result.category == "infant_harm"
    assert result.emergency_response is not None
    # Must instruct safe placement (e.g. crib) and provide maternal mental health hotline
    assert "crib" in result.emergency_response.lower()
    assert "14416" in result.emergency_response  # Tele-MANAS (India)
    assert "112" in result.emergency_response    # Emergency (India)
    assert "1-833-852-6262" in result.emergency_response
    assert "988" in result.emergency_response
    assert "INFANT_HARM_INTENT" in result.matched_rules


def test_safety_guard_immediate_danger_escalation():
    """Immediate physical danger must trigger 112/911 emergency response."""
    guard = SafetyGuard()
    result = guard.evaluate("I am in immediate danger, someone is attacking me")

    assert result.is_safe is False
    assert result.category == "immediate_danger"
    assert "112" in result.emergency_response
    assert "911" in result.emergency_response


def test_safety_guard_empty_and_whitespace():
    """Empty or whitespace text is handled safely."""
    guard = SafetyGuard()
    assert guard.evaluate("").is_safe is True
    assert guard.evaluate("   \n\t  ").is_safe is True


# =============================================================================
# 3. Gemini Service: Emergency Bypass (Gemini Never Called)
# =============================================================================

def test_emergency_bypasses_gemini_completely():
    """Emergency detection must bypass Gemini and never make an API call."""
    mock_client = MagicMock()
    service = GeminiVoiceAssistantService(
        config=VoiceAssistantConfig(api_key="mock-key"),
        client=mock_client,
    )

    emergency_input = "I'm having thoughts of harming my baby"
    response: VoiceAssistantResponse = service.generate_response(emergency_input)

    # Verify response is emergency from safety_guard
    assert response.is_emergency is True
    assert response.category == "infant_harm"
    assert response.source == "safety_guard"
    assert "14416" in response.text
    assert "1-833-852-6262" in response.text

    # Crucial assertion: Gemini API client was NEVER called!
    mock_client.models.generate_content.assert_not_called()


# =============================================================================
# 4. Gemini Service: Mocked Normal Responses & Multi-turn History
# =============================================================================

def test_gemini_service_normal_response_mocked():
    """Verify normal empathetic responses using mocked google-genai client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "You are doing wonderful, mama. Please take a gentle breath."
    mock_client.models.generate_content.return_value = mock_response

    service = GeminiVoiceAssistantService(
        config=VoiceAssistantConfig(api_key="mock-key"),
        client=mock_client,
    )

    response = service.generate_response("I'm feeling a little overwhelmed today.")

    assert response.is_emergency is False
    assert response.is_fallback is False
    assert response.source == "gemini"
    assert response.text == "You are doing wonderful, mama. Please take a gentle breath."

    mock_client.models.generate_content.assert_called_once()
    _, kwargs = mock_client.models.generate_content.call_args
    assert kwargs["model"] == DEFAULT_GEMINI_MODEL
    assert len(kwargs["contents"]) == 1
    assert kwargs["config"].temperature == 0.7


def test_gemini_service_multi_turn_history_formatting():
    """Verify caller-provided conversation history is formatted into Content objects."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "I'm right here with you."
    mock_client.models.generate_content.return_value = mock_response

    service = GeminiVoiceAssistantService(
        config=VoiceAssistantConfig(api_key="mock-key"),
        client=mock_client,
    )

    history = [
        {"role": "user", "content": "I haven't slept in two days."},
        {"role": "assistant", "content": "That sounds exhausting. Newborn sleep is so hard."},
    ]

    response = service.generate_response(
        user_message="Now the baby won't latch either.",
        conversation_history=history,
    )

    assert response.text == "I'm right here with you."
    mock_client.models.generate_content.assert_called_once()

    _, kwargs = mock_client.models.generate_content.call_args
    contents = kwargs["contents"]
    # 2 history turns + 1 current prompt = 3 Content items
    assert len(contents) == 3
    assert contents[0].role == "user"
    assert contents[1].role == "model"
    assert contents[2].role == "user"


def test_gemini_service_candidate_parts_fallback():
    """Verify response parsing if .text attribute is empty but candidate parts exist."""
    mock_client = MagicMock()
    mock_part = MagicMock()
    mock_part.text = "Candidate text response."
    mock_candidate = MagicMock()
    mock_candidate.content.parts = [mock_part]

    mock_response = MagicMock(spec=[])
    mock_response.candidates = [mock_candidate]
    mock_client.models.generate_content.return_value = mock_response

    service = GeminiVoiceAssistantService(
        config=VoiceAssistantConfig(api_key="mock-key"),
        client=mock_client,
    )

    response = service.generate_response("I'm feeling tired.")
    assert response.text == "Candidate text response."


# =============================================================================
# 5. Missing Credentials & Startup Safety
# =============================================================================

def test_service_missing_credentials_graceful_fallback(monkeypatch):
    """Missing API key must not crash service initialization or normal call."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    service = GeminiVoiceAssistantService()
    assert service._client is None  # Lazy: not initialized at startup

    # Default call returns supportive fallback message rather than crashing
    response = service.generate_response("I'm feeling exhausted today.", raise_on_error=False)
    assert response.is_fallback is True
    assert response.source == "fallback"
    assert FALLBACK_SUPPORT_MESSAGE in response.text


def test_service_missing_credentials_raises_when_requested(monkeypatch):
    """When raise_on_error=True, missing credentials raises GeminiCredentialsMissingError."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    service = GeminiVoiceAssistantService()
    with pytest.raises(GeminiCredentialsMissingError):
        service.generate_response("I'm feeling exhausted today.", raise_on_error=True)


# =============================================================================
# 6. Provider Failures Handling
# =============================================================================

def test_service_provider_failure_returns_fallback():
    """Upstream API failure (timeout, network error) returns graceful fallback message."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("Upstream API 503 Service Unavailable")

    service = GeminiVoiceAssistantService(
        config=VoiceAssistantConfig(api_key="mock-key"),
        client=mock_client,
    )

    response = service.generate_response("I'm having a hard day.", raise_on_error=False)
    assert response.is_fallback is True
    assert response.source == "fallback"
    assert FALLBACK_SUPPORT_MESSAGE in response.text


def test_service_provider_failure_raises_when_requested():
    """When raise_on_error=True, upstream failure raises GeminiProviderError."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = ConnectionError("Connection refused")

    service = GeminiVoiceAssistantService(
        config=VoiceAssistantConfig(api_key="mock-key"),
        client=mock_client,
    )

    with pytest.raises(GeminiProviderError) as exc_info:
        service.generate_response("I'm having a hard day.", raise_on_error=True)
    assert "ConnectionError" in str(exc_info.value)


# =============================================================================
# 7. Privacy-Safe Logging (Zero Persistence & Zero Message Content)
# =============================================================================

def test_privacy_safe_logging_never_logs_user_narrative(caplog):
    """Verify that private narrative text is NEVER logged across any log level."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "You are not alone, mama."
    mock_client.models.generate_content.return_value = mock_response

    service = GeminiVoiceAssistantService(
        config=VoiceAssistantConfig(api_key="mock-key"),
        client=mock_client,
    )

    sensitive_narrative = "CONFIDENTIAL_PATIENT_TEXT_SECRET_TOKEN_XYZ_12345"
    sensitive_history_turn = "CONFIDENTIAL_HISTORY_SECRET_TOKEN_ABC_67890"

    with caplog.at_level(logging.DEBUG):
        service.generate_response(
            user_message=sensitive_narrative,
            conversation_history=[{"role": "user", "content": sensitive_history_turn}],
        )

    # Assert neither sensitive string appears anywhere in any log record
    log_text = caplog.text
    assert sensitive_narrative not in log_text
    assert sensitive_history_turn not in log_text


# =============================================================================
# 8. Input Validation Tests
# =============================================================================

@pytest.mark.parametrize("empty_input", ["", "   ", "\n\t  "])
def test_empty_user_message_raises_value_error(empty_input):
    """Empty or whitespace-only messages raise a ValueError."""
    service = GeminiVoiceAssistantService(config=VoiceAssistantConfig(api_key="mock-key"))
    with pytest.raises(ValueError, match="user_message cannot be empty"):
        service.generate_response(empty_input)


# =============================================================================
# 9. System Prompt Persona & Boundary Verification
# =============================================================================

def test_system_prompt_persona_and_clinical_boundaries():
    """Verify system prompt contains required empathetic tone and non-diagnostic boundaries."""
    config = VoiceAssistantConfig()
    prompt = config.get_system_prompt()

    # Empathy & validation
    assert "empathetic" in prompt.lower() or "compassionate" in prompt.lower()
    assert "validate" in prompt.lower() or "validation" in prompt.lower()

    # Voice & playback optimization
    assert "voice" in prompt.lower() or "speech" in prompt.lower()

    # Clinical safety boundaries: No diagnosis, no medication
    assert "never diagnose" in prompt.lower()
    assert "medication" in prompt.lower()
    assert "healthcare provider" in prompt.lower() or "ob-gyn" in prompt.lower()

