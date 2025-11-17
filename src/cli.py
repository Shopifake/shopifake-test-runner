"""
CLI entry point for Shopifake Test Runner.
"""

import sys

import click

from src.config import TestConfig
from src.orchestrator import TestOrchestrator


@click.command()
@click.option(
    "--mode",
    type=click.Choice(["pr", "staging"], case_sensitive=False),
    required=True,
    help="Execution mode: pr (local docker-compose) or staging (deployed environment)",
)
@click.option(
    "--suite",
    type=click.Choice(["system", "load", "chaos", "all"], case_sensitive=False),
    default="system",
    help="Test suite to run",
)
@click.option(
    "--base-url",
    type=str,
    help="Override base URL for tests (optional)",
)
@click.option(
    "--timeout",
    type=int,
    help="Override default timeout in seconds (optional)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.version_option(version="1.0.0", prog_name="Shopifake Test Runner")
def main(mode: str, suite: str, base_url: str | None, timeout: int | None, verbose: bool):
    """Shopifake Test Runner - Execute system, load, and chaos tests."""
    click.echo("🚀 Starting Shopifake Test Runner")
    click.echo(f"   Mode: {mode.upper()}")
    click.echo(f"   Suite: {suite}")
    click.echo()

    # Load configuration
    config = TestConfig.from_mode(mode)
    
    # Override with CLI args if provided
    if base_url:
        config.base_url = base_url
    if timeout:
        config.timeout = timeout
    
    config.verbose = verbose

    # Create and run orchestrator
    orchestrator = TestOrchestrator(config)
    report = orchestrator.run(suite)

    # Exit with appropriate code
    sys.exit(0 if report.success else 1)


if __name__ == "__main__":
    main()
