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

def test_gemini_service_normal_response_mocked(monkeypatch):
    """Verify normal empathetic responses using mocked google-genai client."""
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
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


# =============================================================================
# 10. Multilingual Automatic Language Detection Tests
# =============================================================================

@pytest.mark.parametrize(
    "expected_code,phrase",
    [
        ("en", "I am feeling exhausted and lonely with the baby today."),
        ("hi", "मुझे बहुत थकान महसूस हो रही है और रोना आ रहा है।"),
        ("kn", "ನನಗೆ ತುಂಬಾ ಸುಸ್ತಾಗಿದೆ ಮತ್ತು ಮಗುವಿನ ಆರೈಕೆ ಕಷ್ಟವಾಗುತ್ತಿದೆ."),
        ("ta", "எனக்கு மிகவும் பயமாகவும் சோர்வாகவும் இருக்கிறது."),
        ("te", "నాకు చాలా అలసటగా ఉంది, సరిగ్గా నిద్ర పట్టడం లేదు."),
        ("ml", "എനിക്ക് വളരെ ക്ഷീണം തോന്നുന്നു, സങ്കടം സഹിക്കാൻ കഴിയുന്നില്ല."),
        ("bn", "আমার খুব একা লাগছে এবং সারারাত ঘুম হচ্ছে না।"),
        ("mr", "मला खूप थकवा जाणवतोय आणि बाळाची काळजी वाटतेय."),
    ],
)
def test_multilingual_language_detection(expected_code, phrase):
    """Verify accurate detection across all 8 supported languages."""
    from backend.services.voice_assistant.config import detect_language, SUPPORTED_LANGUAGES

    detected = detect_language(phrase)
    assert detected == expected_code
    assert detected in SUPPORTED_LANGUAGES


def test_multilingual_supported_languages_metadata():
    """Verify all 8 languages have names, native names, and BCP-47 locales."""
    from backend.services.voice_assistant.config import SUPPORTED_LANGUAGES

    expected_languages = ["en", "hi", "kn", "ta", "te", "ml", "bn", "mr"]
    for code in expected_languages:
        assert code in SUPPORTED_LANGUAGES
        meta = SUPPORTED_LANGUAGES[code]
        assert "name" in meta
        assert "native_name" in meta
        assert "locale" in meta
        assert meta["locale"].endswith("-IN")


# =============================================================================
# 11. Multilingual Speech Recognition Processing Tests
# =============================================================================

@pytest.mark.parametrize(
    "expected_lang,expected_locale,transcript,hint",
    [
        ("en", "en-IN", "I am feeling very tired.", None),
        ("hi", "hi-IN", "मुझे बहुत चिंता हो रही है", "hi-IN"),
        ("kn", "kn-IN", "ನನಗೆ ನಿದ್ದೆ ಬರುತ್ತಿಲ್ಲ", None),
        ("ta", "ta-IN", "எனக்கு கவலையாக இருக்கிறது", "ta-IN"),
        ("te", "te-IN", "నాకు చాలా భయంగా ఉంది", None),
        ("ml", "ml-IN", "എനിക്ക് വിഷമം തോന്നുന്നു", "ml-IN"),
        ("bn", "bn-IN", "আমার খুব ভয় লাগছে", None),
        ("mr", "mr-IN", "मला खूप त्रास होतोय", "mr-IN"),
    ],
)
def test_process_speech_recognition_multilingual(expected_lang, expected_locale, transcript, hint):
    """Verify speech recognition input is parsed with correct language and voice locale."""
    service = GeminiVoiceAssistantService()
    result = service.process_speech_recognition(transcript, language_hint=hint)

    assert result["transcript"] == transcript
    assert result["language"] == expected_lang
    assert result["voice_locale"] == expected_locale
    assert result["is_supported"] is True


def test_process_speech_recognition_empty_defaults_to_english():
    """Empty speech recognition transcript safely defaults to English without error."""
    service = GeminiVoiceAssistantService()
    result = service.process_speech_recognition("")
    assert result["language"] == "en"
    assert result["voice_locale"] == "en-IN"


# =============================================================================
# 12. Multilingual Response Generation & Voice Locale Mapping
# =============================================================================

@pytest.mark.parametrize(
    "lang_code,user_prompt,mock_ai_reply",
    [
        ("hi", "मुझे बहुत घबराहट हो रही है", "आपकी घबराहट स्वाभाविक है, आप अकेली नहीं हैं।"),
        ("kn", "ನನಗೆ ನಿದ್ದೆ ಬರುತ್ತಿಲ್ಲ", "ಹೊಸ ತಾಯಂದಿರಿಗೆ ನಿದ್ದೆಯ ಕೊರತೆ ಸಹಜ, ವಿಶ್ರಾಂತಿ ತೆಗೆದುಕೊಳ್ಳಿ."),
        ("ta", "எனக்கு பயமாக இருக்கிறது", "உங்கள் பயம் புரிகிறது, நீங்கள் தைரியமாக இருக்கிறீர்கள்."),
        ("te", "నాకు చాలా ఆందోళనగా ఉంది", "మీ ఆందోళన సహజం, మీరు ఒంటరిగా లేరు."),
        ("ml", "എനിക്ക് വല്ലാത്ത സങ്കടം", "നിങ്ങൾ അനുഭവിക്കുന്ന വിഷമം സ്വാഭാവികം മാത്രമാണ്."),
        ("bn", "আমার খুব কান্না পাচ্ছে", "নতুন মায়েদের কান্না আসা খুব স্বাভাবিক, আপনি একা নন।"),
        ("mr", "मला खूप काळजी वाटतेय", "काळजी वाटणे स्वाभाविक आहे, तुम्ही खूप चांगले प्रयत्न करत आहात."),
    ],
)
def test_multilingual_response_and_voice_locale(lang_code, user_prompt, mock_ai_reply):
    """Verify Gemini responds in the same language with corresponding voice synthesis locale."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = mock_ai_reply
    mock_client.models.generate_content.return_value = mock_response

    service = GeminiVoiceAssistantService(
        config=VoiceAssistantConfig(api_key="mock-key"),
        client=mock_client,
    )

    response = service.generate_response(user_prompt)

    assert response.language == lang_code
    assert response.voice_locale == f"{lang_code}-IN"
    assert response.text == mock_ai_reply
    assert response.is_emergency is False
    assert response.source == "gemini"


# =============================================================================
# 13. Natural Language Switching with Context Preservation
# =============================================================================

def test_multilingual_conversation_language_switching():
    """Verify user can switch languages naturally while preserving multi-turn context."""
    mock_client = MagicMock()
    service = GeminiVoiceAssistantService(
        config=VoiceAssistantConfig(api_key="mock-key"),
        client=mock_client,
    )

    # Turn 1: Mother starts in English
    mock_resp1 = MagicMock()
    mock_resp1.text = "I hear you, mama. Sleep deprivation is so hard."
    mock_client.models.generate_content.return_value = mock_resp1

    turn1_user = "I haven't slept for two days because the baby is crying."
    resp1 = service.generate_response(turn1_user)
    assert resp1.language == "en"
    assert resp1.voice_locale == "en-IN"

    # Turn 2: Mother switches to Kannada naturally
    history = [
        {"role": "user", "content": turn1_user},
        {"role": "assistant", "content": resp1.text},
    ]
    mock_resp2 = MagicMock()
    mock_resp2.text = "ಹೌದು, ಇದು ತುಂಬಾ ಕಷ್ಟಕರ. ದಯವಿಟ್ಟು ನಿಧಾನವಾಗಿ ಉಸಿರಾಡಿ."
    mock_client.models.generate_content.return_value = mock_resp2

    turn2_user = "ಈಗ ನನಗೆ ತುಂಬಾ ಭಯವಾಗುತ್ತಿದೆ, ನಾನು ಒಳ್ಳೆಯ ತಾಯಿಯೇ ಅಲ್ಲ ಅನ್ನಿಸುತ್ತಿದೆ"
    resp2 = service.generate_response(turn2_user, conversation_history=history)

    assert resp2.language == "kn"
    assert resp2.voice_locale == "kn-IN"
    assert resp2.text == mock_resp2.text

    # Verify context of Turn 1 was provided to Gemini on Turn 2
    mock_client.models.generate_content.assert_called()
    _, kwargs = mock_client.models.generate_content.call_args
    contents = kwargs["contents"]
    # 2 history turns (English) + 1 current prompt (Kannada) = 3 Content parts
    assert len(contents) == 3
    assert contents[0].parts[0].text == turn1_user
    assert contents[1].parts[0].text == resp1.text
    assert contents[2].parts[0].text == turn2_user

    # Turn 3: Mother switches to Hindi
    history.append({"role": "user", "content": turn2_user})
    history.append({"role": "assistant", "content": resp2.text})

    mock_resp3 = MagicMock()
    mock_resp3.text = "आप एक बहुत अच्छी माँ हैं। अपनी देखभाल भी जरूरी है।"
    mock_client.models.generate_content.return_value = mock_resp3

    turn3_user = "क्या आप मुझे थोड़ी हिम्मत दे सकती हैं?"
    resp3 = service.generate_response(turn3_user, conversation_history=history)

    assert resp3.language == "hi"
    assert resp3.voice_locale == "hi-IN"

    # Verify all 4 history items + current turn sent
    _, kwargs3 = mock_client.models.generate_content.call_args
    assert len(kwargs3["contents"]) == 5


# =============================================================================
# 14. Multilingual Safety Escalation & Benign Distress Differentiation
# =============================================================================

@pytest.mark.parametrize(
    "lang_code,crisis_phrase",
    [
        ("hi", "मैं आत्महत्या करना चाहती हूँ, मैं बहुत परेशान हूँ"),
        ("kn", "ನಾನು ಸಾಯಬೇಕು ಎಂದುಕೊಂಡಿದ್ದೇನೆ, ನನಗೆ ಬದುಕಲು ಇಷ್ಟವಿಲ್ಲ"),
        ("ta", "நான் தற்கொலை செய்து கொள்ள விரும்புகிறேன்"),
        ("te", "నేను ఆత్మహత్య చేసుకోవాలనుకుంటున్నాను"),
        ("ml", "എനിക്ക് ജീവനൊടുക്കാൻ തോന്നുന്നു, ആത്മഹത്യ ചെയ്യണം"),
        ("bn", "আমি আত্মহত্যা করতে চাই, বাঁচতে চাই না"),
        ("mr", "मला आत्महत्या करावीशी वाटते, मी जगू शकत नाही"),
    ],
)
def test_multilingual_safety_guard_self_harm_escalation(lang_code, crisis_phrase):
    """Acute crisis in supported Indian languages triggers immediate emergency response in that language."""
    mock_client = MagicMock()
    service = GeminiVoiceAssistantService(
        config=VoiceAssistantConfig(api_key="mock-key"),
        client=mock_client,
    )

    response = service.generate_response(crisis_phrase)

    assert response.is_emergency is True
    assert response.category == "self_harm"
    assert response.source == "safety_guard"
    assert response.language == lang_code
    assert response.voice_locale == f"{lang_code}-IN"
    # National helpline Tele-MANAS (14416) and emergency 112 must be present
    assert "14416" in response.text
    assert "112" in response.text
    # Gemini must NOT be called
    mock_client.models.generate_content.assert_not_called()


@pytest.mark.parametrize(
    "lang_code,benign_phrase",
    [
        ("hi", "मैं बहुत थक गई हूँ और बच्चा सो नहीं रहा है"),
        ("kn", "ನನಗೆ ತುಂಬಾ ಆಯಾಸವಾಗಿದೆ, ಮಗುವಿಗೆ ಹಾಲೂಡಿಸುವುದು ಕಷ್ಟವಾಗಿದೆ"),
        ("ta", "எனக்கு மிகவும் தூக்கம் வருகிறது, சோர்வாக இருக்கிறது"),
        ("te", "నాకు చాలా నీరసంగా ఉంది, విశ్రాంతి దొరకడం లేదు"),
        ("ml", "എനിക്ക് നല്ല ക്ഷീണം തോന്നുന്നു, ഉറക്കം കുറവാണ്"),
        ("bn", "আমার খুব ক্লান্তি লাগছে, বাচ্চা ঘুমাচ্ছে না"),
        ("mr", "मला खूप थकवा आला आहे आणि झोप येत नाही"),
    ],
)
def test_multilingual_safety_guard_benign_distress_not_escalated(lang_code, benign_phrase):
    """Ordinary maternal fatigue, crying, or stress in Indian languages must NOT trigger emergency."""
    guard = SafetyGuard()
    result = guard.evaluate(benign_phrase)
    assert result.is_safe is True
    assert result.category is None
    assert result.language == lang_code


# =============================================================================
# 15. Multilingual Localized Fallbacks
# =============================================================================

def test_multilingual_missing_credentials_returns_localized_fallback(monkeypatch):
    """When credentials missing, fallback message is in the mother's detected language."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    service = GeminiVoiceAssistantService()

    resp_hi = service.generate_response("मुझे बहुत थकान हो रही है", raise_on_error=False)
    assert resp_hi.is_fallback is True
    assert resp_hi.language == "hi"
    assert resp_hi.voice_locale == "hi-IN"
    assert "अकेली नहीं हैं" in resp_hi.text

    resp_kn = service.generate_response("ನನಗೆ ತುಂಬಾ ಸುಸ್ತಾಗಿದೆ", raise_on_error=False)
    assert resp_kn.is_fallback is True
    assert resp_kn.language == "kn"
    assert resp_kn.voice_locale == "kn-IN"
    assert "ಒಬ್ಬಂಟಿಯಲ್ಲ" in resp_kn.text


