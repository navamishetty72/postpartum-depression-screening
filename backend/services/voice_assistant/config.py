"""Configuration management for the Voice Assistant Gemini service.

Reads environment variables safely without breaking application startup
when API keys or configurations are missing.
"""

import os
from pathlib import Path
from typing import Optional

# Default verified model recommendation (configurable via GEMINI_MODEL)
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

# Relative path to default system prompt file
DEFAULT_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent / "system_prompt.txt"


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

