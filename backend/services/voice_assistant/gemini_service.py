"""Empathetic postpartum mother-support LLM service powered by Gemini.

Uses the official google-genai SDK with lazy initialization, strict emergency bypass,
conversation history formatting, and privacy-safe zero-message logging.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from backend.services.voice_assistant.config import (
    VoiceAssistantConfig,
    get_voice_assistant_config,
)
from backend.services.voice_assistant.safety_guard import (
    SafetyCheckResult,
    SafetyGuard,
)

logger = logging.getLogger("ppd.voice_assistant")

FALLBACK_SUPPORT_MESSAGE = (
    "I am having a brief connection issue right now, but please know you are not alone "
    "and you are doing a wonderful job. Take a slow, gentle breath, and please try talking with me again."
)


class GeminiServiceError(Exception):
    """Base exception for voice assistant service errors."""


class GeminiCredentialsMissingError(GeminiServiceError):
    """Raised when an operation requiring the Gemini API is called without credentials."""


class GeminiProviderError(GeminiServiceError):
    """Raised when the upstream Gemini API returns an unrecoverable error."""


@dataclass
class VoiceAssistantResponse:
    """Structured response from the Voice Assistant."""

    text: str
    is_emergency: bool = False
    category: Optional[str] = None
    is_fallback: bool = False
    source: str = "gemini"  # "gemini" | "safety_guard" | "fallback"
    model: Optional[str] = None


class GeminiVoiceAssistantService:
    """Provides empathetic mother-support responses using the Gemini model.

    Features:
    - Lazy client initialization: No network calls or crashes during backend startup.
    - Deterministic emergency bypass: Acute crises immediately return vetted safety hotlines.
    - Multi-turn support: Formats caller-provided conversation history.
    - Zero data persistence: Neither conversations nor raw transcripts are saved or logged.
    """

    def __init__(
        self,
        config: Optional[VoiceAssistantConfig] = None,
        safety_guard: Optional[SafetyGuard] = None,
        client: Optional[Any] = None,
    ) -> None:
        """Initialize service dependencies without making external network calls.

        Args:
            config: Optional configuration instance. Defaults to get_voice_assistant_config().
            safety_guard: Optional safety guard. Defaults to SafetyGuard().
            client: Optional pre-configured genai.Client instance (useful for testing).
        """
        self.config: VoiceAssistantConfig = config or get_voice_assistant_config()
        self.safety_guard: SafetyGuard = safety_guard or SafetyGuard()
        self._client: Optional[Any] = client

    def _get_client(self) -> Any:
        """Lazily initialize the google-genai Client on first demand.

        Raises:
            GeminiCredentialsMissingError: If GEMINI_API_KEY is not configured.
        """
        if self._client is not None:
            return self._client

        if not self.config.is_configured:
            raise GeminiCredentialsMissingError(
                "Gemini API key is missing. Set GEMINI_API_KEY in the environment or configuration."
            )

        self._client = genai.Client(api_key=self.config.api_key)
        return self._client

    def generate_response(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        raise_on_error: bool = False,
    ) -> VoiceAssistantResponse:
        """Generate an empathetic mother-support response or trigger emergency escalation.

        Args:
            user_message: Current message from the mother.
            conversation_history: Optional list of previous turns formatted as
                [{"role": "user"|"model"|"assistant", "content": "..."}, ...].
            raise_on_error: If True, raises GeminiServiceError on provider failures.
                If False, returns a compassionate fallback message.

        Returns:
            VoiceAssistantResponse containing the generated or escalated text.

        Raises:
            ValueError: If user_message is empty or whitespace.
            GeminiCredentialsMissingError: If API key is missing and raise_on_error=True.
            GeminiProviderError: If Gemini API fails and raise_on_error=True.
        """
        if not user_message or not user_message.strip():
            raise ValueError("user_message cannot be empty or whitespace.")

        clean_message = user_message.strip()
        history = conversation_history or []

        # ---------------------------------------------------------------------
        # 1. Deterministic Emergency Safety Guard Check (BYPASSES GEMINI)
        # ---------------------------------------------------------------------
        safety_result: SafetyCheckResult = self.safety_guard.evaluate(clean_message)

        if not safety_result.is_safe:
            # Privacy-safe logging: log only category and matched rule names, NEVER patient narrative
            logger.warning(
                "Safety guard triggered: category=%s, matched_rules=%s",
                safety_result.category,
                safety_result.matched_rules,
            )
            return VoiceAssistantResponse(
                text=safety_result.emergency_response or FALLBACK_SUPPORT_MESSAGE,
                is_emergency=True,
                category=safety_result.category,
                is_fallback=False,
                source="safety_guard",
                model=None,
            )

        # ---------------------------------------------------------------------
        # 2. Build Gemini API Payload
        # ---------------------------------------------------------------------
        # Privacy-safe logging: log turn count and char length, NEVER message contents
        logger.info(
            "Generating voice assistant response: history_turns=%d, input_chars=%d, model=%s",
            len(history),
            len(clean_message),
            self.config.model,
        )

        try:
            client = self._get_client()
        except GeminiCredentialsMissingError as exc:
            logger.error("Voice assistant cannot invoke Gemini: API credentials missing.")
            if raise_on_error:
                raise
            return VoiceAssistantResponse(
                text=FALLBACK_SUPPORT_MESSAGE,
                is_emergency=False,
                is_fallback=True,
                source="fallback",
                model=self.config.model,
            )

        # Map conversation history into google-genai Content structures
        contents: List[types.Content] = []
        for turn in history:
            role_raw = turn.get("role", "user").lower()
            role = "model" if role_raw in ("assistant", "model") else "user"
            turn_content = turn.get("content", "").strip()
            if turn_content:
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=turn_content)],
                    )
                )

        # Append current user prompt
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=clean_message)],
            )
        )

        generate_config = types.GenerateContentConfig(
            system_instruction=self.config.get_system_prompt(),
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_output_tokens,
        )

        # ---------------------------------------------------------------------
        # 3. Remote LLM Invocation
        # ---------------------------------------------------------------------
        try:
            response = client.models.generate_content(
                model=self.config.model,
                contents=contents,
                config=generate_config,
            )

            response_text = ""
            if hasattr(response, "text") and response.text:
                response_text = response.text.strip()
            elif hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "content") and candidate.content:
                    parts = candidate.content.parts or []
                    response_text = "".join(
                        p.text for p in parts if hasattr(p, "text") and p.text
                    ).strip()

            if not response_text:
                response_text = FALLBACK_SUPPORT_MESSAGE

            # Privacy-safe log: log response length only
            logger.info(
                "Voice assistant response generated successfully: response_chars=%d, model=%s",
                len(response_text),
                self.config.model,
            )

            return VoiceAssistantResponse(
                text=response_text,
                is_emergency=False,
                category=None,
                is_fallback=False,
                source="gemini",
                model=self.config.model,
            )

        except Exception as exc:
            # Privacy-safe log: log exception class only, NEVER user prompt
            logger.error(
                "Voice assistant provider failure encountered: error_type=%s",
                type(exc).__name__,
            )
            if raise_on_error:
                raise GeminiProviderError(
                    f"Gemini generation failed: {type(exc).__name__}"
                ) from exc

            return VoiceAssistantResponse(
                text=FALLBACK_SUPPORT_MESSAGE,
                is_emergency=False,
                category=None,
                is_fallback=True,
                source="fallback",
                model=self.config.model,
            )

