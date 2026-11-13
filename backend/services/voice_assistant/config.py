"""Configuration management for the Voice Assistant Gemini service.

Reads environment variables safely without breaking application startup
when API keys or configurations are missing.
"""

import os
from pathlib import Path
import re
from typing import Any, Dict, Optional

# Default verified model recommendation (configurable via GEMINI_MODEL)
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

# Relative path to default system prompt file
DEFAULT_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent / "system_prompt.txt"

# Default fallback language
DEFAULT_LANGUAGE = "en"

# Supported languages with English names, native names, and speech recognition/TTS voice locales
SUPPORTED_LANGUAGES: Dict[str, Dict[str, str]] = {
    "en": {"name": "English", "native_name": "English", "locale": "en-IN"},
    "hi": {"name": "Hindi", "native_name": "हिन्दी", "locale": "hi-IN"},
    "kn": {"name": "Kannada", "native_name": "ಕನ್ನಡ", "locale": "kn-IN"},
    "ta": {"name": "Tamil", "native_name": "தமிழ்", "locale": "ta-IN"},
    "te": {"name": "Telugu", "native_name": "తెలుగు", "locale": "te-IN"},
    "ml": {"name": "Malayalam", "native_name": "മലയാളം", "locale": "ml-IN"},
    "bn": {"name": "Bengali", "native_name": "বাংলা", "locale": "bn-IN"},
    "mr": {"name": "Marathi", "native_name": "मराठी", "locale": "mr-IN"},
}


def detect_language(text: str) -> str:
    """Automatically detect the spoken or typed language from input text.

    Supports: English (en), Hindi (hi), Kannada (kn), Tamil (ta),
    Telugu (te), Malayalam (ml), Bengali (bn), and Marathi (mr).

    Uses Unicode character ranges and language-specific orthographic/vocabulary markers
    without requiring third-party machine learning dependencies.

    Args:
        text: Input string from speech recognition or user text input.

    Returns:
        ISO 639-1 language code of the detected supported language. Defaults to 'en'.
    """
    if not text or not text.strip():
        return DEFAULT_LANGUAGE

    clean = text.strip()

    # Script character distribution
    counts = {
        "kn": len(re.findall(r"[\u0C80-\u0CFF]", clean)),  # Kannada script
        "ta": len(re.findall(r"[\u0B80-\u0BFF]", clean)),  # Tamil script
        "te": len(re.findall(r"[\u0C00-\u0C7F]", clean)),  # Telugu script
        "ml": len(re.findall(r"[\u0D00-\u0D7F]", clean)),  # Malayalam script
        "bn": len(re.findall(r"[\u0980-\u09FF]", clean)),  # Bengali script
        "deva": len(re.findall(r"[\u0900-\u097F]", clean)),  # Devanagari (Hindi / Marathi)
        "en": len(re.findall(r"[a-zA-Z]", clean)),
    }

    # Identify primary non-Latin script
    indic_max = max(
        [
            ("kn", counts["kn"]),
            ("ta", counts["ta"]),
            ("te", counts["te"]),
            ("ml", counts["ml"]),
            ("bn", counts["bn"]),
            ("deva", counts["deva"]),
        ],
        key=lambda item: item[1],
    )

    if indic_max[1] > 0 and indic_max[1] >= counts["en"] * 0.2:
        if indic_max[0] == "deva":
            # Disambiguate Marathi vs Hindi using distinctive characters and vocabulary
            # \u0933 is Marathi letter LLA (ळ), \u0931 is Marathi letter RRA (ऱ)
            has_marathi_char = bool(re.search(r"[\u0933\u0931]", clean))
            tokens = set(re.findall(r"[\u0900-\u097F]+", clean))
            marathi_vocab = {
                "आहे", "आहेत", "नाही", "मला", "मी", "तुला", "आम्ही", "तुम्ही",
                "काय", "कसं", "कसा", "कशी", "बाळ", "बाळाची", "बाळाला", "खूप",
                "वाटतं", "वाटते", "होतो", "होते", "झाले", "झाला", "झाली", "त्रास",
                "झोप", "काळजी", "सांगा", "बरं", "विचार", "शकत", "करावीशी", "करावे",
                "करावा", "आलो", "आले", "आली",
            }
            hindi_vocab = {
                "है", "हैं", "हूँ", "नहीं", "मुझे", "तुम्हें", "हम", "आप",
                "क्या", "कैसे", "कैसा", "कैसी", "बच्चा", "बच्चे", "बहुत",
                "लगता", "लगती", "लगते", "था", "थे", "थी", "हुआ", "हुई", "हुए",
                "परेशानी", "नींद", "चिंता", "बताओ", "अच्छा", "लग", "रहा", "रही", "रहे",
            }
            marathi_score = len(tokens & marathi_vocab)
            hindi_score = len(tokens & hindi_vocab)
            if has_marathi_char or marathi_score > hindi_score:
                return "mr"
            return "hi"
        return indic_max[0]

    # For Latin script inputs: check for common transliterated markers (Hinglish / regional romanization)
    lower = clean.lower()
    if re.search(r"\b(?:mujhe|mera|meri|hum|nahi|bahut|kya|kaise|thakan|neend|chinta|baccha|bacche|madad|pareshan)\b", lower):
        return "hi"
    if re.search(r"\b(?:nange|nanage|tumba|beku|agide|illa|kannada|magu|nidde|bhaya|sahaya|hege)\b", lower):
        return "kn"
    if re.search(r"\b(?:enakku|romba|illa|irukku|kuzhandhai|thookam|bayam|udhavi|eppadi)\b", lower):
        return "ta"
    if re.search(r"\b(?:naaku|chala|ledu|undhi|bidda|nidra|bhayam|sahayam|ela)\b", lower):
        return "te"
    if re.search(r"\b(?:enikku|valare|illa|undu|kunju|urakkam|pedi|sahayam|enganey)\b", lower):
        return "ml"
    if re.search(r"\b(?:aamar|khub|na|ache|baccha|ghum|bhoy|sahajjo|kemon)\b", lower):
        return "bn"
    if re.search(r"\b(?:mala|khup|nahi|ahe|baal|zhop|kalji|madat|kasa|kashi)\b", lower):
        return "mr"

    return DEFAULT_LANGUAGE


class VoiceAssistantConfig:
    """Encapsulates runtime configuration for the Gemini mother-support assistant."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        system_prompt_path: Optional[Path] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 300,
    ) -> None:
        """Initialize configuration from parameters or environment variables.

        Args:
            api_key: Optional Gemini API key. Defaults to GEMINI_API_KEY env var.
            model: Optional Gemini model identifier. Defaults to GEMINI_MODEL env var or gemini-3.8-flash.
            system_prompt_path: Optional path to system prompt file.
            temperature: Sampling temperature for empathetic tone balance.
            max_output_tokens: Token budget keeping voice playback responses concise.
        """
        env_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.api_key: Optional[str] = (
            api_key.strip() if api_key and api_key.strip() else (env_key or None)
        )
        self.model: str = (
            (model.strip() if model and model.strip() else None)
            or os.getenv("GEMINI_MODEL", "").strip()
            or DEFAULT_GEMINI_MODEL
        )
        self.system_prompt_path: Path = system_prompt_path or DEFAULT_SYSTEM_PROMPT_PATH
        self.temperature: float = temperature
        self.max_output_tokens: int = max_output_tokens
        self._cached_prompt: Optional[str] = None

    @property
    def is_configured(self) -> bool:
        """Whether a valid Gemini API key is provided."""
        return bool(self.api_key and len(self.api_key) > 0)

    def get_system_prompt(self) -> str:
        """Load and cache the empathetic voice assistant system prompt.

        Returns:
            The raw system prompt text.

        Raises:
            FileNotFoundError: If the system prompt file cannot be located.
        """
        if self._cached_prompt is None:
            if not self.system_prompt_path.exists():
                raise FileNotFoundError(
                    f"Voice assistant system prompt file not found at: {self.system_prompt_path}"
                )
            self._cached_prompt = self.system_prompt_path.read_text(encoding="utf-8").strip()
        return self._cached_prompt

    def is_language_supported(self, lang_code: str) -> bool:
        """Check whether a language code is in the supported languages."""
        return (lang_code or "").lower().strip() in SUPPORTED_LANGUAGES

    def get_voice_locale(self, lang_code: str) -> str:
        """Get the BCP-47 speech recognition / TTS voice locale for a language code."""
        code = (lang_code or "").lower().strip()
        return SUPPORTED_LANGUAGES.get(code, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])["locale"]

    def get_language_name(self, lang_code: str) -> str:
        """Get the English display name of a supported language."""
        code = (lang_code or "").lower().strip()
        return SUPPORTED_LANGUAGES.get(code, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])["name"]

    def detect_language(self, text: str) -> str:
        """Detect the language code of the provided text."""
        return detect_language(text)

    def __repr__(self) -> str:
        """Safe representation ensuring API credentials are never logged."""
        key_status = "configured" if self.is_configured else "missing"
        return (
            f"VoiceAssistantConfig(model='{self.model}', "
            f"api_key=[{key_status}], "
            f"max_output_tokens={self.max_output_tokens})"
        )


def get_voice_assistant_config() -> VoiceAssistantConfig:
    """Factory function returning a freshly evaluated VoiceAssistantConfig instance."""
    return VoiceAssistantConfig()

