"""Base class for LLM targets."""

from abc import ABC, abstractmethod
from typing import Any


class BaseTarget(ABC):
    """Abstract base class for LLM testing targets."""

    def __init__(self, name: str = "unnamed"):
        self.name = name
        self._configured = False

    @property
    @abstractmethod
    def target_type(self) -> str:
        """Return the type identifier for this target."""

    @abstractmethod
    async def send_message(self, message: str) -> str:
        """
        Send a message to the target and return the response.

        Args:
            message: The prompt/message to send to the target.

        Returns:
            The response text from the target.

        Raises:
            TargetError: If communication with the target fails.
        """

    @abstractmethod
    async def reset_conversation(self) -> None:
        """Reset the conversation state if applicable."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the target is properly configured."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self) -> None:
        """Clean up resources."""

    def get_info(self) -> dict[str, Any]:
        """Return information about this target."""
        return {
            "name": self.name,
            "type": self.target_type,
            "configured": self.is_configured(),
        }


class TargetError(Exception):
    """Exception raised when target communication fails."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error
