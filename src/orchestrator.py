"""
Test orchestrator - coordinates test execution and post-test actions.
"""

import time
from dataclasses import dataclass

import pytest

from src.config import TestConfig


@dataclass
class TestReport:
    """Test execution report."""

    success: bool
    duration: float
    system_passed: bool = False
    load_passed: bool = False
    chaos_passed: bool = False
    details: dict = None

    def to_markdown(self) -> str:
        """Generate markdown summary of test results."""
        status_emoji = "✅" if self.success else "❌"
        
        md = f"# {status_emoji} Test Results\n\n"
        md += f"**Duration:** {self.duration:.2f}s\n\n"
        md += "## Test Suites\n\n"
        
        if self.system_passed is not None:
            md += f"- System Tests: {'✅ PASSED' if self.system_passed else '❌ FAILED'}\n"
        if self.load_passed is not None:
            md += f"- Load Tests: {'✅ PASSED' if self.load_passed else '❌ FAILED'}\n"
        if self.chaos_passed is not None:
            md += f"- Chaos Tests: {'✅ PASSED' if self.chaos_passed else '❌ FAILED'}\n"
        
        return md


class TestOrchestrator:
    """Orchestrates test execution based on mode and suite."""

    def __init__(self, config: TestConfig):
        self.config = config
        self.results = {}

    def run(self, suite: str) -> TestReport:
        """Run test suite according to mode."""
        start_time = time.time()
        
        print(f"[{self.config.mode.upper()}] Running tests against {self.config.base_url}")
        print()

        # Run tests based on suite
        system_passed = None
        load_passed = None
        chaos_passed = None

        if suite in ["all", "system"]:
            print(f"[{self.config.mode.upper()}] Running system tests...")
            system_passed = self._run_system_tests()
            print()

        if suite in ["all", "load"] and self.config.mode == "staging":
            print("[STAGING] Running load tests...")
            load_passed = self._run_load_tests()
            print()

        if suite in ["all", "chaos"] and self.config.mode == "staging":
            print("[STAGING] Running chaos tests...")
            chaos_passed = self._run_chaos_tests()
            print()

        # Calculate overall success
        all_results = [r for r in [system_passed, load_passed, chaos_passed] if r is not None]
        success = all(all_results) if all_results else False

        duration = time.time() - start_time

        # Create report
        report = TestReport(
            success=success,
            duration=duration,
            system_passed=system_passed,
            load_passed=load_passed,
            chaos_passed=chaos_passed,
        )

        # Handle results based on mode
        if self.config.mode == "staging":
            self._handle_staging_results(report)
        elif self.config.mode == "pr":
            self._handle_pr_results(report)

        return report

    def _run_system_tests(self) -> bool:
        """Run pytest system tests."""
        args = [
            "src/tests/system",
            f"--base-url={self.config.base_url}",
            "--html=reports/system.html",
            "--self-contained-html",
            "-v" if self.config.verbose else "",
        ]
        args = [arg for arg in args if arg]  # Remove empty strings

        exit_code = pytest.main(args)
        return exit_code == 0

    def _run_load_tests(self) -> bool:
        """Run load tests (staging only)."""
        print("TODO: Implement load tests with Locust")
        return True

    def _run_chaos_tests(self) -> bool:
        """Run chaos tests (staging only)."""
        print("TODO: Implement chaos tests")
        return True

    def _handle_pr_results(self, report: TestReport):
        """Handle PR test results (simple output)."""
        print("=" * 60)
        print(f"PR Test Results")
        print("=" * 60)
        print(f"Status: {'✅ PASSED' if report.success else '❌ FAILED'}")
        print(f"Duration: {report.duration:.2f}s")
        print("=" * 60)

    def _handle_staging_results(self, report: TestReport):
        """Handle staging test results (PR creation + email)."""
        print("=" * 60)
        print(f"Staging Test Results")
        print("=" * 60)
        print(report.to_markdown())

        if report.success and self.config.create_pr:
            print("\n✅ All tests passed - Creating promotion PR...")
            self._create_promotion_pr(report)
        elif not report.success and self.config.send_email:
            print("\n❌ Tests failed - Sending notification...")
            self._send_failure_email(report)

        print("=" * 60)

    def _create_promotion_pr(self, report: TestReport):
        """Create promotion PR from staging to main."""
        if not self.config.github_token:
            print("⚠️  GITHUB_TOKEN not set, skipping PR creation")
            return

        try:
            from github import Github

            g = Github(self.config.github_token)
            repo = g.get_repo(self.config.github_repo)

            # Create PR
            pr = repo.create_pull(
                title="chore: promote staging to main",
                body=report.to_markdown(),
                head="staging",
                base="main",
            )

            print(f"✅ Created promotion PR: {pr.html_url}")

            # Add comment with test summary
            pr.create_issue_comment(report.to_markdown())

        except Exception as e:
            print(f"❌ Failed to create PR: {e}")

    def _send_failure_email(self, report: TestReport):
        """Send email notification on test failure."""
        print("TODO: Implement email notification via GitHub Actions")
        print(f"Would send email with report:\n{report.to_markdown()}")

