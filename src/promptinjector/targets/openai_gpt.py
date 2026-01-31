"""OpenAI GPT target implementation for testing custom GPTs."""

import os
from typing import Any

from .base import BaseTarget, TargetError

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None


class OpenAIGPTTarget(BaseTarget):
    """Target for testing OpenAI custom GPTs and assistants."""

    def __init__(
        self,
        name: str = "openai-gpt",
        api_key: str | None = None,
        model: str = "gpt-4",
        assistant_id: str | None = None,
        system_prompt: str | None = None,
        base_url: str | None = None,
    ):
        """
        Initialize an OpenAI GPT target.

        Args:
            name: Friendly name for this target.
            api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
            model: Model to use (default: gpt-4).
            assistant_id: Optional Assistant ID for testing Assistants API.
            system_prompt: System prompt to simulate a custom GPT's instructions.
            base_url: Optional custom base URL for API-compatible endpoints.
        """
        super().__init__(name)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.assistant_id = assistant_id
        self.system_prompt = system_prompt
        self.base_url = base_url

        self._client: AsyncOpenAI | None = None
        self._conversation_history: list[dict[str, str]] = []
        self._thread_id: str | None = None

    @property
    def target_type(self) -> str:
        return "openai-gpt"

    def is_configured(self) -> bool:
        return self.api_key is not None and AsyncOpenAI is not None

    async def _get_client(self) -> "AsyncOpenAI":
        if self._client is None:
            if AsyncOpenAI is None:
                raise TargetError("openai package not installed. Run: pip install openai")
            kwargs: dict[str, Any] = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    async def send_message(self, message: str) -> str:
        """Send a message using the Chat Completions API."""
        if not self.is_configured():
            raise TargetError("OpenAI target not configured. Set OPENAI_API_KEY.")

        client = await self._get_client()

        # Build messages list
        messages: list[dict[str, str]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.extend(self._conversation_history)
        messages.append({"role": "user", "content": message})

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
            )
            assistant_message = response.choices[0].message.content or ""

            # Store in history for multi-turn attacks
            self._conversation_history.append({"role": "user", "content": message})
            self._conversation_history.append({"role": "assistant", "content": assistant_message})

            return assistant_message

        except Exception as e:
            raise TargetError(f"OpenAI API error: {e}", original_error=e)

    async def send_message_assistant(self, message: str) -> str:
        """Send a message using the Assistants API (for testing real Assistants)."""
        if not self.assistant_id:
            raise TargetError("No assistant_id configured for Assistants API")

        client = await self._get_client()

        try:
            # Create thread if needed
            if self._thread_id is None:
                thread = await client.beta.threads.create()
                self._thread_id = thread.id

            # Add message to thread
            await client.beta.threads.messages.create(
                thread_id=self._thread_id,
                role="user",
                content=message,
            )

            # Run the assistant
            run = await client.beta.threads.runs.create_and_poll(
                thread_id=self._thread_id,
                assistant_id=self.assistant_id,
            )

            if run.status != "completed":
                raise TargetError(f"Assistant run failed with status: {run.status}")

            # Get the response
            messages = await client.beta.threads.messages.list(
                thread_id=self._thread_id,
                order="desc",
                limit=1,
            )

            if messages.data:
                content = messages.data[0].content
                if content and hasattr(content[0], "text"):
                    return content[0].text.value

            return ""

        except TargetError:
            raise
        except Exception as e:
            raise TargetError(f"Assistants API error: {e}", original_error=e)

    async def reset_conversation(self) -> None:
        """Reset conversation history and thread."""
        self._conversation_history = []
        self._thread_id = None

    async def close(self) -> None:
        """Close the client."""
        if self._client:
            await self._client.close()
            self._client = None

    def get_info(self) -> dict[str, Any]:
        info = super().get_info()
        info.update(
            {
                "model": self.model,
                "assistant_id": self.assistant_id,
                "has_system_prompt": self.system_prompt is not None,
                "base_url": self.base_url,
            }
        )
        return info
