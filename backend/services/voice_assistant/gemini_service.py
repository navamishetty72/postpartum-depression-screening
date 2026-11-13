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
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    VoiceAssistantConfig,
    detect_language,
    get_voice_assistant_config,
)
from backend.services.voice_assistant.safety_guard import (
    SafetyCheckResult,
    SafetyGuard,
)

logger = logging.getLogger("ppd.voice_assistant")

FALLBACK_SUPPORT_MESSAGES: Dict[str, str] = {
    "en": (
        "I am having a brief connection issue right now, but please know you are not alone "
        "and you are doing a wonderful job. Take a slow, gentle breath, and please try talking with me again."
    ),
    "hi": (
        "मुझे अभी जुड़ने में थोड़ी समस्या आ रही है, लेकिन आप अकेली नहीं हैं और आप बहुत अच्छा कर रही हैं। "
        "एक शांत गहरी सांस लें, और कृपया मुझसे फिर से बात करने का प्रयास करें।"
    ),
    "kn": (
        "ಸಂಪರ್ಕದಲ್ಲಿ ಸಣ್ಣ ಸಮಸ್ಯೆಯಾಗಿದೆ, ಆದರೆ ನೀವು ಒಬ್ಬಂಟಿಯಲ್ಲ ಮತ್ತು ನೀವು ಅದ್ಭುತವಾಗಿ ತಾಯ್ತನ ನಿಭಾಯಿಸುತ್ತಿದ್ದೀರಿ. "
        "ನಿಧಾನವಾಗಿ ಉಸಿರಾಡಿ, ದಯವಿಟ್ಟು ನನ್ನೊಂದಿಗೆ ಮತ್ತೆ ಮಾತನಾಡಿ."
    ),
    "ta": (
        "இணைப்பில் ஒரு சிறிய சிக்கல் ஏற்பட்டுள்ளது, ஆனால் நீங்கள் தனியாக இல்லை, மிகச் சிறப்பாக செய்கிறீர்கள். "
        "மெதுவாக மூச்சை உள்ளிழுத்து, தயவுசெய்து என்னுடன் மீண்டும் பேசுங்கள்."
    ),
    "te": (
        "కనెక్షన్‌లో చిన్న సమస్య వచ్చింది, కానీ మీరు ఒంటరిగా లేరు, మీరు చాలా అద్భుతంగా చూసుకుంటున్నారు. "
        "ప్రశాంతంగా శ్వాస తీసుకోండి, దయచేసి నాతో మళ్ళీ మాట్లాడండి."
    ),
    "ml": (
        "കണക്ഷനിൽ ഒരു ചെറിയ തടസ്സം നേരിടുന്നു, എന്നാൽ നിങ്ങൾ തനിച്ചല്ലെന്ന് ഓർക്കുക. "
        "ദീർഘമായി ശ്വാസമെടുക്കൂ, ദയവായി എന്നോട് വീണ്ടും സംസാരിക്കൂ."
    ),
    "bn": (
        "সংযোগের সামান্য সমস্যা হচ্ছে, তবে জানবেন আপনি একা নন এবং আপনি খুব ভালো কাজ করছেন। "
        "একটি শান্ত দীর্ঘশ্বাস নিন এবং দয়া করে আমার সাথে আবার কথা বলুন।"
    ),
    "mr": (
        "संपर्कात थोडी अडचण येत आहे, पण तुम्ही एकट्या नाही आहात आणि तुम्ही खूप छान सांभाळत आहात. "
        "शांतपणे श्वास घ्या आणि कृपया माझ्याशी पुन्हा बोला."
    ),
}

FALLBACK_SUPPORT_MESSAGE = FALLBACK_SUPPORT_MESSAGES["en"]


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
    language: str = "en"
    language_name: str = "English"
    voice_locale: str = "en-IN"


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
        language: Optional[str] = None,
        raise_on_error: bool = False,
    ) -> VoiceAssistantResponse:
        """Generate an empathetic mother-support response or trigger emergency escalation.

        Supports multilingual conversations in English, Hindi, Kannada, Tamil,
        Telugu, Malayalam, Bengali, and Marathi, with automatic language detection,
        seamless mid-conversation language switching, and voice playback metadata.

        Args:
            user_message: Current message from the mother (from speech recognition or text).
            conversation_history: Optional list of previous turns formatted as
                [{"role": "user"|"model"|"assistant", "content": "..."}, ...].
            language: Optional explicit language code (e.g. 'hi', 'kn', 'ta', 'en').
                If None or omitted, automatically detected from user_message.
            raise_on_error: If True, raises GeminiServiceError on provider failures.
                If False, returns a compassionate fallback message in the detected language.

        Returns:
            VoiceAssistantResponse containing the generated or escalated text,
            detected language, and BCP-47 voice locale for audio playback.

        Raises:
            ValueError: If user_message is empty or whitespace.
            GeminiCredentialsMissingError: If API key is missing and raise_on_error=True.
            GeminiProviderError: If Gemini API fails and raise_on_error=True.
        """
        if not user_message or not user_message.strip():
            raise ValueError("user_message cannot be empty or whitespace.")

        clean_message = user_message.strip()
        history = conversation_history or []

        # Automatically detect or resolve the conversational language
        resolved_lang = (language or self.config.detect_language(clean_message)).lower().strip()
        if not self.config.is_language_supported(resolved_lang):
            resolved_lang = DEFAULT_LANGUAGE
        lang_info = SUPPORTED_LANGUAGES.get(resolved_lang, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])

        # ---------------------------------------------------------------------
        # 1. Deterministic Emergency Safety Guard Check (BYPASSES GEMINI)
        # ---------------------------------------------------------------------
        safety_result: SafetyCheckResult = self.safety_guard.evaluate(
            clean_message, language=resolved_lang
        )

        if not safety_result.is_safe:
            # Privacy-safe logging: log only category and matched rule names, NEVER patient narrative
            logger.warning(
                "Safety guard triggered: category=%s, matched_rules=%s, language=%s",
                safety_result.category,
                safety_result.matched_rules,
                resolved_lang,
            )
            fallback_for_lang = FALLBACK_SUPPORT_MESSAGES.get(resolved_lang, FALLBACK_SUPPORT_MESSAGE)
            return VoiceAssistantResponse(
                text=safety_result.emergency_response or fallback_for_lang,
                is_emergency=True,
                category=safety_result.category,
                is_fallback=False,
                source="safety_guard",
                model=None,
                language=resolved_lang,
                language_name=lang_info["name"],
                voice_locale=lang_info["locale"],
            )

        # ---------------------------------------------------------------------
        # 2. Build Gemini API Payload
        # ---------------------------------------------------------------------
        # Privacy-safe logging: log turn count, char length, and language, NEVER message contents
        logger.info(
            "Generating voice assistant response: history_turns=%d, input_chars=%d, language=%s, model=%s",
            len(history),
            len(clean_message),
            resolved_lang,
            self.config.model,
        )

        localized_fallback = FALLBACK_SUPPORT_MESSAGES.get(
            resolved_lang, FALLBACK_SUPPORT_MESSAGE
        )

        try:
            client = self._get_client()
        except GeminiCredentialsMissingError as exc:
            logger.error("Voice assistant cannot invoke Gemini: API credentials missing.")
            if raise_on_error:
                raise
            return VoiceAssistantResponse(
                text=localized_fallback,
                is_emergency=False,
                is_fallback=True,
                source="fallback",
                model=self.config.model,
                language=resolved_lang,
                language_name=lang_info["name"],
                voice_locale=lang_info["locale"],
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
                response_text = localized_fallback

            # Verify response language or align with detected conversation language
            resp_lang = self.config.detect_language(response_text)
            final_lang = resolved_lang if resolved_lang != DEFAULT_LANGUAGE else resp_lang
            final_lang_info = SUPPORTED_LANGUAGES.get(final_lang, lang_info)

            # Privacy-safe log: log response length only
            logger.info(
                "Voice assistant response generated successfully: response_chars=%d, language=%s, model=%s",
                len(response_text),
                final_lang,
                self.config.model,
            )

            return VoiceAssistantResponse(
                text=response_text,
                is_emergency=False,
                category=None,
                is_fallback=False,
                source="gemini",
                model=self.config.model,
                language=final_lang,
                language_name=final_lang_info["name"],
                voice_locale=final_lang_info["locale"],
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
                text=localized_fallback,
                is_emergency=False,
                category=None,
                is_fallback=True,
                source="fallback",
                model=self.config.model,
                language=resolved_lang,
                language_name=lang_info["name"],
                voice_locale=lang_info["locale"],
            )

    def process_speech_recognition(
        self,
        transcript: str,
        language_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process speech recognition transcript and resolve speech recognition / TTS voice locale.

        Args:
            transcript: Raw text output from microphone speech recognition.
            language_hint: Optional language code hint from speech recognizer (e.g. 'hi-IN' or 'hi').

        Returns:
            Dict containing:
            - 'transcript': Cleaned transcript string
            - 'language': Detected/resolved ISO language code (e.g. 'hi', 'kn', 'en')
            - 'language_name': Display name (e.g. 'Hindi', 'Kannada', 'English')
            - 'native_name': Native language name (e.g. 'हिन्दी', 'ಕನ್ನಡ')
            - 'voice_locale': BCP-47 locale tag for TTS voice playback (e.g. 'hi-IN')
            - 'is_supported': Whether language is within the 8 supported languages
        """
        clean = (transcript or "").strip()
        if not clean:
            lang = DEFAULT_LANGUAGE
        elif language_hint and language_hint.strip():
            norm_hint = language_hint.strip().split("-")[0].lower()
            lang = norm_hint if self.config.is_language_supported(norm_hint) else self.config.detect_language(clean)
        else:
            lang = self.config.detect_language(clean)

        lang_info = SUPPORTED_LANGUAGES.get(lang, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])
        return {
            "transcript": clean,
            "language": lang,
            "language_name": lang_info["name"],
            "native_name": lang_info["native_name"],
            "voice_locale": lang_info["locale"],
            "is_supported": self.config.is_language_supported(lang),
        }

