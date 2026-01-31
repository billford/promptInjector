"""Pytest configuration and fixtures."""

import sys
from unittest.mock import MagicMock

# Mock google.generativeai before importing promptinjector modules
# This is needed because the google-generativeai package has import issues
# in some environments
if 'google' not in sys.modules:
    sys.modules['google'] = MagicMock()
if 'google.generativeai' not in sys.modules:
    sys.modules['google.generativeai'] = MagicMock()
