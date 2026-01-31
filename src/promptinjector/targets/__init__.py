"""Target implementations for different LLM platforms."""

from .base import BaseTarget
from .openai_gpt import OpenAIGPTTarget
from .google_gem import GoogleGemTarget

__all__ = ["BaseTarget", "OpenAIGPTTarget", "GoogleGemTarget"]
