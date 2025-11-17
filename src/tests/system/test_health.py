"""
Health check tests for all Shopifake microservices.
Tests services through the API Gateway.
"""

import pytest
import requests


# Spring Boot services (use /actuator/health)
SPRING_BOOT_SERVICES = [
    "access",
    "audit",
    "catalog",
    "customers",
    "inventory",
    "orders",
    "pricing",
    "sales-dashboard",
    "sites",
]

# Python/FastAPI services (use /health)
PYTHON_SERVICES = [
    "chatbot",
    "recommender",
]

# Auth services (use /healthz)
AUTH_SERVICES = [
    "auth-b2c",
    "auth-b2e",
]


def test_gateway_health(base_url):
    """Test that the API Gateway is healthy."""
    response = requests.get(f"{base_url}/actuator/health", timeout=10)
    assert response.status_code == 200, f"Gateway unhealthy: {response.text}"
    
    data = response.json()
    assert data.get("status") == "UP", f"Gateway status is not UP: {data}"


@pytest.mark.parametrize("service", SPRING_BOOT_SERVICES)
def test_spring_boot_service_health(base_url, service):
    """Test health of Spring Boot microservices through gateway."""
    url = f"{base_url}/api/{service}/actuator/health"
    response = requests.get(url, timeout=10)
    
    assert response.status_code == 200, (
        f"{service} health check failed\n"
        f"URL: {url}\n"
        f"Status: {response.status_code}\n"
        f"Response: {response.text}"
    )
    
    data = response.json()
    assert data.get("status") == "UP", (
        f"{service} is not healthy\n"
        f"Status: {data.get('status')}\n"
        f"Details: {data}"
    )


@pytest.mark.parametrize("service", PYTHON_SERVICES)
def test_python_service_health(base_url, service):
    """Test health of Python/FastAPI microservices through gateway."""
    url = f"{base_url}/api/{service}/health"
    response = requests.get(url, timeout=10)
    
    assert response.status_code == 200, (
        f"{service} health check failed\n"
        f"URL: {url}\n"
        f"Status: {response.status_code}\n"
        f"Response: {response.text}"
    )


@pytest.mark.parametrize("service", AUTH_SERVICES)
def test_auth_service_health(base_url, service):
    """Test health of authentication services through gateway."""
    url = f"{base_url}/api/{service}/healthz"
    response = requests.get(url, timeout=10)
    
    assert response.status_code == 200, (
        f"{service} health check failed\n"
        f"URL: {url}\n"
        f"Status: {response.status_code}\n"
        f"Response: {response.text}"
    )

