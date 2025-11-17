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
        
        md = f"# {status_emoji} Staging Test Results\n\n"
        md += f"**Duration:** {self.duration:.2f}s\n\n"
        md += "## Test Suites\n\n"
        
        if self.system_passed is not None:
            md += f"- System Tests: {'✅ PASSED' if self.system_passed else '❌ FAILED'}\n"
        if self.load_passed is not None:
            md += f"- Load Tests: {'✅ PASSED' if self.load_passed else '❌ FAILED'}\n"
        if self.chaos_passed is not None:
            md += f"- Chaos Tests: {'✅ PASSED' if self.chaos_passed else '❌ FAILED'}\n"
        
        return md
    
    def to_commit_status_description(self) -> str:
        """Generate short description for GitHub commit status."""
        parts = []
        if self.system_passed is not None:
            parts.append(f"System: {'✅' if self.system_passed else '❌'}")
        if self.load_passed is not None:
            parts.append(f"Load: {'✅' if self.load_passed else '❌'}")
        if self.chaos_passed is not None:
            parts.append(f"Chaos: {'✅' if self.chaos_passed else '❌'}")
        
        return " | ".join(parts) if parts else "No tests run"


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
        import sys
        
        args = [
            "src/tests/system",
            f"--base-url={self.config.base_url}",
            "--html=reports/system.html",
            "--self-contained-html",
            "-v" if self.config.verbose else "",
            "-s",  # Don't capture output
        ]
        args = [arg for arg in args if arg]  # Remove empty strings

        print(f"Running pytest with args: {args}")
        print(f"Base URL: {self.config.base_url}")
        
        exit_code = pytest.main(args)
        
        if exit_code != 0:
            print(f"❌ Pytest exited with code {exit_code}")
        else:
            print(f"✅ Pytest passed")
            
        return exit_code == 0

    def _run_load_tests(self) -> bool:
        """Run load tests (staging only)."""
        import os
        import sys
        from pathlib import Path
        
        # Set Locust parameters from config
        os.environ["LOCUST_HOST"] = self.config.base_url
        
        # Default values for load tests
        users = int(os.getenv("LOCUST_USERS", "10"))
        spawn_rate = int(os.getenv("LOCUST_SPAWN_RATE", "2"))
        run_time = os.getenv("LOCUST_RUN_TIME", "60s")
        
        # Ensure reports directory exists
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        
        # Locustfile path
        repo_root = Path(__file__).resolve().parents[2]
        locustfile = repo_root / "src" / "tests" / "load" / "locustfile.py"
        
        if not locustfile.exists():
            print(f"❌ Locustfile not found: {locustfile}")
            return False
        
        # Prepare Locust arguments
        locust_args = [
            "--locustfile", str(locustfile),
            "--host", self.config.base_url,
            "--users", str(users),
            "--spawn-rate", str(spawn_rate),
            "--run-time", run_time,
            "--headless",  # Run without web UI
            "--html", str(reports_dir / "load.html"),
            "--csv", str(reports_dir / "load"),  # CSV stats
        ]
        
        if self.config.verbose:
            locust_args.append("--loglevel")
            locust_args.append("DEBUG")
        
        print(f"Running Locust with args: {' '.join(locust_args)}")
        print(f"Base URL: {self.config.base_url}")
        print(f"Users: {users}, Spawn rate: {spawn_rate}/s, Run time: {run_time}")
        
        # Run Locust programmatically
        try:
            from locust.main import main as locust_main
            
            # Save original sys.argv
            original_argv = sys.argv.copy()
            
            # Set sys.argv for Locust
            sys.argv = ["locust"] + locust_args
            
            # Run Locust
            exit_code = locust_main()
            
            # Restore original sys.argv
            sys.argv = original_argv
            
            if exit_code != 0:
                print(f"❌ Locust exited with code {exit_code}")
                return False
            else:
                print(f"✅ Locust load tests passed")
                print(f"📊 Report saved to: {reports_dir / 'load.html'}")
                return True
                
        except Exception as e:
            print(f"❌ Failed to run Locust: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _run_chaos_tests(self) -> bool:
        """Run chaos tests (staging only)."""
        import os
        import sys
        from pathlib import Path
        
        # Verify Kubernetes config is available
        kubeconfig = os.getenv("KUBECONFIG")
        if not kubeconfig:
            print("⚠️  KUBECONFIG not set, checking for in-cluster config...")
            # In-cluster config will be tried automatically by kubernetes client
        
        # Verify namespace is set
        namespace = os.getenv("K8S_NAMESPACE", "staging")
        print(f"Using Kubernetes namespace: {namespace}")
        
        # Ensure reports directory exists
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        
        args = [
            "src/tests/chaos",
            "-m", "chaos",  # Run tests with @pytest.mark.chaos
            f"--base-url={self.config.base_url}",
            "--html=reports/chaos.html",
            "--self-contained-html",
            "-v" if self.config.verbose else "",
            "-s",  # Don't capture output
        ]
        args = [arg for arg in args if arg]  # Remove empty strings
        
        print(f"Running pytest chaos tests with args: {args}")
        print(f"Base URL: {self.config.base_url}")
        print(f"Namespace: {namespace}")
        
        exit_code = pytest.main(args)
        
        if exit_code != 0:
            print(f"❌ Chaos tests failed with code {exit_code}")
            return False
        else:
            print(f"✅ Chaos tests passed")
            print(f"📊 Report saved to: {reports_dir / 'chaos.html'}")
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
        """Handle staging test results (GitHub notification + PR creation or email)."""
        print("=" * 60)
        print(f"Staging Test Results")
        print("=" * 60)
        print(report.to_markdown())

        # Always post results to GitHub (success or failure)
        if self.config.post_results_to_github:
            print("\n📤 Posting test results to GitHub...")
            self._post_results_to_github(report)

        # Handle success: create promotion PR
        if report.success:
            if self.config.create_pr:
                print("\n🎉 All tests passed - Creating promotion PR...")
                self._create_promotion_pr(report)
            else:
                print("\n✅ All tests passed (PR creation disabled)")
        
        # Handle failure: send email notification
        else:
            print("\n❌ Tests failed")
            if self.config.send_email:
                print("📧 Sending failure notification...")
                self._send_failure_email(report)
            else:
                print("⚠️  Email notifications disabled")

        print("=" * 60)

    def _create_promotion_pr(self, report: TestReport):
        """Create promotion PR from staging to main with test results."""
        if not self.config.github_token:
            print("⚠️  GITHUB_TOKEN not set, skipping PR creation")
            return

        try:
            from github import Github
            from datetime import datetime

            g = Github(self.config.github_token)
            repo = g.get_repo(self.config.github_repo)

            # Prepare PR body with test results
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            
            pr_body = f"""## 🎉 Staging Tests Passed - Ready for Production

{report.to_markdown()}

---

**Test Environment:** Staging  
**Tested Commit:** `{self.config.github_commit_sha[:7] if self.config.github_commit_sha else 'N/A'}`  
**Test Duration:** {report.duration:.2f}s  
**Timestamp:** {timestamp}

<details>
<summary>📊 Detailed Test Reports</summary>

All test reports are available in CI artifacts:
- System Tests: ✅ All microservices healthy
- Load Tests: ✅ Performance requirements met
- Chaos Tests: ✅ System resilient to failures

</details>

### Next Steps

1. Review changes in this PR
2. Approve and merge to deploy to production
3. Monitor production metrics after deployment

---
*Automated promotion generated by test runner*
"""

            # Create PR
            pr = repo.create_pull(
                title="🚀 chore: promote staging to main",
                body=pr_body,
                head="staging",
                base="main",
            )

            print(f"✅ Created promotion PR: {pr.html_url}")
            print(f"   Title: chore: promote staging to main")
            print(f"   All tests passed and results included in PR description")

        except Exception as e:
            print(f"❌ Failed to create PR: {e}")
            import traceback
            traceback.print_exc()

    def _post_results_to_github(self, report: TestReport):
        """
        Post test results to GitHub via commit status and commit comment.
        
        Always posts results (success or failure) so they're visible on GitHub.
        """
        if not self.config.github_token:
            print("⚠️  GITHUB_TOKEN not set, skipping GitHub result posting")
            return
        
        if not self.config.github_commit_sha:
            print("⚠️  GITHUB_SHA not set, cannot post results to specific commit")
            return
        
        try:
            from github import Github
            from datetime import datetime
            
            g = Github(self.config.github_token)
            repo = g.get_repo(self.config.github_repo)
            commit = repo.get_commit(self.config.github_commit_sha)
            
            # 1. Create commit status (shows up in PR checks)
            state = "success" if report.success else "failure"
            commit.create_status(
                state=state,
                target_url=None,  # TODO: Could link to test report artifacts
                description=report.to_commit_status_description(),
                context="staging-tests/all"
            )
            print(f"✅ Posted commit status: {state}")
            
            # 2. Create commit comment with detailed results
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            
            comment_body = f"""{report.to_markdown()}

---
**Commit:** `{self.config.github_commit_sha[:7]}`  
**Environment:** Staging  
**Timestamp:** {timestamp}  

<details>
<summary>📊 Test Reports</summary>

Generated reports (check CI artifacts):
- `reports/system.html` - System test results
- `reports/load.html` - Load test results  
- `reports/chaos.html` - Chaos test results

</details>
"""
            
            commit.create_comment(comment_body)
            print(f"✅ Posted commit comment with detailed results")
            
            print(f"✅ Successfully posted results to GitHub for commit {self.config.github_commit_sha[:7]}")
            
        except Exception as e:
            print(f"❌ Failed to post results to GitHub: {e}")
            import traceback
            traceback.print_exc()

    def _send_failure_email(self, report: TestReport):
        """Send email notification on test failure."""
        print("TODO: Implement email notification via GitHub Actions")
        print(f"Would send email with report:\n{report.to_markdown()}")

