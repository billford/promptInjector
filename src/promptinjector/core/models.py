"""Data models for prompt injection testing."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Severity(Enum):
    """Severity levels for injection vulnerabilities."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TestStatus(Enum):
    """Status of a test execution."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    VULNERABLE = "vulnerable"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class TestCase:
    """A single prompt injection test case."""

    id: str
    name: str
    category: str
    payload: str
    description: str = ""
    severity: Severity = Severity.MEDIUM
    detection_patterns: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.severity, str):
            self.severity = Severity(self.severity)


@dataclass
class TestResult:
    """Result of executing a single test case."""

    test_case: TestCase
    status: TestStatus
    response: str = ""
    is_vulnerable: bool = False
    confidence: float = 0.0
    matched_patterns: list[str] = field(default_factory=list)
    execution_time: float = 0.0
    error_message: str = ""
    raw_response: Any = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if isinstance(self.status, str):
            self.status = TestStatus(self.status)


@dataclass
class TestSuite:
    """A collection of test results from a testing session."""

    target_name: str
    target_type: str
    results: list[TestResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tests(self) -> int:
        return len(self.results)

    @property
    def vulnerable_count(self) -> int:
        return sum(1 for r in self.results if r.is_vulnerable)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.PASSED)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if r.status in (TestStatus.FAILED, TestStatus.ERROR))

    @property
    def vulnerability_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return self.vulnerable_count / self.total_tests

    def get_by_severity(self, severity: Severity) -> list[TestResult]:
        return [r for r in self.results if r.test_case.severity == severity and r.is_vulnerable]

    def get_by_category(self, category: str) -> list[TestResult]:
        return [r for r in self.results if r.test_case.category == category]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "target_name": self.target_name,
            "target_type": self.target_type,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "summary": {
                "total": self.total_tests,
                "vulnerable": self.vulnerable_count,
                "passed": self.passed_count,
                "failed": self.failed_count,
                "vulnerability_rate": f"{self.vulnerability_rate:.1%}",
            },
            "results": [
                {
                    "test_id": r.test_case.id,
                    "test_name": r.test_case.name,
                    "category": r.test_case.category,
                    "severity": r.test_case.severity.value,
                    "status": r.status.value,
                    "is_vulnerable": r.is_vulnerable,
                    "confidence": r.confidence,
                    "matched_patterns": r.matched_patterns,
                    "response_preview": r.response[:500] if r.response else "",
                    "execution_time": r.execution_time,
                    "error": r.error_message,
                }
                for r in self.results
            ],
            "metadata": self.metadata,
        }
