"""Command-line interface for PromptInjector."""

import argparse
import asyncio
import sys
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.text import Text

from . import __version__
from .core.analyzer import ResultAnalyzer
from .core.models import Severity, TestStatus
from .core.runner import TestRunner
from .injections.library import InjectionLibrary, InjectionCategory
from .targets.openai_gpt import OpenAIGPTTarget
from .targets.google_gem import GoogleGemTarget

console = Console()


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="promptinjector",
        description="Security testing tool for prompt injection vulnerabilities in custom GPTs and Gems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test a custom GPT with a system prompt
  promptinjector test openai --system-prompt "You are a helpful cooking assistant"

  # Test a Google Gem
  promptinjector test google --system-instruction "You help with recipes"

  # Run only system prompt extraction tests
  promptinjector test openai --category system_prompt_extraction

  # Run high and critical severity tests only
  promptinjector test openai --min-severity high

  # List all available injection categories
  promptinjector list --categories

  # Export results to JSON
  promptinjector test openai --output results.json --format json
        """,
    )

    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Test command
    test_parser = subparsers.add_parser("test", help="Run prompt injection tests")
    test_subparsers = test_parser.add_subparsers(dest="target_type", help="Target type")

    # OpenAI target
    openai_parser = test_subparsers.add_parser("openai", help="Test OpenAI GPT")
    openai_parser.add_argument(
        "--api-key",
        help="OpenAI API key (or set OPENAI_API_KEY env var)",
    )
    openai_parser.add_argument(
        "--model",
        default="gpt-4",
        help="Model to use (default: gpt-4)",
    )
    openai_parser.add_argument(
        "--system-prompt",
        help="System prompt to test (simulates custom GPT instructions)",
    )
    openai_parser.add_argument(
        "--system-prompt-file",
        type=Path,
        help="File containing the system prompt",
    )
    openai_parser.add_argument(
        "--assistant-id",
        help="OpenAI Assistant ID to test directly",
    )
    openai_parser.add_argument(
        "--base-url",
        help="Custom base URL for API-compatible endpoints",
    )
    _add_common_test_args(openai_parser)

    # Google target
    google_parser = test_subparsers.add_parser("google", help="Test Google Gem")
    google_parser.add_argument(
        "--api-key",
        help="Google AI API key (or set GOOGLE_API_KEY env var)",
    )
    google_parser.add_argument(
        "--model",
        default="gemini-1.5-flash",
        help="Model to use (default: gemini-1.5-flash)",
    )
    google_parser.add_argument(
        "--system-instruction",
        help="System instruction to test (simulates custom Gem)",
    )
    google_parser.add_argument(
        "--system-instruction-file",
        type=Path,
        help="File containing the system instruction",
    )
    _add_common_test_args(google_parser)

    # List command
    list_parser = subparsers.add_parser("list", help="List available tests and categories")
    list_parser.add_argument(
        "--categories", action="store_true", help="List all injection categories"
    )
    list_parser.add_argument(
        "--tests", action="store_true", help="List all test cases"
    )
    list_parser.add_argument(
        "--tags", action="store_true", help="List all tags"
    )
    list_parser.add_argument(
        "--category", help="Filter tests by category when using --tests"
    )

    return parser


def _add_common_test_args(parser: argparse.ArgumentParser) -> None:
    """Add common arguments for test commands."""
    parser.add_argument(
        "--name",
        default="target",
        help="Name for this target (for reports)",
    )
    parser.add_argument(
        "-c", "--category",
        action="append",
        dest="categories",
        choices=[c.value for c in InjectionCategory],
        help="Filter by category (can be specified multiple times)",
    )
    parser.add_argument(
        "--min-severity",
        choices=["info", "low", "medium", "high", "critical"],
        default="info",
        help="Minimum severity level to test",
    )
    parser.add_argument(
        "-t", "--tag",
        action="append",
        dest="tags",
        help="Filter by tag (can be specified multiple times)",
    )
    parser.add_argument(
        "--test-id",
        action="append",
        dest="test_ids",
        help="Run specific test IDs only",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file for results",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["json", "markdown", "text"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between tests in seconds (default: 0.5)",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Don't reset conversation between tests",
    )
    parser.add_argument(
        "--custom-payloads",
        type=Path,
        help="Directory with custom payload YAML files",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Minimal output",
    )


async def run_tests(args: argparse.Namespace) -> int:
    """Execute tests against a target."""
    # Create target based on type
    if args.target_type == "openai":
        system_prompt = args.system_prompt
        if args.system_prompt_file:
            system_prompt = args.system_prompt_file.read_text()

        target = OpenAIGPTTarget(
            name=args.name,
            api_key=args.api_key,
            model=args.model,
            system_prompt=system_prompt,
            assistant_id=args.assistant_id,
            base_url=args.base_url,
        )
    elif args.target_type == "google":
        system_instruction = args.system_instruction
        if args.system_instruction_file:
            system_instruction = args.system_instruction_file.read_text()

        target = GoogleGemTarget(
            name=args.name,
            api_key=args.api_key,
            model=args.model,
            system_instruction=system_instruction,
        )
    else:
        console.print("[red]Error: Unknown target type[/red]")
        return 1

    if not target.is_configured():
        console.print(f"[red]Error: {args.target_type} target not configured.[/red]")
        console.print("Set the appropriate API key environment variable or use --api-key")
        return 1

    # Create library
    custom_dir = str(args.custom_payloads) if args.custom_payloads else None
    library = InjectionLibrary(custom_payloads_dir=custom_dir)
    library.load()

    # Create runner
    runner = TestRunner(
        target=target,
        library=library,
        reset_between_tests=not args.no_reset,
        delay_between_tests=args.delay,
    )

    # Determine tests to run
    severity = Severity(args.min_severity) if args.min_severity else None

    # Count total tests
    all_tests = library.get_all()
    if args.categories:
        all_tests = [t for t in all_tests if t.category in args.categories]
    if severity:
        severity_order = list(Severity)
        min_idx = severity_order.index(severity)
        all_tests = [t for t in all_tests if severity_order.index(t.severity) >= min_idx]
    if args.tags:
        all_tests = [t for t in all_tests if any(tag in t.tags for tag in args.tags)]
    if args.test_ids:
        all_tests = [t for t in all_tests if t.id in args.test_ids]

    total_tests = len(all_tests)

    if total_tests == 0:
        console.print("[yellow]No tests match the specified filters.[/yellow]")
        return 0

    if not args.quiet:
        console.print(Panel.fit(
            f"[bold]PromptInjector v{__version__}[/bold]\n"
            f"Target: {target.name} ({target.target_type})\n"
            f"Tests: {total_tests}",
            title="Starting Security Test",
        ))

    # Run tests with progress
    async with target:
        suite = await runner.run_all(
            categories=args.categories,
            severity=severity,
            tags=args.tags,
            test_ids=args.test_ids,
        )

    # Analyze and display results
    analyzer = ResultAnalyzer(suite)

    if not args.quiet:
        # Print summary
        console.print(analyzer.print_summary())

        # Show critical findings
        critical = analyzer.get_critical_findings()
        if critical:
            console.print("\n[bold red]CRITICAL/HIGH FINDINGS:[/bold red]")
            for result in critical[:5]:  # Show first 5
                console.print(f"  • [red]{result.test_case.id}[/red]: {result.test_case.name}")
                console.print(f"    Confidence: {result.confidence:.0%}")

    # Export results
    if args.output:
        if args.format == "json":
            analyzer.export_json(args.output)
        elif args.format == "markdown":
            analyzer.export_markdown(args.output)
        else:
            args.output.write_text(analyzer.print_summary())

        if not args.quiet:
            console.print(f"\n[green]Results saved to: {args.output}[/green]")

    # Return exit code based on vulnerabilities
    if suite.vulnerable_count > 0:
        return 2  # Vulnerabilities found
    return 0


def list_items(args: argparse.Namespace) -> int:
    """List available tests, categories, or tags."""
    library = InjectionLibrary()
    library.load()

    if args.categories:
        console.print("[bold]Available Injection Categories:[/bold]\n")
        table = Table(show_header=True)
        table.add_column("Category", style="cyan")
        table.add_column("Tests", justify="right")
        table.add_column("Description")

        category_descriptions = {
            "system_prompt_extraction": "Extract hidden system prompts",
            "instruction_override": "Override original instructions",
            "jailbreak": "Bypass safety guidelines",
            "role_play": "Persona-based manipulation",
            "encoding_bypass": "Encoding/obfuscation attacks",
            "context_manipulation": "Context injection attacks",
            "delimiter_attack": "Delimiter/boundary attacks",
            "indirect_injection": "External content injection",
        }

        for cat in sorted(library.get_categories()):
            count = len(library.get_by_category(cat))
            desc = category_descriptions.get(cat, "")
            table.add_row(cat, str(count), desc)

        console.print(table)
        console.print(f"\nTotal: {library.count} tests")

    elif args.tests:
        console.print("[bold]Available Test Cases:[/bold]\n")

        tests = library.get_all()
        if args.category:
            tests = [t for t in tests if t.category == args.category]

        table = Table(show_header=True)
        table.add_column("ID", style="cyan")
        table.add_column("Name")
        table.add_column("Category")
        table.add_column("Severity")
        table.add_column("Tags")

        severity_colors = {
            Severity.CRITICAL: "red",
            Severity.HIGH: "yellow",
            Severity.MEDIUM: "blue",
            Severity.LOW: "green",
            Severity.INFO: "dim",
        }

        for test in tests:
            sev_color = severity_colors.get(test.severity, "white")
            table.add_row(
                test.id,
                test.name[:40],
                test.category,
                Text(test.severity.value, style=sev_color),
                ", ".join(test.tags[:3]),
            )

        console.print(table)
        console.print(f"\nTotal: {len(tests)} tests")

    elif args.tags:
        console.print("[bold]Available Tags:[/bold]\n")
        tags = library.get_tags()
        for tag in tags:
            count = len(library.get_by_tags([tag]))
            console.print(f"  • {tag} ({count} tests)")

    else:
        console.print("Use --categories, --tests, or --tags to list items")
        return 1

    return 0


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "test":
            if not args.target_type:
                console.print("[red]Error: Specify target type (openai or google)[/red]")
                return 1
            return asyncio.run(run_tests(args))

        elif args.command == "list":
            return list_items(args)

    except KeyboardInterrupt:
        console.print("\n[yellow]Aborted by user[/yellow]")
        return 130
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
