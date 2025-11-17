"""
Pytest configuration and fixtures for system tests.
"""

import pytest


def pytest_addoption(parser):
    """Add custom command-line options for pytest."""
    parser.addoption(
        "--base-url",
        action="store",
        default="http://localhost:8080",
        help="Base URL for the API Gateway",
    )


@pytest.fixture(scope="session")
def base_url(request):
    """Provide base URL for tests."""
    return request.config.getoption("--base-url")


@pytest.fixture(scope="session")
def services():
    """List of all services to test."""
    return [
        "access",
        "audit",
        "catalog",
        "customers",
        "inventory",
        "orders",
        "pricing",
        "sales-dashboard",
        "sites",
        "chatbot",
        "recommender",
        "auth-b2c",
        "auth-b2e",
    ]

