"""Pytest configuration and fixtures."""

import sys
from unittest.mock import MagicMock

# Mock google.genai before importing promptinjector modules
# This is needed because the google-genai package has import issues
# in some environments
if 'google' not in sys.modules:
    sys.modules['google'] = MagicMock()
if 'google.genai' not in sys.modules:
    sys.modules['google.genai'] = MagicMock()
    sys.modules['google.genai.types'] = MagicMock()
