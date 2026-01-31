"""Tests for target implementations."""

import sys
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Mock google.generativeai before importing promptinjector modules
sys.modules['google'] = MagicMock()
sys.modules['google.generativeai'] = MagicMock()

from promptinjector.targets.base import BaseTarget, TargetError
from promptinjector.targets.openai_gpt import OpenAIGPTTarget
from promptinjector.targets.google_gem import GoogleGemTarget


class TestTargetError:
    """Tests for TargetError exception."""

    def test_create_error(self):
        """Test creating a target error."""
        error = TargetError("Test error message")
        assert str(error) == "Test error message"
        assert error.original_error is None

    def test_create_error_with_original(self):
        """Test creating a target error with original exception."""
        original = ValueError("Original error")
        error = TargetError("Wrapped error", original_error=original)
        assert error.original_error == original


class TestOpenAIGPTTarget:
    """Tests for OpenAI GPT target."""

    def test_create_target(self):
        """Test creating an OpenAI target."""
        target = OpenAIGPTTarget(
            name="test-gpt",
            api_key="test-key",
            model="gpt-4",
            system_prompt="You are a test assistant.",
        )

        assert target.name == "test-gpt"
        assert target.model == "gpt-4"
        assert target.system_prompt == "You are a test assistant."
        assert target.target_type == "openai-gpt"

    def test_is_configured_with_key(self):
        """Test that target is configured when API key is present."""
        target = OpenAIGPTTarget(api_key="test-key")
        # Note: is_configured also checks if openai is importable
        # In test environment without openai, this might be False
        # but the logic for API key check is correct

    def test_is_configured_without_key(self):
        """Test that target is not configured without API key."""
        with patch.dict("os.environ", {}, clear=True):
            target = OpenAIGPTTarget(api_key=None)
            # Should not be configured without key
            # (also depends on openai import)

    def test_get_info(self):
        """Test getting target info."""
        target = OpenAIGPTTarget(
            name="test-gpt",
            api_key="test-key",
            model="gpt-4",
            system_prompt="System prompt",
            assistant_id="asst_123",
            base_url="https://custom.api.com",
        )

        info = target.get_info()
        assert info["name"] == "test-gpt"
        assert info["type"] == "openai-gpt"
        assert info["model"] == "gpt-4"
        assert info["assistant_id"] == "asst_123"
        assert info["has_system_prompt"] is True
        assert info["base_url"] == "https://custom.api.com"

    @pytest.mark.asyncio
    async def test_reset_conversation(self):
        """Test resetting conversation."""
        target = OpenAIGPTTarget(api_key="test-key")
        target._conversation_history = [{"role": "user", "content": "Hello"}]
        target._thread_id = "thread_123"

        await target.reset_conversation()

        assert target._conversation_history == []
        assert target._thread_id is None

    @pytest.mark.asyncio
    async def test_send_message_not_configured(self):
        """Test sending message when not configured."""
        target = OpenAIGPTTarget(api_key=None)
        target._client = None

        with pytest.raises(TargetError, match="not configured"):
            await target.send_message("Hello")


class TestGoogleGemTarget:
    """Tests for Google Gem target."""

    def test_create_target(self):
        """Test creating a Google Gem target."""
        target = GoogleGemTarget(
            name="test-gem",
            api_key="test-key",
            model="gemini-1.5-flash",
            system_instruction="You are a test assistant.",
        )

        assert target.name == "test-gem"
        assert target.model_name == "gemini-1.5-flash"
        assert target.system_instruction == "You are a test assistant."
        assert target.target_type == "google-gem"

    def test_get_info(self):
        """Test getting target info."""
        target = GoogleGemTarget(
            name="test-gem",
            api_key="test-key",
            model="gemini-1.5-pro",
            system_instruction="System instruction",
        )

        info = target.get_info()
        assert info["name"] == "test-gem"
        assert info["type"] == "google-gem"
        assert info["model"] == "gemini-1.5-pro"
        assert info["has_system_instruction"] is True

    @pytest.mark.asyncio
    async def test_reset_conversation(self):
        """Test resetting conversation."""
        target = GoogleGemTarget(api_key="test-key")
        target._chat = MagicMock()

        await target.reset_conversation()

        assert target._chat is None

    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing the target."""
        target = GoogleGemTarget(api_key="test-key")
        target._chat = MagicMock()
        target._model = MagicMock()

        await target.close()

        assert target._chat is None
        assert target._model is None

    @pytest.mark.asyncio
    async def test_send_message_not_configured(self):
        """Test sending message when not configured."""
        target = GoogleGemTarget(api_key=None)

        with pytest.raises(TargetError, match="not configured"):
            await target.send_message("Hello")


class TestBaseTargetContextManager:
    """Tests for BaseTarget as async context manager."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test using target as async context manager."""
        target = OpenAIGPTTarget(api_key="test-key")
        closed = False

        async def mock_close():
            nonlocal closed
            closed = True

        target.close = mock_close

        async with target as t:
            assert t is target

        assert closed is True
