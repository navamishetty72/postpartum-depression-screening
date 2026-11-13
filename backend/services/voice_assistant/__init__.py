"""Standalone Voice Assistant module for postpartum mother support.

Provides an empathetic Gemini-powered conversational companion with:
- Deterministic emergency safety escalation (bypassing the LLM)
- Multi-turn conversation formatting
- Privacy-safe, zero-persistence logging
- Safe, non-blocking configuration and initialization
"""

from backend.services.voice_assistant.config import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    VoiceAssistantConfig,
    detect_language,
    get_voice_assistant_config,
)
from backend.services.voice_assistant.gemini_service import (
    FALLBACK_SUPPORT_MESSAGE,
    FALLBACK_SUPPORT_MESSAGES,
    GeminiCredentialsMissingError,
    GeminiProviderError,
    GeminiServiceError,
    GeminiVoiceAssistantService,
    VoiceAssistantResponse,
)
from backend.services.voice_assistant.safety_guard import (
    EMERGENCY_RESPONSE_IMMEDIATE_DANGER,
    EMERGENCY_RESPONSE_INFANT_HARM,
    EMERGENCY_RESPONSE_SELF_HARM,
    EMERGENCY_RESPONSES_BY_LANGUAGE,
    SafetyCheckResult,
    SafetyGuard,
)

__all__ = [
    "DEFAULT_GEMINI_MODEL",
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "VoiceAssistantConfig",
    "detect_language",
    "get_voice_assistant_config",
    "GeminiVoiceAssistantService",
    "VoiceAssistantResponse",
    "SafetyGuard",
    "SafetyCheckResult",
    "GeminiServiceError",
    "GeminiCredentialsMissingError",
    "GeminiProviderError",
    "FALLBACK_SUPPORT_MESSAGE",
    "FALLBACK_SUPPORT_MESSAGES",
    "EMERGENCY_RESPONSE_SELF_HARM",
    "EMERGENCY_RESPONSE_INFANT_HARM",
    "EMERGENCY_RESPONSE_IMMEDIATE_DANGER",
    "EMERGENCY_RESPONSES_BY_LANGUAGE",
]

