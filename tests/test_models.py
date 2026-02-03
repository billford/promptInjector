"""Tests for data models."""

import sys
import pytest
from datetime import datetime
from unittest.mock import MagicMock

# Mock google.genai before importing promptinjector modules
sys.modules['google'] = MagicMock()
sys.modules['google.genai'] = MagicMock()
sys.modules['google.genai.types'] = MagicMock()

from promptinjector.core.models import (
    Severity,
    TestStatus,
    TestCase,
    TestResult,
    TestSuite,
)


class TestSeverity:
    """Tests for Severity enum."""

    def test_severity_values(self):
        """Test that all severity values are defined."""
        assert Severity.INFO.value == "info"
        assert Severity.LOW.value == "low"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.HIGH.value == "high"
        assert Severity.CRITICAL.value == "critical"

    def test_severity_from_string(self):
        """Test creating severity from string value."""
        assert Severity("info") == Severity.INFO
        assert Severity("critical") == Severity.CRITICAL


class TestTestStatus:
    """Tests for TestStatus enum."""

    def test_status_values(self):
        """Test that all status values are defined."""
        assert TestStatus.PENDING.value == "pending"
        assert TestStatus.RUNNING.value == "running"
        assert TestStatus.PASSED.value == "passed"
        assert TestStatus.FAILED.value == "failed"
        assert TestStatus.VULNERABLE.value == "vulnerable"
        assert TestStatus.ERROR.value == "error"
        assert TestStatus.SKIPPED.value == "skipped"


class TestTestCase:
    """Tests for TestCase dataclass."""

    def test_create_test_case(self):
        """Test creating a test case."""
        test = TestCase(
            id="test-001",
            name="Test Case",
            category="test_category",
            payload="Test payload",
        )
        assert test.id == "test-001"
        assert test.name == "Test Case"
        assert test.category == "test_category"
        assert test.payload == "Test payload"
        assert test.severity == Severity.MEDIUM  # default
        assert test.detection_patterns == []
        assert test.tags == []

    def test_create_test_case_with_all_fields(self):
        """Test creating a test case with all fields."""
        test = TestCase(
            id="test-002",
            name="Full Test Case",
            category="security",
            payload="Injection payload",
            description="Test description",
            severity=Severity.HIGH,
            detection_patterns=["pattern1", "pattern2"],
            tags=["tag1", "tag2"],
        )
        assert test.description == "Test description"
        assert test.severity == Severity.HIGH
        assert len(test.detection_patterns) == 2
        assert len(test.tags) == 2

    def test_severity_string_conversion(self):
        """Test that string severity is converted to enum."""
        test = TestCase(
            id="test-003",
            name="Test",
            category="test",
            payload="payload",
            severity="high",  # type: ignore
        )
        assert test.severity == Severity.HIGH


class TestTestResult:
    """Tests for TestResult dataclass."""

    @pytest.fixture
    def sample_test_case(self):
        """Create a sample test case."""
        return TestCase(
            id="test-001",
            name="Sample Test",
            category="sample",
            payload="Test payload",
        )

    def test_create_test_result(self, sample_test_case):
        """Test creating a test result."""
        result = TestResult(
            test_case=sample_test_case,
            status=TestStatus.PASSED,
        )
        assert result.test_case == sample_test_case
        assert result.status == TestStatus.PASSED
        assert result.is_vulnerable is False
        assert result.confidence == 0.0

    def test_create_vulnerable_result(self, sample_test_case):
        """Test creating a vulnerable result."""
        result = TestResult(
            test_case=sample_test_case,
            status=TestStatus.VULNERABLE,
            response="Leaked system prompt",
            is_vulnerable=True,
            confidence=0.85,
            matched_patterns=["system prompt"],
        )
        assert result.is_vulnerable is True
        assert result.confidence == 0.85
        assert len(result.matched_patterns) == 1

    def test_status_string_conversion(self, sample_test_case):
        """Test that string status is converted to enum."""
        result = TestResult(
            test_case=sample_test_case,
            status="passed",  # type: ignore
        )
        assert result.status == TestStatus.PASSED


class TestTestSuite:
    """Tests for TestSuite dataclass."""

    @pytest.fixture
    def sample_results(self):
        """Create sample test results."""
        test1 = TestCase(
            id="test-001",
            name="Test 1",
            category="cat1",
            payload="payload1",
            severity=Severity.HIGH,
        )
        test2 = TestCase(
            id="test-002",
            name="Test 2",
            category="cat2",
            payload="payload2",
            severity=Severity.MEDIUM,
        )
        test3 = TestCase(
            id="test-003",
            name="Test 3",
            category="cat1",
            payload="payload3",
            severity=Severity.HIGH,
        )

        return [
            TestResult(test_case=test1, status=TestStatus.PASSED),
            TestResult(
                test_case=test2,
                status=TestStatus.VULNERABLE,
                is_vulnerable=True,
            ),
            TestResult(test_case=test3, status=TestStatus.ERROR),
        ]

    def test_create_suite(self, sample_results):
        """Test creating a test suite."""
        suite = TestSuite(
            target_name="test-target",
            target_type="openai",
            results=sample_results,
        )
        assert suite.target_name == "test-target"
        assert suite.target_type == "openai"
        assert len(suite.results) == 3

    def test_suite_counts(self, sample_results):
        """Test suite counting properties."""
        suite = TestSuite(
            target_name="test-target",
            target_type="openai",
            results=sample_results,
        )
        assert suite.total_tests == 3
        assert suite.passed_count == 1
        assert suite.vulnerable_count == 1
        assert suite.failed_count == 1  # ERROR counts as failed

    def test_vulnerability_rate(self, sample_results):
        """Test vulnerability rate calculation."""
        suite = TestSuite(
            target_name="test-target",
            target_type="openai",
            results=sample_results,
        )
        # 1 vulnerable out of 3 = 0.333...
        assert abs(suite.vulnerability_rate - 1 / 3) < 0.01

    def test_empty_suite_vulnerability_rate(self):
        """Test vulnerability rate with no tests."""
        suite = TestSuite(
            target_name="test-target",
            target_type="openai",
        )
        assert suite.vulnerability_rate == 0.0

    def test_get_by_severity(self, sample_results):
        """Test filtering by severity."""
        suite = TestSuite(
            target_name="test-target",
            target_type="openai",
            results=sample_results,
        )
        # Only vulnerable results with matching severity
        high_vulns = suite.get_by_severity(Severity.HIGH)
        assert len(high_vulns) == 0  # The HIGH results aren't vulnerable

        medium_vulns = suite.get_by_severity(Severity.MEDIUM)
        assert len(medium_vulns) == 1

    def test_get_by_category(self, sample_results):
        """Test filtering by category."""
        suite = TestSuite(
            target_name="test-target",
            target_type="openai",
            results=sample_results,
        )
        cat1_results = suite.get_by_category("cat1")
        assert len(cat1_results) == 2

    def test_to_dict(self, sample_results):
        """Test serialization to dictionary."""
        suite = TestSuite(
            target_name="test-target",
            target_type="openai",
            results=sample_results,
        )
        suite.end_time = datetime.now()

        data = suite.to_dict()
        assert data["target_name"] == "test-target"
        assert data["target_type"] == "openai"
        assert "summary" in data
        assert data["summary"]["total"] == 3
        assert len(data["results"]) == 3
