"""Injection payload library management."""

import os
from enum import Enum
from pathlib import Path

import yaml

from ..core.models import Severity, TestCase


class InjectionCategory(Enum):
    """Categories of prompt injection attacks."""

    SYSTEM_PROMPT_EXTRACTION = "system_prompt_extraction"
    INSTRUCTION_OVERRIDE = "instruction_override"
    JAILBREAK = "jailbreak"
    ROLE_PLAY = "role_play"
    ENCODING_BYPASS = "encoding_bypass"
    CONTEXT_MANIPULATION = "context_manipulation"
    DELIMITER_ATTACK = "delimiter_attack"
    MULTI_TURN = "multi_turn"
    INDIRECT_INJECTION = "indirect_injection"


class InjectionLibrary:
    """Manages the library of injection test cases."""

    def __init__(self, custom_payloads_dir: str | None = None):
        """
        Initialize the injection library.

        Args:
            custom_payloads_dir: Optional path to additional payload files.
        """
        self._payloads_dir = Path(__file__).parent / "payloads"
        self._custom_dir = Path(custom_payloads_dir) if custom_payloads_dir else None
        self._test_cases: dict[str, TestCase] = {}
        self._loaded = False

    def load(self) -> None:
        """Load all payload files."""
        if self._loaded:
            return

        # Load built-in payloads
        self._load_from_directory(self._payloads_dir)

        # Load custom payloads if specified
        if self._custom_dir and self._custom_dir.exists():
            self._load_from_directory(self._custom_dir)

        self._loaded = True

    def _load_from_directory(self, directory: Path) -> None:
        """Load all YAML payload files from a directory."""
        if not directory.exists():
            return

        for yaml_file in directory.glob("*.yaml"):
            self._load_payload_file(yaml_file)

    def _load_payload_file(self, filepath: Path) -> None:
        """Load a single YAML payload file."""
        try:
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)

            if not data or "payloads" not in data:
                return

            category = data.get("category", "unknown")
            default_severity = data.get("default_severity", "medium")

            for payload_data in data["payloads"]:
                test_case = TestCase(
                    id=payload_data["id"],
                    name=payload_data["name"],
                    category=category,
                    payload=payload_data["payload"],
                    description=payload_data.get("description", ""),
                    severity=Severity(payload_data.get("severity", default_severity)),
                    detection_patterns=payload_data.get("detection_patterns", []),
                    tags=payload_data.get("tags", []),
                )
                self._test_cases[test_case.id] = test_case

        except Exception as e:
            print(f"Warning: Failed to load {filepath}: {e}")

    def get_all(self) -> list[TestCase]:
        """Get all test cases."""
        self.load()
        return list(self._test_cases.values())

    def get_by_category(self, category: str | InjectionCategory) -> list[TestCase]:
        """Get test cases by category."""
        self.load()
        if isinstance(category, InjectionCategory):
            category = category.value
        return [tc for tc in self._test_cases.values() if tc.category == category]

    def get_by_severity(self, severity: Severity) -> list[TestCase]:
        """Get test cases by severity level."""
        self.load()
        return [tc for tc in self._test_cases.values() if tc.severity == severity]

    def get_by_tags(self, tags: list[str]) -> list[TestCase]:
        """Get test cases that have any of the specified tags."""
        self.load()
        return [tc for tc in self._test_cases.values() if any(t in tc.tags for t in tags)]

    def get_by_id(self, test_id: str) -> TestCase | None:
        """Get a specific test case by ID."""
        self.load()
        return self._test_cases.get(test_id)

    def get_categories(self) -> list[str]:
        """Get list of available categories."""
        self.load()
        return list(set(tc.category for tc in self._test_cases.values()))

    def get_tags(self) -> list[str]:
        """Get list of all tags."""
        self.load()
        tags = set()
        for tc in self._test_cases.values():
            tags.update(tc.tags)
        return sorted(tags)

    @property
    def count(self) -> int:
        """Get total number of test cases."""
        self.load()
        return len(self._test_cases)

    def add_custom_payload(
        self,
        id: str,
        name: str,
        payload: str,
        category: str = "custom",
        severity: Severity = Severity.MEDIUM,
        description: str = "",
        detection_patterns: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> TestCase:
        """Add a custom payload at runtime."""
        test_case = TestCase(
            id=id,
            name=name,
            category=category,
            payload=payload,
            description=description,
            severity=severity,
            detection_patterns=detection_patterns or [],
            tags=tags or ["custom"],
        )
        self._test_cases[id] = test_case
        return test_case
