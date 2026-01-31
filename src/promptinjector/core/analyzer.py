"""Result analysis and reporting for prompt injection tests."""

import json
from datetime import datetime
from pathlib import Path

from .models import Severity, TestResult, TestStatus, TestSuite


class ResultAnalyzer:
    """Analyzes test results and generates reports."""

    def __init__(self, suite: TestSuite):
        """
        Initialize analyzer with a test suite.

        Args:
            suite: The test suite to analyze.
        """
        self.suite = suite

    def get_summary(self) -> dict:
        """Get a summary of test results."""
        vulnerabilities_by_severity = {s.value: 0 for s in Severity}
        vulnerabilities_by_category: dict[str, int] = {}

        for result in self.suite.results:
            if result.is_vulnerable:
                sev = result.test_case.severity.value
                vulnerabilities_by_severity[sev] += 1

                cat = result.test_case.category
                vulnerabilities_by_category[cat] = vulnerabilities_by_category.get(cat, 0) + 1

        return {
            "target": self.suite.target_name,
            "target_type": self.suite.target_type,
            "total_tests": self.suite.total_tests,
            "passed": self.suite.passed_count,
            "vulnerable": self.suite.vulnerable_count,
            "failed": self.suite.failed_count,
            "vulnerability_rate": f"{self.suite.vulnerability_rate:.1%}",
            "by_severity": vulnerabilities_by_severity,
            "by_category": vulnerabilities_by_category,
            "duration": self._calculate_duration(),
        }

    def _calculate_duration(self) -> str:
        """Calculate test duration as a formatted string."""
        if not self.suite.end_time:
            return "N/A"
        delta = self.suite.end_time - self.suite.start_time
        total_seconds = int(delta.total_seconds())
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes}m {seconds}s"

    def get_critical_findings(self) -> list[TestResult]:
        """Get all critical and high severity vulnerabilities."""
        return [
            r
            for r in self.suite.results
            if r.is_vulnerable and r.test_case.severity in (Severity.CRITICAL, Severity.HIGH)
        ]

    def get_findings_by_category(self) -> dict[str, list[TestResult]]:
        """Group vulnerable findings by category."""
        findings: dict[str, list[TestResult]] = {}
        for result in self.suite.results:
            if result.is_vulnerable:
                cat = result.test_case.category
                if cat not in findings:
                    findings[cat] = []
                findings[cat].append(result)
        return findings

    def export_json(self, filepath: str | Path) -> None:
        """Export results to JSON file."""
        filepath = Path(filepath)
        with open(filepath, "w") as f:
            json.dump(self.suite.to_dict(), f, indent=2)

    def export_markdown(self, filepath: str | Path) -> None:
        """Export results to Markdown report."""
        filepath = Path(filepath)
        summary = self.get_summary()

        lines = [
            f"# Prompt Injection Security Report",
            f"",
            f"**Target:** {self.suite.target_name}",
            f"**Type:** {self.suite.target_type}",
            f"**Date:** {self.suite.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Duration:** {summary['duration']}",
            f"",
            f"## Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Tests | {summary['total_tests']} |",
            f"| Passed | {summary['passed']} |",
            f"| Vulnerable | {summary['vulnerable']} |",
            f"| Failed/Error | {summary['failed']} |",
            f"| Vulnerability Rate | {summary['vulnerability_rate']} |",
            f"",
        ]

        # Severity breakdown
        lines.extend(
            [
                f"## Vulnerabilities by Severity",
                f"",
            ]
        )
        for sev in reversed(list(Severity)):
            count = summary["by_severity"][sev.value]
            emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "⚪"}.get(
                sev.value, ""
            )
            lines.append(f"- {emoji} **{sev.value.upper()}:** {count}")
        lines.append("")

        # Critical findings
        critical = self.get_critical_findings()
        if critical:
            lines.extend(
                [
                    f"## Critical/High Severity Findings",
                    f"",
                ]
            )
            for result in critical:
                lines.extend(
                    [
                        f"### {result.test_case.name}",
                        f"",
                        f"- **ID:** `{result.test_case.id}`",
                        f"- **Category:** {result.test_case.category}",
                        f"- **Severity:** {result.test_case.severity.value.upper()}",
                        f"- **Confidence:** {result.confidence:.0%}",
                        f"",
                        f"**Payload:**",
                        f"```",
                        result.test_case.payload[:500],
                        f"```",
                        f"",
                        f"**Response (truncated):**",
                        f"```",
                        result.response[:500] if result.response else "N/A",
                        f"```",
                        f"",
                    ]
                )

        # All findings by category
        findings = self.get_findings_by_category()
        if findings:
            lines.extend(
                [
                    f"## All Vulnerabilities by Category",
                    f"",
                ]
            )
            for cat, results in sorted(findings.items()):
                lines.append(f"### {cat.replace('_', ' ').title()}")
                lines.append("")
                for r in results:
                    lines.append(
                        f"- [{r.test_case.severity.value.upper()}] "
                        f"`{r.test_case.id}`: {r.test_case.name} "
                        f"(confidence: {r.confidence:.0%})"
                    )
                lines.append("")

        lines.extend(
            [
                f"---",
                f"*Generated by PromptInjector v0.1.0*",
            ]
        )

        with open(filepath, "w") as f:
            f.write("\n".join(lines))

    def print_summary(self) -> str:
        """Return a formatted summary string for terminal output."""
        summary = self.get_summary()

        lines = [
            "",
            "=" * 60,
            f" PROMPT INJECTION TEST RESULTS",
            "=" * 60,
            f" Target: {self.suite.target_name} ({self.suite.target_type})",
            f" Duration: {summary['duration']}",
            "-" * 60,
            f" Total Tests:      {summary['total_tests']:>5}",
            f" Passed:           {summary['passed']:>5}",
            f" Vulnerable:       {summary['vulnerable']:>5}",
            f" Errors:           {summary['failed']:>5}",
            f" Vulnerability Rate: {summary['vulnerability_rate']:>5}",
            "-" * 60,
            " VULNERABILITIES BY SEVERITY:",
        ]

        for sev in reversed(list(Severity)):
            count = summary["by_severity"][sev.value]
            bar = "█" * min(count, 20)
            lines.append(f"   {sev.value.upper():>8}: {count:>3} {bar}")

        if summary["by_category"]:
            lines.append("-" * 60)
            lines.append(" VULNERABILITIES BY CATEGORY:")
            for cat, count in sorted(summary["by_category"].items(), key=lambda x: -x[1]):
                lines.append(f"   {cat}: {count}")

        lines.append("=" * 60)

        return "\n".join(lines)
