"""
Pytest configuration and fixtures for system tests.
"""

import pytest

from src.tests.helpers.api_client import APIClient


def pytest_addoption(parser):
    """Add custom command-line options for pytest."""
    parser.addoption(
        "--base-url",
        action="store",
        default="http://localhost:8080",
        help="Base URL for the API Gateway",
    )
    parser.addoption(
        "--http-timeout",
        action="store",
        type=int,
        default=60,
        help="Default timeout for HTTP requests in seconds",
    )


@pytest.fixture(scope="session")
def base_url(request):
    """Provide base URL for tests."""
    return request.config.getoption("--base-url")


@pytest.fixture(scope="session")
def timeout(request):
    """Provide default timeout for HTTP requests."""
    return request.config.getoption("--http-timeout")


@pytest.fixture(scope="session")
def api_client(base_url, timeout):
    """Provide API client instance."""
    return APIClient(base_url=base_url, timeout=timeout)

