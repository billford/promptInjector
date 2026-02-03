"""Google Gemini/Gems target implementation."""

import os
from typing import Any

from .base import BaseTarget, TargetError

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


class GoogleGemTarget(BaseTarget):
    """Target for testing Google Gemini models and custom Gems."""

    def __init__(
        self,
        name: str = "google-gem",
        api_key: str | None = None,
        model: str = "gemini-2.0-flash",
        system_instruction: str | None = None,
    ):
        """
        Initialize a Google Gemini/Gem target.

        Args:
            name: Friendly name for this target.
            api_key: Google AI API key. Falls back to GEMINI_API_KEY or GOOGLE_API_KEY env var.
            model: Model to use (default: gemini-2.0-flash).
            system_instruction: System instruction to simulate a custom Gem.
        """
        super().__init__(name)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = model
        self.system_instruction = system_instruction

        self._client = None
        self._chat = None

    @property
    def target_type(self) -> str:
        return "google-gem"

    def is_configured(self) -> bool:
        return self.api_key is not None and genai is not None

    def _get_client(self):
        if self._client is None:
            if genai is None:
                raise TargetError(
                    "google-genai package not installed. "
                    "Run: pip install google-genai"
                )
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _get_config(self):
        """Get GenerateContentConfig with system instruction if set."""
        if self.system_instruction:
            return types.GenerateContentConfig(system_instruction=self.system_instruction)
        return None

    def _get_chat(self):
        if self._chat is None:
            client = self._get_client()
            config = self._get_config()
            self._chat = client.chats.create(model=self.model_name, config=config)
        return self._chat

    async def send_message(self, message: str) -> str:
        """Send a message to the Gemini model."""
        if not self.is_configured():
            raise TargetError("Google target not configured. Set GEMINI_API_KEY.")

        try:
            chat = self._get_chat()
            response = chat.send_message(message)
            return response.text

        except Exception as e:
            raise TargetError(f"Google AI API error: {e}", original_error=e) from e

    async def send_single_message(self, message: str) -> str:
        """Send a single message without chat history."""
        if not self.is_configured():
            raise TargetError("Google target not configured. Set GEMINI_API_KEY.")

        try:
            client = self._get_client()
            config = self._get_config()
            response = client.models.generate_content(
                model=self.model_name, contents=message, config=config
            )
            return response.text

        except Exception as e:
            raise TargetError(f"Google AI API error: {e}", original_error=e) from e

    async def reset_conversation(self) -> None:
        """Reset the chat session."""
        self._chat = None

    async def close(self) -> None:
        """Clean up resources."""
        self._chat = None
        self._client = None

    def get_info(self) -> dict[str, Any]:
        info = super().get_info()
        info.update(
            {
                "model": self.model_name,
                "has_system_instruction": self.system_instruction is not None,
            }
        )
        return info
