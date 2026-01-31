"""Tests for the injection library."""

import sys
from unittest.mock import MagicMock

import pytest

# Mock google.generativeai before importing promptinjector modules
sys.modules['google'] = MagicMock()
sys.modules['google.generativeai'] = MagicMock()

from promptinjector.injections import InjectionLibrary, InjectionCategory
from promptinjector.core.models import Severity


class TestInjectionLibrary:
    """Test cases for InjectionLibrary."""

    def test_load_library(self):
        """Test that library loads successfully."""
        library = InjectionLibrary()
        library.load()
        assert library.count > 0

    def test_get_categories(self):
        """Test getting available categories."""
        library = InjectionLibrary()
        library.load()
        categories = library.get_categories()
        assert len(categories) > 0
        assert "system_prompt_extraction" in categories

    def test_get_by_category(self):
        """Test filtering by category."""
        library = InjectionLibrary()
        library.load()
        tests = library.get_by_category("system_prompt_extraction")
        assert len(tests) > 0
        for test in tests:
            assert test.category == "system_prompt_extraction"

    def test_get_by_severity(self):
        """Test filtering by severity."""
        library = InjectionLibrary()
        library.load()
        tests = library.get_by_severity(Severity.CRITICAL)
        assert len(tests) > 0
        for test in tests:
            assert test.severity == Severity.CRITICAL

    def test_get_by_id(self):
        """Test getting specific test by ID."""
        library = InjectionLibrary()
        library.load()
        test = library.get_by_id("spe-001")
        assert test is not None
        assert test.id == "spe-001"

    def test_add_custom_payload(self):
        """Test adding custom payloads."""
        library = InjectionLibrary()
        library.load()
        initial_count = library.count

        test = library.add_custom_payload(
            test_id="custom-test-001",
            name="Custom Test",
            payload="Test payload",
            category="custom",
        )

        assert library.count == initial_count + 1
        assert library.get_by_id("custom-test-001") == test

    def test_payload_structure(self):
        """Test that all payloads have required fields."""
        library = InjectionLibrary()
        library.load()

        for test_case in library.get_all():
            assert test_case.id, "Test case must have an ID"
            assert test_case.name, "Test case must have a name"
            assert test_case.payload, "Test case must have a payload"
            assert test_case.category, "Test case must have a category"
            assert isinstance(test_case.severity, Severity)
